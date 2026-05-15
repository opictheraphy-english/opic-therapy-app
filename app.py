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

First entry: after the guest/login entry gate, a short onboarding flow runs
until ``onboarding_completed`` is set (local ``app_session.json``).

(``views/`` 패키지 사용 — Streamlit 예약 디렉터리명 ``pages/`` 는 쓰지 않습니다.)
"""

from __future__ import annotations

import logging
from typing import Any

import streamlit as st

from components.navigation import render_bottom_navigation
from ui.styles import inject_global_styles
from utils.local_profile import hydrate_entry_session, sync_user_progress
from utils.session_state import ensure_mock, ensure_pattern, ensure_settings, sync_settings_to_legacy

logger = logging.getLogger(__name__)

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

# Disk restore ASAP after namespaces exist so onboarding / entry never
# blocks rehydration of a saved in-progress exam (cheap no-op when empty).
if not st.session_state.get("_mock_restored_from_disk"):
    from utils.local_profile import maybe_restore_mock_from_disk

    maybe_restore_mock_from_disk(st.session_state)

if not st.session_state.get("entry_gate_completed"):
    from views.entry_gate import render_entry_gate

    render_entry_gate()
    st.stop()

if not st.session_state.get("onboarding_completed"):
    from views.onboarding import render_onboarding

    render_onboarding()
    st.stop()


def _q_one(name: str) -> str | None:
    v = st.query_params.get(name)
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _router_debug(tag: str, ss: Any, nav_p: str | None, mock_p: str | None) -> None:
    """Server-side only — never shown in UI."""
    mx = ss.get("mock") if isinstance(ss.get("mock"), dict) else {}
    logger.debug(
        "app_router[%s] nav=%r mock=%r page=%r mx_page=%r idx=%r exam_finished=%r "
        "analysis_status=%r audio_bytes=%s pending_recovery=%s restored_flag=%r",
        tag,
        nav_p,
        mock_p,
        ss.get("page"),
        mx.get("mock_page"),
        mx.get("current_idx"),
        mx.get("exam_finished"),
        (mx.get("analysis_status") or "")[:120],
        "yes" if mx.get("audio_bytes") else "no",
        bool(mx.get("pending_recovery")),
        ss.get("_mock_restored_from_disk"),
    )


_ALLOWED_PAGES = {"HOME", "MOCK", "PATTERN", "SCRIPTS", "LECTURES", "SETTINGS"}
_ALLOWED_MOCK_SUBPAGES = {"SURVEY", "TEST", "REPORT", "FINAL"}

nav_param = _q_one("nav")
mock_param = _q_one("mock")
reset_param = _q_one("reset")

# --- Order of operations (read this before tweaking!) ------------------------
# 1. ``?reset=1``           — wipe mx + set ``_suppress_disk_restore``.
# 2. ``maybe_restore_mock_from_disk`` — runs once per session, immediately
# after ``ensure_mock`` (see above) so disk hydrates before entry/onboarding
# gates and before any ``sync_user_progress`` call on the first paint.
#
# 3. Tab switch handler — set ``st.session_state.page`` from ``?nav=``.
# 4. Sub-screen handler — set ``mx["mock_page"]`` from ``?mock=``.
# 5. Render the page.
#
# Steps 3–4 used to clear ``audio_bytes`` when leaving MOCK; that dropped
# in-flight recordings. Restore now runs before entry/onboarding (step 2).

# 1. Explicit exam reset (home "처음부터 다시" anchor)
if reset_param == "1" and (nav_param == "MOCK" or st.session_state.page == "MOCK"):
    from utils.exam_state import reset_exam_state

    _mx_reset = ensure_mock(st.session_state)
    reset_exam_state(_mx_reset, st.session_state)
    # Clean the URL so a refresh doesn't trigger another reset.
    try:
        del st.query_params["reset"]
    except Exception:
        pass

# 3. Tab switch handler
# Any change in the requested tab updates session_state.page in-place and
# lets the *current* rerun continue downstream — no explicit ``st.rerun()``
# here, which saves one full script execution per tab tap.
if nav_param in _ALLOWED_PAGES and nav_param != st.session_state.page:
    st.session_state.page = nav_param
    if nav_param != "MOCK":
        # Mic UI only — never drop in-flight mock audio or exam rows here.
        st.session_state.mock_data["recording_active"] = False

# 4. Mock sub-screen handler — URL intent wins. This runs AFTER restore so
# ``?mock=TEST`` is never overwritten by a stale snapshot value.
if st.session_state.page == "MOCK" and mock_param in _ALLOWED_MOCK_SUBPAGES:
    mx = ensure_mock(st.session_state)
    if mx.get("mock_page") != mock_param:
        prev_m = mx.get("mock_page")
        mx["mock_page"] = mock_param
        if mock_param == "FINAL":
            mx["exam_finished"] = True
        elif mock_param in {"SURVEY", "TEST"}:
            # Do not clear a finished exam or review navigation back into TEST/SURVEY.
            if mx.get("exam_finished"):
                pass
            elif mx.get("final_report_generated") or mx.get("analytics_cache"):
                pass
            elif prev_m in {"REPORT", "FINAL"}:
                pass
            else:
                mx["exam_finished"] = False

page = st.session_state.page

_router_debug("post_handlers", st.session_state, nav_param, mock_param)


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
