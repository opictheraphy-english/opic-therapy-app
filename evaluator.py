"""Backward-compatible shim — implementation in ``services.evaluation``."""

from services.evaluation.gemini_multimodal_pipeline import (
    analyze_answer,
    analyze_audio_with_ai,
    evaluate_grading_logic,
    list_available_gemini_models,
)

__all__ = [
    "analyze_answer",
    "analyze_audio_with_ai",
    "evaluate_grading_logic",
    "list_available_gemini_models",
]
