"""Short Gemini feedback for a single Topic Practice V2 answer (text transcript)."""

from __future__ import annotations

import json
import logging
import random
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
TOPIC_V2_KEYWORD_DRILL_EMPTY_MESSAGE = (
    "이번엔 추천 키워드를 만들지 못했어요. "
    "「같은 질문 다시 말하기」로 한 번 더 시도해 보세요."
)

_ALLOWED_ANSWER_LEVELS = frozenset(
    {"NL", "NM", "NH", "IL", "IM1", "IM2", "IM3", "IH", "AL"}
)


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
) -> Dict[str, Any]:
    return {
        "ok": True,
        "answer_level": answer_level,
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


def _coerce_answer_level(val: Any) -> str:
    raw = _coerce_str(val).upper().replace(" ", "")
    if raw in _ALLOWED_ANSWER_LEVELS:
        return raw
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
        norm["upgrade_sample"] = _FALLBACK_UPGRADE_SAMPLE
    if not norm.get("practice_mission"):
        norm["practice_mission"] = (
            "같은 질문에 첫 문장만 바꿔서 20초 안팎으로 다시 말해 보세요."
        )
    drills = _coerce_keyword_drill(norm.get("keyword_drill"))
    if not drills:
        drills = _fallback_keyword_drill_from_topic(answer)
    norm["keyword_drill"] = drills


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
            logger.info("[TOPIC_V2_FEEDBACK] success")
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

    return {
        "ok": ok,
        "answer_level": _coerce_answer_level(d.get("answer_level")),
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
