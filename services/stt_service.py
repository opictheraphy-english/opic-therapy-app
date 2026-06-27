"""Speech-to-text for saved answer rows — transcription only, no scoring."""

from __future__ import annotations

import concurrent.futures
import io
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from services.api_retry_policy import (
    STT_MAX_ATTEMPTS,
    STT_QUOTA_ERRORS,
    STT_RETRY_DELAYS_SEC,
    is_retryable_error,
    is_stt_retryable_error,
    log_api_call_result,
    should_try_next_model,
    sleep_before_retry,
)
from services.evaluation.eval_config import build_stt_model_candidates

logger = logging.getLogger(__name__)

# Per-Gemini-call HTTP timeout. Kept short: STT normally finishes in a few
# seconds, and a long hang here would block the worker thread well past the
# wrapper timeout below. (Was 45s — reduced as part of the websocket-disconnect
# fix; see transcribe_answer_audio for the threading rationale.)
STT_TIMEOUT_SEC = 20

# Wrapper timeout for the WHOLE STT job (all retries + model fallback combined).
# transcribe_answer_audio runs the retry loop in a background thread and waits
# at most this long. If exceeded, it returns an stt_pending result immediately
# so the Streamlit main thread stays free to answer websocket keepalive pings.
# Must stay below the browser's keepalive ping tolerance (~20-30s).
STT_WRAPPER_TIMEOUT_SEC = 25

# OpenAI Whisper fallback — single attempt after Gemini STT chain fails.
OPENAI_STT_MODEL = (os.getenv("OPENAI_STT_MODEL") or "whisper-1").strip() or "whisper-1"
OPENAI_STT_TIMEOUT_SEC = 22

_MIME_TO_FILENAME_EXT: Dict[str, str] = {
    "audio/webm": "webm",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
}

MIN_ENGLISH_WORDS_FOR_TRANSCRIPT = 5

_NO_SPEECH_EXACT = frozenset(
    {
        "(no speech)",
        "(no speech detected)",
        "no speech detected",
        "[no speech]",
    }
)

