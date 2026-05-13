"""Facade over hybrid evaluation — UI should call this instead of the pipeline module directly."""

from __future__ import annotations

from typing import Any, Dict

from services.evaluation.gemini_multimodal_pipeline import (
    analyze_answer as _engine_analyze_answer,
    analyze_audio_with_ai as _engine_analyze_audio,
)


def analyze_audio_with_ai(
    audio_bytes: bytes,
    question_text: str,
    api_key: str,
    difficulty: int = 5,
) -> Dict[str, Any]:
    """Primary entry: Gemini semantic + rule calibration."""
    return _engine_analyze_audio(audio_bytes, question_text, api_key, difficulty)


def analyze_answer(audio_bytes: bytes, question_text: str, api_key: str) -> Dict[str, Any]:
    return _engine_analyze_answer(audio_bytes, question_text, api_key)
