"""Speech-to-text for saved answer rows — transcription only, no scoring."""

from __future__ import annotations

import concurrent.futures
import logging
import re
from typing import Any, Dict

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
    if "503" in upper or "UNAVAILABLE" in upper:
        return "temporary_overload", msg[:240]
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
    raw = (getattr(response, "text", "") or "").strip()
    if raw:
        return raw
    parts: list[str] = []
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            t = getattr(part, "text", None)
            if t:
                parts.append(str(t))
    return "\n".join(parts).strip()


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


def derive_stt_status(stt: Dict[str, Any]) -> str:
    if not stt.get("ok"):
        return "stt_pending"
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
    """Transcribe answer audio via Gemini (transcription-only prompt)."""
    empty = {
        "ok": False,
        "transcript": "",
        "raw_transcript": "",
        "language": "unknown",
        "confidence": None,
        "word_count": 0,
        "error_category": "",
        "error_message": "",
    }
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

    def _call_gemini() -> str:
        from google import genai
        from google.genai import types as genai_types

        from services.evaluation.audio_mime import resolve_audio_mime
        from services.evaluation.eval_config import MODEL_NAME

        resolved_mime = resolve_audio_mime(audio_bytes, mime_type)
        client = genai.Client(api_key=api_key)
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
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=contents,
            config=config,
        )
        return _extract_response_text(response)

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_call_gemini)
            raw_text = future.result(timeout=STT_TIMEOUT_SEC)
    except concurrent.futures.TimeoutError:
        try:
            logger.warning(
                "[STT] timeout mode=%s question_id=%s timeout_sec=%s",
                mode,
                question_id,
                STT_TIMEOUT_SEC,
            )
        except Exception:
            pass
        empty["error_category"] = "timeout"
        empty["error_message"] = f"stt_timeout_over_{STT_TIMEOUT_SEC}s"
        return empty
    except Exception as exc:
        category, message = _classify_stt_error(exc)
        try:
            logger.warning(
                "[STT] failure mode=%s question_id=%s category=%s exc=%s",
                mode,
                question_id,
                category,
                type(exc).__name__,
            )
        except Exception:
            pass
        empty["error_category"] = category
        empty["error_message"] = message or f"{type(exc).__name__}: {exc}"
        return empty

    raw_transcript = (raw_text or "").strip()
    transcript = _normalize_transcript(raw_transcript)
    word_count = count_english_words(transcript)
    language = "en" if word_count > 0 else "unknown"
    if not raw_transcript:
        return {
            "ok": False,
            "transcript": "",
            "raw_transcript": "",
            "language": "unknown",
            "confidence": None,
            "word_count": 0,
            "error_category": "empty_response",
            "error_message": "empty_stt_response",
        }

    try:
        logger.debug(
            "[STT] ok mode=%s question_id=%s word_count=%s transcript_len=%s",
            mode,
            question_id,
            word_count,
            len(transcript),
        )
    except Exception:
        pass

    return {
        "ok": True,
        "transcript": transcript,
        "raw_transcript": raw_transcript,
        "language": language,
        "confidence": None,
        "word_count": word_count,
        "error_category": "",
        "error_message": "",
    }


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
    err_cat = str(result.get("stt_error_category") or "").strip()
    if err_cat:
        st.caption(f"[dev] STT error: {err_cat}")