# Shared executor for STT jobs. Reused across calls so timed-out (abandoned)
# jobs do not accumulate unbounded threads — a stranded worker is bounded by
# STT_TIMEOUT_SEC and the pool caps concurrency.
_STT_EXECUTOR = concurrent.futures.ThreadPoolExecutor(
    max_workers=4, thread_name_prefix="stt"
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


# --- Repetition / hallucination guard --------------------------------------
# Gemini (and Whisper-family) STT can hallucinate on ~1s / near-silent / very
# low-information audio: it ignores the audio and emits a degenerate loop of one
# phrase until the token cap (e.g. "...and I was just playing in the water, and I
# was just having a good time," repeated dozens of times). Such output has
# abnormally low lexical diversity and/or a short phrase repeated many times, so
# we detect it and treat it as no usable speech (-> insufficient_response) rather
# than grading a 1-second non-answer as a long, fluent response.
_HALLU_MIN_WORDS = 25
_HALLU_UNIQUE_RATIO = 0.22
_HALLU_NGRAM_N = 5
_HALLU_NGRAM_MIN_REPEAT = 5


def looks_like_repetition_hallucination(text: str) -> bool:
    """True iff ``text`` looks like an STT repetition-loop hallucination.

    Conservative by design (only fires on clearly degenerate output) so genuine
    answers — even disfluent ones with fillers — are never dropped:
      * unique-word ratio below ~0.22 over 25+ words, or
      * a 5-word phrase repeated 5+ times.
    """
    words = re.findall(r"[a-zA-Z']+", (text or "").lower())
    n = len(words)
    if n < _HALLU_MIN_WORDS:
        return False
    if len(set(words)) / n < _HALLU_UNIQUE_RATIO:
        return True
    if n >= _HALLU_NGRAM_N * 2:
        from collections import Counter

        grams = Counter(
            tuple(words[i : i + _HALLU_NGRAM_N])
            for i in range(n - _HALLU_NGRAM_N + 1)
        )
        if grams and grams.most_common(1)[0][1] >= _HALLU_NGRAM_MIN_REPEAT:
            return True
    return False


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


def _filename_ext_for_mime(mime_type: str) -> str:
    resolved = (mime_type or "").split(";", 1)[0].strip().lower()
    return _MIME_TO_FILENAME_EXT.get(resolved, "webm")


def _whisper_language_code(language_hint: str) -> Optional[str]:
    hint = (language_hint or "").strip().lower().replace("_", "-")
    if not hint:
        return None
    base = hint.split("-", 1)[0]
    return base if len(base) == 2 else None


def _build_stt_success_from_raw(
    raw_transcript: str,
    *,
    model_used: str,
    provider: str,
    attempts: int,
    elapsed: float,
    audio_len: int,
) -> Optional[Dict[str, Any]]:
    """Normalize raw STT text; return success dict or None if unusable."""
    raw = (raw_transcript or "").strip()
    if not raw:
        return None
    transcript = _normalize_transcript(raw)
    if not transcript:
        transcript = raw
    if transcript and looks_like_repetition_hallucination(transcript):
        try:
            logger.warning(
                "[STT_HALLUCINATION] repetition/low-diversity detected "
                "provider=%s model=%s words=%s audio_len=%s -> insufficient",
                provider,
                model_used,
                count_english_words(transcript),
                audio_len,
            )
        except Exception:
            pass
        transcript = ""
    result = _stt_success_result(
        transcript=transcript,
        raw_transcript=raw,
        model_used=model_used,
        attempts=attempts,
        provider=provider,
    )
    try:
        logger.info(
            "[STT_FINAL_RESULT] success=True provider=%s attempts=%s model_used=%s "
            "error_category=—",
            provider,
            attempts,
            model_used,
        )
    except Exception:
        pass
    log_api_call_result(
        service="stt",
        model_used=model_used,
        attempts=attempts,
        success=True,
        error_category="",
        elapsed=elapsed,
    )
    return result


def _invoke_openai_stt_model(
    *,
    audio_bytes: bytes,
    mime_type: str,
    language_hint: str,
    question_text: str,
) -> Tuple[Optional[str], str, str]:
    """Single OpenAI Whisper transcription. Returns (raw_text, error_category, message)."""
    from services.gemini_json_client import classify_openai_exception, _is_openai_auth_skip_error
    from utils.secrets import get_openai_api_key

    api_key = get_openai_api_key()
    if not api_key:
        return None, "openai_skipped", "openai_api_key_not_configured"

    try:
        from openai import OpenAI
    except ImportError:
        return None, "openai_skipped", "openai_sdk_not_installed"

    ext = _filename_ext_for_mime(mime_type)
    buf = io.BytesIO(audio_bytes)
    buf.name = f"answer.{ext}"
    lang = _whisper_language_code(language_hint)
    prompt = (question_text or "").strip()[:500] or None

    try:
        client = OpenAI(api_key=api_key, timeout=float(OPENAI_STT_TIMEOUT_SEC))
        response = client.audio.transcriptions.create(
            model=OPENAI_STT_MODEL,
            file=buf,
            language=lang,
            prompt=prompt,
            response_format="text",
        )
    except Exception as exc:
        if _is_openai_auth_skip_error(exc):
            return None, "openai_skipped", str(exc)[:240]
        category = classify_openai_exception(exc)
        return None, category, str(exc)[:240] or f"{type(exc).__name__}: {exc}"

    if isinstance(response, str):
        raw_text = response.strip()
    else:
        raw_text = str(getattr(response, "text", "") or response or "").strip()
    if raw_text:
        return raw_text, "", ""
    return None, "empty_response", "empty_openai_stt_response"


def _run_openai_stt_fallback(
    audio_bytes: bytes,
    *,
    mime_type: str,
    language_hint: str,
    question_text: str,
    mode: str,
    question_id: str,
    gemini_attempts: int,
    t0: float,
) -> Optional[Dict[str, Any]]:
    """Try OpenAI Whisper once after the Gemini STT chain fails."""
    try:
        audio_len = len(audio_bytes) if audio_bytes else 0
    except Exception:
        audio_len = 0

    try:
        logger.info(
            "[STT_OPENAI_FALLBACK] mode=%s question_id=%s gemini_attempts=%s model=%s",
            mode,
            question_id,
            gemini_attempts,
            OPENAI_STT_MODEL,
        )
    except Exception:
        pass

    raw_text, err_cat, err_msg = _invoke_openai_stt_model(
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        language_hint=language_hint,
        question_text=question_text,
    )
    elapsed = time.perf_counter() - t0

    if raw_text is not None:
        result = _build_stt_success_from_raw(
            raw_text,
            model_used=OPENAI_STT_MODEL,
            provider="openai",
            attempts=gemini_attempts + 1,
            elapsed=elapsed,
            audio_len=audio_len,
        )
        if result:
            try:
                logger.info(
                    "[STT_OPENAI_FALLBACK] success mode=%s question_id=%s",
                    mode,
                    question_id,
                )
            except Exception:
                pass
            return result
        err_cat = "empty_response"
        err_msg = "empty_openai_stt_response"

    if err_cat == "openai_skipped":
        try:
            logger.info(
                "[STT_OPENAI_FALLBACK] skipped mode=%s question_id=%s reason=%s",
                mode,
                question_id,
                err_msg or err_cat,
            )
        except Exception:
            pass
        return None

    try:
        logger.warning(
            "[STT_OPENAI_FALLBACK] failed mode=%s question_id=%s error_category=%s",
            mode,
            question_id,
            err_cat,
        )
    except Exception:
        pass
    log_api_call_result(
        service="stt_openai_fallback",
        model_used=OPENAI_STT_MODEL,
        attempts=1,
        success=False,
        error_category=err_cat or "unknown",
        elapsed=elapsed,
    )
    return None


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


def _transcribe_answer_audio_impl(
    audio_bytes: bytes,
    *,
    mime_type: str,
    language_hint: str,
    question_text: str,
    mode: str,
    question_id: str,
    api_key: str | None,
) -> Dict[str, Any]:
    """Core STT retry loop. Runs in a background worker thread.

    This is the original transcribe_answer_audio body. It is wrapped by
    transcribe_answer_audio so the Streamlit main thread is never blocked by
    this loop — see that function for the rationale.
    """
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

    models = build_stt_model_candidates() if api_key else []
    if api_key and not models:
        last_category = "config_error"
        last_message = "no_stt_models_configured"
    else:
        last_category = ""
        last_message = ""

    t0 = time.perf_counter()
    model_idx = 0
    attempt_num = 0

    if api_key and models:
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
                if raw_transcript:
                    elapsed = time.perf_counter() - t0
                    result = _build_stt_success_from_raw(
                        raw_transcript,
                        model_used=model_name,
                        provider=provider,
                        attempts=attempt_num,
                        elapsed=elapsed,
                        audio_len=audio_len,
                    )
                    if result:
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

            if last_category in STT_QUOTA_ERRORS:
                try:
                    logger.warning(
                        "[STT_QUOTA_STOP] attempt=%s model=%s error_category=%s "
                        "(no retry / no model fallback)",
                        attempt_num,
                        model_name,
                        last_category,
                    )
                except Exception:
                    pass
                break

            if not is_stt_retryable_error(last_category):
                break

            if should_try_next_model(last_category) and model_idx + 1 < len(models):
                model_idx += 1
                continue

            if attempt_num >= STT_MAX_ATTEMPTS:
                break
    else:
        if not api_key:
            last_category = "missing_api_key"
            last_message = "gemini_api_key_not_configured"

    fallback = _run_openai_stt_fallback(
        audio_bytes,
        mime_type=mime_type,
        language_hint=language_hint,
        question_text=question_text,
        mode=mode,
        question_id=question_id,
        gemini_attempts=attempt_num,
        t0=t0,
    )
    if fallback is not None:
        return fallback

    elapsed = time.perf_counter() - t0
    retry_exhausted = is_stt_retryable_error(last_category)

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


def _stt_timeout_result(*, provider: str = "gemini") -> Dict[str, Any]:
    """Result returned when the STT job exceeds STT_WRAPPER_TIMEOUT_SEC.

    error_category is 'timeout' (a retryable category), so derive_stt_status
    maps this to 'stt_pending' — the answer is saved and the student can
    re-run STT later via the existing "음성 인식 다시 시도" button.
    """
    out = _stt_empty_result(provider=provider)
    out.update(
        {
            "error_category": "timeout",
            "error_message": (
                f"stt_wrapper_timeout_{STT_WRAPPER_TIMEOUT_SEC}s"
            ),
            "retry_exhausted": True,
        }
    )
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
    """Transcribe answer audio via Gemini with retry and model fallback.

    The STT retry loop runs in a background worker thread, and this function
    waits at most STT_WRAPPER_TIMEOUT_SEC for it. This keeps the Streamlit
    main thread free to answer websocket keepalive pings: a slow STT call
    (e.g. Gemini `temporary_overload`) used to block the single-threaded
    event loop long enough to trigger a keepalive ping timeout, which killed
    the browser connection and kicked students out of the mock exam.

    On wrapper timeout the answer is returned as stt_pending (retryable),
    so the exam continues uninterrupted and STT can be retried later.

    The function signature and return-dict shape are unchanged, so all
    existing call sites (views/_run_*_stt, utils/apply_stt_to_*_saved_row)
    work without modification.
    """
    provider = "gemini"

    future = _STT_EXECUTOR.submit(
        _transcribe_answer_audio_impl,
        audio_bytes,
        mime_type=mime_type,
        language_hint=language_hint,
        question_text=question_text,
        mode=mode,
        question_id=question_id,
        api_key=api_key,
    )
    try:
        return future.result(timeout=STT_WRAPPER_TIMEOUT_SEC)
    except concurrent.futures.TimeoutError:
        # The worker thread is abandoned but not cancelled — it will end on
        # its own once the underlying Gemini call hits STT_TIMEOUT_SEC. The
        # shared pool bounds how many such workers can pile up.
        try:
            logger.warning(
                "[STT_WRAPPER_TIMEOUT] timeout=%ss mode=%s question_id=%s "
                "-> stt_pending",
                STT_WRAPPER_TIMEOUT_SEC,
                mode,
                question_id,
            )
        except Exception:
            pass
        return _stt_timeout_result(provider=provider)
    except Exception as exc:
        # An unexpected failure inside the worker — surface it as a normal
        # failed STT result rather than letting it crash the caller.
        try:
            logger.warning(
                "[STT_WRAPPER_ERROR] exc_type=%s mode=%s question_id=%s",
                type(exc).__name__,
                mode,
                question_id,
            )
        except Exception:
            pass
        out = _stt_empty_result(provider=provider)
        out.update(
            {
                "error_category": "api_error",
                "error_message": f"stt_wrapper_error: {type(exc).__name__}",
            }
        )
        return out


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
