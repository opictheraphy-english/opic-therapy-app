"""
OPIc Therapy Clinic — Streamlit entrypoint.
UI 라우팅만 담당하고 페이지·서비스·컴포넌트는 모듈로 분리했습니다.
"""

from __future__ import annotations

import streamlit as st

from components.navigation import render_bottom_navigation
from pages.entry_gate import render_entry_gate
from pages.home import render_home
from pages.lectures import render_lectures
from pages.mock_exam import render_mock_exam_shell, render_mock_flow
from pages.patterns import render_patterns
from pages.scripts import render_scripts
from pages.settings_page import render_settings
from ui.styles import inject_global_styles
from utils.local_profile import hydrate_entry_session, maybe_restore_mock_from_disk, sync_user_progress
from utils.session_state import ensure_mock, ensure_pattern, ensure_settings, sync_settings_to_legacy

# --- Page config & design ---
st.set_page_config(page_title="OPIc Therapy Clinic", layout="wide")
inject_global_styles()

# --- Legacy + namespaced session ---
if "page" not in st.session_state:
    st.session_state.page = "HOME"
if "active_target_sentence" not in st.session_state:
    st.session_state.active_target_sentence = ""

hydrate_entry_session(st.session_state)

ensure_settings(st.session_state)
ensure_mock(st.session_state)
maybe_restore_mock_from_disk(st.session_state)
ensure_pattern(st.session_state)
sync_settings_to_legacy(st.session_state)
sync_user_progress(st.session_state)

if "mock_data" not in st.session_state:
    st.session_state.mock_data = {"recording_active": False}

if not st.session_state.get("entry_gate_completed"):
    render_entry_gate()
    st.stop()

nav_param = st.query_params.get("nav")
if isinstance(nav_param, list):
    nav_param = nav_param[0] if nav_param else None
allowed_pages = {"HOME", "MOCK", "PATTERN", "SCRIPTS", "LECTURES", "SETTINGS"}
if nav_param in allowed_pages and nav_param != st.session_state.page:
    st.session_state.page = nav_param
    if nav_param != "MOCK":
        st.session_state.mock_data["recording_active"] = False
        mx = ensure_mock(st.session_state)
        mx["analysis_status"] = ""
        mx["audio_bytes"] = None
    st.rerun()

page = st.session_state.page

if page == "HOME":
    render_home()
    st.caption("© opictherapist")
    render_bottom_navigation()
    st.stop()

if page == "PATTERN":
    render_patterns()
    st.caption("© opictherapist")
    render_bottom_navigation()
    st.stop()

if page == "SCRIPTS":
    render_scripts()
    st.caption("© opictherapist")
    render_bottom_navigation()
    st.stop()

if page == "LECTURES":
    render_lectures()
    st.caption("© opictherapist")
    render_bottom_navigation()
    st.stop()

if page == "SETTINGS":
    render_settings()
    st.caption("© opictherapist")
    render_bottom_navigation()
    st.stop()

# --- MOCK exam (survey / test / report) ---
render_mock_exam_shell()
render_mock_flow()
