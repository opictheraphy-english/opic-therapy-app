"""Streamlit widget helpers — ASCII keys only; never show keys as labels."""

from __future__ import annotations

import re
from typing import Callable


def ascii_widget_key(*parts: str, max_len: int = 72) -> str:
    """Build a safe Streamlit ``key=`` suffix (ASCII only)."""
    raw = "_".join(str(p or "") for p in parts)
    x = re.sub(r"[^a-zA-Z0-9_-]", "_", raw.strip())
    return (x[:max_len]) or "x"


def is_leaked_internal_label(text: str) -> bool:
    """True when text looks like a Streamlit auto-key (key…_arrow_*)."""
    t = (text or "").strip()
    if not t:
        return True
    if "_arrow_right" in t or "_arrow_down" in t:
        return True
    if t.startswith("key") and len(t) > 3 and ("_" in t[3:] or t[3:].isalnum()):
        return True
    return False


def safe_display_label(text: str, fallback: str = "") -> str:
    """User-facing label; never return internal widget keys."""
    t = (text or "").strip()
    if is_leaked_internal_label(t):
        return fallback
    return t


def clean_visible_label(label: str, fallback: str = "자세히 보기") -> str:
    """Safety fallback when a label looks like a Streamlit auto-key."""
    return safe_display_label(label, fallback) or fallback
