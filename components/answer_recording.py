"""
Unified answer recording UI for mock / coaching / topic practice.

``streamlit_mic_recorder`` cannot be started programmatically (browser security).
One mic control: start label ``답변 시작``, stop label ``녹음 완료``.
"""

from __future__ import annotations

import html
from typing import Any, Callable, Dict, Optional

import streamlit as st

from components.recording_timer import (
    prepare_recording_timer,
    render_recording_timer,
    reset_recording_timer,
    start_recording_timer,
    stop_recording_timer,
)
from utils import audio_pipeline_diag
from utils.speech_recording import recording_byte_length, resolve_mime_for_analysis

STATE_IDLE = "idle"
STATE_RECORDING = "recording"
STATE_RECORDED = "recorded"
STATE_SAVED = "saved"
STATE_ANALYZING = "analyzing"

_STATE_IDLE = STATE_IDLE
_STATE_RECORDING = STATE_RECORDING
_STATE_RECORDED = STATE_RECORDED
_STATE_SAVED = STATE_SAVED
_STATE_ANALYZING = STATE_ANALYZING


def _state_key(question_key: str) -> str:
    return f"recording_ui_state::{question_key}"


def _rerecord_key(question_key: str) -> str:
    return f"recording_rerecord::{question_key}"


def _started_key(question_key: str) -> str:
    return f"recording_started_for::{question_key}"


def _mic_output_key(mic_key: str) -> str:
    return f"{mic_key}_output"


def get_recording_ui_state(
    question_key: str,
    *,
    has_saved: bool,
    analyzing: bool = False,
) -> str:
    if analyzing:
        return STATE_ANALYZING
    explicit = st.session_state.get(_state_key(question_key))
    if explicit == STATE_SAVED:
        return STATE_SAVED
    if has_saved and not st.session_state.get(_rerecord_key(question_key)):
        if explicit == STATE_SAVED:
            return STATE_SAVED
        return STATE_RECORDED
    if st.session_state.get("recording_timer_active"):
        return STATE_RECORDING
    if explicit == STATE_RECORDING:
        return STATE_RECORDING
    return STATE_IDLE


def set_recording_ui_state(question_key: str, state: str) -> None:
    st.session_state[_state_key(question_key)] = state


def reset_recording_ui_for_question(question_key: str) -> None:
    st.session_state.pop(_state_key(question_key), None)
    st.session_state.pop(_rerecord_key(question_key), None)
    st.session_state.pop(_started_key(question_key), None)


def clear_mic_recording_cache(mic_key: str) -> None:
    st.session_state.pop(_mic_output_key(mic_key), None)


def _mic_captured_bytes(mic_key: str, audio: Any) -> bytes | None:
    if isinstance(audio, dict):
        raw = audio.get("bytes")
        if raw:
            return bytes(raw)
    cached = st.session_state.get(_mic_output_key(mic_key))
    if isinstance(cached, dict):
        raw = cached.get("bytes")
        if raw:
            return bytes(raw)
    return None


def _persist_capture(
    mx: dict,
    rec: Dict[str, Any],
    *,
    audio_key: str,
    mic_key: str,
    audio: dict,
    blob: bytes,
) -> None:
    rec[audio_key] = blob
    mx["audio_bytes"] = blob
    fmt = (audio.get("format") or audio.get("mime") or "").strip()
    if fmt:
        mx.setdefault("recording_mime_by_key", {})[audio_key] = fmt
    st.session_state[_mic_output_key(mic_key)] = audio


def render_recording_status_banner(state: str) -> None:
    messages = {
        STATE_IDLE: "🎤 답변 시작을 누르고, 말을 마치면 녹음 완료를 눌러 주세요.",
        STATE_RECORDING: "녹음 중입니다. 2분 안에 핵심을 말해보세요.",
        STATE_RECORDED: "녹음이 저장되었습니다. AI 분석을 시작할 수 있어요.",
        STATE_SAVED: "답변이 저장되었어요.",
        STATE_ANALYZING: "AI가 답변을 분석하고 있어요. 잠시만 기다려 주세요.",
    }
    msg = messages.get(state, "")
    if msg:
        st.markdown(
            f'<p class="mx-record-status">{html.escape(msg)}</p>',
            unsafe_allow_html=True,
        )


