"""Patterns — premium mobile drill screen (step 3 shell + step 5 detail flow).

Tab / accordion layout unchanged. Each pattern is a guided stack (hero →
examples → IH → tip → practice); visuals live in ``ui/styles.py`` under
``.pat-screen``.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

import streamlit as st

from components.pattern_card_compact import render_compact_pattern_card
from config.pattern_ui_mapping import build_pattern_tabs_model
from utils.local_profile import touch_pattern_visit
from utils.session_state import ensure_pattern, sync_settings_to_legacy


def _safe_key(s: str, max_len: int = 48) -> str:
    x = re.sub(r"[^a-zA-Z0-9가-힣_-]", "_", (s or "").strip())
    return (x[:max_len]) or "x"


def _render_hero() -> None:
    st.markdown(
        '<div class="pat-hero">'
        '<p class="pat-eyebrow">Patterns</p>'
        '<p class="pat-title">패턴 드릴</p>'
        "<p class=\"pat-sub\">탭으로 유형을 고르고, 섹션을 펼치면 <b>히어로 → 예문 → IH → 팁 → 직접 말하기</b> 순서로 "
        "안내됩니다. 예문이 많은 패턴은 맨 아래 <b>나머지 예문 더보기</b>로 추가 문장을 볼 수 있어요.</p>"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_section(tab_id: str, sec_uid: str, title: str, patterns: List[Dict[str, Any]]) -> None:
    cnt = len(patterns)
    if not patterns:
        return
    with st.expander(f"{title}  ·  {cnt}", expanded=False):
        for i, pat in enumerate(patterns):
            ex_kw: Dict[str, Any] = {}
            if tab_id in ("experience", "comparison"):
                ex_kw["additional_example_count"] = 3
            render_compact_pattern_card(
                pat, tab_id=tab_id, sec_uid=sec_uid, idx=i, **ex_kw
            )


def render_patterns() -> None:
    sync_settings_to_legacy(st.session_state)
    ensure_pattern(st.session_state)
    touch_pattern_visit(st.session_state)

    # Open the scoped wrapper — every .pat-screen rule in ui/styles.py only
    # activates while this div is in the DOM, so the tab/expander/button
    # overrides never bleed into HOME, MOCK, SETTINGS, etc.
    st.markdown('<div class="pat-screen">', unsafe_allow_html=True)

    _render_hero()

    tabs_model = build_pattern_tabs_model()
    tabs = st.tabs([t["label"] for t in tabs_model])

    for panel, tab in zip(tabs, tabs_model):
        with panel:
            tid = tab["tab_id"]
            sections = tab.get("sections") or []
            empty_msg = tab.get("empty_message")

            if empty_msg and not sections:
                st.info(empty_msg)
                continue

            if not sections:
                st.caption("내용 없음")
                continue

            for si, sec in enumerate(sections):
                title = sec.get("title") or ""
                patterns: List[Dict[str, Any]] = sec.get("patterns") or []
                sec_uid = _safe_key(f"{tid}_{sec.get('section_id') or si}")
                _render_section(tid, sec_uid, title, patterns)

    st.markdown("</div>", unsafe_allow_html=True)
