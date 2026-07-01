"""
Shared answer-saved screen HTML (topic practice shell; mini/real mock later).

Uses ``.tq-screen-marker`` scope in ``ui/styles.py``. Streamlit widgets
(``st.audio``, ``st.button``) stay in views — only chrome is HTML here.
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

_CHECK_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">'
    '<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />'
    '<path d="M9 12l2 2l4 -4" />'
    "</svg>"
)

_RECORDING_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">'
    '<path d="M15 12.9a5 5 0 1 0 -3.902 -3.9" />'
    '<path d="M15 12.9l-3.902 -3.899l-7.513 8.584a2 2 0 1 0 2.827 2.83l8.588 -7.515" />'
    "</svg>"
)

_TRANSCRIPT_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">'
    '<path d="M8 9h8" /><path d="M8 13h6" />'
    '<path d="M5 5a2 2 0 0 1 2 -2h10a2 2 0 0 1 2 2v14l-4 -4h-6a2 2 0 0 1 -2 -2l0 -10" />'
    "</svg>"
)

_SAVED_SECTION_ICO_STYLE = (
    "flex-shrink:0;width:28px;height:28px;border-radius:8px;"
    "display:inline-flex;align-items:center;justify-content:center;"
)

_EMPTY_TRANSCRIPT = "(인식된 텍스트가 아직 없어요.)"


def _normalize_accent(accent: str) -> str:
    key = str(accent or "teal").strip().lower()
    if key not in _ACCENT_NAMES:
        return "teal"
    return key


def build_saved_status_html(*, accent: str = "teal") -> str:
    """Saved status row + ``.tq-screen-marker`` (call once per saved screen)."""
    accent_key = html.escape(_normalize_accent(accent))
    return (
        '<div class="tq-screen-marker" aria-hidden="true"></div>'
        f'<div class="tq-saved-status tq-saved-status--{accent_key}" role="status">'
        f'<span class="tq-saved-status-ico tq-saved-status-ico--{accent_key}">'
        f"{_CHECK_SVG}"
        f"</span>"
        f'<span class="tq-saved-status-text">답변이 저장되었어요</span>'
        f"</div>"
    )


def build_saved_recording_html(*, accent: str = "teal") -> str:
    """Recording card top — pair with ``render_recording_playback_player`` below."""
    accent_key = html.escape(_normalize_accent(accent))
    return (
        f'<div class="tq-saved-section tq-saved-recording-top tq-saved-section--{accent_key}">'
        f'<div class="tq-saved-section-head">'
        f'<span class="tq-saved-section-ico tq-saved-section-ico--{accent_key}">'
        f"{_RECORDING_SVG}"
        f"</span>"
        f'<span class="tq-saved-label">내 녹음 다시 듣기</span>'
        f"</div>"
        f"</div>"
    )


def build_saved_transcript_html(*, transcript: str, accent: str = "teal") -> str:
    """Full card for STT / saved answer text."""
    accent_key = html.escape(_normalize_accent(accent))
    text = str(transcript or "").strip()
    if text:
        body = f'<p class="tq-saved-transcript">{html.escape(text)}</p>'
    else:
        body = (
            f'<p class="tq-saved-transcript tq-saved-transcript--empty">'
            f"{html.escape(_EMPTY_TRANSCRIPT)}"
            f"</p>"
        )
    return (
        '<div class="tq-screen-marker" aria-hidden="true"></div>'
        f'<div class="tq-saved-section tq-saved-section--{accent_key}" role="region" '
        f'aria-label="AI가 인식한 답변">'
        f'<div class="tq-saved-section-head">'
        f'<span class="tq-saved-section-ico tq-saved-section-ico--{accent_key}" '
        f'style="{_SAVED_SECTION_ICO_STYLE}">'
        f"{_TRANSCRIPT_SVG}"
        f"</span>"
        f'<span class="tq-saved-label">AI가 인식한 답변</span>'
        f"</div>"
        f"{body}"
        f"</div>"
    )


def render_saved_status(*, accent: str = "teal") -> None:
    st.markdown(build_saved_status_html(accent=accent), unsafe_allow_html=True)


def render_saved_recording_header(*, accent: str = "teal") -> None:
    st.markdown(build_saved_recording_html(accent=accent), unsafe_allow_html=True)


def render_saved_transcript(*, transcript: str, accent: str = "teal") -> None:
    st.markdown(
        build_saved_transcript_html(transcript=transcript, accent=accent),
        unsafe_allow_html=True,
    )
