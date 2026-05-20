"""Speech-to-text for saved answer rows — transcription only, no scoring."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from services.api_retry_policy import (
    STT_MAX_ATTEMPTS,
    STT_RETRY_DELAYS_SEC,
    is_retryable_error,
    log_api_call_result,
    should_try_next_model,
    sleep_before_retry,
)
from services.evaluation.eval_config import build_stt_model_candidates

logger = logging.getLogger(__name__)

STT_TIMEOUT_SEC = 45
MIN_ENGLISH_WORDS_FOR_TRANSCRIPT = 5

_NO_SPEECH_EXACT = frozenset(
    {
        "(no speech)",
        "(no speech detected)",
        "no speech detected",
        "[no speech]",
    }
)


def count_english_words(text: str) -> int:
    return len(re.findall(r"[a-zA-Z']+", text or ""))


def _classify_stt_error(exc_or_msg: str) -> tuple[str, str]:
    msg = str(exc_or_msg or "").strip()
    if not msg:
        return "unknown", ""
    upper = msg.upper()
    if any(tok in upper for tok in ("429", "RESOURCE_EXHAUSTED", "QUOTA", "RATE LIMIT", "RATE_LIMIT")):
        return "quota_or_rate_limit", msg[:240]
    if any(tok in upper for tok in ("TIMEOUT", "DEADLINE", "TIMED OUT")):
        return "timeout", msg[:240]
    if "503" in upper or "UNAVAILABLE" in upper or "OVERLOADED" in upper:
        return "temporary_overload", msg[:240]
    if any(tok in upper for tok in ("500", "502", "504", "INTERNAL")):
        return "api_error", msg[:240]
    if "404" in upper or "NOT_FOUND" in upper:
        return "model_not_found", msg[:240]
    return "unknown", msg[:240]


def _build_stt_prompt(question_text: str, language_hint: str) -> str:
    hint = (language_hint or "en").strip() or "en"
    q_block = ""
    if (question_text or "").strip():
        q_block = (
            f"\nExam question (context only — do not answer it):\n"
            f"{question_text.strip()}\n"
        )
    return (
        "Transcribe the attached audio only."
        f"{q_block}\n"
        "Rules:\n"
        "- Transcribe only what was spoken.\n"
        "- Do not correct grammar.\n"
        "- Do not rewrite or improve the answer.\n"
        "- Do not add scores, feedback, or commentary.\n"
        "- Preserve filler words (um, uh, like) when you hear them.\n"
        f"- Prefer {hint} when the speaker uses that language.\n"
        "- If no speech is detected, output exactly: (no speech)\n\n"
        "Output only the transcript text, nothing else."
    )


def _extract_response_text(response: Any) -> str:
    if response is None:
        return ""
    raw = (getattr(response, "text", "") or "").strip()
    if raw:
        return raw
    if isinstance(response, dict):
        for key in ("text", "transcript", "content"):
            val = response.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    parts: list[str] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            t = getattr(part, "text", None)
            if t:
                parts.append(str(t))
    if parts:
        return "\n".join(parts).strip()
    try:
        results = getattr(response, "results", None)
        if results:
            alt = results[0].alternatives[0]
            t = getattr(alt, "transcript", None) or getattr(alt, "text", None)
            if t:
                return str(t).strip()
    except Exception:
        pass
    return ""


def _normalize_transcript(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    lowered = text.lower().strip()
    if lowered in _NO_SPEECH_EXACT:
        return ""
    if lowered.startswith("(no speech"):
        return ""
    return text


def _stt_empty_result(*, provider: str = "gemini") -> Dict[str, Any]:
    return {
        "ok": False,
        "transcript": "",
        "raw_transcript": "",
        "text": "",
        "language": "unknown",
        "confidence": None,
        "word_count": 0,
        "error_category": "",
        "error_message": "",
        "provider": provider,
        "model_used": "",
        "attempts": 0,
        "retry_exhausted": False,
    }


def _stt_success_result(
    *,
    transcript: str,
    raw_transcript: str,
    model_used: str,
    attempts: int,
    provider: str = "gemini",
) -> Dict[str, Any]:
    word_count = count_english_words(transcript)
    return {
        "ok": True,
        "transcript": transcript,
        "raw_transcript": raw_transcript,
        "text": transcript,
        "language": "en" if word_count > 0 else "unknown",
        "confidence": None,
        "word_count": word_count,
        "error_category": "",
        "error_message": "",
        "provider": provider,
        "model_used": model_used,
        "attempts": attempts,
        "retry_exhausted": False,
    }


def _invoke_stt_model(
    *,
    api_key: str,
    audio_bytes: bytes,
    mime_type: str,
    question_text: str,
    language_hint: str,
    model_name: str,
) -> Tuple[Optional[str], str, str]:
    """Single Gemini STT call. Returns (raw_text or None, error_category, error_message)."""
    from google import genai
    from google.genai import types as genai_types

    from services.evaluation.audio_mime import resolve_audio_mime

    resolved_mime = resolve_audio_mime(audio_bytes, mime_type)
    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=STT_TIMEOUT_SEC * 1000),
    )
    prompt = _build_stt_prompt(question_text, language_hint)
    parts = [
        genai_types.Part.from_text(text=prompt),
        genai_types.Part.from_bytes(data=audio_bytes, mime_type=resolved_mime),
    ]
    contents = [genai_types.Content(role="user", parts=parts)]
    config = genai_types.GenerateContentConfig(
        temperature=0.0,
        max_output_tokens=2048,
    )
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
        return _extract_response_text(response), "", ""
    except Exception as exc:
        category, message = _classify_stt_error(exc)
        return None, category, message or f"{type(exc).__name__}: {exc}"


def derive_stt_status(stt: Dict[str, Any]) -> str:
    if not stt.get("ok"):
        cat = str(stt.get("error_category") or "")
        if is_retryable_error(cat) or stt.get("retry_exhausted"):
            return "stt_pending"
        return "stt_failed"
    transcript = (stt.get("transcript") or "").strip()
    if count_english_words(transcript) < MIN_ENGLISH_WORDS_FOR_TRANSCRIPT:
        return "insufficient_response"
    return "transcript_ready"


def merge_stt_into_answer_result(
    result: Dict[str, Any],
    stt: Dict[str, Any],
    *,
    question_text: str = "",
    question_index: int | None = None,
    question_id: str = "",
    audio_key: str = "",
    audio_len: int = 0,
) -> Dict[str, Any]:
    """Attach STT fields to a saved answer result dict (does not run Gemini analysis)."""
    out = dict(result)
    stt_status = derive_stt_status(stt)
    transcript = ""
    raw_transcript = ""
    if stt.get("ok"):
        transcript = (stt.get("transcript") or "").strip()
        raw_transcript = (stt.get("raw_transcript") or transcript).strip()
    out["stt_status"] = stt_status
    out["raw_transcript"] = raw_transcript
    out["stt_error_category"] = str(stt.get("error_category") or "")
    out["stt_error_message"] = str(stt.get("error_message") or "")
    out["stt_word_count"] = int(
        stt.get("word_count") if stt.get("word_count") is not None else count_english_words(transcript)
    )
    if question_text:
        out["question_text"] = question_text
    if question_index is not None:
        out["question_index"] = int(question_index)
    if question_id:
        out["question_id"] = str(question_id)
    if audio_key:
        out["audio_key"] = str(audio_key)
    if audio_len:
        out["audio_len"] = int(audio_len)
        out["source_audio_size_bytes"] = int(audio_len)

    if stt_status == "transcript_ready":
        out["transcript"] = transcript
        out["is_gradable"] = True
    elif stt_status == "insufficient_response":
        out["transcript"] = transcript
        out["is_gradable"] = False
        ast = str(out.get("analysis_status") or "").lower()
        if ast in ("", "saved_unanalyzed", "unknown"):
            out["analysis_status"] = "insufficient_response"
        dst = str(out.get("diagnosis_status") or "").lower()
        if dst in ("", "saved_unanalyzed", "ok"):
            out["diagnosis_status"] = "no_speech"
    else:
        out["is_gradable"] = False
        if not out.get("transcript") and transcript:
            out["transcript"] = transcript

    return out


def transcribe_answer_audio(
    audio_bytes: bytes,
    *,
    mime_type: str = "audio/webm",
    language_hint: str = "en",
    question_text: str = "",
    mode: str = "",
    question_id: str = "",
    api_key: str | None = None,
) -> Dict[str, Any]:
    """Transcribe answer audio via Gemini with retry and model fallback."""
    provider = "gemini"
    empty = _stt_empty_result(provider=provider)

    try:
        audio_len = len(audio_bytes) if audio_bytes else 0
    except Exception:
        audio_len = 0
    try:
        logger.info(
            "[STT_INPUT] audio_len=%s mime_type=%s language_hint=%s mode=%s question_id=%s",
            audio_len,
            mime_type,
            language_hint,
            mode,
            question_id,
        )
        if 0 < audio_len < 1000:
            logger.warning("[STT_AUDIO_TOO_SMALL] audio_len=%s mode=%s", audio_len, mode)
    except Exception:
        pass

    if not audio_bytes:
        empty["error_category"] = "empty_audio"
        empty["error_message"] = "empty_audio_bytes"
        return empty

    if not api_key:
        from utils.secrets import get_gemini_api_key

        api_key = get_gemini_api_key()
    if not api_key:
        empty["error_category"] = "missing_api_key"
        empty["error_message"] = "API key not configured"
        return empty

    models = build_stt_model_candidates()
    if not models:
        empty["error_category"] = "config_error"
        empty["error_message"] = "no_stt_models_configured"
        return empty

    t0 = time.perf_counter()
    last_category = ""
    last_message = ""
    model_idx = 0
    attempt_num = 0

    while attempt_num < STT_MAX_ATTEMPTS and model_idx < len(models):
        attempt_num += 1
        sleep_before_retry(attempt_num, STT_RETRY_DELAYS_SEC)
        model_name = models[model_idx]

        try:
            logger.info(
                "[STT_API_CALL_START] provider=%s model=%s mime_type=%s audio_len=%s attempt=%s",
                provider,
                model_name,
                mime_type,
                audio_len,
                attempt_num,
            )
        except Exception:
            pass

        raw_text, err_cat, err_msg = _invoke_stt_model(
            api_key=api_key,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            question_text=question_text,
            language_hint=language_hint,
            model_name=model_name,
        )

        if raw_text is not None:
            raw_transcript = raw_text.strip()
            transcript = _normalize_transcript(raw_transcript)
            if not transcript and raw_transcript:
                transcript = raw_transcript
            if raw_transcript:
                elapsed = time.perf_counter() - t0
                result = _stt_success_result(
                    transcript=transcript,
                    raw_transcript=raw_transcript,
                    model_used=model_name,
                    attempts=attempt_num,
                    provider=provider,
                )
                try:
                    logger.info(
                        "[STT_FINAL_RESULT] success=True attempts=%s model_used=%s "
                        "error_category=—",
                        attempt_num,
                        model_name,
                    )
                except Exception:
                    pass
                log_api_call_result(
                    service="stt",
                    model_used=model_name,
                    attempts=attempt_num,
                    success=True,
                    error_category="",
                    elapsed=elapsed,
                )
                return result
            err_cat = "empty_response"
            err_msg = "empty_stt_response"

        last_category = err_cat or "unknown"
        last_message = err_msg or last_category

        try:
            logger.warning(
                "[STT_RETRY] attempt=%s model=%s delay_next=%s error_category=%s",
                attempt_num,
                model_name,
                STT_RETRY_DELAYS_SEC[min(attempt_num - 1, len(STT_RETRY_DELAYS_SEC) - 1)]
                if attempt_num < STT_MAX_ATTEMPTS
                else 0,
                last_category,
            )
        except Exception:
            pass

        if last_category == "model_not_found":
            model_idx += 1
            continue

        if not is_retryable_error(last_category):
            break

        if should_try_next_model(last_category) and model_idx + 1 < len(models):
            model_idx += 1
            continue

        if attempt_num >= STT_MAX_ATTEMPTS:
            break

    elapsed = time.perf_counter() - t0
    retry_exhausted = is_retryable_error(last_category)

    try:
        logger.warning(
            "[STT_FINAL_RESULT] success=False attempts=%s model_used=%s error_category=%s",
            attempt_num,
            models[min(model_idx, len(models) - 1)] if models else "—",
            last_category,
        )
    except Exception:
        pass

    log_api_call_result(
        service="stt",
        model_used=models[min(model_idx, len(models) - 1)] if models else "",
        attempts=attempt_num,
        success=False,
        error_category=last_category,
        elapsed=elapsed,
    )

    empty.update(
        {
            "error_category": last_category or "unknown",
            "error_message": last_message or "stt_failed",
            "model_used": models[min(model_idx, len(models) - 1)] if models else "",
            "attempts": attempt_num,
            "retry_exhausted": retry_exhausted,
        }
    )
    return empty


def render_stt_dev_debug_capsule(result: Dict[str, Any], *, key_suffix: str = "") -> None:
    """Show STT status/transcript only when ``show_dev_debug`` is enabled."""
    import streamlit as st

    if not st.session_state.get("show_dev_debug"):
        return
    if not isinstance(result, dict):
        return
    status = str(result.get("stt_status") or "—")
    wc = result.get("stt_word_count", "—")
    st.caption(f"[dev] STT · {status} · words={wc}")
    transcript = (result.get("transcript") or "").strip()
    if transcript:
        st.text_area(
            "transcript",
            transcript,
            height=72,
            disabled=True,
            key=f"stt_dev_transcript_{key_suffix}",
        )
    err_cat = str(result.get("error_category") or "").strip()
    if err_cat:
        st.caption(f"[dev] STT error: {err_cat}")
