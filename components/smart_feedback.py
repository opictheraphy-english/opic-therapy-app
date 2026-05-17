"""Render the smart-feedback cards (grammar corrections + alt expressions)."""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

import streamlit as st

from utils.grammar_corrections import (
    detect_alternative_expressions,
    detect_grammar_corrections,
)
from utils.streamlit_ui import clean_visible_label


def render_grammar_corrections(
    transcript: str,
    *,
    title: str = "📝 문법 교정",
    empty_message: Optional[str] = "이번 답변에서 자주 보이는 문법 슬립은 감지되지 않았습니다.",
    show_heading: bool = True,
    hits: Optional[List[Dict[str, str]]] = None,
) -> int:
    """Render grammar-correction cards; return hit count."""
    rows = hits if hits is not None else detect_grammar_corrections(transcript)
    if show_heading and title:
        safe_title = clean_visible_label(title, "")
        if safe_title:
            st.markdown(f"##### {html.escape(safe_title)}")
    if not rows:
        if empty_message:
            st.markdown(
                f'<p class="mx-coach-empty-note">{html.escape(empty_message)}</p>',
                unsafe_allow_html=True,
            )
        return 0
    cards: List[str] = []
    for row in rows:
        wrong = html.escape(row.get("wrong", ""))
        right = html.escape(row.get("right", ""))
        note = html.escape(row.get("note", ""))
        cards.append(
            f'<div class="grammar-fix coach-gf-card">'
            f'<p class="gf-label">문장</p>'
            f'<p class="gf-val gf-bad">{wrong}</p>'
            f'<p class="gf-label">교정</p>'
            f'<p class="gf-val gf-good">{right}</p>'
            f'<p class="gf-label">이유</p>'
            f'<p class="gf-note">{note}</p>'
            f"</div>"
        )
    st.markdown("".join(cards), unsafe_allow_html=True)
    return len(rows)


def render_alternative_expressions(
    transcript: str,
    *,
    title: str = "💡 표현 업그레이드",
    empty_message: Optional[str] = None,
    show_heading: bool = True,
    hits: Optional[List[Dict[str, Any]]] = None,
) -> int:
    """Render expression-upgrade cards; return hit count."""
    rows = hits if hits is not None else detect_alternative_expressions(transcript)
    if show_heading and title:
        safe_title = clean_visible_label(title, "")
        if safe_title:
            st.markdown(f"##### {html.escape(safe_title)}")
    if not rows:
        if empty_message:
            st.markdown(
                f'<p class="mx-coach-empty-note">{html.escape(empty_message)}</p>',
                unsafe_allow_html=True,
            )
        return 0
    cards: List[str] = []
    for row in rows:
        phrase = html.escape(str(row.get("phrase", "")))
        note = html.escape(str(row.get("note", "")))
        alts = row.get("alternatives") or []
        if not isinstance(alts, list):
            continue
        alt_html = " · ".join(
            f'<span class="alt-chip">{html.escape(str(a))}</span>' for a in alts[:3]
        )
        cards.append(
            f'<div class="alt-card coach-alt-card">'
            f'<p class="gf-label">Before</p>'
            f'<p class="gf-val gf-bad">{phrase}</p>'
            f'<p class="gf-label">Better</p>'
            f'<div class="alt-list">{alt_html}</div>'
            f'<p class="gf-label">Why</p>'
            f'<p class="alt-note">{note}</p>'
            f"</div>"
        )
    st.markdown("".join(cards), unsafe_allow_html=True)
    return len(rows)


def render_smart_feedback_block(transcript: str) -> Dict[str, int]:
    """Render both cards back-to-back."""
    grammar_hits = render_grammar_corrections(transcript)
    alt_hits = render_alternative_expressions(transcript)
    return {"grammar": grammar_hits, "alternatives": alt_hits}


__all__ = [
    "render_grammar_corrections",
    "render_alternative_expressions",
    "render_smart_feedback_block",
]
