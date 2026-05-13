"""Pre-generated pattern MP3 assets under assets/pattern_audio/ (no Streamlit import required)."""

from __future__ import annotations

from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
PATTERN_AUDIO_DIR = _ROOT / "assets" / "pattern_audio"


def asset_path_for(audio_file: str) -> Path:
    return PATTERN_AUDIO_DIR / audio_file


def mime_for_audio_filename(filename: str) -> str:
    lower = (filename or "").lower()
    if lower.endswith(".wav"):
        return "audio/wav"
    return "audio/mpeg"
