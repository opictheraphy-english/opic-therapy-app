"""
OPIc Therapy Clinic — Streamlit entrypoint.

Single-entry mobile router. Each tab is a view that we import lazily so the
cold-start path stays minimal on Render. Persistent **bottom nav** + per-page
**top bar** give the app a continuous, mobile-first feel (back + home are
always reachable; tab switching is instant).

Navigation: ``st.session_state.page`` + ``navigate_to()`` / bottom nav buttons.
Optional ``?nav=`` query param syncs on load (same browser tab).

First entry: after the guest/login entry gate, a short onboarding flow runs
until ``onboarding_completed`` is set (local ``app_session.json``). Returning
users see a one-time-per-session splash on Home only (``splash_seen_this_session``,
not persisted).

(``views/`` 패키지 사용 — Streamlit 예약 디렉터리명 ``pages/`` 는 쓰지 않습니다.)
"""

from __future__ import annotations

import logging
import time
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
        "[APP_ROUTER] tag=%s nav=%r mock=%r page=%r mx_page=%r real_mock_page=%r idx=%r "
        "exam_finished=%r analysis_status=%r audio_bytes=%s pending_recovery=%s restored_flag=%r",
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
_ALLOWED_MOCK_SUBPAGES = {
    "PICK",
    "TOPIC",
    "TOPIC_V2",
    "TOPIC_V2_HISTORY",
    "MINI_MOCK",
    "SURVEY",
    "TEST",
    "REPORT",
    "FINAL",
}

nav_param = _q_one("nav")
mock_param = _q_one("mock")
reset_param = _q_one("reset")
# 1. Explicit exam reset (home "처음부터 다시")
if reset_param == "1" and (nav_param == "MOCK" or st.session_state.page == "MOCK"):
    from utils.exam_state import reset_exam_state

    _mx_reset = ensure_mock(st.session_state)
    reset_exam_state(_mx_reset, st.session_state)
    try:
        del st.query_params["reset"]
    except Exception:
        pass

# 2. Sync primary tab from URL (bookmark / refresh)
if nav_param in _ALLOWED_PAGES:
    st.session_state.page = nav_param
    if nav_param != "MOCK":
        st.session_state.mock_data["recording_active"] = False
    # Do not reset practice routing on every ?nav=MOCK load — that wiped portal
    # button state. Use ?nav=MOCK&reset_practice=1 or bottom-nav reset instead.

# 3. Mock sub-screen from URL (never force PICK over an active practice mode)
if st.session_state.page == "MOCK" and mock_param in _ALLOWED_MOCK_SUBPAGES:
    mx = ensure_mock(st.session_state)
    if mock_param == "PICK":
        if not st.session_state.get("practice_portal_selected"):
            mx["mock_page"] = "PICK"
            st.session_state["mock_page"] = "PICK"
    elif mock_param == "TOPIC_V2_HISTORY":
        from views.topic_practice_v2 import apply_topic_v2_history_route

        apply_topic_v2_history_route(mx, source="url")
    elif mx.get("mock_page") != mock_param:
        prev_m = mx.get("mock_page")
        mx["mock_page"] = mock_param
        st.session_state["mock_page"] = mock_param
        if mock_param in {"SURVEY", "TEST", "REPORT", "FINAL", "TOPIC", "TOPIC_V2", "MINI_MOCK"}:
            st.session_state["practice_portal_selected"] = True
        if mock_param == "FINAL":
            mx["exam_finished"] = True
        elif mock_param in {"SURVEY", "TEST"}:
            if mx.get("exam_finished"):
                pass
            elif mx.get("final_report_generated") or mx.get("analytics_cache"):
                pass
            elif prev_m in {"REPORT", "FINAL"}:
                pass
            else:
                mx["exam_finished"] = False

page = st.session_state.page
if page not in _ALLOWED_PAGES:
    st.session_state.page = "HOME"
    page = "HOME"

_router_debug("post_handlers", st.session_state, nav_param, mock_param)


def _render_active_page() -> None:
    """Render the selected view — page content only (no bottom nav)."""
    if page == "HOME":
        if not st.session_state.get("splash_seen_this_session"):
            from views.splash import render_splash_screen

            if not st.session_state.get("_splash_once"):
                render_splash_screen()
                st.session_state._splash_once = True
                st.rerun()
            render_splash_screen()
            time.sleep(1.2)
            st.session_state.splash_seen_this_session = True
            st.session_state.pop("_splash_once", None)
            st.rerun()

        from views.home import render_home

        render_home()
        sync_user_progress(st.session_state)
        return

    if page == "MOCK":
        from views.mock_exam import render_mock_exam_shell, render_mock_flow

        render_mock_exam_shell()
        render_mock_flow()
        sync_user_progress(st.session_state)
        return

    if page == "PATTERN":
        from views.patterns import render_patterns

        render_patterns()
        return

    if page == "SCRIPTS":
        from views.scripts import render_scripts

        render_scripts()
        return

    if page == "LECTURES":
        from views.lectures import render_lectures

        render_lectures()
        return

    if page == "SETTINGS":
        from views.settings_page import render_settings

        render_settings()
        return


# --- Main shell: page body first, navigation last ----------------------------
_render_active_page()
st.caption("© opictherapist")
render_bottom_navigation()
st.stop()
