"""2-minute answer timer for mock / coaching / topic practice (UI only)."""

from __future__ import annotations

import html
import time
from datetime import timedelta

import streamlit as st

RECORDING_TIMER_DURATION_SEC = 120
RECORDING_TIMER_WARN_SEC = 15
RECORDING_TIMER_UI_WARN_SEC = 30


def reset_recording_timer() -> None:
    """Clear timer state (portal, new question, retry)."""
    st.session_state["recording_timer_active"] = False
    st.session_state["recording_mic_armed"] = False
    st.session_state.pop("recording_mic_armed_key", None)
    st.session_state.pop("recording_timer_started_at", None)
    st.session_state.pop("recording_timer_question_key", None)
    st.session_state.pop("recording_timer_time_up", None)
    st.session_state.pop("recording_timer_warned", None)
    st.session_state["recording_timer_duration_sec"] = RECORDING_TIMER_DURATION_SEC


def arm_recording_mic(question_key: str) -> None:
    """Open the answer/mic area without starting the countdown."""
    prepare_recording_timer_question(question_key)
    st.session_state["recording_mic_armed"] = True
    st.session_state["recording_mic_armed_key"] = (question_key or "").strip()


def prepare_recording_timer_question(question_key: str) -> None:
    """Bind timer to the current question; reset when the question changes."""
    qk = (question_key or "").strip()
    if not qk:
        return
    if st.session_state.get("recording_timer_question_key") != qk:
        reset_recording_timer()
        st.session_state["recording_timer_question_key"] = qk


def prepare_recording_timer(
    question_key: str | None = None,
    duration_sec: int | None = None,
) -> None:
    """
    Prepare inactive timer state for a question (safe on page render).

    Does not start the countdown — use ``start_recording_timer`` when recording begins.
    """
    if duration_sec is not None:
        try:
            st.session_state["recording_timer_duration_sec"] = max(
                1, int(duration_sec)
            )
        except (TypeError, ValueError):
            st.session_state["recording_timer_duration_sec"] = RECORDING_TIMER_DURATION_SEC
    elif "recording_timer_duration_sec" not in st.session_state:
        st.session_state["recording_timer_duration_sec"] = RECORDING_TIMER_DURATION_SEC
    if question_key:
        prepare_recording_timer_question(str(question_key))


def start_recording_timer(question_key: str) -> None:
    """Start countdown when the user begins actual recording (mic / 말하기)."""
    prepare_recording_timer_question(question_key)
    st.session_state["recording_timer_duration_sec"] = RECORDING_TIMER_DURATION_SEC
    st.session_state["recording_timer_started_at"] = time.time()
    st.session_state["recording_timer_active"] = True
    st.session_state["recording_timer_time_up"] = False
    st.session_state["recording_timer_warned"] = False


def stop_recording_timer() -> None:
    st.session_state["recording_timer_active"] = False


def sync_recording_timer(
    question_key: str,
    *,
    has_saved_audio: bool,
) -> None:
    """Stop when audio is saved; countdown starts via start_recording_timer only."""
    prepare_recording_timer_question(question_key)
    if has_saved_audio:
        stop_recording_timer()


def _duration_sec() -> int:
    try:
        return int(st.session_state.get("recording_timer_duration_sec") or RECORDING_TIMER_DURATION_SEC)
    except (TypeError, ValueError):
        return RECORDING_TIMER_DURATION_SEC


def remaining_seconds() -> int:
    """Seconds left; derived from start time (no manual decrement drift)."""
    if not st.session_state.get("recording_timer_active"):
        return _duration_sec()
    started = st.session_state.get("recording_timer_started_at")
    if not started:
        return _duration_sec()
    try:
        elapsed = int(time.time() - float(started))
    except (TypeError, ValueError):
        elapsed = 0
    return max(0, _duration_sec() - elapsed)


def _format_mm_ss(total_sec: int) -> str:
    s = max(0, int(total_sec))
    return f"{s // 60:02d}:{s % 60:02d}"


def _timer_state(rem: int, *, active: bool) -> str:
    if not active:
        return "idle"
    if rem <= 0:
        return "up"
    if rem <= RECORDING_TIMER_UI_WARN_SEC:
        return "warn"
    return "normal"


def _timer_status_label(active: bool, state: str) -> str:
    if not active:
        return "대기 중"
    if state == "up":
        return "시간 종료"
    return "녹음 중"


def _timer_html(rem: int, *, active: bool, state: str) -> str:
    total = _duration_sec()
    time_display = _format_mm_ss(rem)
    progress_pct = int(round((rem / total) * 100)) if total > 0 else 0
    progress_pct = max(0, min(100, progress_pct))
    status = _timer_status_label(active, state)
    state_esc = html.escape(state)
    return f"""
        <div class="mx-rec-timer mx-answer-timer mx-rec-timer--{state_esc}" role="timer" aria-live="polite" aria-atomic="true">
          <div class="mx-answer-timer-head">
            <p class="mx-rec-timer-label mx-answer-timer-label">답변 시간</p>
            <span class="mx-answer-timer-status mx-answer-timer-status--{state_esc}">{html.escape(status)}</span>
          </div>
          <p class="mx-rec-timer-value mx-answer-timer-value">{html.escape(time_display)}</p>
          <div class="mx-rec-timer-progress mx-answer-timer-bar" aria-hidden="true">
            <span class="mx-rec-timer-progress-fill mx-answer-timer-bar-fill" style="width:{progress_pct}%;"></span>
          </div>
        </div>
        """


def _update_timer_flags(rem: int) -> None:
    if rem <= 0:
        st.session_state["recording_timer_time_up"] = True
    if rem <= RECORDING_TIMER_WARN_SEC and rem > 0:
        st.session_state["recording_timer_warned"] = True


def _paint_timer_into(slot, question_key: str, *, has_saved_audio: bool) -> None:
    active = bool(st.session_state.get("recording_timer_active")) and not has_saved_audio
    if (
        active
        and st.session_state.get("recording_timer_question_key") != question_key
    ):
        active = False
    rem = remaining_seconds() if active else _duration_sec()
    if active:
        _update_timer_flags(rem)
    state = _timer_state(rem, active=active)
    slot.markdown(_timer_html(rem, active=active, state=state), unsafe_allow_html=True)


def render_recording_timer(question_key: str, *, has_saved_audio: bool) -> None:
    """Render timer card; ticks every 1s while recording is armed."""
    sync_recording_timer(question_key, has_saved_audio=has_saved_audio)

    active = bool(st.session_state.get("recording_timer_active")) and not has_saved_audio

    if active and hasattr(st, "fragment"):
        try:
            run_every = timedelta(seconds=1)
        except Exception:
            run_every = None

        if run_every is not None:

            @st.fragment(run_every=run_every)
            def _refresh_timer() -> None:
                if st.session_state.get("recording_timer_question_key") != question_key:
                    return
                if not st.session_state.get("recording_timer_active"):
                    return
                slot = st.empty()
                _paint_timer_into(slot, question_key, has_saved_audio=has_saved_audio)

            _refresh_timer()
            return

    timer_slot = st.empty()
    _paint_timer_into(timer_slot, question_key, has_saved_audio=has_saved_audio)
