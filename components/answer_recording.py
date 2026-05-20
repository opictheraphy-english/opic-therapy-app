"""
Unified answer recording UI for mock / coaching / topic practice.

``streamlit_mic_recorder`` cannot be started programmatically (browser security).
One mic control: start label ``답변 시작``, stop label ``녹음 완료``.
"""

from __future__ import annotations

import html
import logging
from typing import Any, Callable, Dict, Optional, Tuple

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

logger = logging.getLogger(__name__)

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

_ACTIVE_AUDIO_KEY = "recording_active_audio_key"


def _retry_nonce_storage_key(
    mode: str,
    question_id: str,
    question_index: int | None,
) -> str:
    qid = str(question_id or "").strip()
    idx = int(question_index) if question_index is not None else -1
    return f"recording_retry_nonce::{mode}::{qid}::{idx}"


def get_recording_retry_nonce(
    mode: str,
    question_id: str,
    question_index: int | None = None,
) -> int:
    key = _retry_nonce_storage_key(mode, question_id, question_index)
    try:
        return max(0, int(st.session_state.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def bump_recording_retry_nonce(
    mode: str,
    question_id: str,
    question_index: int | None = None,
) -> int:
    """Increment retry nonce so mic widget remounts after 다시 녹음 / 다시 말하기."""
    storage = _retry_nonce_storage_key(mode, question_id, question_index)
    nonce = get_recording_retry_nonce(mode, question_id, question_index) + 1
    st.session_state[storage] = nonce
    try:
        logger.debug(
            "[RECORDER_RESET] mode=%s q_idx=%s retry_nonce=%s",
            mode,
            question_index if question_index is not None else "—",
            nonce,
        )
    except Exception:
        pass
    return nonce


def real_mock_empty_commit_guard_key(question_key: str, audio_key: str) -> str:
    """Once-per-attempt guard so empty commit does not loop on rerun."""
    return f"real_mock_empty_commit_done_{question_key}_{audio_key}"


def clear_real_mock_empty_commit_guard(
    question_key: str,
    audio_key: str,
    *,
    mic_key: str = "",
) -> None:
    st.session_state.pop(real_mock_empty_commit_guard_key(question_key, audio_key), None)
    st.session_state.pop(f"{question_key}_mic_id_at_mount", None)
    st.session_state.pop(f"{question_key}_mic_stop_completed", None)
    st.session_state.pop(f"{question_key}_mic_had_return", None)
    if mic_key:
        clear_mic_recording_cache(mic_key)


def clear_all_real_mock_empty_commit_guards() -> None:
    for key in list(st.session_state.keys()):
        sk = str(key)
        if sk.startswith("real_mock_empty_commit_done_"):
            st.session_state.pop(key, None)
        elif sk.endswith("_mic_id_at_mount") or sk.endswith("_mic_stop_completed"):
            st.session_state.pop(key, None)


def build_recording_keys(
    mode: str,
    question_id: str,
    question_index: int | None = None,
    *,
    retry_nonce: int | None = None,
) -> Tuple[str, str]:
    """Stable keys per question + retry — ``(recording_question_key, mic_key)``."""
    qid = str(question_id or "").strip()
    idx = int(question_index) if question_index is not None else 0
    nonce = (
        int(retry_nonce)
        if retry_nonce is not None
        else get_recording_retry_nonce(mode, qid, question_index)
    )
    rqk = f"{mode}_{qid}_{idx}_{nonce}"
    return rqk, f"mic_{rqk}"


def get_saved_audio_for_key(
    recordings: Optional[dict],
    audio_key: str,
) -> bytes | None:
    """Source of truth for whether this question already has saved audio."""
    if not isinstance(recordings, dict) or not audio_key:
        return None
    blob = recordings.get(audio_key)
    if blob and isinstance(blob, (bytes, bytearray)):
        return bytes(blob)
    return None


def _state_key(question_key: str) -> str:
    return f"recording_ui_state::{question_key}"


def _rerecord_key(question_key: str) -> str:
    return f"recording_rerecord::{question_key}"


def _started_key(question_key: str) -> str:
    return f"recording_started_for::{question_key}"


def _mic_output_key(mic_key: str) -> str:
    return f"{mic_key}_output"


def _mic_widget_invoked_key(mic_key: str) -> str:
    return f"{mic_key}_widget_invoked"


def _mic_mount_rerun_key(mic_key: str) -> str:
    return f"{mic_key}_mount_rerun_done"


def _resolved_saved_audio(
    mx: dict,
    rec: Dict[str, Any],
    audio_key: str,
) -> bytes | None:
    """Saved bytes for this question only — never infer from stale ``mx['audio_bytes']``."""
    return get_saved_audio_for_key(rec, audio_key)


def _clear_stale_saved_ui_state(question_key: str, *, has_saved: bool) -> None:
    if not has_saved and st.session_state.get(_state_key(question_key)) == STATE_SAVED:
        st.session_state.pop(_state_key(question_key), None)


def _detach_global_audio_for_other_question(mx: dict, audio_key: str) -> None:
    """Legacy ``mx['audio_bytes']`` must not mark a new question as already saved."""
    active = st.session_state.get(_ACTIVE_AUDIO_KEY)
    if active and active != audio_key:
        mx["audio_bytes"] = None
    elif not active and mx.get("audio_bytes"):
        mx["audio_bytes"] = None


def get_recording_ui_state(
    question_key: str,
    *,
    has_saved: bool,
    analyzing: bool = False,
) -> str:
    if analyzing:
        return STATE_ANALYZING
    explicit = st.session_state.get(_state_key(question_key))
    if explicit == STATE_SAVED and not has_saved:
        st.session_state.pop(_state_key(question_key), None)
        explicit = None
    if explicit == STATE_SAVED:
        return STATE_SAVED
    if has_saved and not st.session_state.get(_rerecord_key(question_key)):
        if explicit == STATE_SAVED:
            return STATE_SAVED
        return STATE_RECORDED
    if st.session_state.get("recording_timer_active"):
        if st.session_state.get("recording_timer_question_key") == question_key:
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
    st.session_state.pop(_mic_widget_invoked_key(mic_key), None)
    st.session_state.pop(_mic_mount_rerun_key(mic_key), None)


def _mic_captured_bytes(mic_key: str, audio: Any) -> bytes | None:
    """Return bytes when capture exists; ``b\"\"`` when recorder returned empty audio."""
    if isinstance(audio, dict) and "bytes" in audio:
        raw = audio.get("bytes")
        if raw is None:
            return b""
        return bytes(raw) if raw else b""
    cached = st.session_state.get(_mic_output_key(mic_key))
    if isinstance(cached, dict) and "bytes" in cached:
        raw = cached.get("bytes")
        if raw is None:
            return b""
        return bytes(raw) if raw else b""
    return None


def _mic_output_exists(mic_key: str) -> bool:
    return _mic_output_key(mic_key) in st.session_state


def _track_real_mock_mic_stop(question_key: str, mic_key: str, audio: Any) -> bool:
    """True after streamlit_mic_recorder reports a new recording id (stop completed)."""
    mount_key = f"{question_key}_mic_id_at_mount"
    stop_key = f"{question_key}_mic_stop_completed"
    if mount_key not in st.session_state:
        st.session_state[mount_key] = int(st.session_state.get("_last_mic_recorder_audio_id") or 0)
    try:
        current_id = int(st.session_state.get("_last_mic_recorder_audio_id") or 0)
    except (TypeError, ValueError):
        current_id = 0
    mount_id = int(st.session_state.get(mount_key) or 0)
    if audio is not None or current_id > mount_id:
        st.session_state[stop_key] = True
    return bool(st.session_state.get(stop_key))


def _persist_capture(
    mx: dict,
    rec: Dict[str, Any],
    *,
    audio_key: str,
    mic_key: str,
    audio: dict,
    blob: bytes,
    mode: str = "",
    question_index: int | None = None,
) -> None:
    rec[audio_key] = blob
    mx["audio_bytes"] = blob
    st.session_state[_ACTIVE_AUDIO_KEY] = audio_key
    fmt = (audio.get("format") or audio.get("mime") or "").strip()
    if fmt:
        mx.setdefault("recording_mime_by_key", {})[audio_key] = fmt
    st.session_state[_mic_output_key(mic_key)] = audio
    try:
        logger.debug(
            "[RECORDER_SAVE] mode=%s q_idx=%s audio_len=%s audio_key=%s",
            mode or "—",
            question_index if question_index is not None else "—",
            len(blob),
            audio_key,
        )
    except Exception:
        pass


def render_recording_status_banner(state: str, *, compact: bool = False) -> None:
    if compact:
        messages = {
            STATE_IDLE: "답변 시작을 누르면 녹음과 타이머가 시작됩니다.",
            STATE_RECORDING: "말을 마치면 녹음 완료를 눌러 주세요.",
        }
    else:
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


def open_record_stage(
    title: str = "마이크로 답변을 녹음하세요",
    *,
    compact: bool = False,
) -> None:
    if compact:
        st.markdown(
            """
            <div class="mx-record-stage mx-record-stage--compact">
              <p class="mx-record-eyebrow">답변 녹음</p>
            """,
            unsafe_allow_html=True,
        )
        return
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
    mode: str = "",
    question_index: int | None = None,
) -> Optional[bytes]:
    """Mic + timer. Returns saved audio bytes when recording is complete."""
    from streamlit_mic_recorder import mic_recorder

    rec: Dict[str, Any] = (
        recordings if recordings is not None else mx.setdefault("recordings", {})
    )
    _detach_global_audio_for_other_question(mx, audio_key)
    saved = _resolved_saved_audio(mx, rec, audio_key)
    has_saved = bool(saved)
    _clear_stale_saved_ui_state(question_key, has_saved=has_saved)
    mode_norm = str(mode or "").strip().lower()
    is_real_mock = mode_norm == "real_mock"
    state = get_recording_ui_state(question_key, has_saved=has_saved, analyzing=analyzing)
    show_recorder = state in (STATE_IDLE, STATE_RECORDING)

    visible_control = "hidden"
    try:
        if state == STATE_IDLE:
            visible_control = "start"
        elif state == STATE_RECORDING:
            visible_control = "stop"
    except Exception:
        pass
    try:
        logger.debug(
            "[RECORDER_UI_RENDER] mode=%s q_idx=%s audio_key=%s state=%s "
            "show_recorder=%s has_saved=%s visible_control=%s",
            mode or "—",
            question_index if question_index is not None else "—",
            audio_key,
            state,
            show_recorder,
            has_saved,
            visible_control,
        )
    except Exception:
        pass

    prepare_recording_timer(question_key)
    render_recording_timer(question_key, has_saved_audio=has_saved)

    if state == STATE_ANALYZING:
        return saved if has_saved else None

    if state == STATE_SAVED:
        if has_saved:
            return saved
        if is_real_mock:
            st.session_state.pop(_state_key(question_key), None)
            state = get_recording_ui_state(
                question_key, has_saved=has_saved, analyzing=analyzing
            )
            show_recorder = state in (STATE_IDLE, STATE_RECORDING)
        else:
            return None

    if state == STATE_RECORDED and has_saved:
        if on_recording_complete is None:
            return saved
        if mode_norm == "mini_mock_v2":
            show_recorder = state in (STATE_IDLE, STATE_RECORDING)
        else:
            st.markdown(
                '<p class="mx-record-status">녹음이 완료되었습니다. 저장을 다시 시도해 주세요.</p>',
                unsafe_allow_html=True,
            )
            show_recorder = True

    if not show_recorder and not has_saved:
        show_recorder = True

    if not show_recorder:
        return saved if has_saved else None

    st.session_state[_ACTIVE_AUDIO_KEY] = audio_key

    user_started = bool(st.session_state.get(_started_key(question_key)))
    use_compact_copy = is_real_mock or mode_norm in (
        "mini_mock",
        "mini_mock_v2",
        "topic_practice",
    )
    mic_was_invoked = bool(st.session_state.get(_mic_widget_invoked_key(mic_key)))

    render_recording_status_banner(
        STATE_RECORDING if user_started else STATE_IDLE,
        compact=use_compact_copy,
    )

    audio = mic_recorder(
        start_prompt="🎤 답변 시작",
        stop_prompt="■ 녹음 완료",
        key=mic_key,
        use_container_width=True,
        just_once=True,
    )
    st.session_state[_mic_widget_invoked_key(mic_key)] = True

    if (
        mic_was_invoked
        and not user_started
        and audio is None
        and _mic_captured_bytes(mic_key, audio) is None
    ):
        start_recording_timer(question_key)
        st.session_state[_started_key(question_key)] = True
        set_recording_ui_state(question_key, STATE_RECORDING)
        user_started = True
        try:
            if mode_norm == "mini_mock_v2":
                logger.info(
                    "[MINI_V2_START_CLICK_NO_COMMIT] idx=%s audio_key=%s",
                    question_index if question_index is not None else "—",
                    audio_key,
                )
            logger.info(
                "[RECORDER_START] mode=%s q_idx=%s audio_key=%s",
                mode or "—",
                question_index if question_index is not None else "—",
                audio_key,
            )
        except Exception:
            pass

    state = get_recording_ui_state(question_key, has_saved=has_saved, analyzing=analyzing)

    blob = _mic_captured_bytes(mic_key, audio)
    mic_stop_completed = False
    if is_real_mock:
        mic_stop_completed = _track_real_mock_mic_stop(question_key, mic_key, audio)

    try:
        logger.debug(
            "[RECORDER_COMPONENT_VALUE] mode=%s question_key=%s mic_key=%s "
            "audio_is_none=%s audio_type=%s blob_is_none=%s blob_len=%s mic_stop=%s",
            mode or "—",
            question_key,
            mic_key,
            audio is None,
            type(audio).__name__ if audio is not None else "none",
            blob is None,
            len(blob) if blob is not None else -1,
            mic_stop_completed,
        )
    except Exception:
        pass

    has_capture = blob is not None
    mic_had_return_key = f"{question_key}_mic_had_return"
    if audio is not None:
        st.session_state[mic_had_return_key] = True
    is_mini_mock_v2 = mode_norm == "mini_mock_v2"
    stop_no_blob = (
        is_real_mock
        and on_recording_complete is not None
        and not has_capture
        and (
            audio is not None
            or mic_stop_completed
            or bool(st.session_state.get(mic_had_return_key))
        )
    )
    empty_commit_key = real_mock_empty_commit_guard_key(question_key, audio_key)

    if has_capture or stop_no_blob:
        try:
            logger.info(
                "[RECORDER_STOP] mode=%s q_idx=%s audio_key=%s has_blob=%s bytes=%s",
                mode or "—",
                question_index if question_index is not None else "—",
                audio_key,
                bool(has_capture and blob and len(blob) > 0),
                len(blob) if blob is not None else 0,
            )
        except Exception:
            pass
        if has_capture and len(blob) > 0:
            audio_dict = audio if isinstance(audio, dict) else st.session_state.get(_mic_output_key(mic_key))
            if not isinstance(audio_dict, dict):
                audio_dict = {"bytes": blob}
            _persist_capture(
                mx,
                rec,
                audio_key=audio_key,
                mic_key=mic_key,
                audio=audio_dict,
                blob=blob,
                mode=mode,
                question_index=question_index,
            )
            stop_recording_timer()
            st.session_state.pop(_rerecord_key(question_key), None)
            mime_logged = resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key)
            audio_pipeline_diag.log_captured(
                q_index=int(mx.get("current_idx") or question_index or 0),
                audio_bytes=blob,
                mime_type=mime_logged,
            )
            commit_blob: bytes = blob
        elif has_capture and len(blob) == 0:
            if is_real_mock and st.session_state.get(empty_commit_key):
                return saved
            stop_recording_timer()
            st.session_state.pop(_rerecord_key(question_key), None)
            commit_blob = b""
        elif stop_no_blob:
            if is_real_mock and st.session_state.get(empty_commit_key):
                return saved
            try:
                logger.warning(
                    "[RECORDER_NO_BLOB] mode=%s question_key=%s mic_key=%s ui_state=%s "
                    "active_key=%s output_exists=%s mic_stop=%s",
                    mode or "—",
                    question_key,
                    mic_key,
                    state,
                    st.session_state.get(_ACTIVE_AUDIO_KEY),
                    _mic_output_exists(mic_key),
                    mic_stop_completed,
                )
            except Exception:
                pass
            stop_recording_timer()
            commit_blob = b""
        else:
            return saved

        empty_attempt = is_real_mock and (stop_no_blob or len(commit_blob) == 0)
        if empty_attempt:
            try:
                logger.debug(
                    "[RECORDER_EMPTY_COMMIT_ATTEMPT] question_key=%s audio_key=%s "
                    "stop_no_blob=%s bytes=%s",
                    question_key,
                    audio_key,
                    stop_no_blob,
                    len(commit_blob),
                )
            except Exception:
                pass
            st.session_state[empty_commit_key] = True

        committed = False
        if on_recording_complete:
            try:
                if empty_attempt:
                    try:
                        logger.warning(
                            "[REAL_MOCK_EMPTY_COMMIT_FROM_COMPONENT] q_idx=%s audio_key=%s "
                            "reason=%s bytes=%s",
                            question_index if question_index is not None else "—",
                            audio_key,
                            "recorder_stop_no_bytes" if stop_no_blob else "recorder_empty_bytes",
                            len(commit_blob),
                        )
                    except Exception:
                        pass
                try:
                    logger.debug(
                        "[RECORDER_ON_COMPLETE_CALLED] mode=%s question_key=%s bytes=%s",
                        mode or "—",
                        question_key,
                        len(commit_blob),
                    )
                except Exception:
                    pass
                committed = bool(on_recording_complete(commit_blob))
            except Exception:
                logger.exception(
                    "[RECORDER_SAVE] on_recording_complete failed mode=%s audio_key=%s",
                    mode,
                    audio_key,
                )
                committed = False
            finally:
                if empty_attempt and not committed:
                    st.session_state.pop(empty_commit_key, None)
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
    mode: str = "",
    question_index: int | None = None,
    question_id: str = "",
) -> None:
    rec = recordings if recordings is not None else mx.get("recordings") or {}
    saved = _resolved_saved_audio(mx, rec, audio_key)
    state = get_recording_ui_state(
        question_key,
        has_saved=bool(saved),
    )
    if state == STATE_SAVED:
        return

    if not saved:
        st.markdown(
            '<p class="mx-record-empty">먼저 녹음을 완료해 주세요.</p>',
            unsafe_allow_html=True,
        )
        return

    if st.session_state.get("show_dev_debug"):
        audio_len = recording_byte_length(saved)
        st.caption(f"[dev] 녹음 저장됨 · {audio_len:,} bytes")

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
                if mode:
                    qid = (
                        str(question_id).strip()
                        or (
                            str(audio_key)[2:]
                            if str(audio_key).startswith("q_")
                            else str(audio_key)
                        )
                    )
                    bump_recording_retry_nonce(mode, qid, question_index)
                if isinstance(rec, dict):
                    rec.pop(audio_key, None)
                mx["audio_bytes"] = None
                mx.pop("preview_transcript", None)
                if st.session_state.get(_ACTIVE_AUDIO_KEY) == audio_key:
                    st.session_state.pop(_ACTIVE_AUDIO_KEY, None)
                if mic_key:
                    clear_mic_recording_cache(mic_key)
                reset_recording_ui_for_question(question_key)
                reset_recording_timer()
                st.session_state[_rerecord_key(question_key)] = True

            _clear()
            st.rerun()
