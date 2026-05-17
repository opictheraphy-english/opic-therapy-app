"""MIME guess for inline audio bytes (WAV / WebM / MP3)."""

from __future__ import annotations

from typing import Optional


def guess_audio_mime(audio_bytes: bytes) -> str:
    """인라인 오디오 파트용 MIME 추정 (WAV / WebM / MP3 등)."""
    if not audio_bytes or len(audio_bytes) < 12:
        return "audio/wav"
    if audio_bytes[:4] == b"RIFF":
        return "audio/wav"
    if audio_bytes[:4] == b"\x1a\x45\xdf\xa3":
        return "audio/webm"
    if audio_bytes[:3] == b"ID3" or (
        len(audio_bytes) >= 2 and audio_bytes[:2] in (b"\xff\xfb", b"\xff\xf3")
    ):
        return "audio/mpeg"
    return "audio/wav"


def resolve_audio_mime(audio_bytes: bytes, mime_guess: Optional[str] = None) -> str:
    """Prefer recorder/browser MIME; fall back to byte sniffing."""
    mg = (mime_guess or "").strip()
    if mg:
        if "/" not in mg:
            from utils.audio_utils import mime_from_audio_format

            return mime_from_audio_format(mg)
        return mg
    return guess_audio_mime(audio_bytes)
