"""Temporary audio pipeline diagnostics — search logs for ``[AUDIO_DIAG]``."""

from __future__ import annotations

import logging
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)


def _q_label(q_index: Optional[int] = None) -> str:
    if q_index is not None:
        return str(q_index)
    try:
        from services.evaluation.ai_diag import _DIAG_CTX

        ctx = _DIAG_CTX.get()
        if ctx.get("question_index") not in (None, ""):
            return str(ctx.get("question_index"))
        if ctx.get("question_id") not in (None, ""):
            return f"id:{ctx.get('question_id')}"
    except Exception:
        pass
    return "—"


def _preview(text: str, limit: int = 80) -> str:
    one = " ".join((text or "").split())
    if len(one) <= limit:
        return one
    return one[: limit - 1] + "…"


def log_captured(
    *,
    q_index: Optional[int] = None,
    audio_bytes: bytes | None = None,
    mime_type: str = "",
) -> None:
    nbytes = len(audio_bytes) if audio_bytes else 0
    logger.info(
        "[AUDIO_DIAG] captured audio | q=%s | bytes=%s | mime=%s",
        _q_label(q_index),
        nbytes,
        mime_type or "—",
    )


def log_before_gemini(
    *,
    q_index: Optional[int] = None,
    audio_bytes: bytes | None = None,
    mime_type: str = "",
) -> None:
    nbytes = len(audio_bytes) if audio_bytes else 0
    logger.info(
        "[AUDIO_DIAG] before gemini | q=%s | bytes=%s | mime=%s",
        _q_label(q_index),
        nbytes,
        mime_type or "—",
    )


def log_after_gemini(
    *,
    q_index: Optional[int] = None,
    response_ok: bool = False,
    raw_keys: Optional[list[str]] = None,
) -> None:
    keys = raw_keys if raw_keys is not None else []
    logger.info(
        "[AUDIO_DIAG] after gemini | q=%s | response_ok=%s | raw_keys=%s",
        _q_label(q_index),
        response_ok,
        keys,
    )


def log_transcript(
    *,
    q_index: Optional[int] = None,
    transcript: str = "",
) -> None:
    tx = (transcript or "").strip()
    logger.info(
        "[AUDIO_DIAG] transcript | q=%s | transcript_len=%s | transcript_preview=%s",
        _q_label(q_index),
        len(tx),
        _preview(tx),
    )


def log_no_speech_gate(
    *,
    q_index: Optional[int] = None,
    audio_bytes: bytes | None = None,
    transcript: str = "",
    trust_result: str = "",
    status: str = "",
) -> None:
    nbytes = len(audio_bytes) if audio_bytes else 0
    logger.info(
        "[AUDIO_DIAG] no_speech_gate | q=%s | bytes=%s | transcript_len=%s | "
        "trust_result=%s | status=%s",
        _q_label(q_index),
        nbytes,
        len((transcript or "").strip()),
        trust_result or "—",
        status or "—",
    )


def trust_result_label(result: Optional[Mapping[str, Any]]) -> str:
    if not isinstance(result, dict):
        return "—"
    if result.get("trust_gate_passed") is True:
        return "passed"
    if result.get("trust_gate_rejected"):
        return "rejected"
    if result.get("no_speech_detected"):
        return "no_speech_flag"
    return str(result.get("trust_gate_result") or "—")
