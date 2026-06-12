"""Patterns — mobile drill screen (tabs → sections → tappable cards)."""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from components.collapsible_section import render_collapsible_section
from components.pattern_card_compact import render_compact_pattern_card
from config.pattern_ui_mapping import TAB_DEFINITIONS, build_pattern_tabs_model
from utils.local_profile import touch_pattern_visit
from utils.session_state import ensure_pattern, sync_settings_to_legacy
from utils.streamlit_ui import ascii_widget_key, clean_visible_label

PATTERN_TABS: tuple[tuple[str, str], ...] = tuple(TAB_DEFINITIONS)

_PATTERN_TAB_IDS: tuple[str, ...] = tuple(tid for tid, _ in PATTERN_TABS)
_PATTERN_TAB_LABEL_BY_ID: Dict[str, str] = {tid: label for tid, label in PATTERN_TABS}
_PATTERN_TAB_DISPLAY_BY_ID: Dict[str, str] = {
    **dict(PATTERN_TABS),
    "roleplay": "롤플",
}


def _render_hero() -> None:
    st.markdown(
        '<div class="pat-hero">'
        '<p class="pat-title">패턴 드릴</p>'
        '<p class="pat-sub">유형을 고르고, 카드를 눌러 예문까지 한 번에</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def _render_pattern_tab_bar(tabs_model: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Horizontal radio tabs — segment control, ASCII-only internal keys."""
    valid_ids = {t["tab_id"] for t in tabs_model}
    if "pattern_active_tab" not in st.session_state:
        st.session_state.pattern_active_tab = _PATTERN_TAB_IDS[0]
    active = str(st.session_state.pattern_active_tab or "")
    if active not in valid_ids:
        st.session_state.pattern_active_tab = _PATTERN_TAB_IDS[0]
        active = _PATTERN_TAB_IDS[0]

    st.markdown(
        '<div class="pat-tab-radio-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.radio(
        "패턴 유형",
        options=list(_PATTERN_TAB_IDS),
        format_func=lambda tab_id: _PATTERN_TAB_DISPLAY_BY_ID.get(
            tab_id, _PATTERN_TAB_LABEL_BY_ID.get(tab_id, tab_id)
        ),
        horizontal=True,
        key="pattern_active_tab",
        label_visibility="collapsed",
    )

    active = str(st.session_state.pattern_active_tab)
    return next(
        (t for t in tabs_model if t["tab_id"] == active),
        tabs_model[0],
    )


def _render_section(
    tab_id: str,
    sec_uid: str,
    title: str,
    patterns: List[Dict[str, Any]],
) -> None:
    if not patterns:
        return

    def _body() -> None:
        for i, pat in enumerate(patterns):
            ex_kw: Dict[str, Any] = {}
            if tab_id in ("experience", "comparison"):
                ex_kw["additional_example_count"] = 2
            render_compact_pattern_card(
                pat, tab_id=tab_id, sec_uid=sec_uid, idx=i, **ex_kw
            )

    render_collapsible_section(
        title or "섹션",
        sec_uid,
        _body,
        count=len(patterns),
        css_scope="pat-sec",
        header_toggle=True,
    )


def render_patterns() -> None:
    sync_settings_to_legacy(st.session_state)
    ensure_pattern(st.session_state)
    touch_pattern_visit(st.session_state)

    st.markdown(
        '<div class="pat-screen-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )

    _render_hero()

    tabs_model = build_pattern_tabs_model()
    active = _render_pattern_tab_bar(tabs_model)
    tid = active["tab_id"]
    sections = active.get("sections") or []
    empty_msg = active.get("empty_message")

    if empty_msg and not sections:
        st.info(empty_msg)
    elif not sections:
        st.caption("내용 없음")
    else:
        for si, sec in enumerate(sections):
            title = clean_visible_label(str(sec.get("title") or ""), "섹션")
            patterns: List[Dict[str, Any]] = sec.get("patterns") or []
            sec_id = str(sec.get("section_id") or si)
            sec_uid = ascii_widget_key(tid, sec_id)
            _render_section(
                tid,
                sec_uid,
                title,
                patterns,
            )
