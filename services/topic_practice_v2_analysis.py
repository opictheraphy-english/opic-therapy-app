"""Short Gemini feedback for a single Topic Practice V2 answer (text transcript)."""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, Dict, List, Optional, Tuple

from services.api_retry_policy import GEMINI_JSON_FEEDBACK_MAX_OUTPUT_TOKENS
from services.evaluation.eval_config import build_topic_feedback_model_candidates
from services.gemini_json_client import run_gemini_json_model_chain
from services.stt_service import count_english_words
from services.topic_practice_v2_rubric import (
    RUBRIC_VERSION,
    build_topic_practice_v2_feedback_rubric,
)

logger = logging.getLogger(__name__)

GEMINI_REQUEST_TIMEOUT_SEC = 20
GEMINI_REQUEST_TIMEOUT_MS = GEMINI_REQUEST_TIMEOUT_SEC * 1000

_STUDENT_FEEDBACK_UNAVAILABLE = (
    "방금 답변은 안전하게 보관 중이에요. "
    "재녹음 없이 분석만 다시 받을 수 있어요."
)

_FALLBACK_UPGRADE_SAMPLE = (
    "이번엔 업그레이드 예시를 만들지 못했어요. "
    "「같은 질문 다시 말하기」로 한 번 더 시도해 보세요."
)

_QUOTED_PHRASE_RE = re.compile(r'["「]([^"」]+)["」]')
_REPLACEMENT_ARROW_RE = re.compile(
    r'["「\']([^"」\']+)["」\']\s*(?:→|->)\s*["「\']([^"」\']+)["」\']',
)
_ENGLISHISH_RE = re.compile(r"[A-Za-z]")
_LIGHT_TRANSCRIPT_SWAPS: Tuple[Tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\breally like\b", re.I), "really enjoy"),
    (re.compile(r"\bI like\b", re.I), "I enjoy"),
    (re.compile(r"\bI go\b", re.I), "I usually go"),
    (re.compile(r"\bvery much\b", re.I), "a lot"),
)
TOPIC_V2_KEYWORD_DRILL_EMPTY_MESSAGE = (
    "이번엔 추천 키워드를 만들지 못했어요. "
    "「같은 질문 다시 말하기」로 한 번 더 시도해 보세요."
)

_ALLOWED_ANSWER_LEVELS = frozenset(
    {"NL", "NM", "NH", "IL", "IM1", "IM2", "IM3", "IH", "AL"}
)

# Compact-key aliases after _normalize_level_token (spaces/hyphens stripped, upper).
_LEVEL_ALIASES: Dict[str, str] = {
    "IM": "IM2",
    "INTERMEDIATE": "IM2",
    "INTERMEDIATEMID": "IM2",
    "INTERMEDIATEMID1": "IM1",
    "INTERMEDIATEMID2": "IM2",
    "INTERMEDIATEMID3": "IM3",
    "INTERMEDIATELOW": "IL",
    "INTERMEDIATEHIGH": "IH",
    "ADVANCEDLOW": "AL",
    "ADVANCED": "AL",
    "NOVICELOW": "NL",
    "NOVICEMID": "NM",
    "NOVICEHIGH": "NH",
    "NOVICE": "NH",
}

_LEVEL_PHRASE_PATTERNS: Tuple[Tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"intermediate\s*mid(?:dle)?\s*3", re.I), "IM3"),
    (re.compile(r"intermediate\s*mid(?:dle)?\s*2", re.I), "IM2"),
    (re.compile(r"intermediate\s*mid(?:dle)?\s*1", re.I), "IM1"),
    (re.compile(r"intermediate\s*mid(?:dle)?", re.I), "IM2"),
    (re.compile(r"intermediate\s*high", re.I), "IH"),
    (re.compile(r"intermediate\s*low", re.I), "IL"),
    (re.compile(r"advanced\s*low", re.I), "AL"),
    (re.compile(r"novice\s*high", re.I), "NH"),
    (re.compile(r"novice\s*mid(?:dle)?", re.I), "NM"),
    (re.compile(r"novice\s*low", re.I), "NL"),
)

