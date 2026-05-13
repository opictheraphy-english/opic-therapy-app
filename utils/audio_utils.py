"""Audio helper utilities for Streamlit payloads."""

from __future__ import annotations

from typing import Any, Optional, Tuple


def mime_from_audio_format(audio_format: str) -> str:
    f = (audio_format or "audio/mp3").lower()
    if "wav" in f:
        return "audio/wav"
    return "audio/mpeg"


def extract_playable_audio(payload: Any) -> Tuple[Optional[bytes], Optional[str]]:
    if not payload:
        return None, None
    if isinstance(payload, dict):
        audio_bytes = payload.get("audio_bytes")
        audio_format = payload.get("audio_format", "audio/mp3")
    else:
        audio_bytes = payload
        audio_format = "audio/mp3"
    if not isinstance(audio_bytes, (bytes, bytearray)):
        return None, None
    if len(audio_bytes) < 512:
        return None, None
    return bytes(audio_bytes), audio_format
