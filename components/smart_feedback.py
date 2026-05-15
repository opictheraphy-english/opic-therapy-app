"""Render the smart-feedback cards (grammar corrections + alt expressions).

Both the per-question coaching card (``views.mock_exam._render_report``) and
the final-report expander (``views.final_report``) consume these so the
visual is consistent across the app.

The detectors live in :mod:`utils.grammar_corrections` and are pure regex —
no LLM calls. The renderer is intentionally tiny so the report stays mobile-
friendly even when many hits surface.
"""

from __future__ import annotations

import html
from typing import Dict, List, Optional

import streamlit as st

from utils.grammar_corrections import (
    detect_alternative_expressions,
    detect_grammar_corrections,
)


def render_grammar_corrections(
    transcript: str,
    *,
    title: str = "📝 문법 교정",
    empty_message: Optional[str] = "이번 답변에서 자주 보이는 문법 슬립은 감지되지 않았습니다.",
    show_heading: bool = True,
) -> int:
    """Render the grammar-correction card and return the number of hits shown."""
    hits = detect_grammar_corrections(transcript)
    if show_heading and title:
        st.markdown(f"##### {title}")
    if not hits:
        if empty_message:
            st.caption(empty_message)
        return 0
    cards: List[str] = []
    for row in hits:
        wrong = html.escape(row.get("wrong", ""))
        right = html.escape(row.get("right", ""))
        note = html.escape(row.get("note", ""))
        cards.append(
            f'<div class="grammar-fix coach-gf-card">'
            f'<div class="gf-line gf-bad-line">'
            f'<span class="gf-mark gf-bad">✗</span>'
            f'<span class="gf-text">{wrong}</span></div>'
            f'<div class="gf-line gf-good-line">'
            f'<span class="gf-mark gf-good">✓</span>'
            f'<span class="gf-text gf-good">{right}</span></div>'
            f'<div class="gf-note">{note}</div></div>'
        )
    st.markdown("".join(cards), unsafe_allow_html=True)
    return len(hits)


def render_alternative_expressions(
    transcript: str,
    *,
    title: str = "💡 대체 표현 추천",
    empty_message: Optional[str] = "이번 답변에서 상향 교체가 가능한 표현은 발견되지 않았습니다.",
    show_heading: bool = True,
) -> int:
    """Render the alternative-expression card and return the number of hits."""
    hits = detect_alternative_expressions(transcript)
    if show_heading and title:
        st.markdown(f"##### {title}")
    if not hits:
        if empty_message:
            st.caption(empty_message)
        return 0
    cards: List[str] = []
    for row in hits:
        phrase = html.escape(str(row.get("phrase", "")))
        note = html.escape(str(row.get("note", "")))
        alts = row.get("alternatives") or []
        if not isinstance(alts, list):
            continue
        alt_chips = "".join(
            f'<span class="alt-chip">{html.escape(str(a))}</span>' for a in alts
        )
        cards.append(
            f'<div class="alt-card coach-alt-card">'
            f'<div class="alt-header">"<b>{phrase}</b>"</div>'
            f'<div class="alt-list">{alt_chips}</div>'
            f'<div class="alt-note">{note}</div></div>'
        )
    st.markdown("".join(cards), unsafe_allow_html=True)
    return len(hits)


def render_smart_feedback_block(transcript: str) -> Dict[str, int]:
    """Render both cards back-to-back. Returns ``{grammar, alternatives}`` hit counts."""
    grammar_hits = render_grammar_corrections(transcript)
    alt_hits = render_alternative_expressions(transcript)
    return {"grammar": grammar_hits, "alternatives": alt_hits}


__all__ = [
    "render_grammar_corrections",
    "render_alternative_expressions",
    "render_smart_feedback_block",
]
