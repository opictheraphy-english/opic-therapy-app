"""Legacy TTS + st.audio button (optional utilities)."""

from __future__ import annotations

import logging

import streamlit as st

from services.tts_service import (
    DEFAULT_TTS_PITCH,
    DEFAULT_TTS_SPEAKING_RATE,
    neural2_voice_for_session,
    tts_audio_cached,
)

logger = logging.getLogger(__name__)


def render_cloud_speak_button(text: str, label: str = "🔊 재생", button_key: str | None = None) -> None:
    if not button_key:
        button_key = f"cloud_tts_{abs(hash((text, label))) % (10**8)}"
    resolved_voice = neural2_voice_for_session()
    state_key = f"_cloud_tts_payload_{button_key}"
    err_key = f"_cloud_tts_err_{button_key}"
    if st.button(label, key=f"btn_{button_key}", use_container_width=True):
        st.session_state.pop(err_key, None)
        try:
            payload = tts_audio_cached(
                text,
                resolved_voice,
                DEFAULT_TTS_SPEAKING_RATE,
                DEFAULT_TTS_PITCH,
            )
            st.session_state[state_key] = payload
        except Exception as e:
            st.session_state.pop(state_key, None)
            st.session_state[err_key] = str(e)
            logger.warning("TTS pipeline failed: %s: %s", type(e).__name__, e)
    err = st.session_state.get(err_key)
    if err:
        st.error(f"음성을 만들 수 없습니다.\n\n{err}")
    payload = st.session_state.get(state_key)
    if payload and payload.get("audio_bytes"):
        st.audio(payload["audio_bytes"], format=payload.get("audio_format", "audio/mp3"))
