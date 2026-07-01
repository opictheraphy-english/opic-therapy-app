"""Gemini diagnostic report for Mini Mock V2 — transcript text only, no raw audio."""

from __future__ import annotations

import concurrent.futures
import json
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from services.api_retry_policy import (
    REPORT_MAX_ATTEMPTS,
    REPORT_RETRY_DELAYS_SEC,
)
from services.evaluation.eval_config import (
    MINI_REPORT_MODEL_NAME,
    build_mini_mock_v2_report_model_candidates,
)
from services.gemini_json_client import run_report_json_model_chain
from services.evaluation.eval_text import (
    count_sentences_punctuation_only,
    count_spoken_units,
    filler_hits,
)
from services.mini_mock_v2_level_rules import (
    LEVEL_RULE_VERSION,
    MINI_MOCK_V2_CONNECTOR_MARKERS,
)
from services.speech_rate_scoring import (
    apply_speech_rate_to_report,
    build_per_answer_speech_metrics,
    count_content_words,
)
from services.mini_mock_v2_rubric import (
    RUBRIC_VERSION,
    build_mini_mock_v2_light_rubric_prompt,
)
from services.stt_service import count_english_words

logger = logging.getLogger(__name__)

# HTTP deadline for a single generate_content call (google.genai HttpOptions.timeout = ms).
GEMINI_REQUEST_TIMEOUT_SEC = 45
GEMINI_REQUEST_TIMEOUT_MS = GEMINI_REQUEST_TIMEOUT_SEC * 1000
# Outer thread-pool deadline (prompt build + JSON parse margin over HTTP timeout).
# 55s: Wi-Fi OpenAI primary (~25s) + Gemini fallback (up to 45s HTTP) needs headroom.
ANALYSIS_WRAPPER_TIMEOUT_SEC = 55
MIN_USABLE_WORDS = 5
REPORT_MAX_ANSWER_WORDS = 180

_SCORE_KEYS = (
    "response_amount",
    "relevance",
    "structure",
    "grammar",
    "vocabulary",
    "naturalness",
)


def _empty_score_breakdown() -> Dict[str, int]:
    return {k: 0 for k in _SCORE_KEYS}


def _student_answer_text(row: Dict[str, Any]) -> str:
    for key in (
        "student_answer",
        "transcript",
        "raw_transcript",
        "placeholder_text",
        "stt_transcript",
    ):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return ""


def _question_type_kind(question_type: str, question_text: str) -> str:
    """Map saved labels to rubric bucket (description / experience / roleplay / general)."""
    t = (question_type or "").lower()
    q = (question_text or "").lower()
    if "roleplay" in t or "롤플레" in t or "role play" in t:
        return "roleplay"
    if "experience" in t or "memorable" in t or "기억" in t or "경험" in t:
        return "experience"
    if "description" in t or "묘사" in t or "describe" in t:
        return "description"
    if ("ask me" in q or "ask you" in q) and "question" in q:
        return "roleplay"
    if "tell me about" in q and "experience" in q:
        return "experience"
    if "tell me about" in q and ("place" in q or "often go" in q):
        return "description"
    return "general"


def _row_analysis_status(row: Dict[str, Any], text: str) -> str:
    """Whether a saved row is sent to Gemini — usable text only, not STT/recording failure.

    A question echo (reading the prompt back) is treated as a non-answer even
    when its word count clears MIN_USABLE_WORDS — its length must never feed the
    level (see RELEVANCE_GATE in the shared level rules).
    """
    row_status = str(row.get("status") or "").strip()
    if row_status in ("stt_failed", "recording_failed"):
        return "insufficient_response"
    if count_english_words(text) < MIN_USABLE_WORDS:
        return "insufficient_response"
    if _question_echo_signal(text, str(row.get("question_text") or "")).get("question_echo"):
        return "insufficient_response"
    return "saved"


