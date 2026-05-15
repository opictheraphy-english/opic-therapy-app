"""App settings."""

from __future__ import annotations

import streamlit as st

from services.tts_service import NEURAL2_DANIEL, NEURAL2_EVA
from utils.local_profile import reset_onboarding_for_rerun
from utils.session_state import ensure_settings, sync_settings_to_legacy


def render_step_header(step_title: str) -> None:
    st.markdown(
        f"""
        <div class="glass-card" style="border-left:4px solid #0D9488;">
          <div style="font-size:13px;color:#0f766e;font-weight:600;">{step_title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_settings() -> None:
    render_step_header("Step 6. 환경 설정")
    st.markdown('<p class="ds-h2">환경 설정</p>', unsafe_allow_html=True)
    st.caption(
        f"질문·패턴 음성: Cloud Neural2 우선 (Eva `{NEURAL2_EVA}` / Daniel `{NEURAL2_DANIEL}`), 필요 시 gTTS·macOS 보조."
    )

    sett = ensure_settings(st.session_state)

    st.markdown('<p class="ds-muted">재생 Neural2 음성 프로필을 선택합니다.</p>', unsafe_allow_html=True)
    current_voice = sett.get("voice_choice", "Eva")
    selected_voice = st.radio(
        "재생 음성",
        ["Eva", "Daniel"],
        index=0 if current_voice == "Eva" else 1,
        horizontal=True,
        key="settings_voice_radio",
    )
    st.caption("Eva: Neural2 여성 · Daniel: Neural2 남성 (Cloud TTS 고정)")
    if selected_voice != current_voice:
        sett["voice_choice"] = selected_voice
        sync_settings_to_legacy(st.session_state)
        st.rerun()

    st.markdown('<p class="ds-muted" style="margin-top:18px;">목표 난이도를 선택합니다.</p>', unsafe_allow_html=True)
    current_diff = int(sett.get("difficulty", 5))
    selected_diff = st.radio(
        "목표 난이도",
        [5, 6],
        index=0 if current_diff == 5 else 1,
        format_func=lambda v: "레벨 5 (IH 목표)" if v == 5 else "레벨 6 (AL 목표)",
        horizontal=True,
        key="settings_difficulty_radio",
    )
    if int(selected_diff) != current_diff:
        sett["difficulty"] = int(selected_diff)
        sync_settings_to_legacy(st.session_state)
        st.rerun()

    st.divider()
    st.markdown('<p class="ds-muted" style="margin-top:8px;">앱을 처음 쓰는 분께 안내 화면을 다시 보여 드립니다.</p>', unsafe_allow_html=True)
    if st.button("온보딩 다시 보기", use_container_width=True, key="settings_reset_onboarding"):
        reset_onboarding_for_rerun(st.session_state)
        st.rerun()
