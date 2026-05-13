"""Thin wrappers for regex-heavy scoring helpers used by reports."""

from __future__ import annotations

import re


def word_boundary_pattern(term: str) -> str:
    return rf"\b{re.escape(term)}\b"