_LEVEL_TOKEN_RE = re.compile(
    r"(?<![A-Z0-9])(NL|NM|NH|IL|IM3|IM2|IM1|IM|IH|AL)(?![A-Z0-9])",
    re.I,
)

ANSWER_LEVEL_MISSING_LABEL = "등급 미표시"


def _failure(
    *,
    category: str,
    message: str,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "summary": "",
        "strength": "",
        "correction_focus": "",
        "better_expression": "",
        "upgrade_sample": "",
        "keyword_drill": [],
        "practice_mission": "",
        "answer_level": "",
        "answer_level_missing": False,
        "error_category": category,
        "error_message": message,
    }


def _ok_payload(
    summary: str,
    strength: str,
    correction_focus: str,
    better_expression: str,
    upgrade_sample: str,
    keyword_drill: List[str],
    practice_mission: str,
    answer_level: str = "",
    answer_level_missing: bool = False,
) -> Dict[str, Any]:
    return {
        "ok": True,
        "answer_level": answer_level,
        "answer_level_missing": bool(answer_level_missing),
        "summary": summary,
        "strength": strength,
        "correction_focus": correction_focus,
        "better_expression": better_expression,
        "upgrade_sample": upgrade_sample,
        "keyword_drill": list(keyword_drill),
        "practice_mission": practice_mission,
        "error_category": "",
        "error_message": "",
    }


def _coerce_str(val: Any) -> str:
    return str(val or "").strip()


def _normalize_level_token(raw: str) -> str:
    return re.sub(r"[\s\-_]+", "", str(raw or "").strip().upper())


def _extract_answer_level_token_from_text(text: str) -> str:
    """Find first OPIc level token in free text (summary etc.); no invented grades."""
    if not text:
        return ""
    for match in _LEVEL_TOKEN_RE.finditer(text):
        token = _normalize_level_token(match.group(1))
        if token == "IM":
            return "IM2"
        if token in _ALLOWED_ANSWER_LEVELS:
            return token
    return ""


def _coerce_answer_level(val: Any) -> str:
    raw = _coerce_str(val)
    if not raw:
        return ""
    compact = _normalize_level_token(raw)
    if compact in _ALLOWED_ANSWER_LEVELS:
        return compact
    alias = _LEVEL_ALIASES.get(compact)
    if alias:
        return alias
    for pattern, level in _LEVEL_PHRASE_PATTERNS:
        if pattern.search(raw):
            return level
    return _extract_answer_level_token_from_text(raw)


def _fallback_answer_level_from_feedback(norm: Dict[str, Any]) -> str:
    """Recover level only from model-produced feedback text fields."""
    for key in (
        "summary",
        "strength",
        "correction_focus",
        "better_expression",
        "practice_mission",
    ):
        found = _extract_answer_level_token_from_text(_coerce_str(norm.get(key)))
        if found:
            return found
    return ""


def _coerce_keyword_drill(val: Any) -> List[str]:
    if val is None:
        return []
    if isinstance(val, str):
        chunks = [x.strip() for x in val.replace(";", ",").split(",") if x.strip()]
        if len(chunks) <= 1 and val.strip():
            chunks = [x.strip() for x in val.split() if x.strip()]
        return chunks[:6]
    if isinstance(val, list):
        out: List[str] = []
        for x in val:
            s = _coerce_str(x)
            if s:
                out.append(s)
        return out[:6]
    return []


def _answer_transcript(answer: Dict[str, Any]) -> str:
    for key in ("transcript", "student_answer", "stt_transcript", "raw_transcript"):
        t = _coerce_str(answer.get(key))
        if t:
            return t
    return ""


def _speech_metrics_for_transcript(transcript: str, duration_seconds: float) -> Dict[str, Any]:
    from services.speech_rate_scoring import build_per_answer_speech_metrics, count_content_words

    try:
        dur = float(duration_seconds or 0.0)
    except (TypeError, ValueError):
        dur = 0.0
    content_wc = count_content_words(transcript)
    return build_per_answer_speech_metrics(content_wc, dur)


