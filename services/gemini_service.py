"""Gemini API helpers (model discovery). Heavy lifting: ``services.evaluation.gemini_multimodal_pipeline``."""

from __future__ import annotations

from typing import List

from services.evaluation.gemini_multimodal_pipeline import list_available_gemini_models


def list_models(api_key: str) -> List[str]:
    return list_available_gemini_models(api_key)
