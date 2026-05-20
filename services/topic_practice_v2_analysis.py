"""Short Gemini feedback for a single Topic Practice V2 answer (text transcript)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

from services.evaluation.eval_config import _dedupe_models
from services.stt_service import count_english_words
from services.topic_practice_v2_rubric import (
    RUBRIC_VERSION,
    build_topic_practice_v2_feedback_rubric,
)

logger = logging.getLogger(__name__)

GEMINI_REQUEST_TIMEOUT_SEC = 35
GEMINI_REQUEST_TIMEOUT_MS = GEMINI_REQUEST_TIMEOUT_SEC * 1000

_DEFAULT_TOPIC_FEEDBACK = "gemini-2.5-flash-lite"
TOPIC_FEEDBACK_MODEL_ENV = (os.getenv("GEMINI_TOPIC_FEEDBACK_MODEL") or "").strip()


def build_topic_v2_feedback_model_candidates() -> List[str]:
    """Flash / Flash-Lite only — env first, then fixed fallbacks. No Pro."""
    return _dedupe_models(
        [
            TOPIC_FEEDBACK_MODEL_ENV or _DEFAULT_TOPIC_FEEDBACK,
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
        ]
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
        "practice_mission": "",
        "error_category": category,
        "error_message": message,
    }


def _ok_payload(
    summary: str,
    strength: str,
    correction_focus: str,
    better_expression: str,
    practice_mission: str,
) -> Dict[str, Any]:
    return {
        "ok": True,
        "summary": summary,
        "strength": strength,
        "correction_focus": correction_focus,
        "better_expression": better_expression,
        "practice_mission": practice_mission,
        "error_category": "",
        "error_message": "",
    }


def _coerce_str(val: Any) -> str:
    return str(val or "").strip()


def _answer_transcript(answer: Dict[str, Any]) -> str:
    for key in ("transcript", "student_answer", "stt_transcript", "raw_transcript"):
        t = _coerce_str(answer.get(key))
        if t:
            return t
    return ""


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


def _invoke_model(api_key: str, prompt: str, model_name: str) -> Tuple[Optional[Dict[str, Any]], str]:
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=GEMINI_REQUEST_TIMEOUT_MS),
    )
    parts = [genai_types.Part.from_text(text=prompt)]
    contents = [genai_types.Content(role="user", parts=parts)]
    config = genai_types.GenerateContentConfig(temperature=0.2, max_output_tokens=1024)
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

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


def _build_prompt(answer: Dict[str, Any], transcript: str) -> str:
    rubric = build_topic_practice_v2_feedback_rubric()
    q_en = _coerce_str(answer.get("en"))
    q_ko = _coerce_str(answer.get("ko"))
    topic = _coerce_str(answer.get("topic"))
    payload = {
        "rubric_version": RUBRIC_VERSION,
        "topic": topic,
        "question_en": q_en,
        "question_ko": q_ko,
        "transcript": transcript,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return rubric + "\n\nAnswer data JSON:\n" + body


def _normalize_success(parsed: Dict[str, Any]) -> Dict[str, Any]:
    return _ok_payload(
        summary=_coerce_str(parsed.get("summary")),
        strength=_coerce_str(parsed.get("strength")),
        correction_focus=_coerce_str(parsed.get("correction_focus")),
        better_expression=_coerce_str(parsed.get("better_expression")),
        practice_mission=_coerce_str(parsed.get("practice_mission")),
    )


def analyze_topic_practice_v2_answer(answer: dict) -> dict:
    """
    One short feedback call chain (try model list once each, stop on first success).

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
    models = build_topic_v2_feedback_model_candidates()
    last_err = "no_models"
    for model_name in models[:4]:
        try:
            logger.info("[TOPIC_V2_FEEDBACK] model=%s transcript_words=%s", model_name, wc)
        except Exception:
            pass
        parsed, err = _invoke_model(api_key, prompt, model_name)
        if parsed:
            norm = _normalize_success(parsed)
            if not norm["summary"]:
                norm["summary"] = "Brief feedback generated; see other fields."
            if not norm["strength"]:
                norm["strength"] = "(See summary.)"
            if not norm["correction_focus"]:
                norm["correction_focus"] = "Keep answering in full sentences next time."
            if not norm["better_expression"]:
                norm["better_expression"] = "(Review correction_focus.)"
            if not norm["practice_mission"]:
                norm["practice_mission"] = "Record the same question again with a clearer opening sentence."
            try:
                logger.info("[TOPIC_V2_FEEDBACK] success model=%s", model_name)
            except Exception:
                pass
            return _stringify_result(norm)
        last_err = err or "unknown"
        try:
            logger.warning("[TOPIC_V2_FEEDBACK] model_failed model=%s err=%s", model_name, last_err)
        except Exception:
            pass

    return _stringify_result(
        _failure(
            category="api_error",
            message=f"피드백을 가져오지 못했어요. 잠시 후 다시 시도해 주세요. ({last_err})",
        )
    )


def _stringify_result(d: Dict[str, Any]) -> dict:
    """Normalize to required schema."""
    ok_raw = d.get("ok")
    if isinstance(ok_raw, bool):
        ok = ok_raw
    else:
        ok = str(ok_raw).lower() in ("true", "1", "yes")
    return {
        "ok": ok,
        "summary": _coerce_str(d.get("summary")),
        "strength": _coerce_str(d.get("strength")),
        "correction_focus": _coerce_str(d.get("correction_focus")),
        "better_expression": _coerce_str(d.get("better_expression")),
        "practice_mission": _coerce_str(d.get("practice_mission")),
        "error_category": _coerce_str(d.get("error_category")),
        "error_message": _coerce_str(d.get("error_message")),
    }