def _build_prompt(answer: Dict[str, Any], transcript: str) -> str:
    rubric = build_topic_practice_v2_feedback_rubric()
    q_en = _coerce_str(answer.get("en"))
    q_ko = _coerce_str(answer.get("ko"))
    topic = _coerce_str(answer.get("topic"))
    opic_type = _coerce_str(answer.get("opic_type"))
    try:
        dur = float(answer.get("duration_seconds") or 0.0)
    except (TypeError, ValueError):
        dur = 0.0
    speech = _speech_metrics_for_transcript(transcript, dur)
    payload = {
        "rubric_version": RUBRIC_VERSION,
        "topic": topic,
        "opic_type": opic_type,
        "question_en": q_en,
        "question_ko": q_ko,
        "transcript": transcript,
        "speech_rate_metrics": speech,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return rubric + "\n\nAnswer data JSON:\n" + body


def _normalize_success(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """Map model JSON to payload; missing new fields get safe defaults (backward compatible)."""
    drills = _coerce_keyword_drill(parsed.get("keyword_drill"))
    summary = _coerce_str(parsed.get("summary"))
    return _ok_payload(
        answer_level=_coerce_answer_level(parsed.get("answer_level")),
        summary=summary,
        strength=_coerce_str(parsed.get("strength")),
        correction_focus=_coerce_str(parsed.get("correction_focus")),
        better_expression=_coerce_str(parsed.get("better_expression")),
        upgrade_sample=_coerce_str(parsed.get("upgrade_sample")),
        keyword_drill=drills,
        practice_mission=_coerce_str(parsed.get("practice_mission")),
    )


def _topic_id_for_keyword_pool(answer: Dict[str, Any]) -> str:
    for key in ("topic", "topic_id"):
        val = _coerce_str(answer.get(key))
        if val:
            return val
    return ""


def _fallback_keyword_drill_from_topic(answer: Dict[str, Any]) -> List[str]:
    """Curriculum target expressions for this topic (not model-invented drill words)."""
    topic_id = _topic_id_for_keyword_pool(answer)
    if not topic_id:
        return []
    try:
        from data.keyword_constraint_sets import get_keyword_constraint_practice_set

        rows = get_keyword_constraint_practice_set(topic_id)
    except Exception:
        return []
    pool: List[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        for item in row.get("target_expressions") or []:
            if isinstance(item, dict):
                expr = _coerce_str(item.get("expr"))
            else:
                expr = _coerce_str(item)
            if expr and expr not in pool:
                pool.append(expr)
    if not pool:
        return []
    count = min(3, len(pool))
    if len(pool) <= count:
        return pool[:count]
    return random.sample(pool, count)


def _looks_englishish(text: str) -> bool:
    raw = _coerce_str(text)
    if not raw:
        return False
    letters = len(_ENGLISHISH_RE.findall(raw))
    return letters >= max(3, len(raw) // 3)


def _extract_quoted_phrases(text: str) -> List[str]:
    out: List[str] = []
    for match in _QUOTED_PHRASE_RE.finditer(text or ""):
        phrase = _coerce_str(match.group(1))
        if phrase and _looks_englishish(phrase) and phrase not in out:
            out.append(phrase)
    return out


def _extract_replacement_pairs(text: str) -> List[Tuple[str, str]]:
    pairs: List[Tuple[str, str]] = []
    for match in _REPLACEMENT_ARROW_RE.finditer(text or ""):
        old = _coerce_str(match.group(1))
        new = _coerce_str(match.group(2))
        if old and new and _looks_englishish(old) and _looks_englishish(new):
            pairs.append((old, new))
    return pairs


def _replace_phrase_ci(text: str, old: str, new: str) -> str:
    if not text or not old:
        return text
    pattern = re.compile(re.escape(old), re.I)
    return pattern.sub(new, text, count=1)


def _split_transcript_sentences(text: str) -> List[str]:
    raw = re.sub(r"\s+", " ", (text or "").strip())
    if not raw:
        return []
    parts = re.split(r"(?<=[.!?])\s+", raw)
    return [p.strip() for p in parts if p.strip()]


def _polish_transcript_light(text: str) -> str:
    out = re.sub(r"\s+", " ", (text or "").strip())
    for pattern, repl in _LIGHT_TRANSCRIPT_SWAPS:
        out = pattern.sub(repl, out)
    return out.strip()


def _upgrade_sample_from_transcript(text: str, *, max_sentences: int = 4) -> str:
    polished = _polish_transcript_light(text)
    sentences = _split_transcript_sentences(polished)
    if not sentences:
        return polished
    return " ".join(sentences[:max_sentences]).strip()


def _fallback_upgrade_sample_from_answer(
    answer: Dict[str, Any],
    norm: Dict[str, Any],
) -> str:
    """Build a substantive English upgrade sample when the model omits the field."""
    transcript = _answer_transcript(answer)
    correction = _coerce_str(norm.get("correction_focus"))
    better = _coerce_str(norm.get("better_expression"))

    pairs: List[Tuple[str, str]] = []
    for field in (correction, better):
        pairs.extend(_extract_replacement_pairs(field))

    if transcript:
        upgraded = transcript
        for old, new in pairs:
            upgraded = _replace_phrase_ci(upgraded, old, new)
        upgraded = _polish_transcript_light(upgraded)
        sample = _upgrade_sample_from_transcript(upgraded)
        if sample and count_english_words(sample) >= 3:
            if sample != transcript or pairs:
                return sample
            if count_english_words(sample) >= 5:
                return sample

    english_quotes: List[str] = []
    for field in (better, correction):
        for phrase in _extract_quoted_phrases(field):
            if phrase not in english_quotes:
                english_quotes.append(phrase)

    if transcript and english_quotes:
        base_sents = _split_transcript_sentences(_polish_transcript_light(transcript))
        lead = base_sents[0] if base_sents else _polish_transcript_light(transcript)
        alt = english_quotes[-1]
        if alt.lower() not in lead.lower():
            if lead.endswith((".", "!", "?")):
                return f"{lead} For example, {alt}."
            return f"{lead}. For example, {alt}."
        if len(english_quotes) >= 2:
            return f"{english_quotes[0]} {english_quotes[1]}."
        return english_quotes[0]

    if english_quotes:
        return " ".join(english_quotes[:2]).strip()

    if transcript:
        sample = _upgrade_sample_from_transcript(transcript)
        if sample and count_english_words(sample) >= 3:
            return sample

    hint = better or correction
    if hint:
        return (
            "Try saying your answer again with this in mind: "
            f"{hint[:180].rstrip()}…"
            if len(hint) > 180
            else f"Try saying your answer again with this in mind: {hint}"
        )

    return _FALLBACK_UPGRADE_SAMPLE


def _apply_ok_field_fallbacks(norm: Dict[str, Any], answer: Dict[str, Any]) -> None:
    """Fill missing optional coaching fields after a successful model parse."""
    if not norm.get("summary"):
        norm["summary"] = "짧은 피드백이 생성되었어요. 아래 항목을 함께 확인해 주세요."
    if not norm.get("strength"):
        norm["strength"] = "요약에서 전체 흐름을 참고해 주세요."
    if not norm.get("correction_focus"):
        norm["correction_focus"] = (
            "다음에는 핵심부터 한 문장으로 시작하고, 이유나 예를 한 가지 더 붙여 보세요."
        )
    if not norm.get("better_expression"):
        norm["better_expression"] = (
            "위 ‘바로 고칠 점’을 반영해 같은 내용을 한 번 더 자연스럽게 말해 보세요."
        )
    if not _coerce_str(norm.get("upgrade_sample")):
        norm["upgrade_sample"] = _fallback_upgrade_sample_from_answer(answer, norm)
    if not norm.get("practice_mission"):
        norm["practice_mission"] = (
            "같은 질문에 첫 문장만 바꿔서 20초 안팎으로 다시 말해 보세요."
        )
    drills = _coerce_keyword_drill(norm.get("keyword_drill"))
    if not drills:
        drills = _fallback_keyword_drill_from_topic(answer)
    norm["keyword_drill"] = drills

    level = _coerce_str(norm.get("answer_level"))
    if not level:
        recovered = _fallback_answer_level_from_feedback(norm)
        if recovered:
            norm["answer_level"] = recovered
            norm["answer_level_missing"] = False
        else:
            norm["answer_level"] = ""
            norm["answer_level_missing"] = True
    else:
        norm["answer_level"] = _coerce_answer_level(level)
        norm["answer_level_missing"] = not bool(norm["answer_level"])


def analyze_topic_practice_v2_answer(answer: dict) -> dict:
    """
    Try each feedback model once; skip unavailable (404) models immediately.

    Returns dict matching the Topic V2 feedback schema; ``ok`` is a bool.
    """
    if not isinstance(answer, dict):
        return _stringify_result(_failure(category="invalid_input", message="answer_must_be_dict"))

    transcript = _answer_transcript(answer)
    wc = count_english_words(transcript)
    if wc < 5:
        return _stringify_result(
            _failure(
                category="insufficient_text",
                message="답변 텍스트가 너무 짧거나 비어 있어요. 영어로 몇 문장 이상 적어 주세요.",
            )
        )

    from utils.secrets import get_gemini_api_key

    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        return _stringify_result(
            _failure(
                category="api_key",
                message="API 키가 없습니다. 설정에서 키를 확인해 주세요.",
            )
        )

    prompt = _build_prompt(answer, transcript)
    models = build_topic_feedback_model_candidates()

    def _log_attempt(model_name: str, attempt_no: int) -> None:
        try:
            logger.info(
                "[TOPIC_V2_FEEDBACK] model=%s attempt=%s transcript_words=%s",
                model_name,
                attempt_no,
                wc,
            )
        except Exception:
            pass

    parsed, err = run_gemini_json_model_chain(
        api_key=api_key,
        prompt=prompt,
        models=models,
        temperature=0.2,
        max_output_tokens=GEMINI_JSON_FEEDBACK_MAX_OUTPUT_TOKENS,
        timeout_ms=GEMINI_REQUEST_TIMEOUT_MS,
        log_tag="TOPIC_V2_FEEDBACK",
        on_attempt=_log_attempt,
    )
    if parsed:
        norm = _normalize_success(parsed)
        _apply_ok_field_fallbacks(norm, answer)
        try:
            level = _coerce_str(norm.get("answer_level")) or "—"
            missing = bool(norm.get("answer_level_missing"))
            logger.info(
                "[TOPIC_V2_FEEDBACK] success answer_level=%s missing=%s",
                level,
                missing,
            )
        except Exception:
            pass
        return _stringify_result(norm)

    try:
        logger.warning("[TOPIC_V2_FEEDBACK] model_chain_failed err=%s", err)
    except Exception:
        pass
    final_cat = "model_not_found" if err == "model_not_found" else "api_error"
    return _stringify_result(
        _failure(
            category=final_cat,
            message=_STUDENT_FEEDBACK_UNAVAILABLE,
        )
    )


def _stringify_result(d: Dict[str, Any]) -> dict:
    """Normalize to required schema (expanded + backward compatible keys)."""
    ok_raw = d.get("ok")
    if isinstance(ok_raw, bool):
        ok = ok_raw
    else:
        ok = str(ok_raw).lower() in ("true", "1", "yes")

    raw_drill = d.get("keyword_drill")
    drill_list = _coerce_keyword_drill(raw_drill)

    missing_raw = d.get("answer_level_missing")
    if isinstance(missing_raw, bool):
        answer_level_missing = missing_raw
    else:
        answer_level_missing = str(missing_raw).lower() in ("true", "1", "yes")

    return {
        "ok": ok,
        "answer_level": _coerce_answer_level(d.get("answer_level")),
        "answer_level_missing": answer_level_missing,
        "summary": _coerce_str(d.get("summary")),
        "strength": _coerce_str(d.get("strength")),
        "correction_focus": _coerce_str(d.get("correction_focus")),
        "better_expression": _coerce_str(d.get("better_expression")),
        "upgrade_sample": _coerce_str(d.get("upgrade_sample")),
        "keyword_drill": drill_list,
        "practice_mission": _coerce_str(d.get("practice_mission")),
        "error_category": _coerce_str(d.get("error_category")),
        "error_message": _coerce_str(d.get("error_message")),
    }
