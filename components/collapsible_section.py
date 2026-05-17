"""Collapsible sections without ``st.expander`` (Korean labels leak as key…_arrow_*)."""

from __future__ import annotations

import html
from typing import Callable, Optional

import streamlit as st

from utils.streamlit_ui import ascii_widget_key, clean_visible_label


def render_collapsible_section(
    title: str,
    key_suffix: str,
    render_body: Callable[[], None],
    *,
    default_open: bool = False,
    toggle_open_label: str = "펼치기",
    toggle_close_label: str = "접기",
    count: Optional[int] = None,
    css_scope: str = "ui-col",
) -> None:
    """HTML header + ``st.button`` toggle; body only when open."""
    safe_title = clean_visible_label((title or "").strip(), "내용")
    title_h = html.escape(safe_title)

    wid = ascii_widget_key(key_suffix)
    open_key = f"{css_scope}_open_{wid}"
    if open_key not in st.session_state:
        st.session_state[open_key] = bool(default_open)
    is_open = bool(st.session_state[open_key])

    count_html = ""
    if count is not None:
        count_html = f'<span class="{css_scope}-count">{int(count)}</span>'

    open_cls = f"{css_scope}-head--open" if is_open else ""
    st.markdown(
        f'<div class="{css_scope}-head {open_cls}">'
        f'<span class="{css_scope}-title">{title_h}</span>'
        f"{count_html}"
        f"</div>",
        unsafe_allow_html=True,
    )
    toggle_label = toggle_close_label if is_open else toggle_open_label
    if st.button(
        toggle_label,
        key=f"{css_scope}_toggle_{wid}",
        use_container_width=True,
    ):
        st.session_state[open_key] = not is_open
        st.rerun()

    if not is_open:
        return

    st.markdown(f'<div class="{css_scope}-body">', unsafe_allow_html=True)
    render_body()
    st.markdown("</div>", unsafe_allow_html=True)
