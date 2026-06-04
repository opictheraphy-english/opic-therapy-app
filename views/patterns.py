"""Patterns — mobile drill screen (phase-1 UI: compact hero, tappable rows, merged detail).

Tab → section (inline header toggle) → pattern row (card tap) → merged 예문 block.
"""

from __future__ import annotations

import html as html_mod
from typing import Any, Dict, List

import streamlit as st

from components.pattern_card_compact import pat_chevron_markup, render_compact_pattern_card
from config.pattern_ui_mapping import TAB_DEFINITIONS, build_pattern_tabs_model
from utils.local_profile import touch_pattern_visit
from utils.session_state import ensure_pattern, sync_settings_to_legacy
from utils.streamlit_ui import ascii_widget_key, clean_visible_label

# Visible labels only — never use these strings as Streamlit widget keys.
PATTERN_TABS: tuple[tuple[str, str], ...] = tuple(TAB_DEFINITIONS)

_PATTERN_TAB_IDS: tuple[str, ...] = tuple(tid for tid, _ in PATTERN_TABS)
_PATTERN_TAB_LABEL_BY_ID: Dict[str, str] = {tid: label for tid, label in PATTERN_TABS}


def _render_hero() -> None:
    st.markdown(
        '<div class="pat-hero">'
        '<p class="pat-eyebrow">Patterns</p>'
        '<p class="pat-title">패턴 드릴</p>'
        '<p class="pat-sub">탭에서 유형을 고르고, 패턴 카드를 눌러 예문과 연습을 확인하세요.</p>'
        "</div>",
        unsafe_allow_html=True,
    )


def _render_pattern_tab_bar(tabs_model: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Horizontal radio tabs — visible Korean labels, ASCII-only internal keys."""
    valid_ids = {t["tab_id"] for t in tabs_model}
    if "pattern_active_tab" not in st.session_state:
        st.session_state.pattern_active_tab = _PATTERN_TAB_IDS[0]
    active = str(st.session_state.pattern_active_tab or "")
    if active not in valid_ids:
        st.session_state.pattern_active_tab = _PATTERN_TAB_IDS[0]
        active = _PATTERN_TAB_IDS[0]

    st.markdown('<div class="pat-tab-radio" role="tablist" aria-label="패턴 유형">', unsafe_allow_html=True)
    st.radio(
        "패턴 유형",
        options=list(_PATTERN_TAB_IDS),
        format_func=lambda tab_id: _PATTERN_TAB_LABEL_BY_ID.get(tab_id, tab_id),
        horizontal=True,
        key="pattern_active_tab",
        label_visibility="collapsed",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    active = str(st.session_state.pattern_active_tab)
    return next(
        (t for t in tabs_model if t["tab_id"] == active),
        tabs_model[0],
    )


def _render_section(tab_id: str, sec_uid: str, title: str, patterns: List[Dict[str, Any]]) -> None:
    """Section with title + count + toggle on one row (no separate full-width button)."""
    if not patterns:
        return

    safe_title = clean_visible_label((title or "").strip(), "섹션")
    title_h = html_mod.escape(safe_title)
    wid = ascii_widget_key("patsec", tab_id, sec_uid)
    open_key = f"pat_sec_open_{wid}"
    if open_key not in st.session_state:
        st.session_state[open_key] = False
    is_open = bool(st.session_state[open_key])
    open_cls = " pat-sec-head--open" if is_open else ""

    st.markdown(
        f'<div class="pat-sec-stack">'
        f'<div class="pat-sec-head pat-sec-head--inline{open_cls}">'
        f'<span class="pat-sec-title">{title_h}</span>'
        f'<span class="pat-sec-count">{len(patterns)}</span>'
        f"{pat_chevron_markup()}"
        "</div></div>",
        unsafe_allow_html=True,
    )
    if st.button(
        " ",
        key=f"pat_sec_toggle_{wid}",
        use_container_width=True,
        help="섹션 펼치기/접기",
        label_visibility="collapsed",
    ):
        st.session_state[open_key] = not is_open
        st.rerun()

    if not is_open:
        return

    st.markdown('<div class="pat-sec-body">', unsafe_allow_html=True)
    st.markdown('<div class="pat-list-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    for i, pat in enumerate(patterns):
        ex_kw: Dict[str, Any] = {}
        if tab_id in ("experience", "comparison"):
            ex_kw["additional_example_count"] = 2
        render_compact_pattern_card(
            pat, tab_id=tab_id, sec_uid=sec_uid, idx=i, **ex_kw
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_patterns() -> None:
    sync_settings_to_legacy(st.session_state)
    ensure_pattern(st.session_state)
    touch_pattern_visit(st.session_state)

    st.markdown('<div class="pat-screen">', unsafe_allow_html=True)

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
            _render_section(tid, sec_uid, title, patterns)

    st.markdown("</div>", unsafe_allow_html=True)
