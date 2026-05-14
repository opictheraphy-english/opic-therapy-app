"""Mobile-style top bar — back arrow + section title + home, anchor-based.

Anchor links keep the navigation lightweight (single Streamlit rerun, no full
asset reload). All hrefs target internal Streamlit query parameters and have
no ``target="_blank"``, so the browser stays in the **same tab**.
"""

from __future__ import annotations

import html
from typing import Optional

import streamlit as st

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
    """Render a compact mobile-style header.

    Parameters
    ----------
    title: Section name shown in the center.
    back_href: When provided, renders a left-side back chevron linking to this
        anchor (e.g. ``"?nav=HOME"`` or ``"?nav=MOCK&mock=SURVEY"``). When
        ``None`` no back affordance is rendered.
    show_home: Renders the right-side 🏠 anchor to ``?nav=HOME``. Disabled when
        the current screen is HOME so the bar reads as a pure header there.
    eyebrow: Tiny label above the title (e.g. "MOCK · Q3"). Optional.
    """
    title_html = html.escape((title or "").strip())
    eyebrow_html = html.escape((eyebrow or "").strip()) if eyebrow else ""

    if back_href:
        back_html = (
            f'<a class="tb-btn tb-back" href="{html.escape(back_href, quote=True)}" '
            f'aria-label="뒤로가기">{_BACK_SVG}</a>'
        )
    else:
        back_html = '<span class="tb-btn tb-spacer" aria-hidden="true"></span>'

    if show_home:
        home_html = (
            '<a class="tb-btn tb-home" href="?nav=HOME" aria-label="홈으로">'
            f"{_HOME_SVG}</a>"
        )
    else:
        home_html = '<span class="tb-btn tb-spacer" aria-hidden="true"></span>'

    eyebrow_block = (
        f'<div class="tb-eyebrow">{eyebrow_html}</div>' if eyebrow_html else ""
    )

    # IMPORTANT: single concatenated string with no leading whitespace per
    # line. A multi-line indented f-string would be parsed by markdown as a
    # code block and the HTML would render as literal text.
    st.markdown(
        '<header class="topbar" role="banner">'
        f"{back_html}"
        '<div class="tb-titleblock">'
        f"{eyebrow_block}"
        f'<div class="tb-title">{title_html}</div>'
        "</div>"
        f"{home_html}"
        "</header>",
        unsafe_allow_html=True,
    )
