"""Bottom navigation — fixed horizontal tab bar (CSS flex, no ``st.columns``)."""

from __future__ import annotations

import html
import re
from urllib.parse import parse_qs

import streamlit as st

_ALLOWED_PAGES = frozenset({"HOME", "MOCK", "PATTERN", "SCRIPTS", "LECTURES", "SETTINGS"})

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
    "study": (
        '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
        '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>'
        '<line x1="8" y1="6" x2="16" y2="6"/>'
        '<line x1="8" y1="10" x2="14" y2="10"/></svg>'
    ),
}

NAV_ITEMS = (
    ("HOME", "홈", "home"),
    ("MOCK", "학습하기", "study"),
    ("PATTERN", "패턴", "wave"),
    ("SCRIPTS", "스크립트", "file"),
    ("LECTURES", "강의", "play"),
    ("SETTINGS", "설정", "settings"),
)


def _href_key(href: str) -> str:
    """Stable Streamlit widget key suffix from a legacy ``?nav=…`` href."""
    q = (href or "").strip().lstrip("?").replace("&amp;", "&")
    safe = re.sub(r"[^a-zA-Z0-9_]+", "_", q)[:64]
    return safe or "back"


def navigate_to(
    page: str,
    *,
    mock: str | None = None,
    reset: bool = False,
) -> None:
    """Set active tab in session (and sync URL). Caller should ``st.rerun()``."""
    if page not in _ALLOWED_PAGES:
        page = "HOME"
    st.session_state.page = page

    if page != "MOCK":
        md = st.session_state.get("mock_data")
        if isinstance(md, dict):
            md["recording_active"] = False

    if page == "MOCK":
        from utils.session_state import ensure_mock
        from views.mock_exam import reset_to_learning_portal

        mx = ensure_mock(st.session_state)
        prev_m = mx.get("mock_page")
        if mock == "TOPIC_V2_HISTORY":
            # App-level route; may not see in-session TPV2 history after full page reload.
            from views.topic_practice_v2 import (
                MOCK_MODE_TOPIC_V2,
                enter_topic_v2_history_nav,
            )

            enter_topic_v2_history_nav(source="navigate_to")
            mx["mock_page"] = "TOPIC_V2"
            st.session_state["mock_page"] = "TOPIC_V2"
            mx["mock_mode"] = MOCK_MODE_TOPIC_V2
            st.session_state["mock_mode"] = MOCK_MODE_TOPIC_V2
            st.session_state["practice_portal_selected"] = True
            mx["mock_mode_label"] = "주제별 답변 연습"
        elif mock:
            mx["mock_page"] = mock
            st.session_state["mock_page"] = mock
            st.session_state["practice_portal_selected"] = True
        else:
            reset_to_learning_portal()
        if mock == "FINAL":
            mx["exam_finished"] = True
        elif mock in {"SURVEY", "TEST"}:
            if mx.get("exam_finished"):
                pass
            elif mx.get("final_report_generated") or mx.get("analytics_cache"):
                pass
            elif prev_m in {"REPORT", "FINAL"}:
                pass
            else:
                mx["exam_finished"] = False

    try:
        st.query_params.clear()
        st.query_params["nav"] = page
        if mock:
            st.query_params["mock"] = mock
        elif page == "MOCK":
            st.query_params["reset_practice"] = "1"
        if reset:
            st.query_params["reset"] = "1"
    except Exception:
        pass


def navigate_from_href(href: str) -> None:
    """Parse ``?nav=…&mock=…`` for top-bar back buttons."""
    q = (href or "").strip()
    if q.startswith("?"):
        q = q[1:]
    q = q.replace("&amp;", "&")
    params = parse_qs(q, keep_blank_values=True)
    page = (params.get("nav") or ["HOME"])[0]
    mock_vals = params.get("mock")
    mock = mock_vals[0] if mock_vals else None
    reset_vals = params.get("reset")
    reset = bool(reset_vals and reset_vals[0] == "1")
    navigate_to(page, mock=mock, reset=reset)


_NAV_SAME_TAB_SCRIPT = """
<script>
(function () {
  var bar = document.querySelector(".opic-bottom-nav");
  if (!bar || bar.dataset.opicNavBound === "1") return;
  bar.dataset.opicNavBound = "1";
  bar.addEventListener("click", function (e) {
    var el = e.target.closest("a.opic-bottom-nav__item[data-nav]");
    if (!el) return;
    e.preventDefault();
    var page = el.getAttribute("data-nav");
    if (!page) return;
    var params = new URLSearchParams(window.location.search);
    params.set("nav", page);
    params.delete("reset");
    if (page === "MOCK") {
      params.set("reset_practice", "1");
      params.delete("mock");
    } else {
      params.delete("mock");
      params.delete("reset_practice");
    }
    var qs = params.toString();
    var url = window.location.pathname + (qs ? "?" + qs : "");
    window.location.assign(url);
  });
})();
</script>
"""


def _build_opic_bottom_nav_html(page: str) -> str:
    """Single-row flex tab bar — same-tab ``?nav=`` via ``location.assign`` (not new tab)."""
    tabs: list[str] = []
    for key, label, ico in NAV_ITEMS:
        active = " opic-bottom-nav__item--active" if page == key else ""
        aria = ' aria-current="page"' if page == key else ""
        svg = _SVG.get(ico, _SVG["home"])
        safe_key = html.escape(key)
        href = f"?nav={safe_key}&reset_practice=1" if key == "MOCK" else f"?nav={safe_key}"
        tabs.append(
            f'<a class="opic-bottom-nav__item{active}"'
            f' href="{href}"'
            f' target="_self"'
            f' data-nav="{safe_key}"'
            f' role="tab"'
            f' aria-label="{html.escape(label)}"{aria}>'
            f'<span class="opic-bottom-nav__ico">{svg}</span>'
            f'<span class="opic-bottom-nav__label">{html.escape(label)}</span>'
            "</a>"
        )
    return (
        f'<nav class="opic-bottom-nav" aria-label="주요 메뉴">{"".join(tabs)}</nav>'
        f"{_NAV_SAME_TAB_SCRIPT}"
    )


def render_bottom_navigation() -> None:
    """Fixed horizontal bottom tab bar — always one row, never ``st.columns``."""
    page = st.session_state.get("page", "HOME")
    st.markdown(_build_opic_bottom_nav_html(page), unsafe_allow_html=True)
