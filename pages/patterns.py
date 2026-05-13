"""Patterns — mobile-first, text-only drill list (no TTS / no audio UI)."""

from __future__ import annotations

import re
from typing import Any, Dict, List

import streamlit as st

from components.pattern_card_compact import render_compact_pattern_card
from config.pattern_ui_mapping import build_pattern_tabs_model
from utils.local_profile import sync_user_progress, touch_pattern_visit
from utils.session_state import ensure_pattern, sync_settings_to_legacy


def _safe_key(s: str, max_len: int = 48) -> str:
    x = re.sub(r"[^a-zA-Z0-9가-힣_-]", "_", (s or "").strip())
    return (x[:max_len]) or "x"


def _compact_css() -> None:
    st.markdown(
        """
<style>
.pat-wrap { max-width: 640px; margin: 0 auto; }
.pat-head {
  font-size: 0.95rem; font-weight: 600; color: #0f766e; margin: 0 0 6px 0;
}
.pat-sub { font-size: 0.72rem; color: #64748b; margin: 0 0 10px 0; line-height: 1.35; }
.pat-card {
  border: 1px solid #e2e8f0; border-radius: 10px; padding: 8px 10px; margin: 0 0 6px 0;
  background: #fff;
}
.pat-en { font-size: 0.88rem; color: #0f172a; line-height: 1.35; font-weight: 500; }
.pat-ko { font-size: 0.78rem; color: #475569; line-height: 1.4; margin-top: 4px; }
.pat-ex-wrap {
  margin-top: 6px; padding: 6px 8px; background: #f8fafc; border-radius: 8px;
  font-size: 0.74rem; color: #334155; line-height: 1.45;
}
.pat-ex-wrap ul { margin: 4px 0 0 16px; padding: 0; }
.pat-wrap button[kind="secondary"] {
  min-height: 1.75rem !important;
  padding: 0.1rem 0.5rem !important;
  font-size: 12px !important;
}
div[data-testid="stExpander"] details { border: 1px solid #e2e8f0; border-radius: 10px; }
</style>
""",
        unsafe_allow_html=True,
    )


def _render_section(tab_id: str, sec_uid: str, title: str, patterns: List[Dict[str, Any]]) -> None:
    cnt = len(patterns)
    if not patterns:
        return
    with st.expander(f"{title} · {cnt}", expanded=False):
        for i, pat in enumerate(patterns):
            ex_kw: Dict[str, Any] = {}
            if tab_id == "experience":
                ex_kw["additional_example_count"] = 3
            render_compact_pattern_card(
                pat, tab_id=tab_id, sec_uid=sec_uid, idx=i, **ex_kw
            )


def render_patterns() -> None:
    sync_settings_to_legacy(st.session_state)
    ensure_pattern(st.session_state)
    touch_pattern_visit(st.session_state)

    _compact_css()

    st.markdown(
        '<div class="pat-wrap">'
        '<p class="pat-head">패턴</p>'
        "<p class='pat-sub'>카테고리 → 섹션 → 카드. 예문은 처음 2개만 보이고, 「예문 더보기」 시 영문 예문 2개만 추가로 펼칩니다. "
        "다시 「예문 접기」로 접을 수 있습니다. 루틴 탭은 주제별로 나뉩니다. (오디오 비활성)</p>"
        "</div>",
        unsafe_allow_html=True,
    )

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

    sync_user_progress(st.session_state)
