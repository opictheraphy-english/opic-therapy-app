"""
Developer-only diagnostics when Gemini analysis is deferred (pending).

Logs use ``[AI_PENDING_REASON]`` — never shown to students unless ``show_dev_debug``.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)

ErrorSource = Union[str, BaseException, None]

_CATEGORY_QUOTA = "quota_or_rate_limit"
_CATEGORY_OVERLOAD = "temporary_overload"
_CATEGORY_TIMEOUT = "timeout"
_CATEGORY_AUDIO = "audio_format_error"
_CATEGORY_EMPTY = "empty_response"
_CATEGORY_LOCK = "lock_queue_timeout"
_CATEGORY_UNKNOWN = "unknown"

_LEGACY_KIND_MAP = {
    _CATEGORY_QUOTA: "rate_limit",
    _CATEGORY_OVERLOAD: "overload",
    _CATEGORY_TIMEOUT: "timeout",
    _CATEGORY_AUDIO: "engine_path",
    _CATEGORY_EMPTY: "unknown",
    _CATEGORY_LOCK: "timeout",
    _CATEGORY_UNKNOWN: "unknown",
}


def classify_ai_error(
    source: ErrorSource,
    *,
    empty_response: bool = False,
) -> str:
    """Coarse failure category for pending analysis (developer metadata)."""
    if empty_response:
        return _CATEGORY_EMPTY

    text = _message_text(source)
    if not text:
        return _CATEGORY_UNKNOWN

    upper = text.upper()
    if any(
        tok in upper
        for tok in (
            "429",
            "RESOURCE_EXHAUSTED",
            "RESOURCEEXHAUSTED",
            "QUOTA",
            "RATE LIMIT",
            "RATE_LIMIT",
            "TOO MANY REQUESTS",
        )
    ) or "할당량" in text:
        return _CATEGORY_QUOTA

    if any(
        tok in upper
        for tok in (
            "503",
            "UNAVAILABLE",
            "OVERLOAD",
            "OVERLOADED",
            "SERVICE UNAVAILABLE",
        )
    ):
        return _CATEGORY_OVERLOAD

    if any(
        tok in upper
        for tok in (
            "TIMEOUT",
            "DEADLINE",
            "504",
            "TIMED OUT",
            "LOCK ACQUIRE",
            "대기열 타임아웃",
        )
    ):
        return _CATEGORY_TIMEOUT

    if any(
        tok in upper
        for tok in (
            "MIME",
            "UNSUPPORTED",
            "AUDIO FORMAT",
            "INVALID AUDIO",
            "BAD AUDIO",
            "AUDIO/WAV",
            "DECODE",
        )
    ):
        return _CATEGORY_AUDIO

    if any(
        tok in text
        for tok in (
            "비어",
            "empty",
            "EMPTY TEXT",
            "EMPTY RESPONSE",
            "결과값이 비어",
        )
    ):
        return _CATEGORY_EMPTY

    if "대기열" in text and "타임아웃" in text:
        return _CATEGORY_LOCK

    return _CATEGORY_UNKNOWN


def category_to_legacy_error_kind(category: str) -> str:
    return _LEGACY_KIND_MAP.get(category or _CATEGORY_UNKNOWN, "unknown")


def error_type_name(source: ErrorSource) -> str:
    if isinstance(source, BaseException):
        return type(source).__name__
    text = _message_text(source)
    if text and ":" in text:
        head = text.split(":", 1)[0].strip()
        if head and head[0].isalpha():
            return head
    return "Error"


def analysis_error_short(message: str, *, limit: int = 180) -> str:
    text = " ".join((message or "").split())
    if not text:
        return ""
    text = re.sub(r"(?i)api[_-]?key[=:]\s*\S+", "api_key=[redacted]", text)
    text = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "[redacted]", text)
    if len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def _message_text(source: ErrorSource) -> str:
    if source is None:
        return ""
    if isinstance(source, BaseException):
        return f"{type(source).__name__}: {source}"
    return str(source)


def log_ai_pending_reason(
    *,
    question_index: Optional[int] = None,
    mode: str = "",
    audio_bytes_len: int = 0,
    mime_type: str = "",
    model: str = "",
    error_type: str = "",
    error_message: str = "",
    retry_count: int = 0,
    elapsed_ms: Optional[float] = None,
    empty_response: bool = False,
    category: str = "",
) -> str:
    """Emit a single-line developer log; returns the resolved category."""
    cat = category or classify_ai_error(
        error_message, empty_response=empty_response
    )
    short = analysis_error_short(error_message)
    etype = error_type or error_type_name(error_message)
    elapsed_part = ""
    if elapsed_ms is not None:
        try:
            elapsed_part = f" elapsed_ms={int(float(elapsed_ms))}"
        except (TypeError, ValueError):
            pass
    logger.warning(
        "[AI_PENDING_REASON] q=%s mode=%s bytes=%s mime=%s model=%s "
        "error_type=%s category=%s empty_response=%s retry_count=%s%s error=%r",
        question_index if question_index is not None else "—",
        mode or "—",
        audio_bytes_len,
        mime_type or "—",
        model or "—",
        etype,
        cat,
        bool(empty_response),
        retry_count,
        elapsed_part,
        short,
    )
    return cat


def build_pending_error_metadata(
    error_message: str,
    *,
    exc: ErrorSource = None,
    empty_response: bool = False,
    question_index: Optional[int] = None,
    mode: str = "",
    audio_bytes_len: int = 0,
    mime_type: str = "",
    model: str = "",
    retry_count: int = 0,
    elapsed_ms: Optional[float] = None,
) -> Dict[str, Any]:
    """Metadata stored on pending rows + ``pending_recovery`` (not shown to students)."""
    src = exc if exc is not None else error_message
    category = classify_ai_error(src, empty_response=empty_response)
    short = analysis_error_short(_message_text(src) or error_message)
    etype = error_type_name(src)
    log_ai_pending_reason(
        question_index=question_index,
        mode=mode,
        audio_bytes_len=audio_bytes_len,
        mime_type=mime_type,
        model=model,
        error_type=etype,
        error_message=short or error_message,
        retry_count=retry_count,
        elapsed_ms=elapsed_ms,
        empty_response=empty_response,
        category=category,
    )
    return {
        "analysis_error_category": category,
        "analysis_error_short": short,
        "analysis_error_type": etype,
    }


def render_ai_pending_dev_expander(
    data: Optional[Dict[str, Any]],
    *,
    pending_recovery: Optional[Dict[str, Any]] = None,
) -> None:
    """Developer-only expander — requires ``show_dev_debug``."""
    try:
        import streamlit as st
    except Exception:
        return

    if not st.session_state.get("show_dev_debug", False):
        return

    src = dict(pending_recovery or {})
    res = data if isinstance(data, dict) else {}
    for key in (
        "analysis_error_category",
        "analysis_error_short",
        "analysis_error_type",
        "analysis_attempts",
        "mime_type",
        "audio_mime_guess",
        "model_used",
    ):
        if key in res and key not in src:
            src[key] = res.get(key)
    if not any(
        src.get(k)
        for k in (
            "analysis_error_category",
            "analysis_error_short",
            "error_message",
            "error_kind",
        )
    ):
        return

    with st.expander("개발 확인: AI 분석 지연 원인", expanded=False):
        st.text(f"error_type: {src.get('analysis_error_type') or '—'}")
        st.text(f"category: {src.get('analysis_error_category') or src.get('error_kind') or '—'}")
        st.text(f"short_error: {src.get('analysis_error_short') or src.get('error_message') or '—'}")
        st.text(f"audio_bytes: {src.get('pending_audio_bytes') or src.get('source_audio_size_bytes') or '—'}")
        st.text(f"mime_type: {src.get('mime_type') or src.get('audio_mime_guess') or '—'}")
        st.text(f"model: {src.get('model') or src.get('model_used') or '—'}")
        st.text(f"retry_count: {src.get('retry_count') or src.get('attempts') or src.get('analysis_attempts') or '—'}")