def _log_v2_analysis_input(
    answers: List[Dict[str, Any]],
    inputs: List[Dict[str, Any]],
    payload: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Per-answer lengths before Gemini; full text only when show_dev_debug."""
    show_full = False
    try:
        import streamlit as st

        show_full = bool(st.session_state.get("show_dev_debug"))
    except Exception:
        pass
    try:
        for row in sorted(
            [a for a in answers if isinstance(a, dict)],
            key=lambda x: int(x.get("question_index") or 0),
        ):
            q_idx = int(row.get("question_index") or 0)
            q_display = q_idx + 1
            transcript = str(row.get("transcript") or "")
            raw_transcript = str(row.get("raw_transcript") or "")
            student_answer = str(row.get("student_answer") or "")
            answer_text = str(row.get("answer_text") or "")
            audio_bytes = row.get("audio_bytes")
            audio_len = 0
            try:
                audio_len = int(row.get("audio_len") or 0)
            except (TypeError, ValueError):
                audio_len = 0
            if audio_len <= 0 and audio_bytes is not None:
                try:
                    audio_len = len(audio_bytes)
                except Exception:
                    audio_len = 0
            resolved = _student_answer_text(row)
            resolved_wc = count_english_words(resolved)
            input_status = (
                "saved" if resolved_wc >= MIN_USABLE_WORDS else "insufficient_response"
            )
            wpm_available = bool(row.get("wpm_available"))
            try:
                wpm = float(row.get("wpm") or 0.0)
            except (TypeError, ValueError):
                wpm = 0.0
            if not wpm_available:
                wpm = 0.0
            logger.info(
                "[MINI_V2_ANALYSIS_INPUT] q=%s input_status=%s student_answer_len=%s "
                "transcript_len=%s raw_transcript_len=%s answer_text_len=%s "
                "audio_len=%s audio_saved=%s resolved_text_len=%s word_count=%s "
                "wpm=%s wpm_available=%s row_status=%s",
                q_display,
                input_status,
                len(student_answer),
                len(transcript),
                len(raw_transcript),
                len(answer_text),
                audio_len,
                row.get("audio_saved"),
                len(resolved),
                resolved_wc,
                wpm,
                wpm_available,
                row.get("status"),
            )
            if show_full and resolved:
                logger.debug(
                    "[MINI_V2_ANALYSIS_INPUT] q=%s resolved_text_preview=%s",
                    q_display,
                    resolved[:500],
                )
        for item in payload or []:
            logger.info(
                "[MINI_V2_ANALYSIS_INPUT] gemini_payload q=%s question_type=%s "
                "question_text_len=%s student_answer_len=%s word_count=%s wpm=%s "
                "wpm_available=%s",
                item.get("question_index"),
                item.get("question_type"),
                len(str(item.get("question_text") or "")),
                len(str(item.get("student_answer") or "")),
                item.get("word_count"),
                item.get("wpm"),
                item.get("wpm_available"),
            )
    except Exception:
        logger.debug("[MINI_V2_ANALYSIS_INPUT] log_failed", exc_info=True)


def _sentence_count_for_report(text: str) -> int:
    if not (text or "").strip():
        return 0
    punct = count_sentences_punctuation_only(text)
    units = count_spoken_units(text)
    return max(punct, units)


def _connector_count(lower: str) -> int:
    return sum(1 for marker in MINI_MOCK_V2_CONNECTOR_MARKERS if marker in lower)


def _repetition_hint(text: str) -> str:
    words = re.findall(r"[a-zA-Z']+", (text or "").lower())
    if len(words) < 8:
        return "low"
    unique = len(set(words))
    ratio = unique / len(words)
    if ratio < 0.45:
        return "high_repetition"
    if ratio < 0.6:
        return "moderate_repetition"
    return "low"


# Function words ignored when comparing an answer to its question prompt: they
# overlap trivially even for genuine answers, so they would inflate the echo
# ratio. Keeping question stems (tell/describe/what/how/...) here means a real
# answer's CONTENT words must overlap the question for it to count as an echo.
_ECHO_STOPWORDS = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "so", "to", "of", "in", "on", "at",
        "for", "with", "about", "is", "are", "am", "was", "were", "be", "been",
        "do", "does", "did", "can", "could", "would", "will", "should", "i",
        "you", "me", "my", "your", "we", "it", "this", "that", "these", "those",
        "what", "how", "when", "where", "why", "who", "which", "please", "tell",
        "describe", "talk", "give", "let", "some", "any", "as", "like",
    }
)

# Echo thresholds: a verbatim "read the question back" answer scores overlap ~1.0
# with ~0 novel content words. Genuine answers reuse a few keywords but add new
# content, so they stay well under these limits.
_ECHO_OVERLAP_MIN = 0.8
_ECHO_NOVEL_MAX = 3


def _content_tokens(text: str) -> List[str]:
    return [
        w
        for w in re.findall(r"[a-zA-Z']+", (text or "").lower())
        if w not in _ECHO_STOPWORDS and len(w) > 1
    ]


def _question_echo_signal(answer_text: str, question_text: str) -> Dict[str, Any]:
    """Detect 'reading the question back' (parroting) deterministically.

    Returns overlap ratio (share of answer content words also in the question),
    count of novel content words (answer words not in the question), and an
    is_echo flag. Conservative thresholds so genuine answers that merely reuse a
    few question keywords are NOT flagged.
    """
    ans_tokens = _content_tokens(answer_text)
    q_tokens = set(_content_tokens(question_text))
    if not ans_tokens or not q_tokens:
        return {"question_echo": False, "question_overlap_ratio": 0.0, "novel_word_count": len(ans_tokens)}
    novel = [w for w in ans_tokens if w not in q_tokens]
    overlap_ratio = round(1.0 - (len(novel) / len(ans_tokens)), 3)
    novel_distinct = len(set(novel))
    is_echo = overlap_ratio >= _ECHO_OVERLAP_MIN and novel_distinct <= _ECHO_NOVEL_MAX
    return {
        "question_echo": is_echo,
        "question_overlap_ratio": overlap_ratio,
        "novel_word_count": novel_distinct,
    }


def _per_answer_fluency_metrics(text: str) -> Dict[str, Any]:
    lower = (text or "").lower()
    return {
        "sentence_count": _sentence_count_for_report(text),
        "filler_hits": filler_hits(lower),
        "connector_count": _connector_count(lower),
        "repetition_hint": _repetition_hint(text),
    }


def _roleplay_answer_status(
    answers: List[Dict[str, Any]],
    *,
    saved_count: int,
) -> str:
    """Q3 roleplay row status for aggregate metrics (input only)."""
    rows = sorted(
        [a for a in answers if isinstance(a, dict)],
        key=lambda x: int(x.get("question_index") or 0),
    )
    q3_row: Optional[Dict[str, Any]] = None
    for row in rows:
        q_idx = int(row.get("question_index") or 0)
        if q_idx == 2:
            q3_row = row
            break
    if q3_row is None and len(rows) >= 3:
        q3_row = rows[2]
    if q3_row is None:
        return "missing"
    q_type = str(q3_row.get("question_type") or "")
    q_text = str(q3_row.get("question_text") or "")
    kind = _question_type_kind(q_type, q_text)
    if kind != "roleplay":
        return "not_roleplay"
    text = _student_answer_text(q3_row)
    status = _row_analysis_status(q3_row, text)
    if status == "saved":
        return "saved"
    if saved_count == 0:
        return "insufficient_response"
    return "insufficient_response"


def build_mini_mock_v2_aggregate_metrics(
    answers: List[Dict[str, Any]],
    payload: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Cross-question metrics for Gemini input only."""
    total_word_count = 0
    total_sentence_count = 0
    total_duration_seconds = 0.0
    wpm_values: List[float] = []
    wpm_available_any = False
    saved_answer_count = 0

    for item in payload:
        wc = int(item.get("word_count") or 0)
        sc = int(item.get("sentence_count") or 0)
        total_word_count += wc
        total_sentence_count += sc
        if item.get("student_answer"):
            saved_answer_count += 1
        try:
            total_duration_seconds += float(item.get("duration_seconds") or 0.0)
        except (TypeError, ValueError):
            pass
        if item.get("wpm_available"):
            wpm_available_any = True
            try:
                wpm_values.append(float(item.get("wpm") or 0.0))
            except (TypeError, ValueError):
                pass

    average_wpm = 0.0
    if wpm_available_any and wpm_values:
        average_wpm = round(sum(wpm_values) / len(wpm_values), 1)

    roleplay_status = _roleplay_answer_status(answers, saved_count=saved_answer_count)

    from services.speech_rate_scoring import build_exam_aggregate_speech_metrics

    speech = build_exam_aggregate_speech_metrics(payload)
    speech["level_rule_version"] = LEVEL_RULE_VERSION
    speech["total_sentence_count"] = total_sentence_count
    speech["question_count"] = len(payload)
    speech["saved_answer_count"] = saved_answer_count
    speech["roleplay_answer_status"] = roleplay_status
    if average_wpm > 0:
        speech["average_wpm"] = average_wpm
    speech["wpm_available"] = bool(speech.get("wpm_available") or wpm_available_any)
    return speech


def _log_aggregate_metrics(metrics: Dict[str, Any]) -> None:
    try:
        logger.info(
            "[MINI_V2_AGG_METRICS] total_word_count=%s total_sentence_count=%s "
            "total_duration_seconds=%s average_wpm=%s roleplay_status=%s",
            metrics.get("total_word_count"),
            metrics.get("total_sentence_count"),
            metrics.get("total_duration_seconds"),
            metrics.get("average_wpm"),
            metrics.get("roleplay_answer_status"),
        )
    except Exception:
        pass


def build_mini_mock_v2_gemini_report_input(
    answers: List[Dict[str, Any]],
    payload: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Gemini request body: aggregate metrics + per-answer payload."""
    answer_payload = payload if payload is not None else build_mini_mock_v2_report_payload(answers)
    aggregate = build_mini_mock_v2_aggregate_metrics(answers, answer_payload)
    _log_aggregate_metrics(aggregate)
    return {"aggregate_metrics": aggregate, "answers": answer_payload}


def _truncate_answer_for_report(text: str, max_words: int = REPORT_MAX_ANSWER_WORDS) -> str:
    """Truncate copy sent to Gemini only — does not mutate stored answers."""
    raw = (text or "").strip()
    if not raw:
        return ""
    words = re.findall(r"[a-zA-Z']+", raw)
    if len(words) <= max_words:
        return raw
    return " ".join(words[:max_words])


def build_mini_mock_v2_analysis_inputs(answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Internal status + metrics per answer (logging / usable filter)."""
    items: List[Dict[str, Any]] = []
    for row in sorted(
        [a for a in answers if isinstance(a, dict)],
        key=lambda x: int(x.get("question_index") or 0),
    ):
        resolved_text = _student_answer_text(row)
        word_count = count_english_words(resolved_text)
        status = _row_analysis_status(row, resolved_text)
        q_idx = int(row.get("question_index") or 0)
        items.append(
            {
                "question_index": q_idx + 1,
                "status": status,
                "word_count": word_count,
                "student_answer_len": len(resolved_text),
            }
        )
    return items


def build_mini_mock_v2_report_payload(answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Minimal fields for Gemini report request — no debug or audio metadata."""
    payload: List[Dict[str, Any]] = []
    for row in sorted(
        [a for a in answers if isinstance(a, dict)],
        key=lambda x: int(x.get("question_index") or 0),
    ):
        resolved_text = _student_answer_text(row)
        word_count = count_english_words(resolved_text)
        q_idx = int(row.get("question_index") or 0)
        question_type = str(row.get("question_type") or "").strip()
        question_text = str(row.get("question_text") or "").strip()
        echo = _question_echo_signal(resolved_text, question_text)
        status = _row_analysis_status(row, resolved_text)
        text = resolved_text if status == "saved" else ""
        if text:
            text = _truncate_answer_for_report(text)
        # A non-answer (echo / insufficient) contributes 0 to quantity so its
        # length cannot lift response_amount or the level (RELEVANCE_GATE).
        effective_word_count = word_count if status == "saved" else 0
        try:
            duration_seconds = float(row.get("duration_seconds") or 0.0)
        except (TypeError, ValueError):
            duration_seconds = 0.0
        wpm_available = bool(row.get("wpm_available"))
        if wpm_available and duration_seconds > 0 and effective_word_count > 0:
            try:
                wpm = float(row.get("wpm") or 0.0)
            except (TypeError, ValueError):
                wpm = 0.0
        else:
            wpm_available = False
            wpm = 0.0
        fluency = _per_answer_fluency_metrics(text) if text else {
            "sentence_count": 0,
            "filler_hits": 0,
            "connector_count": 0,
            "repetition_hint": "low",
        }
        speech_wc = count_content_words(text) if status == "saved" else 0
        speech_row = build_per_answer_speech_metrics(speech_wc, duration_seconds)
        payload.append(
            {
                "question_index": q_idx + 1,
                "question_type": question_type,
                "question_text": question_text,
                "student_answer": text,
                "word_count": effective_word_count,
                "sentence_count": fluency["sentence_count"],
                "duration_seconds": duration_seconds,
                "wpm": wpm,
                "wpm_available": wpm_available,
                "question_echo": bool(echo.get("question_echo")),
                "question_overlap_ratio": echo.get("question_overlap_ratio"),
                "novel_word_count": echo.get("novel_word_count"),
                "words_normalized_90s": speech_row.get("words_normalized_90s"),
                "speech_rate_level": speech_row.get("speech_rate_level"),
                "response_amount_score_rule": speech_row.get("response_amount_score_rule"),
                "filler_hits": fluency["filler_hits"],
                "connector_count": fluency["connector_count"],
                "repetition_hint": fluency["repetition_hint"],
            }
        )
    return payload


def _all_insufficient_report(inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    q_feedback = []
    for item in inputs:
        q_feedback.append(
            {
                "question_index": int(item.get("question_index") or 0),
                "status": "insufficient_response",
                "feedback": "답변 텍스트가 없거나 분량이 부족해 이 문항은 상세 피드백을 제공하지 않았습니다.",
                "better_direction": "20~30초 이상 영어로 답변한 뒤 다시 시도해 주세요.",
            }
        )
    return {
        "ok": True,
        "overall_level": "응답 부족",
        "summary": "답변량이 부족해 정상적인 등급 산정이 어렵습니다.",
        "score_breakdown": _empty_score_breakdown(),
        "question_feedback": q_feedback,
        "practice_mission": (
            "세 문항 모두 영어로 20~30초 이상 답변한 뒤, 다시 5분 진단을 받아 보세요."
        ),
        "strengths": [],
        "weaknesses": ["답변 분량 부족"],
        "sample_upgrade_direction": "",
        "error_category": "",
        "error_message": "",
        "all_insufficient": True,
    }


def _log_eval_config() -> None:
    try:
        logger.info(
            "[MINI_V2_EVAL_CONFIG] rubric_version=%s level_rule_version=%s",
            RUBRIC_VERSION,
            LEVEL_RULE_VERSION,
        )
    except Exception:
        pass


def _build_gemini_prompt(report_input: Dict[str, Any]) -> str:
    _log_eval_config()
    try:
        logger.info("[MINI_V2_REPORT_PROMPT_MODE] mode=light")
    except Exception:
        pass
    rubric = build_mini_mock_v2_light_rubric_prompt()
    answers = report_input.get("answers") or []
    payload_json = json.dumps(report_input, ensure_ascii=False, separators=(",", ":"))
    try:
        logger.info(
            "[MINI_V2_REPORT_REQUEST_SIZE] prompt_chars=%s payload_chars=%s "
            "answers_count=%s model=%s",
            len(rubric),
            len(payload_json),
            len(answers),
            MINI_REPORT_MODEL_NAME,
        )
    except Exception:
        pass
    return rubric + "\n\nStudent data JSON:\n" + payload_json


def _normalize_parsed(
    parsed: Dict[str, Any],
    *,
    inputs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    breakdown_raw = parsed.get("score_breakdown")
    breakdown: Dict[str, int] = _empty_score_breakdown()
    if isinstance(breakdown_raw, dict):
        for key in _SCORE_KEYS:
            try:
                breakdown[key] = max(0, min(100, int(breakdown_raw.get(key) or 0)))
            except (TypeError, ValueError):
                breakdown[key] = 0

    q_fb_raw = parsed.get("question_feedback")
    q_feedback: List[Dict[str, Any]] = []
    if isinstance(q_fb_raw, list):
        for item in q_fb_raw:
            if not isinstance(item, dict):
                continue
            try:
                qn = int(item.get("question_index") or 0)
            except (TypeError, ValueError):
                qn = 0
            q_feedback.append(
                {
                    "question_index": qn,
                    "status": str(item.get("status") or "saved"),
                    "feedback": str(item.get("feedback") or "").strip(),
                    "better_direction": str(item.get("better_direction") or "").strip(),
                }
            )

    if not q_feedback:
        for item in inputs:
            qn = int(item.get("question_index") or 0)
            st = str(item.get("status") or "saved")
            q_feedback.append(
                {
                    "question_index": qn,
                    "status": st,
                    "feedback": "",
                    "better_direction": "",
                }
            )

    strengths = parsed.get("strengths")
    weaknesses = parsed.get("weaknesses")
    return {
        "ok": True,
        "overall_level": str(parsed.get("overall_level") or "측정 불가").strip(),
        "summary": str(parsed.get("summary") or "").strip(),
        "score_breakdown": breakdown,
        "question_feedback": q_feedback,
        "practice_mission": str(parsed.get("practice_mission") or "").strip(),
        "strengths": [str(s).strip() for s in strengths if str(s).strip()]
        if isinstance(strengths, list)
        else [],
        "weaknesses": [str(s).strip() for s in weaknesses if str(s).strip()]
        if isinstance(weaknesses, list)
        else [],
        "sample_upgrade_direction": str(parsed.get("sample_upgrade_direction") or "").strip(),
        "error_category": "",
        "error_message": "",
        "all_insufficient": False,
    }


def _failure(
    *,
    category: str,
    message: str,
    timed_out: bool = False,
    quota: bool = False,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "overall_level": "",
        "summary": "",
        "score_breakdown": _empty_score_breakdown(),
        "question_feedback": [],
        "practice_mission": "",
        "strengths": [],
        "weaknesses": [],
        "sample_upgrade_direction": "",
        "error_category": category,
        "error_message": message,
        "timed_out": timed_out,
        "quota": quota,
        "all_insufficient": False,
    }


def _classify_gemini_error(err: str) -> str:
    err_l = (err or "").lower()
    if any(
        token in err_l
        for token in ("timeout", "timed out", "deadline exceeded", "readtimeout")
    ):
        return "timeout"
    if "429" in err_l or "resource_exhausted" in err_l or "quota" in err_l:
        return "quota_or_rate_limit"
    if "rate limit" in err_l or "rate_limit" in err_l or "too many requests" in err_l:
        return "rate_limit"
    if any(
        token in err_l
        for token in (
            "api key",
            "api_key",
            "invalid key",
            "unauthenticated",
            "permission denied",
            "401",
        )
    ):
        return "api_key"
    if "503" in err_l or "overloaded" in err_l:
        return "temporary_overload"
    if "unavailable" in err_l:
        return "unavailable"
    if any(
        token in err_l
        for token in ("500", "502", "504", "internal error")
    ):
        return "api_error"
    if "404" in err_l or "not_found" in err_l:
        return "model_not_found"
    return "unknown" if err else "api_error"


def _parse_report_response(raw_text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    from services.evaluation.gemini_multimodal_pipeline import strip_json_fence
    from services.transcript_analysis_service import _extract_json_object

    parsed = _extract_json_object(raw_text)
    if parsed:
        return parsed, ""
    fence_text = strip_json_fence(raw_text)
    if fence_text != raw_text:
        parsed = _extract_json_object(fence_text)
        if parsed:
            return parsed, ""
    return None, "json_parse_failed"


def _analyze_core(answers: List[Dict[str, Any]], *, api_key: str) -> Dict[str, Any]:
    _log_eval_config()
    inputs = build_mini_mock_v2_analysis_inputs(answers)
    payload = build_mini_mock_v2_report_payload(answers)
    report_input = build_mini_mock_v2_gemini_report_input(answers, payload)
    _log_v2_analysis_input(answers, inputs, payload)
    usable = [
        a
        for a in answers
        if isinstance(a, dict)
        and _row_analysis_status(a, _student_answer_text(a)) == "saved"
    ]
    if not usable:
        try:
            logger.info("[MINI_MOCK_V2_ANALYSIS] all_insufficient count=%s", len(inputs))
        except Exception:
            pass
        return _all_insufficient_report(
            [
                {
                    "question_index": int(r.get("question_index") or 0) + 1,
                    "status": "insufficient_response",
                }
                for r in sorted(
                    [a for a in answers if isinstance(a, dict)],
                    key=lambda x: int(x.get("question_index") or 0),
                )
            ]
        )

    prompt = _build_gemini_prompt(report_input)
    models = build_mini_mock_v2_report_model_candidates()
    parsed, err, model = run_report_json_model_chain(
        api_key=api_key,
        prompt=prompt,
        models=models,
        temperature=0.25,
        max_output_tokens=4096,
        timeout_ms=GEMINI_REQUEST_TIMEOUT_MS,
        log_tag="MINI_MOCK_V2_REPORT",
        parser_fn=_parse_report_response,
        retry_max_attempts=REPORT_MAX_ATTEMPTS,
        retry_delays_sec=REPORT_RETRY_DELAYS_SEC,
        detect_truncation=True,
    )
    if not parsed:
        category = _classify_gemini_error(err or "")
        if category == "quota_or_rate_limit":
            category = "quota"
        quota = category in ("quota", "quota_or_rate_limit", "rate_limit")
        try:
            logger.warning(
                "[MINI_MOCK_V2_ANALYSIS] gemini_failed category=%s err=%s model=%s",
                category,
                (err or "")[:200],
                model,
            )
        except Exception:
            pass
        try:
            logger.warning(
                "[MINI_V2_ANALYSIS_ERROR] category=%s message=%s",
                category,
                (err or category)[:240],
            )
        except Exception:
            pass
        message = "analysis_timeout" if category == "timeout" else (err or category)
        return _failure(
            category=category,
            message=message,
            timed_out=(category == "timeout"),
            quota=quota,
        )

    out = _normalize_parsed(parsed, inputs=inputs)
    apply_speech_rate_to_report(out, report_input.get("aggregate_metrics") or {})
    out["model_used"] = model
    try:
        logger.info(
            "[MINI_MOCK_V2_ANALYSIS] ok level=%s usable=%s",
            out.get("overall_level"),
            len(usable),
        )
    except Exception:
        pass
    return out


def analyze_mini_mock_v2_answers(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run one diagnostic report from V2 saved answers (text only).
    HTTP timeout 45s (google.genai) + outer wrapper 55s. Does not read audio blobs.
    """
    from utils.secrets import get_gemini_api_key

    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        try:
            logger.warning(
                "[MINI_V2_ANALYSIS_ERROR] category=api_key message=missing_api_key"
            )
        except Exception:
            pass
        return _failure(category="api_key", message="missing_api_key")

    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_analyze_core, answers, api_key=api_key)
        try:
            return future.result(timeout=ANALYSIS_WRAPPER_TIMEOUT_SEC)
        except concurrent.futures.TimeoutError:
            elapsed = time.time() - started
            try:
                logger.warning(
                    "[MINI_V2_ANALYSIS_TIMEOUT] elapsed=%.1f category=timeout",
                    elapsed,
                )
            except Exception:
                pass
            try:
                logger.warning(
                    "[MINI_V2_ANALYSIS_ERROR] category=timeout message=analysis_timeout"
                )
            except Exception:
                pass
            return _failure(
                category="timeout",
                message="analysis_timeout",
                timed_out=True,
            )
        except Exception as exc:
            try:
                logger.exception(
                    "[MINI_V2_ANALYSIS_ERROR] category=unknown message=%s",
                    f"{type(exc).__name__}: {exc}"[:240],
                )
            except Exception:
                pass
            return _failure(
                category="unknown",
                message=f"{type(exc).__name__}: {exc}",
            )
