"""Script Coaching — DIAGNOSE engine: Gemini analysis of one written script.

# Stage 1 of Script Coaching. Follows the topic_practice_v2_analysis.py
# call/retry/parse pattern. Upgrade (stage 2) is a separate engine.
#
# Deterministic text metrics (word/connector counts, quantity score) are
# computed in code via script_coaching_metrics and injected as FACTS.
# Gemini only judges level + the five quality axes + Korean feedback.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from services.api_retry_policy import (
    STT_RETRY_DELAYS_SEC,
    is_retryable_error,
    sleep_before_retry,
)
from services.evaluation.eval_config import build_topic_feedback_model_candidates
from services.script_coaching_diagnose_rubric import (
    RUBRIC_VERSION,
    build_script_coaching_diagnose_rubric,
)
from services.script_coaching_metrics import build_script_text_metrics

logger = logging.getLogger(__name__)

GEMINI_REQUEST_TIMEOUT_SEC = 35
GEMINI_REQUEST_TIMEOUT_MS = GEMINI_REQUEST_TIMEOUT_SEC * 1000

MIN_SCRIPT_WORDS = 5
_DIAGNOSE_MODEL_ATTEMPTS = 2

_VALID_LEVELS = ("NH", "IL", "IM1", "IM2", "IM3", "IH", "AL")
_SCORE_KEYS = ("response_amount", "vocabulary", "grammar", "context", "structure")

_DIAGNOSE_UNAVAILABLE = (
    "AI 진단 서버가 잠시 바빠요.\n\n"
    "입력하신 스크립트는 그대로 남아 있습니다.\n\n"
    "45초쯤 지난 뒤 「진단 다시 받기」를 한 번만 눌러 주세요."
)


def _coerce_str(val: Any) -> str:
    return str(val or "").strip()


def _coerce_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _coerce_score(val: Any) -> int:
    return max(0, min(100, _coerce_int(val, 0)))


def _coerce_str_list(val: Any, limit: int = 3) -> List[str]:
    if not isinstance(val, list):
        return []
    out: List[str] = []
    for x in val:
        s = _coerce_str(x)
        if s:
            out.append(s)
    return out[:limit]


def _empty_scores() -> Dict[str, int]:
    return {k: 0 for k in _SCORE_KEYS}


def _failure(*, category: str, message: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "overall_level": "",
        "word_count": 0,
        "connector_summary": {"total_hits": 0, "distinct_count": 0, "found": []},
        "score_breakdown": _empty_scores(),
        "summary": "",
        "connector_feedback": "",
        "vocabulary_feedback": "",
        "context_feedback": "",
        "correction_focus": "",
        "better_expression": "",
        "strengths": [],
        "weaknesses": [],
        "error_category": category,
        "error_message": message,
    }


def _is_model_not_found_error(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}"
    low = msg.lower()
    if "404" in msg or "not_found" in low or "not found" in low:
        return True
    if "no longer available" in low or "not available" in low:
        return True
    return getattr(exc, "status_code", None) == 404


def _parse_json_response(raw_text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    from services.evaluation.gemini_multimodal_pipeline import strip_json_fence
    from services.transcript_analysis_service import _extract_json_object

    parsed = _extract_json_object(raw_text)
    if parsed:
        return parsed, ""
    fence = strip_json_fence(raw_text)
    if fence != raw_text:
        parsed = _extract_json_object(fence)
        if parsed:
            return parsed, ""
    return None, "json_parse_failed"


def _invoke_model(
    api_key: str, prompt: str, model_name: str
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Returns (parsed_json, error_token). error_token is '' on success."""
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=GEMINI_REQUEST_TIMEOUT_MS),
    )
    parts = [genai_types.Part.from_text(text=prompt)]
    contents = [genai_types.Content(role="user", parts=parts)]
    config = genai_types.GenerateContentConfig(temperature=0.2, max_output_tokens=1536)
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
    except Exception as exc:
        if _is_model_not_found_error(exc):
            return None, "model_not_found"
        try:
            logger.warning(
                "[SCRIPT_DIAGNOSE] model=%s error_category=api_error exc_type=%s",
                model_name,
                type(exc).__name__,
            )
        except Exception:
            pass
        return None, "api_error"

    raw_text = (getattr(response, "text", "") or "").strip()
    if not raw_text:
        for cand in getattr(response, "candidates", None) or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                t = getattr(part, "text", None)
                if t:
                    raw_text = (raw_text + "\n" + t).strip()
    if not raw_text:
        return None, "empty_response"
    parsed, err = _parse_json_response(raw_text)
    if parsed:
        return parsed, ""
    return None, err or "json_parse_failed"


