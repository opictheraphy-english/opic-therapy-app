"""Mobile-style top bar — back + title + home via in-app buttons (same tab)."""

from __future__ import annotations

import html
from typing import Optional

import streamlit as st

from components.navigation import _href_key, navigate_from_href, navigate_to

_BACK_SVG = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="M19 12H5"/><path d="M12 19l-7-7 7-7"/></svg>'
)
_HOME_SVG = (
    '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
    '<polyline points="9 22 9 12 15 12 15 22"/></svg>'
)


def render_top_bar(
    title: str,
    *,
    back_href: Optional[str] = None,
    show_home: bool = True,
    eyebrow: Optional[str] = None,
) -> None:
    """Render a compact mobile-style header with Streamlit buttons (no ``<a href>``)."""
    title_html = html.escape((title or "").strip())
    eyebrow_html = html.escape((eyebrow or "").strip()) if eyebrow else ""
    eyebrow_block = (
        f'<div class="tb-eyebrow">{eyebrow_html}</div>' if eyebrow_html else ""
    )

    col_back, col_mid, col_home = st.columns([1, 6, 1], gap="small")
    with col_back:
        if back_href:
            if st.button(
                "←",
                key=f"tb_back_{_href_key(back_href)}",
                help="뒤로가기",
                use_container_width=True,
            ):
                navigate_from_href(back_href)
                st.rerun()
        else:
            st.empty()

    with col_mid:
        st.markdown(
            f'<header class="topbar topbar--inline" role="banner">'
            f'<div class="tb-titleblock">{eyebrow_block}'
            f'<div class="tb-title">{title_html}</div>'
            f"</div></header>",
            unsafe_allow_html=True,
        )

    with col_home:
        if show_home:
            if st.button("⌂", key="tb_home", help="홈으로", use_container_width=True):
                navigate_to("HOME")
                st.rerun()
        else:
            st.empty()
