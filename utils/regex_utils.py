"""Centralized regex helpers."""

from __future__ import annotations

import re


def compile_word_boundary(term: str) -> re.Pattern[str]:
    return re.compile(rf"\b{re.escape(term)}\b", re.I)
