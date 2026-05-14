"""Persistent bottom navigation — 6 tabs, mobile-first.

Anchor-based dock. ``<a href="?nav=KEY">`` triggers a normal same-tab
navigation (no ``target="_blank"``) and Streamlit then reads ``?nav=`` to
swap the active view inside the current browser tab.
"""

from __future__ import annotations

import streamlit as st

_SVG = {
    "home": (
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>'
        '<polyline points="9 22 9 12 15 12 15 22"/></svg>'
    ),
    "wave": (
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M2 12h2"/><path d="M6 8v8"/><path d="M10 4v16"/>'
        '<path d="M14 8v8"/><path d="M18 5v14"/><path d="M22 12h2"/></svg>'
    ),
    "mic": (
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>'
        '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/>'
        '<line x1="12" y1="19" x2="12" y2="23"/>'
        '<line x1="8" y1="23" x2="16" y2="23"/></svg>'
    ),
    "play": (
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<rect width="18" height="18" x="3" y="3" rx="2"/>'
        '<path d="m10 8 6 4-6 4V8z"/></svg>'
    ),
    "file": (
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<line x1="16" y1="13" x2="8" y2="13"/>'
        '<line x1="16" y1="17" x2="8" y2="17"/>'
        '<line x1="10" y1="9" x2="8" y2="9"/></svg>'
    ),
    "settings": (
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.47a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/>'
        '<circle cx="12" cy="12" r="3"/></svg>'
    ),
}

NAV_ITEMS = (
    ("HOME", "홈", "home"),
    ("MOCK", "모의고사", "mic"),
    ("PATTERN", "패턴", "wave"),
    ("SCRIPTS", "스크립트", "file"),
    ("LECTURES", "강의", "play"),
    ("SETTINGS", "설정", "settings"),
)


def render_bottom_navigation() -> None:
    page = st.session_state.get("page", "HOME")
    parts = []
    for key, label, ico in NAV_ITEMS:
        active = "active" if page == key else ""
        svg = _SVG.get(ico, _SVG["home"])
        parts.append(
            f'<a class="nav-item {active}" href="?nav={key}" title="{label}">'
            f'<span class="nav-ico">{svg}</span>'
            f'<span class="nav-label">{label}</span></a>'
        )
    html = (
        '<nav class="bottom-nav-dock" aria-label="주요 메뉴">'
        f'<div class="bottom-nav-inner">{"".join(parts)}</div>'
        "</nav>"
        '<div class="page-bottom-space"></div>'
    )
    st.markdown(html, unsafe_allow_html=True)
