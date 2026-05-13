"""Compact pattern card: EN + KO meaning; examples capped + toggle (no audio)."""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List

import streamlit as st

# First N examples always visible
VISIBLE_EXAMPLE_COUNT = 2
# When expanded, show only this many *additional* examples (not the full tail)
ADDITIONAL_EXAMPLE_COUNT = 2


def _safe_fragment(s: str, max_len: int = 56) -> str:
    x = re.sub(r"[^a-zA-Z0-9가-힣_-]", "_", (s or "").strip())
    return (x[:max_len]) or "x"


def _pattern_line(pat: Dict[str, Any]) -> str:
    return (pat.get("pattern_en") or pat.get("pattern") or "").strip() or "—"


def _meaning_line(pat: Dict[str, Any]) -> str:
    return (pat.get("meaning") or "").strip() or "—"


def example_english_only(pat: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    examples = pat.get("examples") if isinstance(pat.get("examples"), list) else []
    for x in examples:
        if not isinstance(x, dict):
            continue
        en = (x.get("en") or "").strip()
        if en:
            out.append(en)
    if not out:
        ex1 = (pat.get("example_en") or "").strip()
        if ex1:
            out.append(ex1)
    return out


def render_compact_pattern_card(
    pat: Dict[str, Any],
    *,
    tab_id: str,
    sec_uid: str,
    idx: int,
    expand_more_label: str = "예문 더보기",
    collapse_label: str = "접기",
    additional_example_count: int | None = None,
) -> None:
    """Single flashcard-style block; English examples only (no KO dump)."""
    add_n = (
        additional_example_count
        if additional_example_count is not None
        else ADDITIONAL_EXAMPLE_COUNT
    )
    pid = (pat.get("pattern_id") or "").strip() or f"{tab_id}_{idx}"
    row_key = _safe_fragment(f"{tab_id}_{sec_uid}_{pid}_{idx}")
    expand_key = f"pat_ex_expand_{row_key}"

    tpl = _pattern_line(pat)
    meaning = _meaning_line(pat)
    en_h = html.escape(tpl)
    ko_h = html.escape(meaning)
    st.markdown(
        f'<div class="pat-card"><div class="pat-en">{en_h}</div><div class="pat-ko">{ko_h}</div></div>',
        unsafe_allow_html=True,
    )

    lines = example_english_only(pat)
    if not lines:
        return

    head = lines[:VISIBLE_EXAMPLE_COUNT]
    lis_head = "".join(f"<li>{html.escape(x)}</li>" for x in head)
    st.markdown(
        f'<div class="pat-ex-wrap"><span style="font-size:0.68rem;color:#64748b;">예문</span>'
        f"<ul>{lis_head}</ul></div>",
        unsafe_allow_html=True,
    )

    if len(lines) <= VISIBLE_EXAMPLE_COUNT:
        return

    expanded = bool(st.session_state.get(expand_key))
    btn_label = collapse_label if expanded else expand_more_label
    if st.button(btn_label, key=f"pat_ex_toggle_{row_key}", type="secondary"):
        st.session_state[expand_key] = not expanded
        expanded = bool(st.session_state.get(expand_key))

    if expanded:
        extra_slice = lines[VISIBLE_EXAMPLE_COUNT : VISIBLE_EXAMPLE_COUNT + add_n]
        if extra_slice:
            lis_extra = "".join(f"<li>{html.escape(x)}</li>" for x in extra_slice)
            st.markdown(
                f'<div class="pat-ex-wrap" style="margin-top:4px;"><ul>{lis_extra}</ul></div>',
                unsafe_allow_html=True,
            )
