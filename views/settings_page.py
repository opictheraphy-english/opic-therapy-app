"""App settings."""

from __future__ import annotations

import streamlit as st

from services.tts_service import NEURAL2_DANIEL, NEURAL2_EVA
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
    )
    st.caption("Eva: Neural2 여성 · Daniel: Neural2 남성 (Cloud TTS 고정)")
    if selected_voice != current_voice:
        sett["voice_choice"] = selected_voice
        sync_settings_to_legacy(st.session_state)
        st.rerun()