def _build_prompt(
    question_en: str,
    question_ko: str,
    script_text: str,
    metrics: Dict[str, Any],
) -> str:
    rubric = build_script_coaching_diagnose_rubric()
    payload = {
        "rubric_version": RUBRIC_VERSION,
        "question_en": question_en,
        "question_ko": question_ko,
        "transcript": script_text,
        "text_metrics": metrics,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return rubric + "\n\nScript data JSON:\n" + body


def _normalize_success(
    parsed: Dict[str, Any],
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """Map model JSON to the diagnose schema.

    word_count and connector_summary are taken from CODE metrics, not the
    model — the model is told to copy them, but code is the source of truth.
    """
    breakdown_raw = parsed.get("score_breakdown")
    breakdown = _empty_scores()
    if isinstance(breakdown_raw, dict):
        for k in _SCORE_KEYS:
            breakdown[k] = _coerce_score(breakdown_raw.get(k))
    # response_amount: trust the code rule as the floor reference.
    rule_amount = _coerce_score(metrics.get("response_amount_score_rule"))
    if breakdown["response_amount"] == 0:
        breakdown["response_amount"] = rule_amount

    level = _coerce_str(parsed.get("overall_level")).upper()
    if level not in _VALID_LEVELS:
        level = _coerce_str(metrics.get("word_count_level_hint")).upper() or "IL"

    return {
        "ok": True,
        "overall_level": level,
        # Code-computed facts — overrides any model recount.
        "word_count": _coerce_int(metrics.get("word_count")),
        "connector_summary": {
            "total_hits": _coerce_int(metrics.get("connector_total_hits")),
            "distinct_count": _coerce_int(metrics.get("connector_distinct_count")),
            "found": list(metrics.get("connectors_found") or []),
        },
        "score_breakdown": breakdown,
        "summary": _coerce_str(parsed.get("summary")),
        "connector_feedback": _coerce_str(parsed.get("connector_feedback")),
        "vocabulary_feedback": _coerce_str(parsed.get("vocabulary_feedback")),
        "context_feedback": _coerce_str(parsed.get("context_feedback")),
        "correction_focus": _coerce_str(parsed.get("correction_focus")),
        "better_expression": _coerce_str(parsed.get("better_expression")),
        "strengths": _coerce_str_list(parsed.get("strengths")),
        "weaknesses": _coerce_str_list(parsed.get("weaknesses")),
        "error_category": "",
        "error_message": "",
    }


def diagnose_script(
    question_en: str,
    script_text: str,
    question_ko: str = "",
) -> Dict[str, Any]:
    """Diagnose one written OPIc script. Returns the diagnose-schema dict.

    Args:
        question_en: the OPIc question, in English (student-typed).
        script_text: the student's typed answer script.
        question_ko: optional Korean translation/notes for the question.
    """
    script_text = _coerce_str(script_text)
    question_en = _coerce_str(question_en)
    question_ko = _coerce_str(question_ko)

    metrics = build_script_text_metrics(script_text)
    if _coerce_int(metrics.get("word_count")) < MIN_SCRIPT_WORDS:
        return _failure(
            category="insufficient_text",
            message="스크립트가 너무 짧아요. 영어로 몇 문장 이상 적어 주세요.",
        )
    if not question_en:
        return _failure(
            category="missing_question",
            message="질문을 영어로 입력해 주세요. 질문이 있어야 유형에 맞게 진단할 수 있어요.",
        )

    from utils.secrets import get_gemini_api_key

    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        return _failure(
            category="api_key",
            message="API 키가 없습니다. 설정에서 키를 확인해 주세요.",
        )

    prompt = _build_prompt(question_en, question_ko, script_text, metrics)
    models = build_topic_feedback_model_candidates()
    saw_model_not_found = False
    saw_other_failure = False

    for model_name in models:
        for attempt_idx in range(1, _DIAGNOSE_MODEL_ATTEMPTS + 1):
            if attempt_idx > 1:
                sleep_before_retry(attempt_idx, STT_RETRY_DELAYS_SEC)
            try:
                logger.info(
                    "[SCRIPT_DIAGNOSE] model=%s attempt=%s words=%s",
                    model_name,
                    attempt_idx,
                    metrics.get("word_count"),
                )
            except Exception:
                pass
            parsed, err = _invoke_model(api_key, prompt, model_name)
            if parsed:
                out = _normalize_success(parsed, metrics)
                if not out["summary"]:
                    out["summary"] = "진단 결과가 생성되었어요. 아래 항목을 함께 확인해 주세요."
                try:
                    logger.info(
                        "[SCRIPT_DIAGNOSE] success model=%s level=%s",
                        model_name,
                        out["overall_level"],
                    )
                except Exception:
                    pass
                return out
            if err == "model_not_found":
                saw_model_not_found = True
                break
            saw_other_failure = True
            if attempt_idx < _DIAGNOSE_MODEL_ATTEMPTS and is_retryable_error(err):
                continue
            break

    final_cat = (
        "model_not_found" if saw_model_not_found and not saw_other_failure else "api_error"
    )
    return _failure(category=final_cat, message=_DIAGNOSE_UNAVAILABLE)
