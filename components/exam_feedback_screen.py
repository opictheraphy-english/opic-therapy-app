"""
Shared AI-feedback screen HTML (topic practice; mini/real mock later).

Uses the ``.tq-screen-marker`` scope in ``ui/styles.py`` — same card tone as
the answer-saved screen (``tq-saved-*``), with an emphasized summary variant
(``tq-feedback-*``). Streamlit widgets stay in views; only chrome is HTML here.
"""

from __future__ import annotations

import html
from typing import Tuple

import streamlit as st

_ACCENT_NAMES: Tuple[str, ...] = (
    "teal",
    "blue",
    "purple",
    "pink",
    "amber",
    "coral",
)

_SPARK_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">'
    '<path d="M12 3l1.8 4.6L18 9.4l-4.2 1.8L12 16l-1.8-4.8L6 9.4l4.2-1.8z" />'
    '<path d="M18 14l.9 2.3L21 17.2l-2.1.9L18 20l-.9-1.9L15 17.2l2.1-.9z" />'
    "</svg>"
)


def _svg(*paths: str) -> str:
    inner = "".join(paths)
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{inner}</svg>'
    )


_FB_ICONS = {
    "circle-check": _svg(
        '<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />',
        '<path d="M9 12l2 2l4 -4" />',
    ),
    "target": _svg(
        '<path d="M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" />',
        '<path d="M12 12m-5 0a5 5 0 1 0 10 0a5 5 0 1 0 -10 0" />',
        '<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />',
    ),
    "edit": _svg(
        '<path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />',
        '<path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />',
        '<path d="M16 5l3 3" />',
    ),
    "message-up": _svg(
        '<path d="M3 20l1.3 -3.9a9 8 0 1 1 3.4 2.9l-4.7 1" />',
        '<path d="M12 14v-4" />',
        '<path d="M10 12l2 -2l2 2" />',
    ),
    "key": _svg(
        '<path d="M16.555 3.843l3.602 3.602a2.877 2.877 0 0 1 0 4.069l-2.643 2.643a2.877 2.877 0 0 1 -4.069 0l-.301 -.301l-6.558 6.558a2 2 0 0 1 -1.239 .578l-.175 .008h-1.575a1 1 0 0 1 -.993 -.883l-.007 -.117v-1.575a2 2 0 0 1 .467 -1.284l.119 -.13l.414 -.414h2v-2h2v-2l2.144 -2.144l-.301 -.301a2.877 2.877 0 0 1 0 -4.069l2.643 -2.643a2.877 2.877 0 0 1 4.069 0z" />',
        '<path d="M15 9h.01" />',
    ),
    "flag": _svg(
        '<path d="M5 5a5 5 0 0 1 7 0a5 5 0 0 0 7 0v9a5 5 0 0 1 -7 0a5 5 0 0 0 -7 0v-9z" />',
        '<path d="M5 21v-7" />',
    ),
}


def _normalize_accent(accent: str) -> str:
    key = str(accent or "teal").strip().lower()
    if key not in _ACCENT_NAMES:
        return "teal"
    return key


def build_feedback_label_html(*, accent: str = "teal") -> str:
    """Small "AI 짧은 피드백" label row (icon box + text) + ``.tq-screen-marker``.

    Plant the screen marker here (once per feedback screen) when the header
    above did not already include it.
    """
    accent_key = html.escape(_normalize_accent(accent))
    return (
        '<div class="tq-feedback-label-row">'
        f'<span class="tq-feedback-label-ico tq-feedback-label-ico--{accent_key}">'
        f"{_SPARK_SVG}"
        f"</span>"
        f'<span class="tq-feedback-label-text">AI 짧은 피드백</span>'
        f"</div>"
    )


def build_feedback_summary_html(summary: str, *, accent: str = "teal") -> str:
    """Emphasized one-line summary card (accent-tinted background + border)."""
    accent_key = html.escape(_normalize_accent(accent))
    text = html.escape(str(summary or "").strip())
    return (
        f'<div class="tq-feedback-summary tq-feedback-summary--{accent_key}" '
        f'role="region" aria-label="한 줄 총평">'
        f'<span class="tq-feedback-summary-label">한 줄 총평</span>'
        f'<p class="tq-feedback-summary-text">{text}</p>'
        f"</div>"
    )


def build_feedback_section_card_html(
    label: str,
    body: str,
    *,
    accent: str = "teal",
    icon: str = "circle-check",
    filled: bool = False,
) -> str:
    """One feedback section card (icon + label + body). ``filled`` tints the bg."""
    accent_key = html.escape(_normalize_accent(accent))
    svg = _FB_ICONS.get(icon, _FB_ICONS["circle-check"])
    filled_cls = " tq-feedback-section--filled" if filled else ""
    text = html.escape(str(body or "").strip())
    return (
        f'<div class="tq-feedback-section tq-feedback-section--{accent_key}{filled_cls}" '
        f'role="region" aria-label="{html.escape(label)}">'
        f'<div class="tq-feedback-section-head">'
        f'<span class="tq-feedback-section-ico tq-feedback-section-ico--{accent_key}">'
        f"{svg}</span>"
        f'<span class="tq-feedback-section-label">{html.escape(label)}</span>'
        f"</div>"
        f'<p class="tq-feedback-section-body">{text}</p>'
        f"</div>"
    )


def build_feedback_keyword_chips_html(keywords, *, accent: str = "teal") -> str:
    """Filled card with pill chips for ``keyword_drill`` (placeholder if empty)."""
    accent_key = html.escape(_normalize_accent(accent))
    svg = _FB_ICONS["key"]
    clean = [str(w or "").strip() for w in (keywords or []) if str(w or "").strip()]
    if clean:
        chips = "".join(
            f'<span class="tq-feedback-chip tq-feedback-chip--{accent_key}">'
            f"{html.escape(w)}</span>"
            for w in clean
        )
        body = f'<div class="tq-feedback-chips">{chips}</div>'
    else:
        body = '<p class="tq-feedback-section-body">—</p>'
    return (
        f'<div class="tq-feedback-section tq-feedback-section--{accent_key} '
        f'tq-feedback-section--filled" role="region" aria-label="다시 말하기 키워드">'
        f'<div class="tq-feedback-section-head">'
        f'<span class="tq-feedback-section-ico tq-feedback-section-ico--{accent_key}">'
        f"{svg}</span>"
        f'<span class="tq-feedback-section-label">다시 말하기 키워드</span>'
        f"</div>"
        f"{body}"
        f"</div>"
    )


def render_feedback_label(*, accent: str = "teal") -> None:
    st.markdown(build_feedback_label_html(accent=accent), unsafe_allow_html=True)


def render_feedback_section_card(
    label: str,
    body: str,
    *,
    accent: str = "teal",
    icon: str = "circle-check",
    filled: bool = False,
) -> None:
    st.markdown(
        build_feedback_section_card_html(
            label, body, accent=accent, icon=icon, filled=filled
        ),
        unsafe_allow_html=True,
    )


def render_feedback_keyword_chips(keywords, *, accent: str = "teal") -> None:
    st.markdown(
        build_feedback_keyword_chips_html(keywords, accent=accent),
        unsafe_allow_html=True,
    )


def render_feedback_summary(summary: str, *, accent: str = "teal") -> None:
    st.markdown(
        build_feedback_summary_html(summary, accent=accent),
        unsafe_allow_html=True,
    )
