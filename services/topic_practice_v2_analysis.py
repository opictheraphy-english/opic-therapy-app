"""Short Gemini feedback for a single Topic Practice V2 answer (text transcript)."""

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
from services.stt_service import count_english_words
from services.topic_practice_v2_rubric import (
    RUBRIC_VERSION,
    build_topic_practice_v2_feedback_rubric,
)

logger = logging.getLogger(__name__)

GEMINI_REQUEST_TIMEOUT_SEC = 35
GEMINI_REQUEST_TIMEOUT_MS = GEMINI_REQUEST_TIMEOUT_SEC * 1000

_STUDENT_FEEDBACK_UNAVAILABLE = (
    "AI 피드백 서버가 잠시 바빠요.\n\n"
    "답변은 이미 저장되어 있습니다.\n\n"
    "45초 정도 지난 뒤 「피드백 다시 받기」를 한 번만 눌러 주세요. "
    "연속으로 누르면 같은 오류가 반복되고 API 사용량만 늘어납니다."
)

_FEEDBACK_MODEL_ATTEMPTS = 2  # one automatic retry per model on transient errors


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
) -> Dict[str, Any]:
    return {
        "ok": True,
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


def _is_model_not_found_error(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}"
    low = msg.lower()
    if "404" in msg:
        return True
    if "not_found" in low or "not found" in low:
        return True
    if "model_not_found" in low:
        return True
    if "no longer available" in low or "not available" in low:
        return True
    status = getattr(exc, "status_code", None)
    if status == 404:
        return True
    return False


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


def _err_to_category(err: str) -> str:
    if err == "model_not_found":
        return "model_not_found"
    if err in ("json_parse_failed", "empty_response"):
        return err
    if is_retryable_error(err) or err == "api_error":
        return "api_error"
    return "api_error"


def _invoke_model(api_key: str, prompt: str, model_name: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Returns (parsed_json, error_token). error_token is '' on success."""
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
        if _is_model_not_found_error(exc):
            try:
                logger.warning(
                    "[TOPIC_V2_FEEDBACK] model=%s error_category=model_not_found",
                    model_name,
                )
            except Exception:
                pass
            return None, "model_not_found"
        try:
            logger.warning(
                "[TOPIC_V2_FEEDBACK] model=%s error_category=api_error exc_type=%s",
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
        summary=summary,
        strength=_coerce_str(parsed.get("strength")),
        correction_focus=_coerce_str(parsed.get("correction_focus")),
        better_expression=_coerce_str(parsed.get("better_expression")),
        upgrade_sample=_coerce_str(parsed.get("upgrade_sample")),
        keyword_drill=drills,
        practice_mission=_coerce_str(parsed.get("practice_mission")),
    )


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
    saw_model_not_found = False
    saw_other_failure = False
    for model_name in models:
        for attempt_idx in range(1, _FEEDBACK_MODEL_ATTEMPTS + 1):
            if attempt_idx > 1:
                sleep_before_retry(attempt_idx, STT_RETRY_DELAYS_SEC)
            try:
                logger.info(
                    "[TOPIC_V2_FEEDBACK] model=%s attempt=%s transcript_words=%s",
                    model_name,
                    attempt_idx,
                    wc,
                )
            except Exception:
                pass
            parsed, err = _invoke_model(api_key, prompt, model_name)
            if parsed:
                norm = _normalize_success(parsed)
                if not norm["summary"]:
                    norm["summary"] = "짧은 피드백이 생성되었어요. 아래 항목을 함께 확인해 주세요."
                if not norm["strength"]:
                    norm["strength"] = "요약에서 전체 흐름을 참고해 주세요."
                if not norm["correction_focus"]:
                    norm["correction_focus"] = "다음에는 핵심부터 한 문장으로 시작하고, 이유나 예를 한 가지 더 붙여 보세요."
                if not norm["better_expression"]:
                    norm["better_expression"] = "위 ‘바로 고칠 점’을 반영해 같은 내용을 한 번 더 자연스럽게 말해 보세요."
                if not norm.get("upgrade_sample"):
                    norm["upgrade_sample"] = ""
                if not norm["practice_mission"]:
                    norm["practice_mission"] = "같은 질문에 첫 문장만 바꿔서 20초 안팎으로 다시 말해 보세요."
                try:
                    logger.info(
                        "[TOPIC_V2_FEEDBACK] success model=%s attempt=%s",
                        model_name,
                        attempt_idx,
                    )
                except Exception:
                    pass
                return _stringify_result(norm)
            cat = _err_to_category(err or "")
            if err == "model_not_found":
                saw_model_not_found = True
                break
            saw_other_failure = True
            try:
                logger.warning(
                    "[TOPIC_V2_FEEDBACK] model_failed model=%s attempt=%s err=%s",
                    model_name,
                    attempt_idx,
                    err,
                )
            except Exception:
                pass
            if attempt_idx < _FEEDBACK_MODEL_ATTEMPTS and is_retryable_error(cat):
                continue
            break

    final_cat = "model_not_found" if saw_model_not_found and not saw_other_failure else "api_error"
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
