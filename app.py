"""
OPIc Therapy Clinic — Streamlit entrypoint.

Single-entry mobile router. Each tab is a view that we import lazily so the
cold-start path stays minimal on Render. Persistent **bottom nav** + per-page
**top bar** give the app a continuous, mobile-first feel (back + home are
always reachable; tab switching is instant).

Navigation contract:
  ``?nav=HOME|PATTERN|MOCK|SCRIPTS|LECTURES|SETTINGS`` — primary tab.
  ``?nav=MOCK&mock=SURVEY|TEST|REPORT|FINAL`` — mock sub-screen (used for
  back). All in-app links target these query parameters via plain ``<a>``
  anchors with no ``target="_blank"``, so the browser stays in the **same
  tab** and Streamlit reruns in-place.

(``views/`` 패키지 사용 — Streamlit 예약 디렉터리명 ``pages/`` 는 쓰지 않습니다.)
"""

from __future__ import annotations

import streamlit as st

from components.navigation import render_bottom_navigation
from ui.styles import inject_global_styles
from utils.local_profile import hydrate_entry_session, sync_user_progress
from utils.session_state import ensure_mock, ensure_pattern, ensure_settings, sync_settings_to_legacy

st.set_page_config(
    page_title="OPIc Therapy Clinic",
    layout="wide",
    initial_sidebar_state="collapsed",
)
inject_global_styles()

if "page" not in st.session_state:
    st.session_state.page = "HOME"
if "active_target_sentence" not in st.session_state:
    st.session_state.active_target_sentence = ""

hydrate_entry_session(st.session_state)
ensure_settings(st.session_state)
ensure_mock(st.session_state)
ensure_pattern(st.session_state)
sync_settings_to_legacy(st.session_state)

if "mock_data" not in st.session_state:
    st.session_state.mock_data = {"recording_active": False}

if not st.session_state.get("entry_gate_completed"):
    from views.entry_gate import render_entry_gate

    render_entry_gate()
    st.stop()


def _q_one(name: str) -> str | None:
    v = st.query_params.get(name)
    if isinstance(v, list):
        return v[0] if v else None
    return v


_ALLOWED_PAGES = {"HOME", "MOCK", "PATTERN", "SCRIPTS", "LECTURES", "SETTINGS"}
_ALLOWED_MOCK_SUBPAGES = {"SURVEY", "TEST", "REPORT", "FINAL"}

nav_param = _q_one("nav")
mock_param = _q_one("mock")

# --- Tab switch handler -------------------------------------------------------
# Any change in the requested tab updates session_state.page in-place and lets
# the *current* rerun continue downstream — no explicit ``st.rerun()`` here,
# which saves one full script execution per tab tap (smoother feel on mobile).
if nav_param in _ALLOWED_PAGES and nav_param != st.session_state.page:
    st.session_state.page = nav_param
    if nav_param != "MOCK":
        st.session_state.mock_data["recording_active"] = False
        mx = ensure_mock(st.session_state)
        mx["analysis_status"] = ""
        mx["audio_bytes"] = None

# --- Mock sub-screen handler --------------------------------------------------
# Back / forward links from the mock top bar use ?nav=MOCK&mock=SURVEY etc.
# Same rationale as above: mutate state in-place and let the current rerun
# carry the new sub-screen through to the view.
if st.session_state.page == "MOCK" and mock_param in _ALLOWED_MOCK_SUBPAGES:
    mx = ensure_mock(st.session_state)
    if mx.get("mock_page") != mock_param:
        if mock_param == "SURVEY":
            mx["audio_bytes"] = None
        mx["mock_page"] = mock_param
        if mock_param == "FINAL":
            mx["exam_finished"] = True
        elif mock_param in {"SURVEY", "TEST"}:
            mx["exam_finished"] = False

page = st.session_state.page

# Disk restore is only relevant once the user enters the mock area.
if page == "MOCK" and not st.session_state.get("_mock_restored_from_disk"):
    from utils.local_profile import maybe_restore_mock_from_disk

    maybe_restore_mock_from_disk(st.session_state)


def _page_footer() -> None:
    st.caption("© opictherapist")
    render_bottom_navigation()


if page == "HOME":
    from views.home import render_home

    render_home()
    _page_footer()
    sync_user_progress(st.session_state)
    st.stop()

if page == "PATTERN":
    from views.patterns import render_patterns

    render_patterns()
    _page_footer()
    st.stop()

if page == "SCRIPTS":
    from views.scripts import render_scripts

    render_scripts()
    _page_footer()
    st.stop()

if page == "LECTURES":
    from views.lectures import render_lectures

    render_lectures()
    _page_footer()
    st.stop()

if page == "SETTINGS":
    from views.settings_page import render_settings

    render_settings()
    _page_footer()
    st.stop()

# --- Default: MOCK ------------------------------------------------------------
from views.mock_exam import render_mock_exam_shell, render_mock_flow

render_mock_exam_shell()
render_mock_flow()
sync_user_progress(st.session_state)