def open_record_stage(title: str = "마이크로 답변을 녹음하세요") -> None:
    st.markdown(
        f"""
        <div class="mx-record-stage">
          <p class="mx-record-eyebrow">답변 녹음</p>
          <div class="mx-record-title">{html.escape(title)}</div>
        """,
        unsafe_allow_html=True,
    )


def close_record_stage() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def render_answer_recording_stage(
    mx: dict,
    *,
    question_key: str,
    mic_key: str,
    audio_key: str,
    recordings: Optional[dict] = None,
    analyzing: bool = False,
    on_recording_complete: Callable[[bytes], bool] | None = None,
) -> Optional[bytes]:
    """Mic + timer. Returns saved audio bytes when recording is complete."""
    from streamlit_mic_recorder import mic_recorder

    rec: Dict[str, Any] = (
        recordings if recordings is not None else mx.setdefault("recordings", {})
    )
    saved = mx.get("audio_bytes") or rec.get(audio_key)
    has_saved = bool(saved)
    state = get_recording_ui_state(question_key, has_saved=has_saved, analyzing=analyzing)

    prepare_recording_timer(question_key)
    render_recording_timer(question_key, has_saved_audio=has_saved)
    render_recording_status_banner(state)

    if state in (STATE_ANALYZING, STATE_SAVED):
        return saved if has_saved else None

    if state == STATE_RECORDED:
        return saved

    # Single mic path — no separate Streamlit "답변 시작" (avoids double start).
    if not st.session_state.get(_started_key(question_key)):
        start_recording_timer(question_key)
        st.session_state[_started_key(question_key)] = True
    set_recording_ui_state(question_key, STATE_RECORDING)

    audio = mic_recorder(
        start_prompt="🎤 답변 시작",
        stop_prompt="⏹️ 녹음 완료",
        key=mic_key,
        use_container_width=True,
        just_once=True,
    )

    blob = _mic_captured_bytes(mic_key, audio)
    if blob:
        audio_dict = audio if isinstance(audio, dict) else st.session_state.get(_mic_output_key(mic_key))
        if not isinstance(audio_dict, dict):
            audio_dict = {"bytes": blob}
        _persist_capture(
            mx, rec, audio_key=audio_key, mic_key=mic_key, audio=audio_dict, blob=blob
        )
        stop_recording_timer()
        st.session_state.pop(_rerecord_key(question_key), None)
        mime_logged = resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key)
        audio_pipeline_diag.log_captured(
            q_index=int(mx.get("current_idx") or 0),
            audio_bytes=blob,
            mime_type=mime_logged,
        )
        committed = False
        if on_recording_complete:
            try:
                committed = bool(on_recording_complete(blob))
            except Exception:
                committed = False
        set_recording_ui_state(
            question_key, STATE_SAVED if committed else STATE_RECORDED
        )
        st.rerun()

    return saved


def render_post_record_actions(
    mx: dict,
    *,
    question_key: str,
    audio_key: str,
    mic_key: str = "",
    recordings: Optional[dict] = None,
    on_analyze: Callable[[], None],
    analyze_label: str = "AI 분석하기",
    analyze_key: str = "analyze",
    rerecord_key: str = "rerecord",
    analyze_disabled: bool = False,
) -> None:
    state = get_recording_ui_state(
        question_key,
        has_saved=bool(mx.get("audio_bytes") or (recordings or mx.get("recordings") or {}).get(audio_key)),
    )
    if state == STATE_SAVED:
        return

    rec = recordings if recordings is not None else mx.get("recordings") or {}
    saved = mx.get("audio_bytes") or rec.get(audio_key)
    if not saved:
        st.markdown(
            '<p class="mx-record-empty">먼저 녹음을 완료해 주세요.</p>',
            unsafe_allow_html=True,
        )
        return

    audio_len = recording_byte_length(saved)
    st.markdown(
        f'<p class="mx-record-saved">녹음 저장됨 · {audio_len:,} bytes</p>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            analyze_label,
            type="primary",
            use_container_width=True,
            disabled=analyze_disabled,
            key=analyze_key,
        ):
            on_analyze()
    with c2:
        if st.button("다시 녹음하기", use_container_width=True, key=rerecord_key):

            def _clear() -> None:
                if isinstance(rec, dict):
                    rec.pop(audio_key, None)
                mx["audio_bytes"] = None
                mx.pop("preview_transcript", None)
                if mic_key:
                    st.session_state.pop(_mic_output_key(mic_key), None)
                reset_recording_ui_for_question(question_key)
                reset_recording_timer()

            _clear()
            st.rerun()
