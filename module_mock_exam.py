"""Backward-compatible shim for legacy imports."""

from services.evaluation.audio_mime import guess_audio_mime
from services.mock_exam.gemini_mock_exam_prompt import (
    GEMINI_MODEL_ID,
    MODEL_NAME,
    build_mock_exam_analysis_prompt,
)

__all__ = [
    "GEMINI_MODEL_ID",
    "MODEL_NAME",
    "guess_audio_mime",
    "build_mock_exam_analysis_prompt",
]
