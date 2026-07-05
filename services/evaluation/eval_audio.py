"""Real audio duration — stdlib WAV header, pydub, MIME-aware byte fallback."""

from __future__ import annotations

import io
import logging
import os
import wave
from typing import Tuple

logger = logging.getLogger(__name__)

# MIME-aware byte-rate heuristics when codecs are unavailable (underestimate → inflate WPS).
_FALLBACK_BYTES_PER_SEC_DEFAULT = 12_000.0
_FALLBACK_BYTES_PER_SEC_BY_MIME: dict[str, float] = {
    "audio/webm": 10_000.0,
    "audio/ogg": 10_000.0,
    "audio/mpeg": 16_000.0,
    "audio/mp3": 16_000.0,
    "audio/mp4": 14_000.0,
    "audio/m4a": 14_000.0,
    "audio/wav": 32_000.0,
    "audio/x-wav": 32_000.0,
}


def _fallback_bytes_per_sec(mime_guess: str, audio_bytes: bytes) -> float:
    mime = (mime_guess or "").split(";", 1)[0].strip().lower()
    if mime in _FALLBACK_BYTES_PER_SEC_BY_MIME:
        return _FALLBACK_BYTES_PER_SEC_BY_MIME[mime]
    if audio_bytes[:4] == b"RIFF":
        return _FALLBACK_BYTES_PER_SEC_BY_MIME["audio/wav"]
    if audio_bytes[:4] == b"\x1a\x45\xdf\xa3":
        return _FALLBACK_BYTES_PER_SEC_BY_MIME["audio/webm"]
    if audio_bytes[:3] == b"ID3" or (
        len(audio_bytes) >= 2 and audio_bytes[:2] in (b"\xff\xfb", b"\xff\xf3")
    ):
        return _FALLBACK_BYTES_PER_SEC_BY_MIME["audio/mp3"]
    try:
        return float(os.getenv("STT_FALLBACK_BYTES_PER_SEC") or _FALLBACK_BYTES_PER_SEC_DEFAULT)
    except (TypeError, ValueError):
        return _FALLBACK_BYTES_PER_SEC_DEFAULT


def _duration_wav_stdlib(audio_bytes: bytes) -> float | None:
    if not audio_bytes or len(audio_bytes) < 44 or audio_bytes[:4] != b"RIFF":
        return None
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate() or 1
            return round(frames / float(rate), 3)
    except Exception:
        return None


def _duration_pydub(audio_bytes: bytes, mime_guess: str) -> float | None:
    try:
        from pydub import AudioSegment  # type: ignore[import-untyped]
    except ImportError:
        return None

    fmt_map = {
        "audio/wav": "wav",
        "audio/x-wav": "wav",
        "audio/webm": "webm",
        "audio/mpeg": "mp3",
        "audio/mp3": "mp3",
        "audio/ogg": "ogg",
    }
    fmt = fmt_map.get((mime_guess or "").lower(), None)
    if not fmt:
        if audio_bytes[:4] == b"RIFF":
            fmt = "wav"
        elif audio_bytes[:4] == b"\x1a\x45\xdf\xa3":
            fmt = "webm"
        elif audio_bytes[:3] == b"ID3" or (
            len(audio_bytes) >= 2 and audio_bytes[:2] in (b"\xff\xfb", b"\xff\xf3")
        ):
            fmt = "mp3"
        else:
            fmt = "wav"

    try:
        seg = AudioSegment.from_file(io.BytesIO(audio_bytes), format=fmt)
        return round(len(seg) / 1000.0, 3)
    except Exception as e:
        logger.debug("pydub duration failed (%s): %s", fmt, e)
        return None


def _duration_fallback_bytes(audio_bytes: bytes, mime_guess: str = "") -> float:
    """Conservative fallback when codecs unavailable — MIME-tuned bytes/sec."""
    if not audio_bytes:
        return 0.0
    bps = _fallback_bytes_per_sec(mime_guess, audio_bytes)
    return round(len(audio_bytes) / bps, 3)


def compute_audio_duration_seconds(audio_bytes: bytes, mime_guess: str = "") -> Tuple[float, str]:
    """
    Returns (duration_seconds, method_label).
    Priority: stdlib WAV header → pydub → MIME-aware byte heuristic.
    """
    if not audio_bytes:
        return 0.0, "empty"

    legacy_bps = 32_000.0
    legacy_est = round(len(audio_bytes) / legacy_bps, 3) if audio_bytes else 0.0

    d = _duration_wav_stdlib(audio_bytes)
    if d is not None and d > 0:
        try:
            logger.info(
                "[STT_DURATION] audio_len=%s mime=%s legacy_est=%.3f header=%.3f method=wave",
                len(audio_bytes),
                mime_guess or "—",
                legacy_est,
                d,
            )
        except Exception:
            pass
        return d, "wave"

    d = _duration_pydub(audio_bytes, mime_guess)
    if d is not None and d > 0:
        try:
            logger.info(
                "[STT_DURATION] audio_len=%s mime=%s legacy_est=%.3f pydub=%.3f method=pydub",
                len(audio_bytes),
                mime_guess or "—",
                legacy_est,
                d,
            )
        except Exception:
            pass
        return d, "pydub"

    fallback = _duration_fallback_bytes(audio_bytes, mime_guess)
    try:
        logger.info(
            "[STT_DURATION] audio_len=%s mime=%s legacy_est=%.3f fallback=%.3f "
            "method=fallback_bytes bps=%.0f",
            len(audio_bytes),
            mime_guess or "—",
            legacy_est,
            fallback,
            _fallback_bytes_per_sec(mime_guess, audio_bytes),
        )
    except Exception:
        pass
    return fallback, "fallback_bytes"


def build_audio_info(audio_bytes: bytes, mime_guess: str) -> dict:
    dur, method = compute_audio_duration_seconds(audio_bytes, mime_guess)
    return {
        "duration_seconds": dur,
        "duration_method": method,
        "source_bytes": len(audio_bytes),
    }
