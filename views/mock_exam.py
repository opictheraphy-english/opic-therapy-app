"""모의고사 SURVEY / TEST / REPORT — lightweight mobile-first version.

Heavy deps (``google.genai``, ``pandas``/``plotly`` via final_report,
``streamlit_mic_recorder``) are imported lazily per branch so cold-start on
Render stays minimal. Visualizer + live-analytics monitoring tiles were
removed per mobile-first spec.

Failure handling
----------------
When Gemini analysis fails (503 / 429 / timeout / network) after all
retries, the row is stored as ``analysis_pending`` so the user can advance;
recordings stay in ``recordings``. Optional recovery still applies for
no-speech trust-gate cases.
"""
from __future__ import annotations

import html
import logging
import re
import secrets
import time
from typing import Any, Callable, Dict

import streamlit as st

from components.audio_player import render_exam_question_audio_player
from components.collapsible_section import render_collapsible_section
from components.ai_analysis_waiting import (
    finish_analysis_waiting_ui,
    render_ai_analysis_waiting,
    render_topic_mini_report_waiting,
)
from components.topic_mini_report_ui import (
    render_topic_all_saved_card,
    render_topic_answer_saved_card,
    render_topic_mini_report,
    render_topic_report_pending_retry_screen,
)
from components.answer_recording import (
    STATE_RECORDED,
    STATE_SAVED,
    bump_recording_retry_nonce,
    build_recording_keys,
    clear_all_real_mock_empty_commit_guards,
    clear_real_mock_empty_commit_guard,
    close_record_stage,
    get_recording_ui_state,
    get_saved_audio_for_key,
    open_record_stage,
    real_mock_empty_commit_guard_key,
    render_answer_recording_stage as _render_answer_recording_stage,
    render_post_record_actions,
)
from components.recording_timer import reset_recording_timer, stop_recording_timer
from components.coaching_experience import (
    render_coaching_cta_preamble,
    render_coaching_retry_banner,
    render_history_expander_coaching,
    render_structured_coaching_report,
)
from components.final_report_preview import (
    render_final_report_preview_card,
    render_real_mock_progress_chip,
)
from components.topbar import render_top_bar
from services.evaluation_service import analyze_audio_with_retry
from services.mock_exam.mock_exam_test_set_generator import generate_test_set
from services.report_service import cache_analysis_payload
from services.tts_service import (
    DEFAULT_TTS_PITCH,
    DEFAULT_TTS_SPEAKING_RATE,
    clear_mock_question_tts_keys,
    neural2_voice_for_session,
    tts_audio_cached,
)
from utils.exam_state import (
    NO_AUDIO_ERROR_SENTINEL,
    NO_SPEECH_ERROR_SENTINEL,
    NEEDS_REVIEW_ERROR_SENTINEL,
    NON_ENGLISH_ERROR_SENTINEL,
    UNCLEAR_SPEECH_ERROR_SENTINEL,
    apply_completed_analysis_result,
    apply_needs_review_result,
    apply_non_english_result,
    apply_insufficient_response_result,
    apply_no_audio_result,
    apply_pending_analysis_result,
    apply_unclear_speech_result,
    build_analysis_pending_result,
    classify_analysis_error,
    clear_pending_recovery,
    count_completed_exam_prefix,
    find_result_row,
    format_mock_attempt_label,
    get_mock_total_questions,
    has_pending_recovery_for,
    has_resumable_exam,
    is_completed_mock,
    is_last_mock_question,
    mark_mock_exam_completed,
    mark_real_mock_exam_completed,
    mark_pending_recovery,
    reconcile_mock_exam_pointer,
    reset_exam_state,
    reset_real_mock_attempt,
    save_answer_placeholder_before_ai,
    save_real_mock_unanalyzed_answer,
    start_new_mock_attempt,
    stored_audio_for_row,
    upsert_mock_exam_result,
)
from utils.local_profile import force_restore_mock_from_disk, iso_now, sync_user_progress
from utils.secrets import get_gemini_api_key
from utils.session_state import mock_session, settings_session, sync_settings_to_legacy
from utils.streamlit_ui import clean_visible_label
from utils import audio_pipeline_diag
from utils.speech_recording import (
    MIN_RECORDED_AUDIO_BYTES,
    VERY_SMALL_SPEECH_AUDIO_BYTES,
    classify_post_analysis_issue,
    classify_pre_analysis_blob,
    classify_pre_gemini_speech,
    has_substantial_recording,
    recording_byte_length,
    should_treat_analysis_failure_as_no_speech,
    render_language_mismatch_preview,
    render_recording_debug_block,
    resolve_mime_for_analysis,
    resolve_mime_for_debug,
    speech_issue_copy,
)
from utils.text_utils import (
    DISCOURSE_MARKERS,
    PRECISION_MAP,
    is_real_speech_transcript,
    keywords,
)

# Per-mode analysis re-entry guards (Phase 1 — no cross-mode blocking).
_LEGACY_ANALYSIS_IN_FLIGHT_KEY = "_analysis_in_flight"
_REAL_MOCK_ANALYSIS_IN_FLIGHT_KEY = "real_mock_analysis_in_flight"
_REAL_MOCK_FINAL_BATCH_IN_FLIGHT_KEY = "real_mock_final_batch_in_flight"
_MINI_MOCK_ANALYSIS_IN_FLIGHT_KEY = "mini_mock_analysis_in_flight"
_TOPIC_PRACTICE_ANALYSIS_IN_FLIGHT_KEY = "topic_practice_analysis_in_flight"
_TOPIC_REPORT_ATTEMPT_KEY = "topic_report_analysis_attempt_id"
_TOPIC_REPORT_BATCH_FINISHED_KEY = "topic_report_analysis_batch_finished"
_COACHING_ANALYSIS_IN_FLIGHT_KEY = "coaching_analysis_in_flight"
_MINI_MOCK_ANALYSIS_IN_PROGRESS_KEY = "mini_mock_analysis_in_progress"
_MINI_MOCK_ANALYSIS_ATTEMPT_KEY = "mini_mock_analysis_attempt_id"
_MINI_MOCK_BATCH_ATTEMPTS_KEY = "_mini_mock_last_batch_attempts"
_MINI_MOCK_BATCH_FINISHED_KEY = "mini_mock_analysis_batch_finished"
_LATEST_MINI_MOCK_API_DEBUG_KEY = "latest_mini_mock_api_debug"
MINI_MOCK_ANALYZING_TIMEOUT_SEC = 60
_REAL_MOCK_PAGE_KEY = "real_mock_page"
_REAL_MOCK_SAVED_Q_KEY = "real_mock_last_saved_q_id"
_REAL_MOCK_SKIP_RECONCILE_KEY = "_real_mock_skip_reconcile_once"
_REAL_MOCK_POST_SAVE_LOCK_KEY = "_real_mock_post_save_lock"
_REAL_MOCK_POST_SAVE_PAGES = frozenset(
    {"SPEECH_RECOVERY", "ANSWER_SAVED", "ANALYSIS_PENDING"},
)
_KNOWN_REAL_MOCK_PAGES = frozenset(
    {
        "QUESTION",
        "ANSWER_SAVED",
        "SPEECH_RECOVERY",
        "ANALYSIS_PENDING",
        "FINAL_READY",
        "FINAL_ANALYZING",
        "FINAL_PREVIEW",
        "FINAL_REPORT",
        "RECOVERY",
    }
)

logger = logging.getLogger(__name__)


def _analysis_in_flight_key(mode: str) -> str:
    m = str(mode or "").strip().lower()
    if m in ("real_mock", "real", "exam"):
        return _REAL_MOCK_ANALYSIS_IN_FLIGHT_KEY
    if m in ("mini_mock", "mini"):
        return _MINI_MOCK_ANALYSIS_IN_FLIGHT_KEY
    if m in ("topic_practice", "topic"):
        return _TOPIC_PRACTICE_ANALYSIS_IN_FLIGHT_KEY
    return _COACHING_ANALYSIS_IN_FLIGHT_KEY


def _get_analysis_in_flight(mode: str) -> bool:
    return bool(st.session_state.get(_analysis_in_flight_key(mode)))


def _set_analysis_in_flight(mode: str, value: bool) -> None:
    key = _analysis_in_flight_key(mode)
    st.session_state[key] = bool(value)
    try:
        logger.debug("[ANALYSIS_FLAG] mode=%s key=%s value=%s", mode, key, value)
    except Exception:
        pass


def _clear_legacy_analysis_in_flight() -> None:
    st.session_state.pop(_LEGACY_ANALYSIS_IN_FLIGHT_KEY, None)


def _clear_all_mode_analysis_in_flight_flags() -> None:
    for key in (
        _LEGACY_ANALYSIS_IN_FLIGHT_KEY,
        _REAL_MOCK_ANALYSIS_IN_FLIGHT_KEY,
        _REAL_MOCK_FINAL_BATCH_IN_FLIGHT_KEY,
        _MINI_MOCK_ANALYSIS_IN_FLIGHT_KEY,
        _TOPIC_PRACTICE_ANALYSIS_IN_FLIGHT_KEY,
        _COACHING_ANALYSIS_IN_FLIGHT_KEY,
    ):
        st.session_state.pop(key, None)


def _real_mock_all_questions_saved(mx: dict) -> bool:
    """True when every exam slot has a saved answer row (pending analysis counts)."""
    if not _is_real_mock(mx):
        return False
    exam = mx.get("current_exam") or mx.get("exam") or []
    if not isinstance(exam, list) or not exam:
        return False
    total = len(exam)
    return count_completed_exam_prefix(mx) >= total


def _real_mock_defer_reconcile() -> bool:
    """Do not move current_idx while a per-question post-save screen is active."""
    if st.session_state.get(_REAL_MOCK_SKIP_RECONCILE_KEY):
        return True
    lock = st.session_state.get(_REAL_MOCK_POST_SAVE_LOCK_KEY)
    if isinstance(lock, str) and lock.strip() in _REAL_MOCK_POST_SAVE_PAGES:
        return True
    return _real_mock_page() in (
        _REAL_MOCK_POST_SAVE_PAGES
        | {"FINAL_READY", "FINAL_ANALYZING"}
    )


def _arm_real_mock_post_save(mx: dict, page: str) -> None:
    """Hold post-save routing until user explicitly leaves (next / retry / portal / reset)."""
    p = str(page or "").strip()
    if p not in _REAL_MOCK_POST_SAVE_PAGES:
        return
    _set_real_mock_page(p)
    st.session_state[_REAL_MOCK_POST_SAVE_LOCK_KEY] = p
    st.session_state[_REAL_MOCK_SKIP_RECONCILE_KEY] = True
    mx["real_mock_post_save_lock"] = p


def _clear_real_mock_post_save_lock(mx: dict) -> None:
    st.session_state.pop(_REAL_MOCK_POST_SAVE_LOCK_KEY, None)
    st.session_state.pop(_REAL_MOCK_SKIP_RECONCILE_KEY, None)
    mx.pop("real_mock_post_save_lock", None)


def _maybe_reconcile_real_mock_pointer(mx: dict, *, consume_skip: bool = False) -> int:
    """Reconcile only on QUESTION — never advance idx during saved/speech-recovery screens."""
    if _real_mock_defer_reconcile():
        return _get_current_real_mock_question_index(mx)
    return reconcile_mock_exam_pointer(mx)


def _ensure_real_mock_completion_state(mx: dict) -> bool:
    """True when all answers are saved (does not auto-start final analysis)."""
    if not _is_real_mock(mx) or mx.get("_final_report_demo"):
        return False
    return _real_mock_all_questions_saved(mx)


def _real_mock_page() -> str:
    lock = st.session_state.get(_REAL_MOCK_POST_SAVE_LOCK_KEY)
    if isinstance(lock, str) and lock.strip() in _REAL_MOCK_POST_SAVE_PAGES:
        p = lock.strip()
        st.session_state[_REAL_MOCK_PAGE_KEY] = p
        mx_snap = st.session_state.get("mock")
        if isinstance(mx_snap, dict):
            mx_snap["real_mock_page"] = p
        return p
    raw = st.session_state.get(_REAL_MOCK_PAGE_KEY)
    mx_snap = st.session_state.get("mock")
    if raw is not None:
        p = str(raw).strip()
        if p and p not in _REAL_MOCK_POST_SAVE_PAGES:
            if isinstance(mx_snap, dict):
                mx_snap["real_mock_page"] = p
                mx_snap.pop("real_mock_post_save_lock", None)
            return p
    mx_raw = mx_snap.get("real_mock_page") if isinstance(mx_snap, dict) else None
    if mx_raw is not None and str(mx_raw).strip() in _REAL_MOCK_POST_SAVE_PAGES:
        p = str(mx_raw).strip()
        if raw is None or str(raw).strip() in ("", "QUESTION"):
            st.session_state[_REAL_MOCK_PAGE_KEY] = p
            st.session_state[_REAL_MOCK_POST_SAVE_LOCK_KEY] = p
            if isinstance(mx_snap, dict):
                mx_snap["real_mock_post_save_lock"] = p
            return p
    if raw is None:
        raw = mx_raw
    if raw is None:
        return "QUESTION"
    return str(raw).strip()


def _real_mock_q_index_for_id(mx: dict, q_id: int) -> int:
    exam = mx.get("current_exam") or mx.get("exam") or []
    if isinstance(exam, list):
        for i, item in enumerate(exam):
            if not isinstance(item, dict):
                continue
            try:
                item_id = int(item.get("id", i + 1))
            except (TypeError, ValueError):
                continue
            if item_id == int(q_id):
                return i
    return _get_current_real_mock_question_index(mx)


def _real_mock_clear_stale_speech_recovery(mx: dict) -> bool:
    """Drop SPEECH_RECOVERY when saved_q is missing or does not match current question."""
    page = _real_mock_page()
    lock = st.session_state.get(_REAL_MOCK_POST_SAVE_LOCK_KEY)
    if page != "SPEECH_RECOVERY" and lock != "SPEECH_RECOVERY":
        return False
    saved_q = _get_real_mock_saved_q_id(mx)
    cur = _real_mock_current_question(mx)
    cur_q = int(cur[2]) if cur else None
    if saved_q is not None and cur_q is not None and int(saved_q) == int(cur_q):
        return False
    try:
        logger.warning(
            "[REAL_MOCK_STALE_SPEECH_RECOVERY_CLEARED] saved_q=%s current_q=%s page=%s lock=%s",
            saved_q,
            cur_q,
            page,
            lock,
        )
    except Exception:
        pass
    _leave_real_mock_post_save(mx)
    _set_real_mock_page("QUESTION")
    mx["real_mock_page"] = "QUESTION"
    return True


def _is_unsupported_real_mock_page(page: str) -> bool:
    p = str(page or "").strip()
    return not p or p not in _KNOWN_REAL_MOCK_PAGES


def _ensure_real_mock_page_state() -> None:
    if _REAL_MOCK_PAGE_KEY not in st.session_state:
        st.session_state[_REAL_MOCK_PAGE_KEY] = "QUESTION"


def _route_real_mock_to_question(mx: dict) -> None:
    """Recovery / resume — keep index and results; route back to the question UI."""
    _set_real_mock_page("QUESTION")
    mp = _get_mock_page(mx)
    if mp in ("TEST", "REPORT", "FINAL", ""):
        _set_mock_page(mx, "TEST")
        st.session_state["mock_page"] = "TEST"


def _real_mock_saved_confirm_key(q_id: int) -> str:
    return f"real_mock_saved_confirm_{q_id}"


def _count_real_mock_saved_answers(mx: dict) -> int:
    return count_completed_exam_prefix(mx)


def _real_mock_log_flow(mx: dict, page: str) -> None:
    try:
        exam = mx.get("current_exam") or mx.get("exam") or []
        total = len(exam) if isinstance(exam, list) and exam else get_mock_total_questions(mx)
        results = mx.get("results") or []
        logger.debug(
            "[REAL_MOCK_ROUTE] page=%s q_idx=%s total=%s results_count=%s "
            "exam_finished=%s mock_page=%s defer_reconcile=%s skip_once=%s saved_q=%s",
            page,
            mx.get("current_idx"),
            total,
            len(results) if isinstance(results, list) else 0,
            bool(mx.get("exam_finished")),
            _get_mock_page(mx),
            _real_mock_defer_reconcile(),
            bool(st.session_state.get(_REAL_MOCK_SKIP_RECONCILE_KEY)),
            st.session_state.get(_REAL_MOCK_SAVED_Q_KEY),
        )
    except Exception:
        pass


def _get_real_mock_total_questions(mx: dict) -> int:
    exam = mx.get("current_exam") or mx.get("exam") or []
    if isinstance(exam, list) and exam:
        return len(exam)
    return int(get_mock_total_questions(mx) or 0)


def _get_current_real_mock_question_index(mx: dict) -> int:
    return int(mx.get("current_idx") or 0)


def _set_current_real_mock_question_index(mx: dict, q_idx: int) -> None:
    mx["current_idx"] = max(0, int(q_idx))


def _set_real_mock_page(page: str) -> None:
    p = str(page or "QUESTION").strip() or "QUESTION"
    st.session_state[_REAL_MOCK_PAGE_KEY] = p
    mx_snap = st.session_state.get("mock")
    if isinstance(mx_snap, dict):
        mx_snap["real_mock_page"] = p
        if p not in _REAL_MOCK_POST_SAVE_PAGES:
            mx_snap.pop("real_mock_post_save_lock", None)
            st.session_state.pop(_REAL_MOCK_POST_SAVE_LOCK_KEY, None)


def _set_real_mock_saved_q_id(mx: dict, q_id: int) -> None:
    st.session_state[_REAL_MOCK_SAVED_Q_KEY] = int(q_id)
    mx["real_mock_last_saved_q_id"] = int(q_id)


def _get_real_mock_saved_q_id(mx: dict) -> int | None:
    try:
        raw = st.session_state.get(_REAL_MOCK_SAVED_Q_KEY)
        if raw is None:
            raw = mx.get("real_mock_last_saved_q_id")
        if raw is None:
            return None
        return int(raw)
    except (TypeError, ValueError):
        return None


def _clear_real_mock_saved_q_id(mx: dict) -> None:
    st.session_state.pop(_REAL_MOCK_SAVED_Q_KEY, None)
    mx.pop("real_mock_last_saved_q_id", None)


def _leave_real_mock_post_save(mx: dict) -> None:
    """Clear post-save lock + saved_q when user advances or retries."""
    _clear_real_mock_post_save_lock(mx)
    _clear_real_mock_saved_q_id(mx)
    clear_pending_recovery(mx)
    mx.pop("real_mock_saved_confirm", None)
    st.session_state.pop("real_mock_saved_confirm", None)


def _clear_real_mock_recording_temp_state(
    mx: dict, *, q_id: int, q_index: int, mic_key: str = ""
) -> None:
    from components.answer_recording import (
        clear_mic_recording_cache,
        reset_recording_ui_for_question,
    )

    timer_key, mk = build_recording_keys("real_mock", str(q_id), q_index)
    audio_key = f"q_{int(q_id)}"
    clear_real_mock_empty_commit_guard(timer_key, audio_key, mic_key=mic_key or mk)
    reset_recording_ui_for_question(timer_key)
    clear_mic_recording_cache(mic_key or mk)
    mx["audio_bytes"] = None
    mx.pop("preview_transcript", None)
    st.session_state.pop("recording_active_audio_key", None)
    reset_recording_timer()


def go_to_next_real_mock_question(mx: dict, *, from_q_id: int | None = None) -> None:
    """Single next-question transition for real mock — all recovery/saved screens use this."""
    old_page = _real_mock_page()
    old_idx = _get_current_real_mock_question_index(mx)
    total = _get_real_mock_total_questions(mx)
    from_q = int(from_q_id) if from_q_id is not None else None
    from_idx = old_idx
    if from_q is not None:
        from_idx = _real_mock_q_index_for_id(mx, from_q)

    had_saved_q = _get_real_mock_saved_q_id(mx) is not None
    had_lock = bool(st.session_state.get(_REAL_MOCK_POST_SAVE_LOCK_KEY))
    had_pending = bool(mx.get("pending_recovery"))

    if from_q is not None:
        st.session_state.pop(_real_mock_saved_confirm_key(int(from_q)), None)
        _, from_mic = build_recording_keys("real_mock", str(from_q), from_idx)
        _clear_real_mock_recording_temp_state(
            mx, q_id=int(from_q), q_index=from_idx, mic_key=from_mic
        )

    _leave_real_mock_post_save(mx)
    mx["real_mock_page"] = "QUESTION"

    next_idx = from_idx + 1
    exam = mx.get("current_exam") or mx.get("exam") or []
    if next_idx < total:
        next_q_id = next_idx + 1
        if isinstance(exam, list) and next_idx < len(exam):
            nq = exam[next_idx]
            if isinstance(nq, dict):
                next_q_id = int(nq.get("id", next_idx + 1))
        _set_current_real_mock_question_index(mx, next_idx)
        _clear_real_mock_recording_temp_state(mx, q_id=next_q_id, q_index=next_idx)
        _set_real_mock_page("QUESTION")
        _set_mock_page(mx, "TEST")
        st.session_state["mock_page"] = "TEST"
        new_page = "QUESTION"
    else:
        _set_real_mock_page("FINAL_READY")
        _set_mock_page(mx, "TEST")
        st.session_state["mock_page"] = "TEST"
        if _real_mock_all_questions_saved(mx):
            mx["exam_finished"] = True
        new_page = "FINAL_READY"

    st.session_state[_REAL_MOCK_SKIP_RECONCILE_KEY] = True
    try:
        logger.info(
            "[REAL_MOCK_NEXT_FROM_RECOVERY] from_q_id=%s old_index=%s new_index=%s "
            "old_page=%s new_page=%s cleared_saved_q=%s cleared_post_save_lock=%s "
            "cleared_pending_recovery=%s",
            from_q,
            old_idx,
            _get_current_real_mock_question_index(mx),
            old_page,
            new_page,
            had_saved_q,
            had_lock,
            had_pending,
        )
    except Exception:
        pass
    _real_mock_log_flow(mx, _real_mock_page())
    st.rerun()


def _render_real_mock_recovery(mx: dict) -> None:
    """Catch-all recovery — never leave a blank screen."""
    render_top_bar(
        "실전 모의고사",
        back_href="?nav=MOCK",
        eyebrow=format_mock_attempt_label(mx),
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">연결 안내</div>
          <div class="rv-title">화면을 다시 연결해야 해요</div>
          <div class="rv-body">현재 모의고사 화면 상태가 정상적으로 연결되지 않았어요.<br/>
            저장된 답변은 유지되어 있습니다. 아래 버튼으로 이어서 진행해 주세요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "현재 문항 다시 열기",
            type="primary",
            use_container_width=True,
            key="real_mock_recovery_open_q",
        ):
            _route_real_mock_to_question(mx)
            st.rerun()
    with c2:
        if st.button(
            "다음 문제로 넘어가기",
            use_container_width=True,
            key="real_mock_recovery_next",
        ):
            ctx = _real_mock_current_question(mx)
            from_q = int(ctx[2]) if ctx else None
            go_to_next_real_mock_question(mx, from_q_id=from_q)
    if st.button(
        "학습하기로 돌아가기",
        use_container_width=True,
        key="real_mock_recovery_portal",
    ):
        reset_to_learning_portal()
        st.rerun()
    if st.button("새 모의고사 시작", use_container_width=True, key="real_mock_recovery_new"):
        reset_real_mock_attempt(mx, st.session_state)
        clear_mock_question_tts_keys()
        _set_real_mock_page("QUESTION")
        _set_mock_page(mx, "SURVEY")
        st.rerun()


def _real_mock_blank_guard(mx: dict, page: str) -> None:
    """Server log when real-mock routing would otherwise render a blank screen."""
    try:
        results = mx.get("results") or []
        results_count = len(results) if isinstance(results, list) else 0
        logger.warning(
            "[REAL_MOCK_BLANK_GUARD] page=%s real_mock_page=%s mock_page=%s "
            "q_idx=%s results_count=%s exam_finished=%s",
            page or "—",
            _real_mock_page() or "—",
            _get_mock_page(mx),
            mx.get("current_idx"),
            results_count,
            bool(mx.get("exam_finished")),
        )
    except Exception:
        logger.debug("[REAL_MOCK_BLANK_GUARD] log failed", exc_info=True)


def _real_mock_remove_result_row(mx: dict, q_id: int) -> None:
    results = mx.get("results")
    if not isinstance(results, list):
        return
    mx["results"] = [
        r
        for r in results
        if not (isinstance(r, dict) and int(r.get("q_id", -1)) == int(q_id))
    ]


def _real_mock_retry_same_question(mx: dict, q_id: int, *, audio_key: str, mic_key: str = "") -> None:
    """Clear only this question's recording; keep index and other answers."""
    from components.answer_recording import (
        clear_mic_recording_cache,
        reset_recording_ui_for_question,
    )

    q_index = _real_mock_q_index_for_id(mx, int(q_id))
    _set_current_real_mock_question_index(mx, q_index)
    bump_recording_retry_nonce("real_mock", str(q_id), q_index)
    timer_key, mk = build_recording_keys("real_mock", str(q_id), q_index)
    reset_recording_ui_for_question(timer_key)
    clear_mic_recording_cache(mic_key or mk)
    rec = mx.get("recordings")
    if isinstance(rec, dict):
        rec.pop(audio_key, None)
    mx["audio_bytes"] = None
    mx["preview_transcript"] = None
    st.session_state.pop("recording_active_audio_key", None)
    reset_recording_timer()
    _real_mock_remove_result_row(mx, int(q_id))
    clear_pending_recovery(mx)
    st.session_state.pop(_real_mock_saved_confirm_key(int(q_id)), None)
    clear_real_mock_empty_commit_guard(timer_key, audio_key, mic_key=mic_key or mk)
    _leave_real_mock_post_save(mx)
    _set_real_mock_page("QUESTION")
    _real_mock_log_flow(mx, "QUESTION")
    st.rerun()


def _render_real_mock_error_fallback(mx: dict) -> None:
    render_top_bar(
        "실전 모의고사",
        back_href="?nav=MOCK",
        eyebrow=format_mock_attempt_label(mx),
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <section class="recovery-card" role="alert">
          <div class="rv-eyebrow">화면 오류</div>
          <div class="rv-title">화면을 불러오는 중 문제가 생겼어요</div>
          <div class="rv-body">답변은 저장되어 있을 수 있어요. 다시 시도하거나 학습 홈으로 돌아가 주세요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("다시 시도", type="primary", use_container_width=True, key="real_mock_err_retry"):
            st.session_state[_REAL_MOCK_PAGE_KEY] = "QUESTION"
            st.rerun()
    with c2:
        if st.button("학습하기로 돌아가기", use_container_width=True, key="real_mock_err_home"):
            reset_to_learning_portal()
            st.rerun()


def _nav_after_question_analysis(mx: dict, qid: int) -> None:
    """Last question → completion screen; otherwise per-question report (coaching only)."""
    if _is_real_mock(mx):
        row = find_result_row(mx, int(qid))
        res = (row or {}).get("result", {}) if isinstance(row, dict) else {}
        if _is_pending_result(res):
            _arm_real_mock_post_save(mx, "ANALYSIS_PENDING")
        else:
            from services.exam_analytics import result_is_no_speech_row

            if result_is_no_speech_row(res) or str(res.get("diagnosis_status") or "") == "no_audio":
                _arm_real_mock_post_save(mx, "SPEECH_RECOVERY")
            else:
                _arm_real_mock_post_save(mx, "ANSWER_SAVED")
        _set_mock_page(mx, "TEST")
        st.session_state["mock_page"] = "TEST"
        return
    if is_last_mock_question(mx, qid):
        mark_mock_exam_completed(mx, st.session_state)
    else:
        mx["mock_page"] = "REPORT"
        st.session_state["mock_page"] = "REPORT"


def _mock_mode(mx: dict) -> str | None:
    raw = st.session_state.get("mock_mode") or mx.get("mock_mode")
    if not raw:
        return None
    mode = str(raw).strip().lower()
    if mode in ("real_mock", "real", "exam"):
        return "real_mock"
    if mode == "coaching":
        return "coaching"
    if mode in ("topic_practice", "topic"):
        return "topic_practice"
    if mode in ("topic_practice_v2", "topic_v2"):
        return "topic_practice_v2"
    if mode in ("mini_mock", "mini"):
        return "mini_mock"
    if mode == "mock_v2":
        return "mock_v2"
    if mode == "script_coaching":
        return "script_coaching"
    return None


def _mock_mode_label(mode: str | None) -> str:
    if mode == "real_mock":
        return "실전 모의고사"
    if mode == "coaching":
        return "AI 코칭 연습"
    if mode == "topic_practice":
        return "주제별 답변 연습"
    if mode == "topic_practice_v2":
        return "주제별 답변 연습"
    if mode == "mini_mock":
        return "5분 진단 미니 모의고사"
    if mode == "mock_v2":
        return "실전 모의고사"
    if mode == "script_coaching":
        return "스크립트 첨삭"
    return "모의고사"


def _is_topic_practice(mx: dict) -> bool:
    return _mock_mode(mx) == "topic_practice"


_TOPIC_PRACTICE_QUESTION_COUNT = 3


def _topic_practice_step() -> str:
    return str(st.session_state.get("topic_practice_step") or "").strip()


def _topic_practice_question_index() -> int:
    try:
        idx = int(st.session_state.get("topic_practice_question_index") or 0)
    except (TypeError, ValueError):
        idx = 0
    return max(0, min(_TOPIC_PRACTICE_QUESTION_COUNT - 1, idx))


def ensure_topic_practice_state() -> None:
    """Initialize topic-practice keys once — never overwrite on every rerun."""
    if "topic_practice_step" not in st.session_state:
        st.session_state["topic_practice_step"] = "select_topic"
    if "topic_practice_question_index" not in st.session_state:
        st.session_state["topic_practice_question_index"] = 0
    if "topic_practice_results" not in st.session_state:
        st.session_state["topic_practice_results"] = []
    if "topic_report_status" not in st.session_state:
        st.session_state["topic_report_status"] = ""
    if "selected_topic_id" not in st.session_state:
        st.session_state["selected_topic_id"] = None


def _clear_topic_practice_state() -> None:
    from utils.topic_practice_state import clear_topic_practice_session

    clear_topic_practice_session()
    st.session_state.pop(_TOPIC_PRACTICE_ANALYSIS_IN_FLIGHT_KEY, None)
    _clear_legacy_analysis_in_flight()


_MINI_MOCK_QUESTION_COUNT = 3


def _is_mini_mock_v2_active() -> bool:
    from views.mini_mock_v2 import is_mini_mock_v2_active

    return is_mini_mock_v2_active()


def _mini_mock_question_index() -> int:
    try:
        idx = int(st.session_state.get("mini_mock_question_index") or 0)
    except (TypeError, ValueError):
        idx = 0
    return max(0, min(_MINI_MOCK_QUESTION_COUNT - 1, idx))


def _mini_mock_last_saved_q_idx() -> int:
    try:
        raw = st.session_state.get("mini_mock_last_saved_q_idx")
        if raw is not None:
            return max(0, min(_MINI_MOCK_QUESTION_COUNT - 1, int(raw)))
    except (TypeError, ValueError):
        pass
    return _mini_mock_question_index()


def _mini_mock_is_last_saved_question(saved_idx: int | None = None) -> bool:
    idx = _mini_mock_last_saved_q_idx() if saved_idx is None else int(saved_idx)
    return idx >= _MINI_MOCK_QUESTION_COUNT - 1


def _mini_mock_page() -> str:
    return str(st.session_state.get("mini_mock_page") or "QUESTION").strip()


def _mini_mock_debug(msg: str) -> None:
    try:
        logger.debug("[MINI_MOCK_DEBUG] %s", msg)
    except Exception:
        pass


def _log_mini_mock_state(*, page: str | None = None, q_idx: int | None = None) -> None:
    try:
        p = page if page is not None else _mini_mock_page()
        qi = q_idx if q_idx is not None else _mini_mock_question_index()
        results_n = len(st.session_state.get("mini_mock_results") or [])
        logger.debug(
            "[MINI_MOCK_STATE] page=%s q_idx=%s results=%s report_status=%s",
            p,
            qi,
            results_n,
            st.session_state.get("mini_mock_report_status"),
        )
    except Exception:
        pass


def _mirror_mini_mock_to_mx(mx: dict) -> None:
    """Session state is source of truth — mirror into mx for legacy readers only."""
    mx["mini_mock_page"] = _mini_mock_page()
    mx["mini_mock_question_index"] = _mini_mock_question_index()
    mx["mini_mock_results"] = list(st.session_state.get("mini_mock_results") or [])
    mx["mini_mock_report_status"] = st.session_state.get("mini_mock_report_status")
    mx["mini_mock_last_saved_q_idx"] = st.session_state.get("mini_mock_last_saved_q_idx")


def _maybe_enable_dev_debug_from_url() -> None:
    """Optional ``?dev_debug=1`` — developer diagnostics only, not shown to students."""
    raw = st.query_params.get("dev_debug")
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if str(raw or "").strip().lower() in ("1", "true", "yes"):
        st.session_state["show_dev_debug"] = True


def ensure_mini_mock_state() -> None:
    """Initialize mini-mock keys once — never overwrite on every rerun."""
    _maybe_enable_dev_debug_from_url()
    if "mini_mock_question_index" not in st.session_state:
        st.session_state["mini_mock_question_index"] = 0
    if "mini_mock_page" not in st.session_state:
        st.session_state["mini_mock_page"] = "QUESTION"
    if "mini_mock_results" not in st.session_state:
        st.session_state["mini_mock_results"] = []
    if "mini_mock_completed" not in st.session_state:
        st.session_state["mini_mock_completed"] = False
    if "mini_mock_report_status" not in st.session_state:
        st.session_state["mini_mock_report_status"] = ""
    if "mini_mock_last_saved_q_idx" not in st.session_state:
        st.session_state["mini_mock_last_saved_q_idx"] = 0
    if _LATEST_MINI_MOCK_API_DEBUG_KEY not in st.session_state:
        st.session_state[_LATEST_MINI_MOCK_API_DEBUG_KEY] = None


def _clear_mini_mock_state() -> None:
    from utils.mini_mock_state import clear_mini_mock_session

    cleared: list[str] = []
    for key in (
        "mini_mock_question_index",
        "mini_mock_results",
        "mini_mock_completed",
        "mini_mock_page",
        "mini_mock_last_saved_q_idx",
        "mini_mock_report_status",
        _MINI_MOCK_ANALYSIS_IN_PROGRESS_KEY,
        _MINI_MOCK_ANALYSIS_ATTEMPT_KEY,
        _MINI_MOCK_BATCH_ATTEMPTS_KEY,
        _MINI_MOCK_BATCH_FINISHED_KEY,
        _LATEST_MINI_MOCK_API_DEBUG_KEY,
        "mini_mock_analysis_started_at",
        "mini_mock_last_api_error_category",
        "mini_mock_last_api_error_preview",
        "mini_mock_pending_reason",
        _MINI_MOCK_ANALYSIS_IN_FLIGHT_KEY,
    ):
        if key in st.session_state:
            cleared.append(key)
        st.session_state.pop(key, None)
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and k.startswith("mm_saved_confirm_"):
            cleared.append(k)
            st.session_state.pop(k, None)
    clear_mini_mock_session()
    _clear_legacy_analysis_in_flight()
    try:
        logger.debug("[STATE_RESET] mode=mini_mock cleared_keys=%s", cleared)
    except Exception:
        pass


def _mini_mock_clear_analysis_guards() -> None:
    st.session_state[_MINI_MOCK_ANALYSIS_IN_PROGRESS_KEY] = False
    _set_analysis_in_flight("mini_mock", False)


def _mini_mock_clear_stuck_analysis_in_flight_flags() -> None:
    st.session_state[_MINI_MOCK_ANALYSIS_IN_PROGRESS_KEY] = False
    _set_analysis_in_flight("mini_mock", False)
    st.session_state.pop(_MINI_MOCK_ANALYSIS_IN_FLIGHT_KEY, None)
    _clear_legacy_analysis_in_flight()


def _mini_mock_analyzing_elapsed() -> float:
    started = st.session_state.get("mini_mock_analysis_started_at")
    if started is None:
        return 0.0
    try:
        return max(0.0, time.time() - float(started))
    except (TypeError, ValueError):
        return 0.0


def _mini_mock_ensure_analyzing_clock() -> None:
    """Start the 60s ANALYZING_REPORT clock once per analysis attempt."""
    if _mini_mock_page() != "ANALYZING_REPORT":
        return
    if st.session_state.get("mini_mock_analysis_started_at") is None:
        st.session_state["mini_mock_analysis_started_at"] = time.time()


def _mini_mock_resolve_analyzing_after_batch(mx: dict) -> None:
    """Leave ANALYZING_REPORT when batch already finished (one click = one batch)."""
    from utils.mini_mock_state import count_mini_mock_analysis_completed

    _mini_mock_clear_stuck_analysis_in_flight_flags()
    completed = count_mini_mock_analysis_completed()
    if completed == _MINI_MOCK_QUESTION_COUNT:
        st.session_state["mini_mock_page"] = "REPORT"
        st.session_state["mini_mock_report_status"] = "completed"
        st.session_state.pop("mini_mock_pending_reason", None)
    else:
        st.session_state.setdefault("mini_mock_pending_reason", "analysis_incomplete")
        st.session_state["mini_mock_page"] = "REPORT_PENDING"
        st.session_state["mini_mock_report_status"] = "pending_retry"
    try:
        logger.debug(
            "[MINI_MOCK_ANALYZING_RESOLVE] completed=%s page=%s",
            completed,
            st.session_state.get("mini_mock_page"),
        )
    except Exception:
        pass


def _mini_mock_abort_analyzing_if_needed(mx: dict) -> bool:
    """Route ANALYZING_REPORT to REPORT_PENDING when timed out or stuck in-flight."""
    if _mini_mock_page() != "ANALYZING_REPORT":
        return False

    _mini_mock_ensure_analyzing_clock()

    attempt = str(st.session_state.get(_MINI_MOCK_ANALYSIS_ATTEMPT_KEY) or "")
    if attempt and st.session_state.get(_MINI_MOCK_BATCH_FINISHED_KEY) == attempt:
        _mini_mock_resolve_analyzing_after_batch(mx)
        return True

    elapsed = _mini_mock_analyzing_elapsed()
    if elapsed <= MINI_MOCK_ANALYZING_TIMEOUT_SEC:
        return False

    in_progress = bool(st.session_state.get(_MINI_MOCK_ANALYSIS_IN_PROGRESS_KEY))
    in_flight = _get_analysis_in_flight("mini_mock") or bool(
        st.session_state.get(_MINI_MOCK_ANALYSIS_IN_FLIGHT_KEY)
    )
    if in_progress or in_flight:
        reason = "stuck_analyzing"
        error_category = "stuck_analyzing"
        error_preview = "analysis_stuck_in_flight"
        try:
            logger.warning(
                "[MINI_MOCK_STUCK_ANALYZING] in_progress=%s in_flight=%s attempt=%s elapsed=%.1f",
                in_progress,
                in_flight,
                attempt,
                elapsed,
            )
        except Exception:
            pass
    else:
        reason = "analysis_timeout"
        error_category = "timeout"
        error_preview = "analysis_timeout_over_60s"
        try:
            logger.warning(
                "[MINI_MOCK_ANALYZING_TIMEOUT] elapsed=%.1f attempt=%s",
                elapsed,
                attempt,
            )
        except Exception:
            pass

    st.session_state["mini_mock_page"] = "REPORT_PENDING"
    st.session_state["mini_mock_report_status"] = "pending_retry"
    st.session_state["mini_mock_pending_reason"] = reason
    st.session_state["mini_mock_last_api_error_category"] = error_category
    st.session_state["mini_mock_last_api_error_preview"] = error_preview
    st.session_state["mini_mock_completed"] = True
    _mini_mock_clear_stuck_analysis_in_flight_flags()
    try:
        logger.warning(
            "[MINI_MOCK_REPORT_PENDING_ROUTE] reason=%s attempt=%s elapsed=%.1f",
            reason,
            attempt,
            elapsed,
        )
    except Exception:
        pass
    return True


def _mini_mock_begin_report_analysis(*, retrying: bool = False) -> None:
    prior_page = st.session_state.get("mini_mock_page")
    st.session_state["mini_mock_page"] = "ANALYZING_REPORT"
    st.session_state["mini_mock_report_status"] = "retrying" if retrying else "analyzing"
    st.session_state[_MINI_MOCK_ANALYSIS_IN_PROGRESS_KEY] = False
    _set_analysis_in_flight("mini_mock", False)
    st.session_state.pop(_MINI_MOCK_BATCH_FINISHED_KEY, None)
    if retrying or prior_page != "ANALYZING_REPORT":
        st.session_state[_MINI_MOCK_ANALYSIS_ATTEMPT_KEY] = secrets.token_hex(8)
        st.session_state["mini_mock_analysis_started_at"] = time.time()
    elif st.session_state.get("mini_mock_analysis_started_at") is None:
        st.session_state["mini_mock_analysis_started_at"] = time.time()
    st.session_state[_MINI_MOCK_BATCH_ATTEMPTS_KEY] = 0
    st.session_state.pop("mini_mock_last_api_error_category", None)
    st.session_state.pop("mini_mock_last_api_error_preview", None)
    st.session_state.pop("mini_mock_pending_reason", None)
    _mini_mock_debug(
        f"begin_report_analysis retrying={retrying} "
        f"attempt={st.session_state.get(_MINI_MOCK_ANALYSIS_ATTEMPT_KEY)}"
    )


def _mini_mock_error_type_from_message(error_message: str) -> str:
    text = (error_message or "").strip()
    if not text:
        return "Unknown"
    m = re.match(r"^([A-Za-z_][\w.]*(?:Error|Exception))", text)
    if m:
        return m.group(1)
    upper = text.upper()
    if "429" in upper or "RESOURCE_EXHAUSTED" in upper:
        return "HTTP429"
    if "503" in upper or "UNAVAILABLE" in upper:
        return "HTTP503"
    if "400" in upper or "BAD REQUEST" in upper:
        return "HTTP400"
    if "LOCK" in upper or "대기열" in text:
        return "LockTimeout"
    if ":" in text:
        return text.split(":", 1)[0].strip()[:48]
    return text[:48]


def _mini_mock_is_quota_error(
    error_message: str = "",
    error_category: str = "",
) -> bool:
    """True when failure is Gemini quota / rate limit (not shown verbatim to students)."""
    if (error_category or "").strip().lower() == "quota_or_rate_limit":
        return True
    text = (error_message or "").strip()
    if not text:
        return False
    upper = text.upper()
    lowered = text.lower()
    if any(
        tok in lowered
        for tok in ("quota", "rate limit", "rate_limit", "할당량")
    ):
        return True
    return any(
        tok in upper for tok in ("429", "RESOURCE_EXHAUSTED", "RESOURCEEXHAUSTED")
    )


def _mini_mock_detect_quota_failure() -> bool:
    """Scan session + row metadata for quota / rate-limit failures."""
    if _mini_mock_is_quota_error(
        error_category=str(st.session_state.get("mini_mock_last_api_error_category") or "")
    ):
        return True
    debug = st.session_state.get(_LATEST_MINI_MOCK_API_DEBUG_KEY)
    if isinstance(debug, dict):
        if _mini_mock_is_quota_error(
            error_message=str(debug.get("error_preview") or ""),
            error_category=str(debug.get("error_category") or ""),
        ):
            return True
        for pq in debug.get("per_question") or []:
            if not isinstance(pq, dict):
                continue
            if _mini_mock_is_quota_error(
                error_message=str(
                    pq.get("error_preview")
                    or pq.get("analysis_error_short")
                    or ""
                ),
                error_category=str(
                    pq.get("error_category") or pq.get("analysis_error_category") or ""
                ),
            ):
                return True
    from utils.mini_mock_state import mini_mock_rows_sorted, row_result

    for row in mini_mock_rows_sorted():
        res = row_result(row)
        if _mini_mock_is_quota_error(
            error_message=str(res.get("analysis_error_short") or ""),
            error_category=str(res.get("analysis_error_category") or ""),
        ):
            return True
    return False


def _mini_mock_mark_quota_pending() -> None:
    st.session_state["mini_mock_pending_reason"] = "quota"
    st.session_state["mini_mock_last_api_error_category"] = "quota_or_rate_limit"
    try:
        logger.debug("[MINI_MOCK_QUOTA] detected=True")
    except Exception:
        pass


def _classify_mini_mock_api_error(
    error_message: str = "",
    *,
    empty_response: bool = False,
    explicit_category: str = "",
) -> tuple[str, str]:
    """Map Gemini / pipeline failures to developer-facing mini-mock categories."""
    if explicit_category:
        return explicit_category, _mini_mock_error_type_from_message(error_message) or explicit_category

    if empty_response:
        return "empty_response", "EmptyResponse"

    text = (error_message or "").strip()
    if not text:
        return "unknown", "Unknown"

    upper = text.upper()
    if any(
        tok in upper
        for tok in (
            "429",
            "RESOURCE_EXHAUSTED",
            "RESOURCEEXHAUSTED",
            "QUOTA",
            "RATE LIMIT",
            "RATE_LIMIT",
            "TOO MANY REQUESTS",
        )
    ) or "할당량" in text:
        return "quota_or_rate_limit", _mini_mock_error_type_from_message(text)

    if any(
        tok in upper
        for tok in (
            "503",
            "UNAVAILABLE",
            "OVERLOAD",
            "OVERLOADED",
            "SERVICE UNAVAILABLE",
        )
    ):
        return "temporary_overload", _mini_mock_error_type_from_message(text)

    if "400" in upper or "BAD REQUEST" in upper:
        return "bad_request_or_audio_format", _mini_mock_error_type_from_message(text)

    if any(tok in upper for tok in ("LOCK ACQUIRE", "LOCK_TIMEOUT", "LOCK QUEUE")) or (
        "대기열" in text and "타임아웃" in text
    ):
        return "lock_queue_timeout", _mini_mock_error_type_from_message(text)

    if any(
        tok in text.lower()
        for tok in ("empty response", "empty text", "empty", "비어", "결과값이 비어")
    ):
        return "empty_response", "EmptyResponse"

    from utils.ai_pending_diag import classify_ai_error

    legacy = classify_ai_error(text, empty_response=False)
    remap = {
        "quota_or_rate_limit": "quota_or_rate_limit",
        "temporary_overload": "temporary_overload",
        "empty_response": "empty_response",
        "lock_queue_timeout": "lock_queue_timeout",
        "audio_format_error": "bad_request_or_audio_format",
        "timeout": "timeout",
        "unknown": "unknown",
    }
    return remap.get(legacy, legacy), _mini_mock_error_type_from_message(text)


def _collect_mini_mock_api_context(*, api_key: str | None = None) -> Dict[str, Any]:
    from utils.mini_mock_state import get_mini_mock_recordings, mini_mock_rows_sorted, row_result

    audio_lens: list[int] = []
    mime_types: list[str] = []
    attempts = int(st.session_state.get(_MINI_MOCK_BATCH_ATTEMPTS_KEY) or 0)
    error_type = ""

    for row in mini_mock_rows_sorted():
        res = row_result(row)
        if isinstance(res, dict):
            attempts = max(
                attempts,
                int(res.get("retry_count") or res.get("attempts") or 0),
            )
            mt = str(res.get("audio_mime_guess") or res.get("mime_type") or "").strip()
            if mt:
                mime_types.append(mt)
            error_type = error_type or str(res.get("analysis_error_type") or "")
        blob = (get_mini_mock_recordings() or {}).get(str(row.get("audio_key") or ""))
        if blob:
            audio_lens.append(len(blob))
        elif row.get("audio_len"):
            audio_lens.append(int(row.get("audio_len") or 0))

    key = (api_key if api_key is not None else get_gemini_api_key()) or ""
    return {
        "audio_lens": audio_lens,
        "mime_types": mime_types,
        "attempts": attempts,
        "error_type": error_type,
        "api_key_present": bool(str(key).strip()),
    }


_MINI_MOCK_VERY_SMALL_AUDIO_BYTES = 30000


def _mini_mock_question_label(question: Dict[str, Any] | None, q_idx: int) -> str:
    if isinstance(question, dict):
        label = question.get("type_label") or question.get("type")
        if label:
            return str(label)
    return f"Q{q_idx + 1}"


def _mini_mock_audio_size_warning(audio_len: int) -> str:
    if audio_len > 0 and audio_len < _MINI_MOCK_VERY_SMALL_AUDIO_BYTES:
        return "very_small_audio"
    return ""


def _mini_mock_infer_pending_reason(
    *,
    result: dict | None,
    last_error: str,
    analysis_failed: bool,
    skipped_analysis: bool = False,
    stored_result: dict | None = None,
) -> str:
    if skipped_analysis:
        return "batch_skipped_needs_analysis_false"
    res = stored_result if isinstance(stored_result, dict) else (result if isinstance(result, dict) else {})
    ast = str(res.get("analysis_status") or "").lower()
    diag = str(res.get("diagnosis_status") or "").lower()
    if ast in ("saved_unanalyzed",) or diag in ("saved_unanalyzed",):
        return "saved_unanalyzed_never_analyzed"
    if result is None and not (last_error or "").strip():
        return "no_error_message_returned"
    if result is None:
        return "api_returned_none"
    if analysis_failed:
        if not (last_error or "").strip():
            return "no_error_message_returned"
        return "api_analysis_failed"
    if diag == "analysis_pending" or ast == "pending" or res.get("analysis_pending"):
        return "result_returned_but_marked_pending"
    if ast == "completed" or diag == "ok":
        return "completed"
    if ast in ("no_audio",) or diag == "no_audio":
        return "no_audio"
    if ast in ("no_speech",) or diag == "no_speech":
        return "no_speech"
    if ast in ("unclear_speech", "needs_review") or diag in ("unclear_speech", "needs_review"):
        return "speech_issue"
    if ast in ("non_english",) or diag in ("non_english",):
        return "non_english"
    return "unknown"


def _mini_mock_build_per_question_entry(
    *,
    q_idx: int,
    question: Dict[str, Any] | None,
    audio_len: int,
    mime_type: str,
    api_key: str | None,
    result: dict | None = None,
    last_error: str = "",
    attempts: int = 0,
    analysis_failed: bool = False,
    stored_result: dict | None = None,
    skipped_analysis: bool = False,
) -> Dict[str, Any]:
    res = stored_result if isinstance(stored_result, dict) else (result if isinstance(result, dict) else {})
    err_msg = (last_error or "").strip()
    if not err_msg and isinstance(res, dict):
        err_msg = str(
            res.get("analysis_error_short")
            or res.get("last_analysis_error")
            or res.get("error")
            or ""
        ).strip()
    if not err_msg and analysis_failed:
        err_msg = "no_error_message_returned"
    elif not err_msg and _is_pending_result(res):
        err_msg = "no_error_message_returned"

    empty_resp = bool(
        err_msg
        and ("비어" in err_msg or "empty" in err_msg.lower())
    )
    if isinstance(res, dict) and res.get("analysis_error_category"):
        err_cat = str(res.get("analysis_error_category") or "")
        err_type = str(res.get("analysis_error_type") or res.get("error_kind") or "")
        err_short = str(res.get("analysis_error_short") or err_msg)
    else:
        err_cat, err_type = _classify_mini_mock_api_error(
            err_msg,
            empty_response=empty_resp or result is None,
        )
        err_short = err_msg[:180] if err_msg else ""

    preview = (err_msg or err_short or "")[:200]
    if not preview and analysis_failed:
        preview = "no_error_message_returned"

    transcript = str(res.get("transcript") or (result or {}).get("transcript") or "")
    pending_reason = _mini_mock_infer_pending_reason(
        result=result,
        last_error=last_error,
        analysis_failed=analysis_failed,
        skipped_analysis=skipped_analysis,
        stored_result=res if res else None,
    )

    return {
        "q": q_idx + 1,
        "question_index": q_idx,
        "label": _mini_mock_question_label(question, q_idx),
        "audio_len": audio_len,
        "mime_type": mime_type or "—",
        "api_key_present": bool(str((api_key if api_key is not None else get_gemini_api_key()) or "").strip()),
        "analysis_result_is_none": result is None,
        "attempts": int(attempts or res.get("retry_count") or res.get("attempts") or 0),
        "analysis_status": str(res.get("analysis_status") or (result or {}).get("analysis_status") or "—"),
        "diagnosis_status": str(res.get("diagnosis_status") or (result or {}).get("diagnosis_status") or "—"),
        "error_category": err_cat,
        "error_type": err_type,
        "error_preview": preview or "—",
        "analysis_error_category": err_cat,
        "analysis_error_type": err_type,
        "analysis_error_short": err_short or preview,
        "transcript_len": len(transcript),
        "estimated_level": (result or res or {}).get("estimated_level"),
        "final_grade_score": (result or res or {}).get("final_grade_score"),
        "pending_reason": pending_reason,
        "audio_size_warning": _mini_mock_audio_size_warning(audio_len),
    }


def _mini_mock_upsert_per_question_debug(entry: Dict[str, Any]) -> list[Dict[str, Any]]:
    existing = st.session_state.get(_LATEST_MINI_MOCK_API_DEBUG_KEY)
    if not isinstance(existing, dict):
        existing = {}
    per_q = existing.get("per_question")
    if not isinstance(per_q, list):
        per_q = []
    q_num = entry.get("q")
    replaced = False
    for i, row in enumerate(per_q):
        if isinstance(row, dict) and row.get("q") == q_num:
            per_q[i] = entry
            replaced = True
            break
    if not replaced:
        per_q.append(entry)
    per_q.sort(key=lambda r: int((r or {}).get("q") or 0))
    existing["per_question"] = per_q
    st.session_state[_LATEST_MINI_MOCK_API_DEBUG_KEY] = existing
    return per_q


def _mini_mock_apply_audio_warnings(payload: Dict[str, Any]) -> None:
    audio_lens = payload.get("audio_lens") or []
    per_q = payload.get("per_question") if isinstance(payload.get("per_question"), list) else []
    if not audio_lens:
        audio_lens = [
            int((row or {}).get("audio_len") or 0)
            for row in per_q
            if isinstance(row, dict) and int((row or {}).get("audio_len") or 0) > 0
        ]
    if len(audio_lens) >= _MINI_MOCK_QUESTION_COUNT and all(
        0 < ln < _MINI_MOCK_VERY_SMALL_AUDIO_BYTES for ln in audio_lens[:_MINI_MOCK_QUESTION_COUNT]
    ):
        payload["overall_warning"] = "all_audio_files_are_very_small"


def _record_mini_mock_per_question_debug(
    *,
    q_idx: int,
    question: Dict[str, Any] | None,
    audio_len: int,
    mime_type: str = "",
    api_key: str | None = None,
    result: dict | None = None,
    last_error: str = "",
    attempts: int = 0,
    analysis_failed: bool = False,
    stored_result: dict | None = None,
    skipped_analysis: bool = False,
) -> Dict[str, Any]:
    entry = _mini_mock_build_per_question_entry(
        q_idx=q_idx,
        question=question,
        audio_len=audio_len,
        mime_type=mime_type,
        api_key=api_key,
        result=result,
        last_error=last_error,
        attempts=attempts,
        analysis_failed=analysis_failed,
        stored_result=stored_result,
        skipped_analysis=skipped_analysis,
    )
    _mini_mock_upsert_per_question_debug(entry)
    try:
        logger.warning(
            "[MINI_MOCK_API_DEBUG] per_question q=%s label=%s audio_len=%s mime=%s "
            "pending_reason=%s error_category=%s error_type=%s error_preview=%s "
            "analysis_status=%s diagnosis_status=%s attempts=%s transcript_len=%s "
            "audio_size_warning=%s result_none=%s",
            entry.get("q"),
            entry.get("label"),
            entry.get("audio_len"),
            entry.get("mime_type"),
            entry.get("pending_reason"),
            entry.get("error_category"),
            entry.get("error_type"),
            entry.get("error_preview"),
            entry.get("analysis_status"),
            entry.get("diagnosis_status"),
            entry.get("attempts"),
            entry.get("transcript_len"),
            entry.get("audio_size_warning"),
            entry.get("analysis_result_is_none"),
        )
    except Exception:
        pass
    return entry


def _finalize_mini_mock_batch_api_debug(
    *,
    error_category: str,
    error_message: str = "",
    error_type: str = "",
    api_key: str | None = None,
) -> Dict[str, Any]:
    """Rebuild per-question rows from session + set overall batch failure metadata."""
    from data.mini_mock_questions import get_mini_mock_question
    from utils.mini_mock_state import (
        find_mini_mock_result,
        get_mini_mock_answer_blob,
        mini_mock_rows_sorted,
        row_result,
    )

    per_question: list[Dict[str, Any]] = []
    for q_idx in range(_MINI_MOCK_QUESTION_COUNT):
        question = get_mini_mock_question(q_idx) or {}
        question_id = str(question.get("question_id") or "")
        row = find_mini_mock_result(question_id)
        if not row:
            for r in mini_mock_rows_sorted():
                if int(r.get("question_index") or -1) == q_idx:
                    row = r
                    break
        blob = get_mini_mock_answer_blob(row) if row else b""
        audio_len = len(blob) if blob else int((row or {}).get("audio_len") or 0)
        res = row_result(row) if row else {}
        mime = str(
            res.get("audio_mime_guess") or res.get("mime_type") or (row or {}).get("mime_type") or ""
        ).strip()
        analysis_failed = _is_pending_result(res) or _is_analysis_failed(res, "")
        last_err = str(res.get("analysis_error_short") or res.get("last_analysis_error") or "")
        entry = _mini_mock_build_per_question_entry(
            q_idx=q_idx,
            question=question,
            audio_len=audio_len,
            mime_type=mime,
            api_key=api_key,
            result=None,
            last_error=last_err,
            attempts=int(res.get("retry_count") or res.get("attempts") or 0),
            analysis_failed=analysis_failed,
            stored_result=res,
        )
        per_question.append(entry)

    return _store_latest_mini_mock_api_debug(
        error_category=error_category,
        error_message=error_message,
        error_type=error_type,
        api_key=api_key,
        per_question=per_question,
        replace_per_question=True,
    )


def _store_latest_mini_mock_api_debug(
    *,
    error_category: str,
    error_message: str = "",
    error_type: str = "",
    attempts: int | None = None,
    api_key: str | None = None,
    empty_response: bool = False,
    per_question: list[Dict[str, Any]] | None = None,
    per_question_entry: Dict[str, Any] | None = None,
    replace_per_question: bool = False,
) -> Dict[str, Any]:
    """Persist + log latest mini-mock API failure (developer only — never show API key)."""
    if error_category in ("missing_api_key", "missing_audio", "stuck_analyzing", "exception"):
        category = error_category
        err_type = error_type or _mini_mock_error_type_from_message(error_message) or error_category
    else:
        category, err_type = _classify_mini_mock_api_error(
            error_message,
            empty_response=empty_response,
            explicit_category=error_category if error_category not in ("unknown", "") else "",
        )
        if error_type:
            err_type = error_type

    ctx = _collect_mini_mock_api_context(api_key=api_key)
    preview = (error_message or "")[:200]
    prior = st.session_state.get(_LATEST_MINI_MOCK_API_DEBUG_KEY)
    prior_pq = (
        list(prior.get("per_question") or [])
        if isinstance(prior, dict) and isinstance(prior.get("per_question"), list)
        else []
    )
    if replace_per_question and per_question is not None:
        merged_pq = list(per_question)
    elif per_question_entry is not None:
        merged_pq = list(prior_pq)
        q_num = per_question_entry.get("q")
        replaced = False
        for i, row in enumerate(merged_pq):
            if isinstance(row, dict) and row.get("q") == q_num:
                merged_pq[i] = per_question_entry
                replaced = True
                break
        if not replaced:
            merged_pq.append(per_question_entry)
        merged_pq.sort(key=lambda r: int((r or {}).get("q") or 0))
    elif per_question is not None:
        merged_pq = list(per_question)
    else:
        merged_pq = prior_pq

    payload = {
        "error_category": category,
        "error_type": err_type or ctx.get("error_type") or category,
        "error_preview": preview,
        "attempts": attempts if attempts is not None else ctx["attempts"],
        "audio_lens": ctx["audio_lens"],
        "mime_types": ctx["mime_types"],
        "api_key_present": ctx["api_key_present"],
        "per_question": merged_pq,
    }
    _mini_mock_apply_audio_warnings(payload)
    st.session_state[_LATEST_MINI_MOCK_API_DEBUG_KEY] = payload
    st.session_state["mini_mock_last_api_error_category"] = category
    if preview:
        st.session_state["mini_mock_last_api_error_preview"] = preview

    try:
        logger.warning(
            "[MINI_MOCK_API_DEBUG] error_category=%s error_type=%s error_preview=%s "
            "attempts=%s audio_lens=%s mime_types=%s api_key_present=%s overall_warning=%s "
            "per_question_count=%s",
            payload["error_category"],
            payload["error_type"],
            payload["error_preview"],
            payload["attempts"],
            payload["audio_lens"],
            payload["mime_types"],
            payload["api_key_present"],
            payload.get("overall_warning") or "",
            len(merged_pq),
        )
    except Exception:
        pass
    return payload


def _render_mini_mock_api_debug_panel() -> None:
    """Temporary on-screen API failure info (REPORT_PENDING only; no API key / raw audio)."""
    debug = st.session_state.get(_LATEST_MINI_MOCK_API_DEBUG_KEY)
    st.markdown(
        """
        <section class="recovery-card" style="margin-top:12px; border-style:dashed; opacity:0.95;"
                 aria-label="API 실패 원인 확인용">
          <div class="rv-eyebrow">디버그</div>
          <div class="rv-title" style="font-size:1rem;">API 실패 원인 확인용</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if not isinstance(debug, dict) or not debug:
        st.caption("아직 API 실패 정보가 저장되지 않았습니다.")
        return
    preview = html.escape(str(debug.get("error_preview") or "—"))
    overall_warning = html.escape(str(debug.get("overall_warning") or "—"))
    overall_html = (
        '<div class="mx-rh-transcript" style="font-size:0.85rem; line-height:1.55;">'
        f"<p><strong>error_category:</strong> {html.escape(str(debug.get('error_category') or '—'))}</p>"
        f"<p><strong>error_type:</strong> {html.escape(str(debug.get('error_type') or '—'))}</p>"
        f"<p><strong>error_preview:</strong> {preview}</p>"
        f"<p><strong>attempts:</strong> {html.escape(str(debug.get('attempts', '—')))}</p>"
        f"<p><strong>audio_lens:</strong> {html.escape(str(debug.get('audio_lens', [])))}</p>"
        f"<p><strong>mime_types:</strong> {html.escape(str(debug.get('mime_types', [])))}</p>"
        f"<p><strong>api_key_present:</strong> {html.escape(str(debug.get('api_key_present', '—')))}</p>"
        f"<p><strong>overall_warning:</strong> {overall_warning}</p>"
        "</div>"
    )
    st.markdown(overall_html, unsafe_allow_html=True)
    per_q = debug.get("per_question")
    if isinstance(per_q, list) and per_q:
        st.markdown("**문항별 분석 실패 정보**")
        for entry in sorted(per_q, key=lambda r: int((r or {}).get("q") or 0)):
            if not isinstance(entry, dict):
                continue
            qn = int(entry.get("q") or 0)
            label = html.escape(str(entry.get("label") or f"Q{qn}"))
            pq_html = (
                '<div class="mx-rh-transcript" style="font-size:0.82rem;margin:0 0 10px 0;'
                'padding-left:8px;border-left:2px dashed #ccc;">'
                f"<p><strong>Q{qn} ({label})</strong></p>"
                f"<p>audio_len: {html.escape(str(entry.get('audio_len', '—')))}"
                f" · mime_type: {html.escape(str(entry.get('mime_type', '—')))}"
                f" · audio_size_warning: {html.escape(str(entry.get('audio_size_warning') or '—'))}</p>"
                f"<p>analysis_status: {html.escape(str(entry.get('analysis_status', '—')))}"
                f" · diagnosis_status: {html.escape(str(entry.get('diagnosis_status', '—')))}"
                f" · pending_reason: {html.escape(str(entry.get('pending_reason', '—')))}</p>"
                f"<p>error_category: {html.escape(str(entry.get('error_category', '—')))}"
                f" · error_type: {html.escape(str(entry.get('error_type', '—')))}</p>"
                f"<p>error_preview: {html.escape(str(entry.get('error_preview', '—')))}"
                f" · transcript_len: {html.escape(str(entry.get('transcript_len', '—')))}"
                f" · attempts: {html.escape(str(entry.get('attempts', '—')))}</p>"
                "</div>"
            )
            st.markdown(pq_html, unsafe_allow_html=True)


def _mini_mock_transition_to_report_pending(
    mx: dict,
    *,
    error_category: str = "unknown",
    error_message: str = "",
    error_type: str = "",
    attempts: int | None = None,
    api_key: str | None = None,
    empty_response: bool = False,
    pending_reason: str | None = None,
) -> None:
    st.session_state["mini_mock_page"] = "REPORT_PENDING"
    st.session_state["mini_mock_report_status"] = "pending_retry"
    st.session_state["mini_mock_completed"] = True
    if pending_reason:
        st.session_state["mini_mock_pending_reason"] = pending_reason
    elif _mini_mock_is_quota_error(error_message, error_category):
        _mini_mock_mark_quota_pending()
    elif error_category in ("timeout", "stuck_analyzing"):
        st.session_state["mini_mock_pending_reason"] = (
            "analysis_timeout" if error_category == "timeout" else "stuck_analyzing"
        )
    _mini_mock_clear_stuck_analysis_in_flight_flags()
    _finalize_mini_mock_batch_api_debug(
        error_category=error_category,
        error_message=error_message,
        error_type=error_type or error_category,
        api_key=api_key,
    )
    try:
        logger.warning(
            "[MINI_MOCK_REPORT_PENDING_ROUTE] reason=%s category=%s",
            st.session_state.get("mini_mock_pending_reason"),
            error_category,
        )
    except Exception:
        pass
    _mini_mock_debug(f"transition REPORT_PENDING category={error_category}")


def _render_mini_mock_saved_answers_list() -> None:
    from utils.mini_mock_state import get_mini_mock_answer_blob, mini_mock_rows_sorted
    from utils.speech_recording import recording_byte_length

    st.markdown("##### 저장된 답변")
    for row in mini_mock_rows_sorted():
        ql = int(row.get("question_index") or 0) + 1
        nbytes = int(row.get("audio_len") or 0)
        if not nbytes:
            blob = get_mini_mock_answer_blob(row)
            if blob:
                nbytes = recording_byte_length(blob)
        if st.session_state.get("show_dev_debug"):
            st.caption(f"[dev] Q{ql} · 녹음 {nbytes:,} bytes")
        else:
            st.markdown(f"- Q{ql} 저장 완료")


def _render_mini_mock_question_status_list() -> None:
    from services.exam_analytics import result_display_status
    from utils.mini_mock_state import mini_mock_rows_sorted, row_result

    st.markdown("##### 문항별 상태")
    for row in mini_mock_rows_sorted():
        ql = int(row.get("question_index") or 0) + 1
        status = result_display_status(row_result(row))
        st.markdown(f"- Q{ql}: {html.escape(status)}")


def _mini_mock_saved_confirm_key(question_id: str) -> str:
    return f"mm_saved_confirm_{question_id}"


def _normalize_topic_practice_step(step: str) -> str:
    s = (step or "").strip()
    if s in ("practice",):
        return "question"
    if s == "mini_report":
        return "report"
    if s in ("complete", "feedback"):
        return "answers_saved"
    return s or "select_topic"


def _log_topic_state(
    *,
    step: str | None = None,
    topic_id: str | None = None,
    q_idx: int | None = None,
) -> None:
    try:
        tid = topic_id if topic_id is not None else st.session_state.get("selected_topic_id")
        qi = q_idx if q_idx is not None else _topic_practice_question_index()
        from utils.topic_practice_state import count_topic_saved_answers

        saved_n = count_topic_saved_answers(str(tid or "")) if tid else 0
        logger.debug(
            "[TOPIC_STATE] step=%s topic_id=%s q_idx=%s saved_count=%s",
            step if step is not None else _topic_practice_step(),
            tid or "—",
            qi,
            saved_n,
        )
    except Exception:
        pass


def _mirror_topic_practice_to_mx(mx: dict) -> None:
    """Mirror session state into mx for legacy readers — never read mx into session."""
    mx["topic_practice_step"] = _topic_practice_step()
    mx["topic_practice_question_index"] = _topic_practice_question_index()
    mx["topic_practice_results"] = list(st.session_state.get("topic_practice_results") or [])
    mx["topic_report_status"] = st.session_state.get("topic_report_status")
    mx["selected_topic_id"] = st.session_state.get("selected_topic_id")
    report = st.session_state.get("topic_report_result") or st.session_state.get(
        "topic_mini_report"
    )
    if isinstance(report, dict):
        mx["topic_report_result"] = report


def _topic_is_quota_error(error_message: str = "", error_category: str = "") -> bool:
    if (error_category or "").strip().lower() == "quota_or_rate_limit":
        return True
    text = (error_message or "").strip()
    if not text:
        return False
    upper = text.upper()
    lowered = text.lower()
    if any(tok in lowered for tok in ("quota", "rate limit", "rate_limit", "할당량")):
        return True
    return any(tok in upper for tok in ("429", "RESOURCE_EXHAUSTED", "RESOURCEEXHAUSTED"))


def _topic_begin_report_analysis(*, retrying: bool = False) -> None:
    st.session_state["topic_practice_step"] = "analyzing_report"
    st.session_state["topic_report_status"] = "retrying" if retrying else "analyzing"
    st.session_state.pop(_TOPIC_REPORT_BATCH_FINISHED_KEY, None)
    st.session_state[_TOPIC_REPORT_ATTEMPT_KEY] = secrets.token_hex(8)
    st.session_state.pop("topic_report_result", None)
    st.session_state.pop("topic_mini_report", None)
    st.session_state.pop("topic_mini_report_pending", None)
    st.session_state.pop("topic_report_last_error", None)
    st.session_state.pop("topic_pending_reason", None)
    _set_analysis_in_flight("topic_practice", False)


def _topic_saved_confirm_key(topic_id: str, question_id: str) -> str:
    return f"tp_saved_confirm_{topic_id}_{question_id}"


def _topic_speech_recovery_key(topic_id: str, question_id: str) -> str:
    return f"tp_speech_recovery_{topic_id}_{question_id}"


_MINI_MOCK_SPEECH_RECOVERY_Q_IDX_KEY = "mini_mock_speech_recovery_q_idx"


def _render_pre_analysis_speech_recovery(
    mx: dict,
    *,
    mode: str,
    question_id: str,
    question_index: int,
    audio_key: str,
    mic_key: str,
    recordings: dict,
    next_label: str,
    on_next,
    retry_key: str,
    next_key: str,
    clear_recovery_flag: Callable[[], None],
) -> None:
    """Recovery when recording is too short / no speech — before answer is committed."""
    from components.answer_recording import (
        clear_mic_recording_cache,
        reset_recording_ui_for_question,
    )
    from utils.speech_recording import recording_byte_length, speech_issue_copy

    _, title, body = speech_issue_copy("unclear_speech")
    blob = get_saved_audio_for_key(recordings, audio_key)
    nbytes = recording_byte_length(blob) if blob else 0
    meta_html = ""
    if nbytes > 0 and st.session_state.get("show_dev_debug"):
        meta_html = (
            f'<div class="mx-rh-meta">'
            f'<span class="mx-rh-chip">[dev] 녹음 저장됨 · {html.escape(f"{nbytes:,}")} bytes</span>'
            f"</div>"
        )
    st.markdown(
        f"""
        <section class="mx-report-hero" role="alert">
          <div class="mx-rh-title">{html.escape(title)}</div>
          <div class="mx-rh-transcript">{html.escape(body)}</div>
          {meta_html}
        </section>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "같은 질문 다시 말하기",
            type="primary",
            use_container_width=True,
            key=retry_key,
        ):
            clear_recovery_flag()
            bump_recording_retry_nonce(mode, question_id, question_index)
            if isinstance(recordings, dict):
                recordings.pop(audio_key, None)
            mx["audio_bytes"] = None
            mx.pop("preview_transcript", None)
            if st.session_state.get("recording_active_audio_key") == audio_key:
                st.session_state.pop("recording_active_audio_key", None)
            timer_key, mk = build_recording_keys(mode, question_id, question_index)
            reset_recording_ui_for_question(timer_key)
            clear_mic_recording_cache(mic_key or mk)
            reset_recording_timer()
            st.rerun()
    with c2:
        if st.button(next_label, use_container_width=True, key=next_key):
            clear_recovery_flag()
            if isinstance(recordings, dict):
                recordings.pop(audio_key, None)
            mx["audio_bytes"] = None
            on_next()


def _exit_topic_practice_to_mode_picker(mx: dict) -> None:
    _clear_topic_practice_state()
    reset_to_learning_portal()


def _has_mock_mode(mx: dict) -> bool:
    return _mock_mode(mx) is not None


def _set_mock_mode(mx: dict, mode: str) -> None:
    if mode not in (
        "real_mock",
        "coaching",
        "topic_practice",
        "topic_practice_v2",
        "mini_mock",
        "mock_v2",
        "script_coaching",
    ):
        mode = "real_mock"
    st.session_state["mock_mode"] = mode
    mx["mock_mode"] = mode
    mx["mock_mode_label"] = _mock_mode_label(mode)


def _redirect_hidden_coaching_mode() -> bool:
    """Launch: coaching mode is hidden — send stale sessions back to the portal."""
    if _session_mock_mode() != "coaching" and _mock_mode(mock_session()) != "coaching":
        return False
    reset_to_learning_portal()
    st.rerun()
    return True


def _clear_mock_mode(mx: dict) -> None:
    """Clear mode label only — does not wipe topic-practice or mock exam rows."""
    st.session_state.pop("mock_mode", None)
    mx.pop("mock_mode", None)
    mx.pop("mock_mode_label", None)


def _practice_portal_selected() -> bool:
    return bool(st.session_state.get("practice_portal_selected"))


def _sync_mock_routing_state(mx: dict) -> None:
    """Align top-level routing keys with the mock namespace (portal buttons write both)."""
    page = st.session_state.get("mock_page")
    if page:
        mx["mock_page"] = page
    elif mx.get("mock_page"):
        st.session_state["mock_page"] = mx["mock_page"]
    else:
        st.session_state["mock_page"] = "PICK"
        mx["mock_page"] = "PICK"

    view_report = bool(
        mx.get("_view_completed_report")
        or st.session_state.get("_view_completed_report")
    )
    if view_report:
        mx["_view_completed_report"] = True
        st.session_state["_view_completed_report"] = True

    if "mock_mode" in st.session_state:
        mode_raw = st.session_state.get("mock_mode")
        if mode_raw:
            mx["mock_mode"] = str(mode_raw).strip().lower()
            mx["mock_mode_label"] = _mock_mode_label(_mock_mode(mx))
        else:
            mx.pop("mock_mode", None)
            mx.pop("mock_mode_label", None)
    elif mx.get("mock_mode"):
        st.session_state["mock_mode"] = mx["mock_mode"]


def _set_mock_page(mx: dict, page: str) -> None:
    st.session_state["mock_page"] = page
    mx["mock_page"] = page


def _get_mock_page(mx: dict) -> str:
    return str(st.session_state.get("mock_page") or mx.get("mock_page") or "PICK")


def reset_to_learning_portal() -> None:
    """Return to the learning portal without deleting saved results."""
    reset_recording_timer()
    mx = mock_session()
    if mx.get("_final_report_demo") or st.session_state.get("_final_report_demo"):
        from services.final_report_demo import exit_demo_final_report

        exit_demo_final_report(mx)
        return
    if _is_mini_mock_v2_active():
        from views.mini_mock_v2 import reset_mini_mock_v2

        reset_mini_mock_v2()
    cleared = [
        "practice_portal_selected",
        "mock_mode",
        "mock_page",
        "topic_practice_step",
        "selected_topic_id",
        "active_learning_mode",
    ]
    mx.pop("_view_completed_report", None)
    st.session_state.pop("_view_completed_report", None)
    st.session_state["practice_portal_selected"] = False
    st.session_state["mock_mode"] = None
    st.session_state["mock_page"] = "PICK"
    st.session_state["topic_practice_step"] = None
    st.session_state["selected_topic_id"] = None
    _clear_mini_mock_state()
    _clear_all_mode_analysis_in_flight_flags()
    _leave_real_mock_post_save(mx)
    st.session_state.pop(_REAL_MOCK_PAGE_KEY, None)
    mx.pop("real_mock_page", None)
    mx["mock_page"] = "PICK"
    mx.pop("mock_mode", None)
    mx.pop("mock_mode_label", None)
    mx.pop("_resume_confirmed", None)
    st.session_state.pop("mock_mode", None)
    try:
        from views.topic_practice_v2 import clear_topic_v2_session, _log_tpv2_state_clear

        _log_tpv2_state_clear("ENTER", "reset_to_learning_portal:before_clear")
        clear_topic_v2_session()
        _log_tpv2_state_clear("EXIT", "reset_to_learning_portal:after_clear")
    except Exception:
        pass
    try:
        from views.script_coaching import clear_script_coaching_session

        clear_script_coaching_session()
    except Exception:
        pass
    try:
        logger.debug(
            "[STATE_RESET] mode=portal cleared_keys=%s (mini/topic via helpers; mx.results preserved)",
            cleared,
        )
    except Exception:
        pass


def _render_learning_portal_back_button(mx: dict) -> None:
    if st.button(
        "학습 방식 다시 선택",
        key="mx_back_to_portal",
        use_container_width=True,
    ):
        reset_to_learning_portal()
        try:
            st.query_params.clear()
            st.query_params["nav"] = "MOCK"
        except Exception:
            pass
        st.rerun()


def _default_coaching_survey_results() -> dict:
    from utils.session_state import settings_session

    return {
        "work": "사업·회사원",
        "housing": "가족과 함께 거주",
        "leisure": ["영화 보기", "공원 가기"],
        "interests": ["음악 감상하기", "요리하기"],
        "sports": ["조깅", "걷기"],
        "travel": ["국내 여행"],
        "difficulty": int(settings_session()["difficulty"]),
    }


def _ensure_coaching_exam(mx: dict) -> None:
    from utils.session_state import settings_session

    if not mx.get("survey_results"):
        mx["survey_results"] = _default_coaching_survey_results()
    mx["survey_completed"] = True
    mx.setdefault("attempt_no", 1)
    _exam = generate_test_set(
        mx["survey_results"],
        difficulty=int(settings_session()["difficulty"]),
    )
    mx["current_exam"] = _exam
    mx["exam"] = _exam
    mx["current_idx"] = 0
    mx["results"] = []
    mx["last_result"] = None
    mx["question_play_counts"] = {}
    mx["exam_listen_nonce"] = secrets.token_hex(8)
    _now = iso_now()
    mx["exam_started_at"] = _now
    mx["exam_last_seen_at"] = _now
    clear_mock_question_tts_keys()


def _clear_reset_practice_query_param() -> None:
    try:
        if "reset_practice" in st.query_params:
            del st.query_params["reset_practice"]
        st.query_params["nav"] = "MOCK"
    except Exception:
        pass


def _maybe_reset_practice_from_url() -> None:
    """Handle ?nav=MOCK&reset_practice=1 only while the portal is visible (not before button handlers)."""
    raw = st.query_params.get("reset_practice")
    if isinstance(raw, list):
        raw = raw[0] if raw else None
    if raw != "1":
        return
    reset_to_learning_portal()
    _clear_reset_practice_query_param()


def _session_mock_mode() -> str | None:
    raw = st.session_state.get("mock_mode")
    if raw is None:
        return None
    mode = str(raw).strip().lower()
    if mode in ("real_mock", "real", "exam"):
        return "real_mock"
    if mode == "coaching":
        return "coaching"
    if mode in ("topic_practice", "topic"):
        return "topic_practice"
    if mode in ("topic_practice_v2", "topic_v2"):
        return "topic_practice_v2"
    if mode in ("mini_mock", "mini"):
        return "mini_mock"
    if mode == "mock_v2":
        return "mock_v2"
    if mode == "script_coaching":
        return "script_coaching"
    return None


def _sync_portal_mode_to_mx(mx: dict, mode: str) -> None:
    st.session_state["mock_mode"] = mode
    mx["mock_mode"] = mode
    mx["mock_mode_label"] = _mock_mode_label(mode)


def _render_dev_portal_debug(mx: dict) -> None:
    if "show_dev_debug" not in st.session_state:
        st.session_state["show_dev_debug"] = False
    if not st.session_state.get("show_dev_debug"):
        return

    if st.button(
        "기존 실전 모의고사 열기",
        use_container_width=True,
        key="portal_start_legacy_real_mock",
    ):
        st.session_state["mock_mode"] = "real_mock"
        st.session_state["practice_portal_selected"] = True
        st.session_state["mock_page"] = "SURVEY"
        _sync_portal_mode_to_mx(mx, "real_mock")
        _set_mock_page(mx, "SURVEY")
        _clear_reset_practice_query_param()
        st.rerun()

    def _dev_state_body() -> None:
        st.json(
            {
                "page": st.session_state.get("page"),
                "mock_page": _get_mock_page(mx),
                "mock_mode": st.session_state.get("mock_mode"),
                "practice_portal_selected": st.session_state.get("practice_portal_selected"),
                "topic_practice_step": st.session_state.get("topic_practice_step"),
                "selected_topic_id": st.session_state.get("selected_topic_id"),
                "mini_mock_question_index": st.session_state.get("mini_mock_question_index"),
                "mini_mock_page": st.session_state.get("mini_mock_page"),
                "mini_mock_completed": st.session_state.get("mini_mock_completed"),
                "current_question_index": mx.get("current_idx"),
            }
        )

    render_collapsible_section(
        "개발용 상태 확인",
        "mx_dev_state",
        _dev_state_body,
        css_scope="mx-col",
    )


def _render_coaching_flow(mx: dict) -> None:
    if (
        has_resumable_exam(mx)
        and not mx.get("_resume_confirmed")
        and _mock_mode(mx) == "coaching"
    ):
        render_resumable_landing(mx)
        return
    mock_page = _get_mock_page(mx)
    if mock_page == "REPORT":
        _render_report(mx)
    else:
        if mock_page != "TEST":
            _ensure_coaching_exam(mx)
            _set_mock_page(mx, "TEST")
        _render_test(mx)


def _retry_first_pending_analysis(mx: dict) -> bool:
    """Re-run Gemini for the first pending row (saved audio only)."""
    from services.exam_analytics import result_display_status

    api_key = get_gemini_api_key()
    if not api_key:
        st.error("Gemini API Key가 없어 다시 시도할 수 없습니다.")
        return False
    for row in mx.get("results") or []:
        if not isinstance(row, dict):
            continue
        res = row.get("result") if isinstance(row.get("result"), dict) else {}
        if result_display_status(res) not in ("분석 대기", "AI 분석 대기 중"):
            continue
        try:
            q_id = int(row.get("q_id"))
        except (TypeError, ValueError):
            continue
        retry_stored_answer_analysis(mx, q_id)
        return True
    st.info("분석 대기 중인 문항이 없습니다.")
    return False


def render_mock_exam_completion_screen(mx: dict) -> None:
    """Shown right after the last real-mock question — before the full report."""
    from services.final_report_preview import build_final_report_preview

    if _is_real_mock(mx):
        mark_real_mock_exam_completed(mx, st.session_state)

    total = get_mock_total_questions(mx)
    results = mx.get("results") or []
    try:
        logger.debug(
            "[REAL_MOCK_COMPLETE] completion_screen rendered results_count=%s total=%s",
            len(results) if isinstance(results, list) else 0,
            total,
        )
    except Exception:
        pass
    preview = build_final_report_preview(results, total_count=total)
    render_top_bar(
        "실전 모의고사",
        back_href="?nav=HOME",
        eyebrow=format_mock_attempt_label(mx),
    )
    st.markdown('<div class="mx-landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <section class="continue-card continue-card--start mx-landing-card" role="region"
                 aria-label="실전 모의고사 완료">
          <div class="cc-eyebrow">완료</div>
          <div class="cc-title">실전 모의고사가 완료되었어요</div>
          <div class="cc-meta">{total}개 문항의 답변이 저장되었습니다.<br/>
            이제 전체 흐름, 문법, 표현, 답변 구조를 바탕으로 최종 리포트를 확인할 수 있어요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    render_final_report_preview_card(preview)

    if st.button(
        "최종 리포트 보기",
        type="primary",
        use_container_width=True,
        key="real_mock_open_final_report",
    ):
        _open_completed_final_report(mx)
        st.rerun()

    if st.button(
        "새 모의고사 시작",
        use_container_width=True,
        key="real_mock_new_attempt",
    ):
        try:
            logger.debug("[REAL_MOCK_COMPLETE] new_mock_clicked")
        except Exception:
            pass
        reset_real_mock_attempt(mx, st.session_state)
        clear_mock_question_tts_keys()
        sync_user_progress(st.session_state)
        try:
            st.query_params.clear()
            st.query_params["nav"] = "MOCK"
            st.query_params["mock"] = "SURVEY"
        except Exception:
            pass
        st.rerun()

    if st.button(
        "학습하기로 돌아가기",
        use_container_width=True,
        key="real_mock_back_portal",
    ):
        _return_to_learning_portal_from_complete(mx)
        try:
            st.query_params.clear()
            st.query_params["nav"] = "MOCK"
        except Exception:
            pass
        st.rerun()

    pending = int(preview.get("pending_count") or 0)
    if pending > 0 and st.button(
        "분석 대기 문항 다시 시도",
        use_container_width=True,
        key="mx_mock_retry_pending",
    ):
        _retry_first_pending_analysis(mx)


def _render_real_mock_flow(mx: dict) -> None:
    if (
        has_resumable_exam(mx)
        and not mx.get("_resume_confirmed")
        and not mx.get("exam_finished")
        and _mock_mode(mx) == "real_mock"
    ):
        render_resumable_landing(mx)
        return
    if is_completed_mock(mx) and _should_show_completed_final_report(mx):
        try:
            logger.debug("[REAL_MOCK_COMPLETE] rendering_final_report")
        except Exception:
            pass
        from views.new_final_report import render_new_final_report

        legacy_results = [r for r in (mx.get("results") or []) if isinstance(r, dict)]
        agg_cache = (
            mx.get("analytics_cache") if isinstance(mx.get("analytics_cache"), dict) else {}
        )
        shared_level = str(mx.get("shared_overall_level") or "").strip()
        shared_breakdown = (
            mx.get("shared_score_breakdown")
            if isinstance(mx.get("shared_score_breakdown"), dict)
            else {}
        )
        report_overlay: Dict[str, Any] = {
            "ok": True,
            "overall_level": str(
                shared_level
                or mx.get("overall_estimated_level")
                or agg_cache.get("overall_display")
                or ""
            ),
            "summary": "",
            "score_breakdown": shared_breakdown,
            "strengths": [],
            "weaknesses": [],
            "practice_mission": "",
        }

        def _legacy_portal() -> None:
            _return_to_learning_portal_from_complete(mx)

        def _legacy_restart() -> None:
            if _is_real_mock(mx):
                reset_real_mock_attempt(mx, st.session_state)
                clear_mock_question_tts_keys()
                sync_user_progress(st.session_state)
                try:
                    st.query_params.clear()
                    st.query_params["nav"] = "MOCK"
                    st.query_params["mock"] = "SURVEY"
                except Exception:
                    pass
                st.rerun()
            elif start_new_mock_attempt(mx, st.session_state):
                clear_mock_question_tts_keys()
                sync_user_progress(st.session_state)
                try:
                    st.query_params.clear()
                    st.query_params["nav"] = "MOCK"
                    st.query_params["mock"] = "TEST"
                except Exception:
                    pass
                st.rerun()
            else:
                st.error("설문 데이터가 없거나 종료된 시험이 아니면 새 시험을 시작할 수 없습니다.")

        render_new_final_report(
            report_overlay,
            [],
            [],
            legacy_results=legacy_results,
            attempt_no=int(mx.get("attempt_no") or 1),
            is_demo=bool(mx.get("_final_report_demo")),
            on_restart=_legacy_restart,
            on_portal=_legacy_portal,
        )
        return
    if is_completed_mock(mx) or _get_mock_page(mx) == "FINAL":
        render_mock_exam_completion_screen(mx)
        return
    mock_page = _get_mock_page(mx)
    if mock_page == "SURVEY":
        _render_survey(mx)
    elif mock_page == "TEST":
        _render_real_mock_exam(mx)
    elif mock_page == "REPORT":
        if _real_mock_all_questions_saved(mx) and not mx.get("exam_finished"):
            _set_mock_page(mx, "TEST")
            _set_real_mock_page("FINAL_READY")
            _render_real_mock_final_ready(mx)
        else:
            _render_report(mx)
    elif mock_page == "FINAL":
        render_mock_exam_completion_screen(mx)
    else:
        _set_mock_page(mx, "SURVEY")
        _render_survey(mx)


def _is_real_mock(mx: dict) -> bool:
    return _mock_mode(mx) == "real_mock"


def _needs_mode_selection(mx: dict) -> bool:
    if has_resumable_exam(mx):
        return False
    if is_completed_mock(mx):
        return False
    return not _has_mock_mode(mx)


def _clear_in_progress_for_mode_pick(mx: dict) -> None:
    """Drop in-flight exam rows but keep survey — show mode selector next."""
    clear_pending_recovery(mx)
    mx["exam_finished"] = False
    mx["results"] = []
    mx["last_result"] = None
    mx["recordings"] = {}
    mx["current_exam"] = []
    mx["exam"] = []
    mx["current_idx"] = 0
    mx["audio_bytes"] = None
    mx["preview_transcript"] = None
    mx["analysis_status"] = ""
    mx["analysis_done"] = False
    mx["analysis_error_msg"] = ""
    mx["analysis_result"] = None
    mx.pop("_show_exam_celebration", None)
    mx.pop("_view_completed_report", None)
    reset_to_learning_portal()


def _begin_new_practice_from_completed(mx: dict) -> bool:
    """Archive finished attempt, clear exam rows, show mode picker (keep survey)."""
    if not start_new_mock_attempt(mx, st.session_state):
        return False
    mx["current_exam"] = []
    mx["exam"] = []
    mx["results"] = []
    mx["current_idx"] = 0
    reset_to_learning_portal()
    _clear_topic_practice_state()
    return True


def render_learning_portal(mx: dict) -> None:
    """Learning portal — real mock, mini mock, topic practice (coaching hidden for launch)."""
    _maybe_reset_practice_from_url()
    mx = mock_session()

    render_top_bar("학습하기", back_href="?nav=HOME", eyebrow="학습하기")
    st.markdown('<div class="mx-landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    st.markdown(
        """
        <section class="mx-mode-intro" role="region" aria-label="학습하기">
          <h2 class="mx-mode-title">오늘은 어떤 방식으로 연습할까요?</h2>
          <p class="mx-mode-subtitle">실전처럼 풀어보거나, 빠른 진단·주제 연습으로 답변 습관을 다듬을 수 있어요.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    _render_portal_sample_report_section(mx)

    st.markdown(
        """
        <section class="mx-portal-practice-intro" role="region" aria-label="연습 방식 선택">
          <h3 class="mx-portal-section-title">연습 방식 선택</h3>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="mx-portal-practice-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <section class="continue-card continue-card--start mx-mode-card mx-portal-mode-card" role="region"
                     aria-label="실전 모의고사">
              <div class="cc-title">실전 모의고사</div>
              <div class="cc-meta">OPIc 실전 흐름에 맞춰 15문항을 연습하고 AI 최종 리포트를 확인해요.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "실전 모의고사 시작",
            type="primary",
            use_container_width=True,
            key="portal_start_real_mock",
        ):
            from views.mock_v2 import begin_mock_v2_session

            begin_mock_v2_session()
            st.session_state["mock_mode"] = "mock_v2"
            st.session_state["practice_portal_selected"] = True
            _sync_portal_mode_to_mx(mx, "mock_v2")
            _clear_reset_practice_query_param()
            try:
                logger.info(
                    "[MOCK_V2_SET_AS_MAIN] source=learning_portal mock_mode=mock_v2"
                )
            except Exception:
                pass
            st.rerun()
    with c2:
        st.markdown(
            """
            <section class="continue-card continue-card--start mx-mode-card mx-portal-mode-card" role="region"
                     aria-label="5분 진단 미니 모의고사">
              <span class="mx-mode-badge">추천 · 약 5분</span>
              <div class="cc-title">5분 진단 미니 모의고사</div>
              <div class="cc-meta">묘사, 경험, 롤플레이 3문항으로 빠르게 현재 답변 습관을 진단해요.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "5분 진단 시작",
            type="primary",
            use_container_width=True,
            key="portal_start_mini_mock",
        ):
            from views.mini_mock_v2 import (
                ACTIVE_LEARNING_MODE_MINI_V2,
                begin_mini_mock_v2_session,
            )

            begin_mini_mock_v2_session(mx)
            _sync_portal_mode_to_mx(mx, "mini_mock")
            _set_mock_page(mx, "MINI_MOCK")
            _clear_reset_practice_query_param()
            try:
                logger.info(
                    "[MINI_MOCK_V2] portal_start mode=%s page=MINI_MOCK legacy_bypassed=True",
                    ACTIVE_LEARNING_MODE_MINI_V2,
                )
            except Exception:
                pass
            st.rerun()

    c3, c4 = st.columns(2)
    with c3:
        st.markdown(
            """
            <section class="continue-card continue-card--start mx-mode-card mx-portal-mode-card" role="region"
                     aria-label="주제별 답변 연습">
              <div class="cc-title">주제별 답변 연습</div>
              <div class="cc-meta">원하는 주제를 골라 3문항씩 연습하고 주제별 리포트를 받아요.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "주제별 연습 시작",
            type="primary",
            use_container_width=True,
            key="portal_start_topic_practice",
        ):
            from views.topic_practice_v2 import MOCK_MODE_TOPIC_V2, clear_topic_v2_session

            clear_topic_v2_session()
            st.session_state["mock_mode"] = MOCK_MODE_TOPIC_V2
            st.session_state["practice_portal_selected"] = True
            st.session_state["mock_page"] = "TOPIC_V2"
            _sync_portal_mode_to_mx(mx, MOCK_MODE_TOPIC_V2)
            _set_mock_page(mx, "TOPIC_V2")
            _clear_reset_practice_query_param()
            try:
                logger.info("[TOPIC_PRACTICE_V2] portal_start mode=%s page=TOPIC_V2", MOCK_MODE_TOPIC_V2)
            except Exception:
                pass
            st.rerun()
    with c4:
        st.markdown(
            """
            <section class="continue-card continue-card--start mx-mode-card mx-portal-mode-card" role="region"
                     aria-label="스크립트 첨삭">
              <div class="cc-title">스크립트 첨삭</div>
              <div class="cc-meta">내가 쓴 답변을 등급별로 진단받아요.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "스크립트 첨삭 시작",
            type="primary",
            use_container_width=True,
            key="portal_start_script_coaching",
        ):
            from views.script_coaching import clear_script_coaching_session

            clear_script_coaching_session()
            st.session_state["mock_mode"] = "script_coaching"
            st.session_state["practice_portal_selected"] = True
            _sync_portal_mode_to_mx(mx, "script_coaching")
            _clear_reset_practice_query_param()
            try:
                logger.info("[SCRIPT_COACHING] portal_start mode=script_coaching")
            except Exception:
                pass
            st.rerun()

    _render_dev_portal_debug(mx)


def _render_portal_sample_report_section(mx: dict) -> None:
    """Sample final report preview — synthetic data only, no Gemini."""
    from services.final_report_demo import (
        build_demo_sample_pdf_bytes,
        open_demo_final_report,
    )
    from utils.exam_state import has_resumable_exam

    st.markdown(
        """
        <section class="mx-portal-sample-section" aria-label="리포트 샘플">
          <section class="continue-card continue-card--start mx-mode-card mx-sample-report-card"
                   role="region" aria-label="리포트 샘플 카드">
            <div class="cc-eyebrow">리포트 샘플 먼저 보기</div>
            <div class="cc-title">모의고사 후 받는 최종 리포트를 미리 확인해 보세요</div>
            <div class="cc-meta">모의고사를 끝내면 어떤 식으로 최종 리포트가 나오는지 미리 확인해 보세요.<br/>
              샘플 리포트는 데모 데이터로 만들어져서 AI 사용량이 차감되지 않습니다.</div>
          </section>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if has_resumable_exam(mx) and not mx.get("_final_report_demo"):
        st.caption(
            "진행 중인 모의고사가 있어도 샘플을 볼 수 있어요. "
            "학습하기로 돌아가면 이어서 풀 수 있습니다."
        )

    pdf_bytes = build_demo_sample_pdf_bytes()
    b_view, b_pdf = st.columns(2)
    with b_view:
        if st.button(
            "샘플 리포트 보기",
            type="primary",
            use_container_width=True,
            key="portal_sample_report_view",
        ):
            open_demo_final_report(mx)
            st.rerun()
    with b_pdf:
        if pdf_bytes:
            st.download_button(
                label="샘플 PDF 다운로드",
                data=pdf_bytes,
                file_name="opic_final_report_sample.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="portal_sample_report_pdf",
            )


def render_mode_selector(mx: dict) -> None:
    """Backward-compatible alias for the learning portal."""
    render_learning_portal(mx)


_TOPIC_PRACTICE_CATEGORY_ORDER = (
    "place",
    "hobby",
    "daily",
    "experience",
    "unexpected",
    "roleplay",
)

_TOPIC_CATEGORY_FILTER_CHIPS: tuple[tuple[str, str], ...] = (
    ("all", "전체"),
    ("place", "장소"),
    ("hobby", "취미"),
    ("daily", "일상"),
    ("experience", "경험·비교"),
    ("unexpected", "돌발"),
    ("roleplay", "롤플레이"),
)


def _sort_topics_by_category(topics: list) -> list:
    order = {cat: idx for idx, cat in enumerate(_TOPIC_PRACTICE_CATEGORY_ORDER)}
    return sorted(topics, key=lambda t: order.get(str(t.get("category") or ""), 99))


def _filter_topic_sets(topics: list, *, category_filter: str, search_query: str) -> list:
    cat = str(category_filter or "all").strip()
    filtered = topics
    if cat and cat != "all":
        filtered = [t for t in filtered if str(t.get("category") or "") == cat]
    q = str(search_query or "").strip().lower()
    if q:
        filtered = [
            t
            for t in filtered
            if q in str(t.get("topic_title") or "").lower()
            or q in str(t.get("topic_subtitle") or "").lower()
        ]
    return filtered


def _render_topic_category_filter_chips() -> None:
    if "topic_category_filter" not in st.session_state:
        st.session_state["topic_category_filter"] = "all"
    active = str(st.session_state.get("topic_category_filter") or "all")

    st.markdown('<div class="tp-filter-label">카테고리</div>', unsafe_allow_html=True)
    for chip_row in (_TOPIC_CATEGORY_FILTER_CHIPS[:4], _TOPIC_CATEGORY_FILTER_CHIPS[4:]):
        cols = st.columns(len(chip_row), gap="small")
        for col, (key, label) in zip(cols, chip_row):
            with col:
                if st.button(
                    label,
                    key=f"tp_cat_{key}",
                    type="primary" if active == key else "secondary",
                    use_container_width=True,
                ):
                    st.session_state["topic_category_filter"] = key
                    st.rerun()


def _render_topic_practice_card(topic: dict) -> None:
    from data.topic_practice_questions import get_category_label

    topic_id = str(topic.get("topic_id") or "")
    title = html.escape(str(topic.get("topic_title") or ""))
    subtitle = html.escape(str(topic.get("topic_subtitle") or ""))
    level = html.escape(str(topic.get("level") or ""))
    cat_label = html.escape(get_category_label(str(topic.get("category") or "")))
    meta = f"{cat_label} · {level} · 3문항"

    st.markdown(
        f"""
        <section class="tp-topic-card" role="region" aria-label="{title}">
          <div class="tp-topic-title">{title}</div>
          <p class="tp-topic-sub">{subtitle}</p>
          <p class="tp-topic-meta">{meta}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if st.button(
        "연습하기",
        type="primary",
        use_container_width=True,
        key=f"mx_topic_pick_{topic_id}",
    ):
        from utils.topic_practice_state import clear_topic_recordings

        clear_topic_recordings()
        st.session_state["selected_topic_id"] = topic_id
        st.session_state["topic_practice_question_index"] = 0
        st.session_state["topic_practice_results"] = []
        st.session_state["topic_practice_step"] = "question"
        st.session_state.pop("topic_report_status", None)
        st.session_state.pop("topic_report_result", None)
        st.session_state.pop("topic_mini_report", None)
        st.session_state.pop("topic_mini_report_pending", None)
        st.session_state.pop("topic_report_last_error", None)
        st.session_state.pop("topic_pending_reason", None)
        st.session_state.pop(_TOPIC_REPORT_ATTEMPT_KEY, None)
        st.session_state.pop(_TOPIC_REPORT_BATCH_FINISHED_KEY, None)
        st.rerun()


def render_topic_selection(mx: dict) -> None:
    from data.topic_practice_questions import get_category_label, get_topic_sets

    render_top_bar("주제별 연습", back_href="?nav=HOME", eyebrow="주제 선택")
    st.markdown('<div class="mx-landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_learning_portal_back_button(mx)

    all_topics = _sort_topics_by_category(get_topic_sets())
    topic_count = len(all_topics)
    total_question_count = topic_count * 3

    st.markdown(
        f"""
        <section class="mx-mode-intro tp-select-intro" role="region" aria-label="주제별 연습 주제 선택">
          <h2 class="mx-mode-title">주제별 연습</h2>
          <p class="mx-mode-subtitle">원하는 오픽 주제를 골라 3문항 콤보로 집중 연습해요.</p>
          <p class="tp-select-summary">총 {topic_count}개 주제 · {total_question_count}개 질문</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    _render_topic_category_filter_chips()

    search_query = st.text_input(
        "주제 검색",
        placeholder="주제 검색하기",
        key="topic_search_input",
        label_visibility="collapsed",
    )

    category_filter = str(st.session_state.get("topic_category_filter") or "all")
    topics = _filter_topic_sets(
        all_topics,
        category_filter=category_filter,
        search_query=search_query,
    )

    if category_filter != "all" or str(search_query or "").strip():
        cat_note = (
            get_category_label(category_filter)
            if category_filter != "all"
            else "전체"
        )
        st.markdown(
            f'<p class="tp-select-visible">표시 중 <b>{len(topics)}</b>개'
            f'{" · " + html.escape(cat_note) if category_filter != "all" else ""}'
            f'{" · 검색" if str(search_query or "").strip() else ""}</p>',
            unsafe_allow_html=True,
        )

    if not topics:
        st.info("조건에 맞는 주제가 없습니다. 다른 카테고리나 검색어를 시도해 보세요.")
    else:
        for row_start in range(0, len(topics), 2):
            row_topics = topics[row_start : row_start + 2]
            if len(row_topics) == 1:
                _render_topic_practice_card(row_topics[0])
            else:
                col_l, col_r = st.columns(2, gap="medium")
                with col_l:
                    _render_topic_practice_card(row_topics[0])
                with col_r:
                    _render_topic_practice_card(row_topics[1])


    if st.button("다른 연습 방식 선택", use_container_width=True, key="mx_topic_back_to_modes"):
        _exit_topic_practice_to_mode_picker(mx)
        st.rerun()


def _render_topic_keyword_chips(keywords: list) -> str:
    chips = []
    for kw in keywords:
        text = str(kw).strip()
        if text:
            chips.append(f'<span class="mx-rh-chip">{html.escape(text)}</span>')
    if not chips:
        return ""
    return f'<div class="mx-rh-meta">{"".join(chips)}</div>'



def _topic_practice_context():
    from data.topic_practice_questions import get_topic_by_id, get_topic_question

    topic_id = st.session_state.get("selected_topic_id")
    if not topic_id:
        return None, None, 0, None
    topic = get_topic_by_id(str(topic_id))
    if not topic:
        return str(topic_id), None, 0, None
    q_idx = _topic_practice_question_index()
    question = get_topic_question(str(topic_id), q_idx)
    return str(topic_id), topic, q_idx, question


def _topic_sync_audio_to_mx(mx: dict, audio_key: str) -> None:
    from utils.topic_practice_state import get_topic_recordings

    blob = get_topic_recordings().get(audio_key)
    if not blob:
        return
    rec = mx.setdefault("recordings", {})
    if not isinstance(rec, dict):
        rec = {}
        mx["recordings"] = rec
    rec[audio_key] = blob
    mx["audio_bytes"] = blob


def _render_topic_question_body(topic: dict, question: dict, q_idx: int) -> str:
    title = str(topic.get("topic_title") or "주제")
    q_display = q_idx + 1
    type_label = html.escape(str(question.get("type_label") or ""))
    question_en = html.escape(str(question.get("question_en") or ""))
    question_ko = html.escape(str(question.get("question_ko") or ""))
    focus = html.escape(str(question.get("focus") or ""))
    keywords = question.get("starter_keywords") or []
    if not isinstance(keywords, list):
        keywords = []
    chips_html = _render_topic_keyword_chips(keywords)
    keywords_block = ""
    if chips_html:
        keywords_block = (
            '<p class="mx-rh-eyebrow" style="margin-top:14px;">답변에 넣어볼 키워드</p>'
            + chips_html
        )
    st.markdown(
        f"""
        <section class="continue-card continue-card--resume mx-landing-card" role="region"
                 aria-label="진행 상황">
          <div class="cc-eyebrow">진행</div>
          <div class="cc-title">Q{q_display} <span class="cc-of">/ {_TOPIC_PRACTICE_QUESTION_COUNT}</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <section class="mx-report-hero" role="region" aria-label="문항">
          <p class="mx-rh-eyebrow">{type_label}</p>
          <div class="mx-rh-title">{question_en}</div>
          <div class="mx-rh-transcript">{question_ko}</div>
          <p class="mx-rh-eyebrow" style="margin-top:14px;">오늘의 포인트</p>
          <div class="mx-rh-transcript">{focus}</div>
          {keywords_block}
        </section>
        """,
        unsafe_allow_html=True,
    )
    return title


def _render_detailed_coaching_for_result(lr: dict, q_label: int, heard_raw: str) -> None:
    _wpm = lr.get("wpm")
    _sent = lr.get("sentence_count", 0)
    _words = lr.get("word_count", 0)
    meta_chips = []
    if isinstance(_wpm, (int, float)):
        meta_chips.append(f'<span class="mx-rh-chip">WPM {_wpm}</span>')
    meta_chips.append(f'<span class="mx-rh-chip">문장 {_sent}</span>')
    meta_chips.append(f'<span class="mx-rh-chip">단어 {_words}</span>')
    meta_html = f'<div class="mx-rh-meta">{"".join(meta_chips)}</div>'
    transcript_html = html.escape(heard_raw)
    st.markdown(
        f"""
        <section class="mx-report-hero">
          <p class="mx-rh-eyebrow">Q{q_label} · 복원 발화</p>
          <div class="mx-rh-title">방금 말씀하신 흐름을 그대로 옮겨 적었어요</div>
          <div class="mx-rh-transcript">{transcript_html}</div>
          {meta_html}
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.text_area(
        f"Q{q_label} 텍스트 (복사·수정용)",
        value=heard_raw,
        height=140,
        key=f"tp_restored_transcript_q_{q_label}",
    )
    render_structured_coaching_report(
        lr,
        heard_raw,
        int(q_label),
        show_hero=True,
        question_text=str(lr.get("question") or ""),
    )


def _topic_back_to_select_topic() -> None:
    from utils.topic_practice_state import clear_topic_recordings

    reset_recording_timer()
    clear_topic_recordings()
    st.session_state["topic_practice_question_index"] = 0
    st.session_state["topic_practice_results"] = []
    for key in (
        "topic_report_status",
        "topic_report_result",
        "topic_mini_report",
        "topic_mini_report_pending",
        "topic_report_last_error",
        "topic_pending_reason",
        _TOPIC_REPORT_ATTEMPT_KEY,
        _TOPIC_REPORT_BATCH_FINISHED_KEY,
    ):
        st.session_state.pop(key, None)
    st.session_state["topic_practice_step"] = "select_topic"


def _topic_advance_after_saved_answer(
    mx: dict, topic_id: str, question_id: str, *, mic_key: str = ""
) -> None:
    from components.answer_recording import clear_mic_recording_cache, reset_recording_ui_for_question

    reset_recording_timer()
    idx = _topic_practice_question_index()
    timer_key, mk = build_recording_keys(f"topic_{topic_id}", question_id, idx)
    reset_recording_ui_for_question(timer_key)
    clear_mic_recording_cache(mic_key or mk)
    mx["audio_bytes"] = None
    st.session_state.pop("recording_active_audio_key", None)
    mx.pop("preview_transcript", None)
    st.session_state.pop(_topic_saved_confirm_key(topic_id, question_id), None)
    if idx >= _TOPIC_PRACTICE_QUESTION_COUNT - 1:
        st.session_state["topic_practice_step"] = "answers_saved"
    else:
        st.session_state["topic_practice_question_index"] = idx + 1
        st.session_state["topic_practice_step"] = "question"
    st.rerun()


def _topic_commit_saved_answer(
    mx: dict,
    *,
    topic_id: str,
    topic_title: str,
    q_idx: int,
    question: dict,
    audio_key: str,
) -> bool:
    from utils.topic_practice_state import get_topic_recordings, save_topic_unanalyzed_answer
    from utils.speech_recording import classify_pre_analysis_blob, recording_byte_length, resolve_mime_for_analysis

    question_id = str(question.get("question_id") or "")
    recordings = get_topic_recordings()
    blob = get_saved_audio_for_key(recordings, audio_key)
    if not blob:
        st.error("녹음이 제대로 저장되지 않았어요. 같은 질문을 다시 말해 주세요.")
        return False
    if classify_pre_analysis_blob(blob) == "no_audio":
        st.session_state[_topic_speech_recovery_key(topic_id, question_id)] = True
        return False
    mime = resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key)
    save_topic_unanalyzed_answer(
        topic_id=topic_id,
        topic_title=topic_title,
        question_index=q_idx,
        question=question,
        audio_key=audio_key,
        audio_bytes=blob,
        mime_type=mime,
    )
    from utils.topic_practice_state import apply_stt_to_topic_saved_row

    apply_stt_to_topic_saved_row(
        topic_id=topic_id,
        topic_title=topic_title,
        question_index=q_idx,
        question=question,
        audio_key=audio_key,
        audio_bytes=blob,
        mime_type=mime,
    )
    st.session_state.pop(_topic_speech_recovery_key(topic_id, question_id), None)
    st.session_state["topic_practice_last_saved_q_idx"] = q_idx
    if q_idx < _TOPIC_PRACTICE_QUESTION_COUNT - 1:
        st.session_state["topic_practice_step"] = "saved"
    else:
        st.session_state["topic_practice_step"] = "answers_saved"
    try:
        logger.debug(
            "[TOPIC_SAVE] q_idx=%s audio_len=%s step=%s",
            q_idx,
            recording_byte_length(blob),
            st.session_state.get("topic_practice_step"),
        )
    except Exception:
        pass
    return True


def _render_topic_api_delay_recovery_card(
    mx: dict,
    topic_id: str,
    topic: dict,
    question: dict,
    q_idx: int,
    audio_key: str,
) -> None:
    from utils.topic_practice_state import get_topic_recordings

    saved_audio = mx.get("audio_bytes") or get_topic_recordings().get(audio_key)
    audio_size = len(saved_audio) if saved_audio else 0
    st.markdown(
        f"""
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">AI 분석 지연</div>
          <div class="rv-title">AI 분석이 잠시 지연되고 있어요</div>
          <div class="rv-body">답변은 저장되었습니다.<br/>
            다음 문항으로 넘어가도 괜찮아요. 나중에 다시 분석할 수 있어요.</div>
          <div class="rv-meta"><span>녹음 {html.escape(f"{audio_size:,}")} bytes 보존됨</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    from utils.ai_pending_diag import render_ai_pending_dev_expander

    render_ai_pending_dev_expander(
        st.session_state.get("last_result") if isinstance(st.session_state.get("last_result"), dict) else {},
    )
    in_flight = _get_analysis_in_flight("topic_practice")
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "다시 분석하기",
            key=f"tp_api_retry_{topic_id}_{q_idx}",
            type="primary",
            use_container_width=True,
            disabled=(audio_size == 0) or in_flight,
        ):
            api_key = get_gemini_api_key()
            if not api_key:
                st.error("API Key가 설정되지 않아 다시 시도할 수 없습니다.")
            else:
                if saved_audio:
                    mx["audio_bytes"] = saved_audio
                _run_topic_practice_analysis(
                    mx,
                    topic_id,
                    topic,
                    question,
                    q_idx,
                    audio_key,
                    api_key,
                    from_retry=True,
                )
    with c2:
        if st.button(
            "다음 문제로",
            key=f"tp_api_next_{topic_id}_{q_idx}",
            use_container_width=True,
        ):
            _topic_advance_after_saved_answer(mx, topic_id, question_id)


def _run_topic_practice_analysis(
    mx: dict,
    topic_id: str,
    topic: dict,
    question: dict,
    q_idx: int,
    audio_key: str,
    api_key: str,
    *,
    from_retry: bool = False,
) -> None:
    """Topic-practice analysis — same pipeline as coaching mock; separate result store."""
    from utils.topic_practice_state import (
        apply_topic_completed_result,
        apply_topic_needs_review_result,
        apply_topic_non_english_result,
        apply_topic_no_audio_result,
        apply_topic_no_speech_result,
        apply_topic_unclear_speech_result,
        apply_topic_pending_result,
        get_topic_recordings,
        save_topic_placeholder_before_ai,
        topic_audio_key,
    )

    if _get_analysis_in_flight("topic_practice"):
        return

    topic_title = str(topic.get("topic_title") or "")
    question_id = str(question.get("question_id") or "")
    if not audio_key:
        audio_key = topic_audio_key(topic_id, question_id, q_idx)

    _set_analysis_in_flight("topic_practice", True)
    try:
        stop_recording_timer()
        mx["analysis_result"] = None
        mx["analysis_error_msg"] = ""
        mx["analysis_done"] = False
        mx["analysis_status"] = ""
        mx["preview_transcript"] = None

        recordings = get_topic_recordings()
        blob = mx.get("audio_bytes") or recordings.get(audio_key)
        if not blob:
            st.error("오디오 데이터가 유실되었습니다. 다시 녹음해주세요.")
            return

        tp_nbytes = recording_byte_length(blob)
        if classify_pre_analysis_blob(blob) == "no_audio":
            if not from_retry:
                save_topic_placeholder_before_ai(
                    topic_id=topic_id,
                    topic_title=topic_title,
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    audio_bytes=blob,
                )
            ns = apply_topic_no_audio_result(
                topic_id=topic_id,
                topic_title=topic_title,
                question_index=q_idx,
                question=question,
                audio_key=audio_key,
                source_audio_size_bytes=tp_nbytes,
            )
            mx["analysis_result"] = ns
            mx["last_result"] = ns
            st.session_state["topic_practice_step"] = "feedback"
            st.rerun()
            return

        if not from_retry:
            save_topic_placeholder_before_ai(
                topic_id=topic_id,
                topic_title=topic_title,
                question_index=q_idx,
                question=question,
                audio_key=audio_key,
                audio_bytes=blob,
            )

        difficulty = int(settings_session()["difficulty"])
        result: dict | None = None
        last_error = ""
        attempts = 0
        question_en = str(question.get("question_en") or "")

        submission_id = secrets.token_hex(4)
        wait_slot = st.empty()

        def _show_analysis_wait(label: str = "AI가 발화를 진단 중입니다…") -> None:
            with wait_slot.container():
                render_ai_analysis_waiting(submission_id, stage_label=label)

        try:
            _show_analysis_wait()

            def _on_status(stage: str, label: str) -> None:
                _show_analysis_wait(label)

            mime_for_gemini = resolve_mime_for_analysis(
                blob, mx=mx, audio_key=audio_key
            )
            audio_pipeline_diag.log_before_gemini(
                q_index=q_idx,
                audio_bytes=blob,
                mime_type=mime_for_gemini,
            )
            result, last_error, attempts = analyze_audio_with_retry(
                blob,
                question_en,
                api_key,
                difficulty,
                mime_guess=mime_for_gemini,
                on_status=_on_status,
                diag={
                    "submission_id": submission_id,
                    "question_index": q_idx,
                    "question_id": question_id,
                    "mock_mode": "topic_practice",
                    "mock_page": mx.get("mock_page"),
                    "caller": "mock_exam._run_topic_practice_analysis",
                    "mime_type": mime_for_gemini,
                },
            )
        except Exception as exc:
            logger.exception("Topic practice Gemini failure topic=%s q=%s", topic_id, question_id)
            last_error = f"{type(exc).__name__}: {exc}"
            result = None
            attempts = max(attempts, 1)
        finally:
            finish_analysis_waiting_ui(wait_slot, submission_id)

        if _is_analysis_failed(result, last_error):
            _empty_resp = bool(last_error and "비어" in last_error)
            pending = apply_topic_pending_result(
                topic_id=topic_id,
                topic_title=topic_title,
                question_index=q_idx,
                question=question,
                audio_key=audio_key,
                error_message=last_error or "AI 분석 실패",
                attempts=attempts,
                mode="topic_practice",
                mime_type=mime_for_gemini,
                model=str((result or {}).get("model_used") or ""),
                audio_bytes_len=tp_nbytes,
                empty_response=_empty_resp,
            )
            mx["analysis_result"] = pending
            mx["last_result"] = pending
            st.session_state["topic_practice_step"] = "feedback"
            st.rerun()
            return

        speech_issue = classify_post_analysis_issue(blob, result)
        audio_pipeline_diag.log_no_speech_gate(
            q_index=q_idx,
            audio_bytes=blob,
            transcript=(result or {}).get("transcript") or "",
            trust_result=audio_pipeline_diag.trust_result_label(result),
            status=speech_issue,
        )
        if speech_issue != "ok":
            mime_guess = resolve_mime_for_debug(
                blob, mx=mx, audio_key=audio_key, result=result
            )
            if speech_issue == "no_audio":
                ns = apply_topic_no_audio_result(
                    topic_id=topic_id,
                    topic_title=topic_title,
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    source_audio_size_bytes=tp_nbytes,
                )
            elif speech_issue == "non_english":
                preview = (result or {}).get("non_english_preview") or ""
                kind = (result or {}).get("language_mismatch_kind") or "korean"
                ns = apply_topic_non_english_result(
                    topic_id=topic_id,
                    topic_title=topic_title,
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    source_audio_size_bytes=tp_nbytes,
                    audio_mime_guess=mime_guess,
                    non_english_preview=preview,
                    language_mismatch_kind=kind,
                )
            elif speech_issue == "needs_review":
                ns = apply_topic_needs_review_result(
                    topic_id=topic_id,
                    topic_title=topic_title,
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    source_audio_size_bytes=tp_nbytes,
                    audio_mime_guess=mime_guess,
                )
            else:
                ns = apply_topic_unclear_speech_result(
                    topic_id=topic_id,
                    topic_title=topic_title,
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    source_audio_size_bytes=tp_nbytes,
                    audio_mime_guess=mime_guess,
                )
            mx["analysis_result"] = ns
            mx["last_result"] = ns
            st.session_state["topic_practice_step"] = "feedback"
            st.rerun()
            return

        _transcript_raw = (result.get("transcript") or "").strip()
        result_to_store = cache_analysis_payload(result)
        result_to_store = apply_topic_completed_result(
            topic_id=topic_id,
            topic_title=topic_title,
            question_index=q_idx,
            question=question,
            audio_key=audio_key,
            result=result_to_store,
        )
        mx["preview_transcript"] = _transcript_raw
        mx["analysis_result"] = result_to_store
        mx["last_result"] = result_to_store
        raw_parse_failed = (result_to_store.get("raw_text_parse_failed") or "").strip()
        if raw_parse_failed:
            st.error(raw_parse_failed)
        st.session_state["topic_practice_step"] = "feedback"
        st.rerun()
    finally:
        _set_analysis_in_flight("topic_practice", False)


def _run_mini_mock_analysis(
    mx: dict,
    question: dict,
    q_idx: int,
    audio_key: str,
    api_key: str,
    *,
    from_retry: bool = False,
    defer_rerun: bool = False,
    manage_in_flight: bool = True,
    external_wait_slot: Any | None = None,
    external_submission_id: str | None = None,
) -> None:
    """Mini mock — same single-answer pipeline as real mock; separate result store."""
    from utils.mini_mock_state import (
        apply_mini_mock_completed_result,
        apply_mini_mock_needs_review_result,
        apply_mini_mock_non_english_result,
        apply_mini_mock_no_audio_result,
        apply_mini_mock_pending_result,
        apply_mini_mock_unclear_speech_result,
        find_mini_mock_result,
        get_mini_mock_recordings,
        mini_mock_audio_key,
        mini_mock_needs_analysis,
        save_mini_mock_placeholder_before_ai,
    )

    if manage_in_flight and _get_analysis_in_flight("mini_mock"):
        return

    question_id = str(question.get("question_id") or "")
    if not audio_key:
        audio_key = mini_mock_audio_key(question_id)

    row = find_mini_mock_result(question_id)
    if row and not from_retry and not mini_mock_needs_analysis(row):
        return

    if manage_in_flight:
        _set_analysis_in_flight("mini_mock", True)
    try:
        if not defer_rerun:
            stop_recording_timer()
        mx["preview_transcript"] = None

        recordings = get_mini_mock_recordings()
        blob = mx.get("audio_bytes") or recordings.get(audio_key)
        if not blob:
            if not defer_rerun:
                st.error("오디오 데이터가 유실되었습니다. 다시 녹음해주세요.")
            return

        mm_nbytes = recording_byte_length(blob)
        if classify_pre_analysis_blob(blob) == "no_audio":
            if not from_retry:
                save_mini_mock_placeholder_before_ai(
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    audio_bytes=blob,
                )
            apply_mini_mock_no_audio_result(
                question_index=q_idx,
                question=question,
                audio_key=audio_key,
                source_audio_size_bytes=mm_nbytes,
            )
            _record_mini_mock_per_question_debug(
                q_idx=q_idx,
                question=question,
                audio_len=mm_nbytes,
                api_key=api_key,
                result=None,
                last_error="no_audio",
                analysis_failed=True,
            )
            if not defer_rerun:
                st.rerun()
            return

        if not from_retry:
            save_mini_mock_placeholder_before_ai(
                question_index=q_idx,
                question=question,
                audio_key=audio_key,
                audio_bytes=blob,
            )

        difficulty = int(settings_session()["difficulty"])
        result: dict | None = None
        last_error = ""
        attempts = 0
        mime_for_gemini = ""
        question_en = str(question.get("question_en") or "")

        submission_id = external_submission_id or secrets.token_hex(4)
        wait_slot = external_wait_slot if external_wait_slot is not None else st.empty()

        def _show_analysis_wait(label: str = "AI가 발화를 진단 중입니다…") -> None:
            if external_wait_slot is not None:
                return
            with wait_slot.container():
                render_ai_analysis_waiting(submission_id, stage_label=label)

        try:
            if external_wait_slot is None:
                _show_analysis_wait()

            if (
                external_wait_slot is not None
                and _mini_mock_analyzing_elapsed() > MINI_MOCK_ANALYZING_TIMEOUT_SEC
            ):
                pending_row = apply_mini_mock_pending_result(
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    error_message="analysis_timeout_over_60s",
                    attempts=0,
                    audio_bytes_len=mm_nbytes,
                )
                st.session_state["mini_mock_pending_reason"] = "analysis_timeout"
                st.session_state["mini_mock_last_api_error_category"] = "timeout"
                st.session_state["mini_mock_last_api_error_preview"] = "analysis_timeout_over_60s"
                _record_mini_mock_per_question_debug(
                    q_idx=q_idx,
                    question=question,
                    audio_len=mm_nbytes,
                    api_key=api_key,
                    result=None,
                    last_error="analysis_timeout_over_60s",
                    attempts=0,
                    analysis_failed=True,
                    stored_result=pending_row,
                )
                return

            def _on_status(stage: str, label: str) -> None:
                if external_wait_slot is not None:
                    with wait_slot.container():
                        render_ai_analysis_waiting(
                            submission_id,
                            title="AI가 3개 답변을 분석하고 있어요",
                            subtitle=(
                                "묘사, 경험, 롤플레이 답변을 바탕으로 현재 말하기 습관을 진단하는 중입니다.<br/>"
                                "조금 시간이 걸릴 수 있어요."
                            ),
                            stage_label=label,
                        )
                else:
                    _show_analysis_wait(label)

            mime_for_gemini = resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key)
            if not (mime_for_gemini or "").strip():
                mime_for_gemini = "audio/webm"
            try:
                logger.warning(
                    "[MINI_MOCK_API_DEBUG] phase=before_analyze q_idx=%s audio_len=%s "
                    "mime_type=%s question_text_len=%s api_key_present=%s",
                    q_idx,
                    mm_nbytes,
                    mime_for_gemini,
                    len(question_en),
                    bool(str(api_key or "").strip()),
                )
            except Exception:
                pass
            audio_pipeline_diag.log_before_gemini(
                q_index=q_idx,
                audio_bytes=blob,
                mime_type=mime_for_gemini,
            )
            result, last_error, attempts = analyze_audio_with_retry(
                blob,
                question_en,
                api_key,
                difficulty,
                mime_guess=mime_for_gemini,
                on_status=_on_status,
                diag={
                    "submission_id": submission_id,
                    "question_index": q_idx,
                    "question_id": question_id,
                    "mock_mode": "mini_mock",
                    "mock_page": mx.get("mock_page"),
                    "caller": "mock_exam._run_mini_mock_analysis",
                    "mime_type": mime_for_gemini,
                },
            )
            st.session_state[_MINI_MOCK_BATCH_ATTEMPTS_KEY] = max(
                int(st.session_state.get(_MINI_MOCK_BATCH_ATTEMPTS_KEY) or 0),
                int(attempts or 0),
            )
            try:
                _empty_resp = bool(
                    last_error
                    and (
                        "비어" in last_error
                        or "empty" in last_error.lower()
                    )
                )
                err_cat, err_type = _classify_mini_mock_api_error(
                    last_error or "",
                    empty_response=_empty_resp or result is None,
                )
                transcript_len = len(str((result or {}).get("transcript") or ""))
                logger.warning(
                    "[MINI_MOCK_API_DEBUG] phase=after_analyze q_idx=%s result_none=%s "
                    "error_category=%s error_type=%s error_preview=%s attempts=%s "
                    "diagnosis_status=%s analysis_status=%s transcript_len=%s "
                    "api_key_present=%s",
                    q_idx,
                    result is None,
                    err_cat,
                    err_type,
                    (last_error or "")[:200],
                    attempts,
                    (result or {}).get("diagnosis_status"),
                    (result or {}).get("analysis_status"),
                    transcript_len,
                    bool(str(api_key or "").strip()),
                )
            except Exception:
                pass
        except Exception as exc:
            logger.exception("Mini mock Gemini failure q=%s", question_id)
            last_error = f"{type(exc).__name__}: {exc}"
            result = None
            attempts = max(attempts, 1)
            st.session_state[_MINI_MOCK_BATCH_ATTEMPTS_KEY] = max(
                int(st.session_state.get(_MINI_MOCK_BATCH_ATTEMPTS_KEY) or 0),
                int(attempts or 0),
            )
        finally:
            if external_wait_slot is None:
                finish_analysis_waiting_ui(wait_slot, submission_id)

        analysis_failed = _is_analysis_failed(result, last_error)
        err_for_debug = (last_error or "").strip()
        if analysis_failed and not err_for_debug:
            err_for_debug = "no_error_message_returned"
        elif (
            not analysis_failed
            and isinstance(result, dict)
            and (
                str(result.get("analysis_status") or "").lower() == "pending"
                or str(result.get("diagnosis_status") or "").lower() == "analysis_pending"
                or result.get("analysis_pending")
            )
        ):
            err_for_debug = "result_returned_but_marked_pending"
        _record_mini_mock_per_question_debug(
            q_idx=q_idx,
            question=question,
            audio_len=mm_nbytes,
            mime_type=mime_for_gemini,
            api_key=api_key,
            result=result,
            last_error=err_for_debug,
            attempts=attempts,
            analysis_failed=analysis_failed,
        )

        if analysis_failed:
            _empty_resp = bool(
                last_error
                and (
                    "비어" in last_error
                    or "empty" in (last_error or "").lower()
                )
            )
            pending_row = apply_mini_mock_pending_result(
                question_index=q_idx,
                question=question,
                audio_key=audio_key,
                error_message=err_for_debug if err_for_debug not in (
                    "no_error_message_returned",
                    "result_returned_but_marked_pending",
                ) else (last_error or err_for_debug or "AI 분석 실패"),
                attempts=attempts,
                mime_type=mime_for_gemini,
                model=str((result or {}).get("model_used") or ""),
                audio_bytes_len=mm_nbytes,
                empty_response=_empty_resp,
            )
            _record_mini_mock_per_question_debug(
                q_idx=q_idx,
                question=question,
                audio_len=mm_nbytes,
                mime_type=mime_for_gemini,
                api_key=api_key,
                result=result,
                last_error=err_for_debug or last_error or "no_error_message_returned",
                attempts=attempts,
                analysis_failed=True,
                stored_result=pending_row,
            )
            err_cat_store, _ = _classify_mini_mock_api_error(
                err_for_debug or last_error or "",
                empty_response=_empty_resp or result is None,
            )
            if _mini_mock_is_quota_error(
                err_for_debug or last_error or "",
                err_cat_store,
            ):
                _mini_mock_mark_quota_pending()
            _store_latest_mini_mock_api_debug(
                error_category=err_cat_store or "analysis_failed",
                error_message=err_for_debug or last_error or "no_error_message_returned",
                attempts=attempts,
                api_key=api_key,
                empty_response=_empty_resp or result is None,
            )
            if not defer_rerun:
                st.rerun()
            return

        speech_issue = classify_post_analysis_issue(blob, result)
        audio_pipeline_diag.log_no_speech_gate(
            q_index=q_idx,
            audio_bytes=blob,
            transcript=(result or {}).get("transcript") or "",
            trust_result=audio_pipeline_diag.trust_result_label(result),
            status=speech_issue,
        )
        if speech_issue != "ok":
            mime_guess = resolve_mime_for_debug(blob, mx=mx, audio_key=audio_key, result=result)
            if speech_issue == "no_audio":
                apply_mini_mock_no_audio_result(
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    source_audio_size_bytes=mm_nbytes,
                )
            elif speech_issue == "non_english":
                preview = (result or {}).get("non_english_preview") or ""
                kind = (result or {}).get("language_mismatch_kind") or "korean"
                apply_mini_mock_non_english_result(
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    source_audio_size_bytes=mm_nbytes,
                    audio_mime_guess=mime_guess,
                    non_english_preview=preview,
                    language_mismatch_kind=kind,
                )
            elif speech_issue == "needs_review":
                apply_mini_mock_needs_review_result(
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    source_audio_size_bytes=mm_nbytes,
                    audio_mime_guess=mime_guess,
                )
            else:
                apply_mini_mock_unclear_speech_result(
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    source_audio_size_bytes=mm_nbytes,
                    audio_mime_guess=mime_guess,
                )
            _record_mini_mock_per_question_debug(
                q_idx=q_idx,
                question=question,
                audio_len=mm_nbytes,
                mime_type=mime_guess,
                api_key=api_key,
                result=result,
                last_error=f"speech_issue:{speech_issue}",
                attempts=attempts,
                analysis_failed=False,
            )
            if not defer_rerun:
                st.rerun()
            return

        result_to_store = cache_analysis_payload(result)
        apply_mini_mock_completed_result(
            question_index=q_idx,
            question=question,
            audio_key=audio_key,
            result=result_to_store,
        )
        _record_mini_mock_per_question_debug(
            q_idx=q_idx,
            question=question,
            audio_len=mm_nbytes,
            mime_type=mime_for_gemini,
            api_key=api_key,
            result=result_to_store,
            last_error="",
            attempts=attempts,
            analysis_failed=False,
            stored_result=result_to_store,
        )
        if not defer_rerun:
            st.rerun()
    finally:
        if manage_in_flight:
            _set_analysis_in_flight("mini_mock", False)


def render_mini_mock_analyzing_screen(mx: dict) -> None:
    """Loading UI only — analysis runs separately in run_mini_mock_report_analysis_once."""
    if _is_mini_mock_v2_active():
        try:
            logger.debug("[MINI_MOCK_LEGACY] analyzing_screen skipped — V2 active")
        except Exception:
            pass
        return
    render_top_bar("5분 진단", back_href="?nav=MOCK", eyebrow="미니 모의고사 · AI 분석")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    attempt_id = str(
        st.session_state.get(_MINI_MOCK_ANALYSIS_ATTEMPT_KEY) or secrets.token_hex(4)
    )
    render_ai_analysis_waiting(
        attempt_id,
        title="AI가 3개 답변을 분석하고 있어요",
        subtitle=(
            "묘사, 경험, 롤플레이 답변을 바탕으로 현재 말하기 습관을 진단하는 중입니다.<br/>"
            "조금 시간이 걸릴 수 있어요."
        ),
    )
    _mini_mock_mount_analyzing_watchdog(mx)


def _mini_mock_mount_analyzing_watchdog(mx: dict) -> None:
    """Re-check timeout while ANALYZING_REPORT so stale in_progress cannot loop forever."""
    from datetime import timedelta

    @st.fragment(run_every=timedelta(seconds=5))
    def _watchdog() -> None:
        if _mini_mock_page() != "ANALYZING_REPORT":
            return
        _mini_mock_ensure_analyzing_clock()
        if _mini_mock_abort_analyzing_if_needed(mx):
            st.rerun()

    _watchdog()


def run_mini_mock_report_analysis_once(mx: dict) -> None:
    """Run batch mini-mock analysis once per user click (no auto-retry on rerun)."""
    if _is_mini_mock_v2_active():
        try:
            logger.debug("[MINI_MOCK_LEGACY] report_analysis skipped — V2 active")
        except Exception:
            pass
        return
    from data.mini_mock_questions import get_mini_mock_question
    from utils.mini_mock_state import (
        apply_mini_mock_pending_result,
        count_mini_mock_analysis_completed,
        count_mini_mock_analysis_pending,
        count_mini_mock_saved_answers,
        get_mini_mock_answer_blob,
        mini_mock_audio_key,
        mini_mock_rows_sorted,
        row_result,
    )

    if _mini_mock_abort_analyzing_if_needed(mx):
        st.rerun()
        return

    _mini_mock_ensure_analyzing_clock()

    attempt_id = str(st.session_state.get(_MINI_MOCK_ANALYSIS_ATTEMPT_KEY) or "")
    if attempt_id and st.session_state.get(_MINI_MOCK_BATCH_FINISHED_KEY) == attempt_id:
        if _mini_mock_page() == "ANALYZING_REPORT":
            _mini_mock_resolve_analyzing_after_batch(mx)
            st.rerun()
        _mini_mock_debug(f"analysis_once skipped (batch_done attempt={attempt_id})")
        return

    if st.session_state.get(_MINI_MOCK_ANALYSIS_IN_PROGRESS_KEY):
        if _mini_mock_abort_analyzing_if_needed(mx):
            st.rerun()
            return
        _mini_mock_debug("analysis_once skipped (already in progress)")
        return

    saved_n = count_mini_mock_saved_answers()
    if saved_n < _MINI_MOCK_QUESTION_COUNT:
        st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
        _mini_mock_clear_analysis_guards()
        st.rerun()
        return

    api_key = get_gemini_api_key()
    if not api_key:
        _mini_mock_transition_to_report_pending(
            mx,
            error_category="missing_api_key",
            error_message="API key not configured",
            error_type="MissingAPIKey",
            api_key="",
            pending_reason="missing_api_key",
        )
        st.rerun()
        return

    st.session_state[_MINI_MOCK_ANALYSIS_IN_PROGRESS_KEY] = True
    _set_analysis_in_flight("mini_mock", True)
    st.session_state[_MINI_MOCK_BATCH_ATTEMPTS_KEY] = 0
    st.session_state[_LATEST_MINI_MOCK_API_DEBUG_KEY] = {"per_question": []}
    submission_id = attempt_id or secrets.token_hex(4)
    if not st.session_state.get(_MINI_MOCK_ANALYSIS_ATTEMPT_KEY):
        st.session_state[_MINI_MOCK_ANALYSIS_ATTEMPT_KEY] = submission_id
    wait_slot = st.empty()
    next_page = "REPORT_PENDING"
    batch_finished = False
    timed_out = False
    has_quota = False

    try:
        with wait_slot.container():
            render_ai_analysis_waiting(
                submission_id,
                title="AI가 3개 답변을 분석하고 있어요",
                subtitle=(
                    "저장된 발화 텍스트를 바탕으로 현재 말하기 습관을 진단하는 중입니다.<br/>"
                    "조금 시간이 걸릴 수 있어요."
                ),
            )
        from services.transcript_analysis_service import analyze_mini_mock_transcripts

        rows_for_batch = mini_mock_rows_sorted()
        for q_idx in range(_MINI_MOCK_QUESTION_COUNT):
            question = get_mini_mock_question(q_idx)
            if not question:
                continue
            question_id = str(question.get("question_id") or "")
            row = None
            for r in rows_for_batch:
                if str(r.get("question_id") or "") == question_id:
                    row = r
                    break
            if not row:
                continue
            audio_key = str(row.get("audio_key") or "") or mini_mock_audio_key(question_id)
            if not get_mini_mock_answer_blob(row):
                apply_mini_mock_pending_result(
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    error_message="missing_audio",
                    attempts=0,
                    audio_bytes_len=0,
                )
                continue

        batch = analyze_mini_mock_transcripts(
            mini_mock_rows_sorted(),
            difficulty=int(settings_session()["difficulty"]),
            api_key=api_key,
        )
        try:
            logger.debug(
                "[MINI_MOCK_TRANSCRIPT_REPORT] ok=%s completed=%s insufficient=%s timeout=%s",
                batch.get("ok"),
                batch.get("completed_count"),
                batch.get("insufficient_count"),
                batch.get("timed_out"),
            )
        except Exception:
            pass

        for item in batch.get("per_question") or []:
            if not isinstance(item, dict):
                continue
            q_idx = int(item.get("question_index") or 0)
            question = get_mini_mock_question(q_idx) or {}
            question_id = str(question.get("question_id") or item.get("question_id") or "")
            audio_key = str(item.get("audio_key") or "") or mini_mock_audio_key(question_id)
            row = None
            for r in mini_mock_rows_sorted():
                if str(r.get("question_id") or "") == question_id:
                    row = r
                    break
            if row:
                audio_key = str(row.get("audio_key") or "") or audio_key
            status = str(item.get("status") or "")
            result = item.get("result")
            if status in ("completed", "insufficient") and isinstance(result, dict):
                stored = cache_analysis_payload(dict(result))
                apply_mini_mock_completed_result(
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    result=stored,
                )
                _record_mini_mock_per_question_debug(
                    q_idx=q_idx,
                    question=question,
                    audio_len=int(row.get("audio_len") or 0) if row else 0,
                    api_key=api_key,
                    stored_result=stored,
                    analysis_failed=status == "insufficient",
                )
            elif status in ("failed", "pending"):
                apply_mini_mock_pending_result(
                    question_index=q_idx,
                    question=question,
                    audio_key=audio_key,
                    error_message=str(item.get("error") or "stt_pending"),
                    attempts=0,
                    audio_bytes_len=int(row.get("audio_len") or 0) if row else 0,
                )

        completed = count_mini_mock_analysis_completed()
        pending = count_mini_mock_analysis_pending()
        st.session_state["mini_mock_completed"] = True
        timed_out = bool(batch.get("timed_out"))
        has_quota = bool(batch.get("quota"))
        if timed_out:
            next_page = "REPORT_PENDING"
            st.session_state["mini_mock_report_status"] = "pending_retry"
            st.session_state["mini_mock_pending_reason"] = "analysis_timeout"
            st.session_state["mini_mock_last_api_error_category"] = "timeout"
            st.session_state["mini_mock_last_api_error_preview"] = "analysis_timeout_over_60s"
            _finalize_mini_mock_batch_api_debug(
                error_category="timeout",
                error_message="analysis_timeout_over_60s",
                error_type="timeout",
                api_key=api_key,
            )
        elif has_quota:
            next_page = "REPORT_PENDING"
            st.session_state["mini_mock_report_status"] = "pending_retry"
            _mini_mock_mark_quota_pending()
            _finalize_mini_mock_batch_api_debug(
                error_category="quota_or_rate_limit",
                error_message=str(batch.get("error_message") or "quota_or_rate_limit"),
                error_type="quota_or_rate_limit",
                api_key=api_key,
            )
        elif batch.get("ok") and (
            batch.get("all_insufficient")
            or int(batch.get("completed_count") or 0) > 0
            or int(batch.get("insufficient_count") or 0) >= _MINI_MOCK_QUESTION_COUNT
        ):
            next_page = "REPORT"
            st.session_state["mini_mock_report_status"] = "completed"
            st.session_state.pop("mini_mock_pending_reason", None)
            _finalize_mini_mock_batch_api_debug(
                error_category="completed",
                api_key=api_key,
            )
        else:
            next_page = "REPORT_PENDING"
            st.session_state["mini_mock_report_status"] = "pending_retry"
            st.session_state["mini_mock_pending_reason"] = "analysis_incomplete"
            _finalize_mini_mock_batch_api_debug(
                error_category="analysis_incomplete",
                error_message=str(
                    batch.get("error_message")
                    or f"completed={completed} pending={pending}"
                ),
                error_type="incomplete_batch",
                api_key=api_key,
            )
        st.session_state["mini_mock_page"] = next_page
        batch_finished = True
        try:
            logger.debug(
                "[MINI_MOCK_REPORT] status=%s completed_count=%s pending_count=%s page=%s",
                st.session_state.get("mini_mock_report_status"),
                completed,
                pending,
                next_page,
            )
        except Exception:
            pass
        _mini_mock_debug(
            f"analysis_once done next_page={next_page} completed={completed} pending={pending}"
        )
    except Exception as exc:
        logger.exception("Mini mock batch report analysis failed")
        _mini_mock_transition_to_report_pending(
            mx,
            error_category="exception",
            error_message=f"{type(exc).__name__}: {exc}",
            error_type=type(exc).__name__,
            api_key=api_key,
            pending_reason="analysis_incomplete",
        )
    finally:
        finish_analysis_waiting_ui(wait_slot, submission_id)
        _mini_mock_clear_stuck_analysis_in_flight_flags()
        if batch_finished and submission_id:
            st.session_state[_MINI_MOCK_BATCH_FINISHED_KEY] = submission_id

    if not batch_finished and _mini_mock_page() == "ANALYZING_REPORT":
        _mini_mock_transition_to_report_pending(
            mx,
            error_category="stuck_analyzing",
            error_message="page_stuck_analyzing",
            error_type="StuckAnalyzing",
            api_key=api_key,
            pending_reason="stuck_analyzing",
        )
    if _mini_mock_page() != "ANALYZING_REPORT":
        st.rerun()


def render_topic_analyzing_screen(mx: dict) -> None:
    """Loading UI only — analysis runs in run_topic_report_analysis_once."""
    topic_id, topic, _, _ = _topic_practice_context()
    title = str(topic.get("topic_title") or "주제") if topic else "주제"
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} · AI 분석")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    attempt_id = str(
        st.session_state.get(_TOPIC_REPORT_ATTEMPT_KEY) or secrets.token_hex(4)
    )
    render_topic_mini_report_waiting(
        attempt_id,
        stage_label="3개 답변을 바탕으로 주제별 풀 리포트를 만드는 중…",
    )


def run_topic_report_analysis_once(mx: dict) -> None:
    """One Gemini report call per button click — no per-question analysis."""
    from services.feedback.topic_mini_report_analysis import (
        TOPIC_REPORT_COMPLETED,
        TOPIC_REPORT_FAILED,
        TOPIC_REPORT_PENDING_RETRY,
        is_real_topic_ai_report,
        run_topic_mini_report_analysis,
    )
    from utils.topic_practice_state import (
        all_topic_answers_saved,
        topic_rows_for_session,
    )

    attempt_id = str(st.session_state.get(_TOPIC_REPORT_ATTEMPT_KEY) or "")
    if attempt_id and st.session_state.get(_TOPIC_REPORT_BATCH_FINISHED_KEY) == attempt_id:
        return
    if _get_analysis_in_flight("topic_practice"):
        return

    topic_id, topic, _, _ = _topic_practice_context()
    if not topic_id or not topic:
        st.session_state["topic_practice_step"] = "select_topic"
        st.rerun()
        return
    if not all_topic_answers_saved(topic_id):
        st.session_state["topic_practice_step"] = "question"
        st.rerun()
        return

    api_key = get_gemini_api_key()
    if not api_key:
        st.session_state["topic_practice_step"] = "report_pending"
        st.session_state["topic_report_status"] = TOPIC_REPORT_PENDING_RETRY
        st.session_state["topic_report_last_error"] = "API key not configured"
        st.rerun()
        return

    rows = topic_rows_for_session(topic_id)
    topic_title = str(topic.get("topic_title") or "")
    topic_category = str(topic.get("category") or topic.get("topic_category") or "")
    submission_id = attempt_id or secrets.token_hex(4)
    if not st.session_state.get(_TOPIC_REPORT_ATTEMPT_KEY):
        st.session_state[_TOPIC_REPORT_ATTEMPT_KEY] = submission_id

    _set_analysis_in_flight("topic_practice", True)
    wait_slot = st.empty()
    batch_finished = False
    path_label = "pending"

    try:
        with wait_slot.container():
            render_topic_mini_report_waiting(
                submission_id,
                stage_label="저장된 발화 텍스트·문법·표현·답변 흐름을 정리하는 중…",
            )
        import concurrent.futures

        from services.transcript_analysis_service import TOPIC_REPORT_TIMEOUT_SEC

        def _topic_report_call() -> dict:
            return run_topic_mini_report_analysis(
                rows,
                {
                    "topic_id": topic_id,
                    "topic_title": topic_title,
                    "topic_category": topic_category,
                },
                api_key,
                difficulty=int(settings_session()["difficulty"]),
                mx=mx,
                consume_daily_slot=not bool(
                    st.session_state.get("topic_report_status") == "retrying"
                ),
                from_retry=st.session_state.get("topic_report_status") == "retrying",
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_topic_report_call)
            try:
                outcome = fut.result(timeout=float(TOPIC_REPORT_TIMEOUT_SEC))
            except concurrent.futures.TimeoutError:
                outcome = {
                    "topic_report_status": TOPIC_REPORT_PENDING_RETRY,
                    "pending_reason": "analysis_timeout_over_60s",
                }
        status = str(outcome.get("topic_report_status") or "")
        pending_reason = str(outcome.get("pending_reason") or "")
        st.session_state["topic_report_status"] = status

        if status == TOPIC_REPORT_COMPLETED:
            report = outcome.get("report")
            if isinstance(report, dict) and is_real_topic_ai_report(report):
                st.session_state["topic_report_result"] = report
                st.session_state["topic_mini_report"] = report
                st.session_state.pop("topic_mini_report_pending", None)
                st.session_state.pop("topic_pending_reason", None)
                st.session_state["topic_practice_step"] = "report"
                path_label = str(report.get("report_source") or "completed")
                try:
                    from utils.history_sync import save_topic_report

                    save_topic_report(
                        report,
                        topic_title=topic_title,
                        sig=f"{topic_id}_{submission_id}",
                    )
                except Exception:
                    pass
            else:
                status = TOPIC_REPORT_PENDING_RETRY
                st.session_state["topic_report_status"] = status
                st.session_state["topic_practice_step"] = "report_pending"
                st.session_state["topic_mini_report_pending"] = True
        elif status == TOPIC_REPORT_PENDING_RETRY:
            st.session_state.pop("topic_report_result", None)
            st.session_state.pop("topic_mini_report", None)
            st.session_state["topic_mini_report_pending"] = True
            st.session_state["topic_practice_step"] = "report_pending"
            if _topic_is_quota_error(pending_reason):
                st.session_state["topic_pending_reason"] = "quota"
                try:
                    logger.debug("[TOPIC_QUOTA] detected=True")
                except Exception:
                    pass
            path_label = "pending_retry"
        elif status == TOPIC_REPORT_FAILED:
            st.session_state.pop("topic_report_result", None)
            st.session_state.pop("topic_mini_report", None)
            st.session_state["topic_practice_step"] = "report_pending"
            st.session_state["topic_report_status"] = TOPIC_REPORT_PENDING_RETRY
            msg = str(outcome.get("user_message") or "").strip()
            if msg:
                st.session_state["topic_report_last_error"] = msg
            path_label = "failed"
        batch_finished = True
        try:
            logger.debug(
                "[TOPIC_REPORT] path=%s status=%s saved_count=%s",
                path_label,
                st.session_state.get("topic_report_status"),
                len(rows),
            )
        except Exception:
            pass
    except Exception as exc:
        logger.exception("Topic report analysis failed")
        st.session_state["topic_practice_step"] = "report_pending"
        st.session_state["topic_report_status"] = TOPIC_REPORT_PENDING_RETRY
        st.session_state["topic_report_last_error"] = f"{type(exc).__name__}: {exc}"
    finally:
        finish_analysis_waiting_ui(wait_slot, submission_id)
        _set_analysis_in_flight("topic_practice", False)
        if batch_finished and submission_id:
            st.session_state[_TOPIC_REPORT_BATCH_FINISHED_KEY] = submission_id
    st.rerun()


def render_topic_saved_screen(mx: dict) -> None:
    """After Q1/Q2 save — next question only (no Gemini)."""
    from components.answer_recording import (
        clear_mic_recording_cache,
        reset_recording_ui_for_question,
    )
    from utils.topic_practice_state import (
        clear_topic_answer_for_question,
        get_topic_answer_blob,
        find_topic_result,
    )
    from utils.speech_recording import recording_byte_length

    topic_id, topic, q_idx, question = _topic_practice_context()
    if not topic_id or not topic or not question:
        st.session_state["topic_practice_step"] = "select_topic"
        st.rerun()
        return

    title = str(topic.get("topic_title") or "주제")
    question_id = str(question.get("question_id") or "")
    row = find_topic_result(topic_id, question_id)
    blob = get_topic_answer_blob(row) if row else None
    audio_len = recording_byte_length(blob) if blob else 0

    render_top_bar(
        "주제별 연습",
        back_href="?nav=MOCK",
        eyebrow=f"{title} 콤보 연습 · Q{q_idx + 1}/3",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    render_topic_answer_saved_card(q_idx=q_idx, audio_len=audio_len, is_last=False)
    if row and st.session_state.get("show_dev_debug"):
        from services.stt_service import render_stt_dev_debug_capsule

        res_dbg = row.get("analysis_result") if isinstance(row.get("analysis_result"), dict) else {}
        render_stt_dev_debug_capsule(res_dbg, key_suffix=f"tp_saved_{topic_id}_{q_idx}")

    if st.button(
        "다음 질문으로",
        type="primary",
        use_container_width=True,
        key=f"tp_next_saved_{topic_id}_{q_idx}",
    ):
        _, mk = build_recording_keys(f"topic_{topic_id}", question_id, q_idx)
        _topic_advance_after_saved_answer(mx, topic_id, question_id, mic_key=mk)

    if st.button(
        "같은 질문 다시 말하기",
        use_container_width=True,
        key=f"tp_rerecord_saved_{topic_id}_{q_idx}",
    ):
        clear_topic_answer_for_question(topic_id, question_id)
        bump_recording_retry_nonce(f"topic_{topic_id}", question_id, q_idx)
        timer_key, mic_key = build_recording_keys(f"topic_{topic_id}", question_id, q_idx)
        reset_recording_ui_for_question(timer_key)
        clear_mic_recording_cache(mic_key)
        reset_recording_timer()
        mx["audio_bytes"] = None
        st.session_state.pop(_topic_speech_recovery_key(topic_id, question_id), None)
        st.session_state["topic_practice_step"] = "question"
        st.rerun()

    if st.button("주제 다시 선택", use_container_width=True, key=f"tp_reselect_saved_{topic_id}_{q_idx}"):
        _topic_back_to_select_topic()
        st.rerun()


def render_topic_practice_question_page(mx: dict) -> None:
    """Topic question + recorder — save only; report after all 3 answers."""
    from utils.topic_practice_state import (
        get_topic_recordings,
        topic_audio_key,
    )

    topic_id, topic, q_idx, question = _topic_practice_context()
    if not topic_id:
        st.session_state["topic_practice_step"] = "select_topic"
        st.rerun()
    if not topic or not question:
        st.warning("주제 또는 문항을 불러올 수 없습니다.")
        if st.button("주제 다시 선택", key="mx_tp_missing_ctx"):
            _topic_back_to_select_topic()
            st.rerun()
        return

    title = str(topic.get("topic_title") or "주제")
    question_id = str(question.get("question_id") or "")
    audio_key = topic_audio_key(topic_id, question_id, q_idx)
    is_last = q_idx >= _TOPIC_PRACTICE_QUESTION_COUNT - 1

    render_top_bar(
        "주제별 연습",
        back_href="?nav=MOCK",
        eyebrow=f"{title} 콤보 연습 · Q{q_idx + 1}/3",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_topic_question_body(topic, question, q_idx)

    recordings = get_topic_recordings()
    timer_key, mic_key = build_recording_keys(
        f"topic_{topic_id}", question_id, q_idx
    )
    recovery_key = _topic_speech_recovery_key(topic_id, question_id)
    if st.session_state.get(recovery_key):

        def _tp_recovery_clear() -> None:
            st.session_state.pop(recovery_key, None)

        def _tp_recovery_next() -> None:
            if is_last:
                st.session_state["topic_practice_step"] = "answers_saved"
            else:
                st.session_state["topic_practice_question_index"] = q_idx + 1
                st.session_state["topic_practice_step"] = "question"
            st.rerun()

        _render_pre_analysis_speech_recovery(
            mx,
            mode=f"topic_{topic_id}",
            question_id=question_id,
            question_index=q_idx,
            audio_key=audio_key,
            mic_key=mic_key,
            recordings=recordings,
            next_label="다음 질문으로",
            on_next=_tp_recovery_next,
            retry_key=f"tp_speech_retry_{topic_id}_{q_idx}",
            next_key=f"tp_speech_next_{topic_id}_{q_idx}",
            clear_recovery_flag=_tp_recovery_clear,
        )
        if st.button("주제 다시 선택", use_container_width=True, key=f"tp_reselect_recovery_{topic_id}_{q_idx}"):
            _topic_back_to_select_topic()
            st.rerun()
        return

    open_record_stage(compact=True)

    def _topic_on_recording_complete(_blob: bytes) -> bool:
        return _topic_commit_saved_answer(
            mx,
            topic_id=topic_id,
            topic_title=title,
            q_idx=q_idx,
            question=question,
            audio_key=audio_key,
        )

    if st.session_state.get("recording_active_audio_key") not in (None, audio_key):
        mx["audio_bytes"] = None
    st.session_state["recording_active_audio_key"] = audio_key
    _render_answer_recording_stage(
        mx,
        question_key=timer_key,
        mic_key=mic_key,
        audio_key=audio_key,
        recordings=recordings,
        analyzing=False,
        on_recording_complete=_topic_on_recording_complete,
        mode="topic_practice",
        question_index=q_idx,
    )
    close_record_stage()
    if st.button("주제 다시 선택", use_container_width=True, key=f"tp_reselect_{topic_id}_{q_idx}"):
        _topic_back_to_select_topic()
        st.rerun()


def render_topic_answers_saved_page(mx: dict) -> None:
    from utils.topic_practice_state import all_topic_answers_saved, topic_rows_for_session

    topic_id, topic, _q_idx, _question = _topic_practice_context()
    if not topic_id or not topic:
        st.session_state["topic_practice_step"] = "select_topic"
        st.rerun()
        return

    title = str(topic.get("topic_title") or "주제")
    if not all_topic_answers_saved(topic_id):
        st.session_state["topic_practice_step"] = "question"
        st.rerun()
        return

    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} · 저장 완료")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    render_topic_all_saved_card(title)

    rows = topic_rows_for_session(topic_id)
    st.markdown("##### 저장된 답변")
    for row in rows:
        ql = int(row.get("question_index") or 0) + 1
        nbytes = int(row.get("audio_len") or 0)
        if st.session_state.get("show_dev_debug"):
            st.caption(f"[dev] Q{ql} · 녹음 {nbytes:,} bytes")
        else:
            st.markdown(f"- Q{ql} 저장 완료")

    api_key = get_gemini_api_key()
    if st.button(
        "AI 풀 리포트 받기",
        type="primary",
        use_container_width=True,
        key=f"tp_mini_report_{topic_id}",
        disabled=_get_analysis_in_flight("topic_practice") or not api_key,
    ):
        _topic_begin_report_analysis()
        st.rerun()

    if st.button(
        "주제 선택으로 돌아가기",
        use_container_width=True,
        key=f"tp_mini_back_topics_{topic_id}",
    ):
        _topic_back_to_select_topic()
        st.rerun()

    if st.button("학습 방식 다시 선택", use_container_width=True, key="tp_mini_portal"):
        _exit_topic_practice_to_mode_picker(mx)
        st.rerun()


def render_topic_report_pending_screen(mx: dict) -> None:
    from utils.topic_practice_state import get_topic_answer_blob, topic_rows_for_session

    _set_analysis_in_flight("topic_practice", False)
    topic_id, topic, _, _ = _topic_practice_context()
    if not topic_id:
        st.session_state["topic_practice_step"] = "select_topic"
        st.rerun()
        return

    rows = topic_rows_for_session(topic_id)
    title = str(topic.get("topic_title") or "주제") if topic else "주제"
    is_quota = st.session_state.get("topic_pending_reason") == "quota"

    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} · AI 분석")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    render_topic_report_pending_retry_screen(
        saved_count=len(rows),
        is_quota=is_quota,
    )
    st.markdown("##### 저장된 답변")
    for row in rows:
        if not isinstance(row, dict):
            continue
        ql = int(row.get("question_index") or 0) + 1
        if get_topic_answer_blob(row):
            st.markdown(f"- Q{ql} 저장 완료")

    if st.session_state.get("show_dev_debug"):
        from services.exam_analytics import result_display_status

        st.markdown("##### 문항별 상태 (dev)")
        for row in rows:
            if not isinstance(row, dict):
                continue
            ql = int(row.get("question_index") or 0) + 1
            res = row.get("analysis_result")
            res = res if isinstance(res, dict) else {}
            status = result_display_status(res)
            st.markdown(f"- Q{ql}: {html.escape(status)}")

    api_key = get_gemini_api_key()
    if st.button(
        "AI 분석 다시 시도",
        type="primary",
        use_container_width=True,
        key=f"tp_report_retry_{topic_id}",
        disabled=_get_analysis_in_flight("topic_practice") or not api_key,
    ):
        _topic_begin_report_analysis(retrying=True)
        st.rerun()

    if st.button(
        "주제 선택으로 돌아가기",
        use_container_width=True,
        key=f"tp_pending_back_topics_{topic_id}",
    ):
        _topic_back_to_select_topic()
        st.rerun()


def render_topic_report(mx: dict) -> None:
    from services.feedback.topic_mini_report_analysis import (
        TOPIC_REPORT_COMPLETED,
        TOPIC_REPORT_PENDING_RETRY,
        is_real_topic_ai_report,
    )
    from utils.topic_practice_state import clear_topic_recordings

    report = st.session_state.get("topic_report_result") or st.session_state.get(
        "topic_mini_report"
    )
    status = str(st.session_state.get("topic_report_status") or "")
    if (
        not isinstance(report, dict)
        or not is_real_topic_ai_report(report)
        or status != TOPIC_REPORT_COMPLETED
    ):
        st.session_state.pop("topic_report_result", None)
        st.session_state.pop("topic_mini_report", None)
        st.session_state["topic_report_status"] = TOPIC_REPORT_PENDING_RETRY
        st.session_state["topic_mini_report_pending"] = True
        st.session_state["topic_practice_step"] = "report_pending"
        st.rerun()
        return

    title = str(report.get("topic_title") or "주제")
    render_top_bar("주제별 풀 리포트", back_href="?nav=MOCK", eyebrow=title)
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    render_topic_mini_report(report)

    if st.button("같은 주제 다시 연습", type="primary", use_container_width=True, key="mx_tp_restart_same"):
        clear_topic_recordings()
        st.session_state["topic_practice_question_index"] = 0
        st.session_state["topic_practice_results"] = []
        for key in (
            "topic_report_status",
            "topic_report_result",
            "topic_mini_report",
            "topic_mini_report_pending",
            "topic_report_last_error",
            "topic_pending_reason",
            _TOPIC_REPORT_ATTEMPT_KEY,
            _TOPIC_REPORT_BATCH_FINISHED_KEY,
        ):
            st.session_state.pop(key, None)
        st.session_state["topic_practice_step"] = "question"
        st.rerun()

    if st.button("다른 주제 선택", use_container_width=True, key="mx_tp_other_topic"):
        st.session_state["selected_topic_id"] = None
        _topic_back_to_select_topic()
        st.rerun()

    if st.button("학습 방식 다시 선택", use_container_width=True, key="mx_tp_mini_portal"):
        _exit_topic_practice_to_mode_picker(mx)
        st.rerun()


def render_topic_mini_report_page(mx: dict) -> None:
    render_topic_report(mx)


def render_topic_practice_feedback(mx: dict) -> None:
    """Legacy per-question feedback — redirect to batch report flow."""
    from services.feedback.topic_mini_report_analysis import (
        TOPIC_REPORT_COMPLETED,
        TOPIC_REPORT_PENDING_RETRY,
        is_real_topic_ai_report,
    )

    report = st.session_state.get("topic_report_result") or st.session_state.get(
        "topic_mini_report"
    )
    status = str(st.session_state.get("topic_report_status") or "")
    if (
        isinstance(report, dict)
        and is_real_topic_ai_report(report)
        and status == TOPIC_REPORT_COMPLETED
    ):
        st.session_state["topic_practice_step"] = "report"
    elif status in (TOPIC_REPORT_PENDING_RETRY, "pending_retry", "failed"):
        st.session_state["topic_practice_step"] = "report_pending"
    else:
        st.session_state["topic_practice_step"] = "answers_saved"
    st.rerun()


def render_topic_practice_complete(mx: dict) -> None:
    from data.topic_practice_questions import get_topic_by_id
    from utils.topic_practice_state import summarize_topic_session

    topic_id = st.session_state.get("selected_topic_id")
    topic = get_topic_by_id(str(topic_id)) if topic_id else None
    title = str(topic.get("topic_title") or "주제") if topic else "주제"
    stats = summarize_topic_session(str(topic_id)) if topic_id else {"answered": 0, "completed": 0, "pending": 0}

    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} 완료")
    st.markdown('<div class="mx-landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <section class="continue-card continue-card--start mx-landing-card" role="region"
                 aria-label="주제별 연습 완료">
          <div class="cc-eyebrow">완료</div>
          <div class="cc-title">{html.escape(title)} 주제 연습 완료</div>
          <div class="cc-meta">3문항 콤보 연습이 끝났어요.<br/>
            완료 문항 {stats["answered"]}개 · 분석 완료 {stats["completed"]}개 · 분석 대기 {stats["pending"]}개</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if st.button("같은 주제 다시 연습", type="primary", use_container_width=True, key="mx_tp_restart_same"):
        st.session_state["topic_practice_question_index"] = 0
        st.session_state["topic_practice_results"] = []
        st.session_state["topic_practice_step"] = "question"
        st.rerun()

    if st.button("다른 주제 선택", use_container_width=True, key="mx_tp_other_topic"):
        st.session_state["selected_topic_id"] = None
        st.session_state["topic_practice_question_index"] = 0
        st.session_state["topic_practice_results"] = []
        st.session_state["topic_practice_step"] = "select_topic"
        st.rerun()

    if st.button("실전 모의고사로 이동", use_container_width=True, key="mx_tp_goto_real_mock"):
        _clear_topic_practice_state()
        st.session_state["practice_portal_selected"] = True
        _set_mock_mode(mx, "real_mock")
        mx["mock_page"] = "SURVEY"
        st.rerun()

    if st.button("학습 방식 다시 선택", use_container_width=True, key="mx_tp_back_modes"):
        _exit_topic_practice_to_mode_picker(mx)
        st.rerun()


def _render_mini_mock_question_body(question: dict, q_idx: int) -> None:
    q_display = q_idx + 1
    type_label = html.escape(str(question.get("type_label") or ""))
    question_en = html.escape(str(question.get("question_en") or ""))
    question_ko = html.escape(str(question.get("question_ko") or ""))
    st.markdown(
        f"""
        <section class="continue-card continue-card--resume mx-landing-card" role="region"
                 aria-label="진행 상황">
          <div class="cc-eyebrow">진행</div>
          <div class="cc-title">Q{q_display} <span class="cc-of">/ {_MINI_MOCK_QUESTION_COUNT}</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <section class="mx-report-hero" role="region" aria-label="문항">
          <p class="mx-rh-eyebrow">{type_label}</p>
          <div class="mx-rh-title">{question_en}</div>
          <div class="mx-rh-transcript">{question_ko}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _mini_mock_sync_audio_to_mx(mx: dict, audio_key: str) -> None:
    from utils.mini_mock_state import get_mini_mock_recordings

    blob = get_mini_mock_recordings().get(audio_key)
    if not blob:
        return
    rec = mx.setdefault("recordings", {})
    if not isinstance(rec, dict):
        rec = {}
        mx["recordings"] = rec
    rec[audio_key] = blob
    mx["audio_bytes"] = blob


def reset_mini_mock_recording_for_question(
    q_idx: int,
    mx: dict,
    *,
    bump_retry: bool = False,
) -> None:
    """Clear recording UI only — do not touch mini_mock_page or saved answers."""
    from components.answer_recording import (
        clear_mic_recording_cache,
        reset_recording_ui_for_question,
    )
    from data.mini_mock_questions import get_mini_mock_question

    question = get_mini_mock_question(q_idx)
    if not question:
        return
    question_id = str(question.get("question_id") or "")
    if bump_retry:
        bump_recording_retry_nonce("mini_mock", question_id, q_idx)
    timer_key, mic_key = build_recording_keys("mini_mock", question_id, q_idx)
    reset_recording_ui_for_question(timer_key)
    clear_mic_recording_cache(mic_key)
    reset_recording_timer()
    mx["audio_bytes"] = None
    mx.pop("preview_transcript", None)
    st.session_state.pop("recording_active_audio_key", None)


def _mini_mock_advance_after_saved_answer(mx: dict, question_id: str, *, mic_key: str = "") -> None:
    idx = _mini_mock_last_saved_q_idx()
    st.session_state.pop(_mini_mock_saved_confirm_key(question_id), None)
    if _mini_mock_is_last_saved_question(idx):
        st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
        st.session_state["mini_mock_report_status"] = "answers_saved"
        try:
            logger.info("[MINI_MOCK_READY_FOR_REPORT] reason=next_on_last_saved q_index=%s", idx)
        except Exception:
            pass
        _mini_mock_debug("set_page READY_FOR_REPORT")
    else:
        next_idx = idx + 1
        try:
            logger.info(
                "[MINI_MOCK_NEXT_CLICK] from_index=%s to_index=%s",
                idx,
                next_idx,
            )
        except Exception:
            pass
        st.session_state["mini_mock_question_index"] = next_idx
        st.session_state["mini_mock_page"] = "QUESTION"
        reset_mini_mock_recording_for_question(next_idx, mx)
        _mini_mock_debug(f"set_page QUESTION q_idx={next_idx}")
    st.rerun()


def _mini_mock_commit_saved_answer(
    mx: dict,
    *,
    q_idx: int,
    question: dict,
    audio_key: str,
) -> bool:
    from utils.mini_mock_state import get_mini_mock_recordings, save_mini_mock_unanalyzed_answer
    from utils.speech_recording import (
        classify_pre_analysis_blob,
        recording_byte_length,
        resolve_mime_for_analysis,
    )

    recordings = get_mini_mock_recordings()
    blob = get_saved_audio_for_key(recordings, audio_key)
    if not blob:
        st.error("녹음이 제대로 저장되지 않았어요. 같은 질문을 다시 말해 주세요.")
        return False
    if classify_pre_analysis_blob(blob) == "no_audio":
        st.session_state[_MINI_MOCK_SPEECH_RECOVERY_Q_IDX_KEY] = q_idx
        return False
    mime = resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key)
    save_mini_mock_unanalyzed_answer(
        question_index=q_idx,
        question=question,
        audio_key=audio_key,
        audio_bytes=blob,
        mime_type=mime,
    )
    from utils.mini_mock_state import apply_stt_to_mini_mock_saved_row

    apply_stt_to_mini_mock_saved_row(
        question_index=q_idx,
        question=question,
        audio_key=audio_key,
        audio_bytes=blob,
        mime_type=mime,
    )
    question_id = str(question.get("question_id") or "")
    st.session_state.pop(_MINI_MOCK_SPEECH_RECOVERY_Q_IDX_KEY, None)
    st.session_state[_mini_mock_saved_confirm_key(question_id)] = True
    st.session_state["mini_mock_last_saved_q_idx"] = q_idx
    is_last = _mini_mock_is_last_saved_question(q_idx)
    try:
        logger.info(
            "[MINI_MOCK_SAVE] q_index=%s total=%s is_last=%s",
            q_idx,
            _MINI_MOCK_QUESTION_COUNT,
            is_last,
        )
    except Exception:
        pass
    if is_last:
        st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
        st.session_state["mini_mock_report_status"] = "answers_saved"
        try:
            logger.info("[MINI_MOCK_READY_FOR_REPORT] reason=q_saved_last q_index=%s", q_idx)
        except Exception:
            pass
        _mini_mock_debug(f"set_page READY_FOR_REPORT q_idx={q_idx}")
    else:
        st.session_state["mini_mock_page"] = "SAVED"
        _mini_mock_debug(f"set_page SAVED q_idx={q_idx}")
    from components.answer_recording import STATE_SAVED, set_recording_ui_state

    timer_key, _ = build_recording_keys("mini_mock", question_id, q_idx)
    set_recording_ui_state(timer_key, STATE_SAVED)
    try:
        logger.debug(
            "[MINI_MOCK_SAVE] q_idx=%s audio_len=%s page=%s",
            q_idx,
            recording_byte_length(blob),
            st.session_state.get("mini_mock_page"),
        )
    except Exception:
        pass
    return True


def _render_mini_mock_answer_saved_card(*, ready_for_report: bool = False) -> None:
    if ready_for_report:
        title = "3개 문항이 모두 저장되었어요"
        meta = (
            "묘사, 경험, 롤플레이 답변이 모두 저장되었습니다.<br/>"
            "이제 AI가 3개 답변을 바탕으로 5분 진단 리포트를 만들어드릴게요."
        )
    else:
        title = "답변이 저장되었어요"
        meta = (
            "좋아요. 지금은 흐름을 끊지 않고 다음 문항으로 넘어갈게요.<br/>"
            "3문항을 모두 끝낸 뒤 AI가 한 번에 진단 리포트를 만들어 드릴게요."
        )
    st.markdown(
        f"""
        <section class="continue-card continue-card--resume mx-landing-card" role="status">
          <div class="cc-eyebrow">저장 완료</div>
          <div class="cc-title">{html.escape(title)}</div>
          <div class="cc-meta">{meta}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_mini_mock_saved_screen(mx: dict) -> None:
    from data.mini_mock_questions import get_mini_mock_question
    from utils.mini_mock_state import find_mini_mock_row_by_index, get_mini_mock_answer_blob
    from utils.speech_recording import recording_byte_length

    q_idx = _mini_mock_last_saved_q_idx()
    is_last_saved = _mini_mock_is_last_saved_question(q_idx)
    _mini_mock_debug(f"render_saved_screen q_idx={q_idx} is_last={is_last_saved}")

    if is_last_saved:
        try:
            logger.info(
                "[MINI_MOCK_READY_FOR_REPORT] reason=saved_screen_last_question q_index=%s",
                q_idx,
            )
        except Exception:
            pass
        st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
        st.session_state["mini_mock_report_status"] = "answers_saved"
        st.rerun()
        return

    row = find_mini_mock_row_by_index(q_idx)
    audio_len = int(row.get("audio_len") or 0) if isinstance(row, dict) else 0
    if not audio_len and row:
        blob = get_mini_mock_answer_blob(row)
        if blob:
            audio_len = recording_byte_length(blob)

    question = get_mini_mock_question(q_idx)

    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow=f"미니 모의고사 · Q{q_idx + 1}/3",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_mini_mock_answer_saved_card(ready_for_report=False)
    if row and st.session_state.get("show_dev_debug"):
        from services.stt_service import render_stt_dev_debug_capsule
        from utils.mini_mock_state import row_result

        render_stt_dev_debug_capsule(row_result(row), key_suffix=f"mm_saved_{q_idx}")
        if audio_len > 0:
            st.caption(f"[dev] audio_len={audio_len:,}")

    _mini_mock_debug(f"next_button_rendered q_idx={q_idx}")
    if st.button(
        "다음 문항으로",
        type="primary",
        use_container_width=True,
        key=f"mini_mock_next_btn_{q_idx}",
    ):
        _mini_mock_debug(f"next_button_clicked q_idx={q_idx}")
        question_id = str(question.get("question_id") or "") if question else ""
        _, mk = build_recording_keys("mini_mock", question_id, q_idx) if question_id else ("", "")
        _mini_mock_advance_after_saved_answer(mx, question_id, mic_key=mk)

    if question:
        question_id = str(question.get("question_id") or "")
        if st.button(
            "같은 질문 다시 말하기",
            use_container_width=True,
            key=f"mm_rerecord_saved_{question_id}_{q_idx}",
        ):
            from utils.mini_mock_state import clear_mini_mock_answer_for_question

            clear_mini_mock_answer_for_question(question_id)
            reset_mini_mock_recording_for_question(q_idx, mx, bump_retry=True)
            st.session_state.pop(_mini_mock_saved_confirm_key(question_id), None)
            st.session_state["mini_mock_page"] = "QUESTION"
            _mini_mock_debug(f"set_page QUESTION q_idx={q_idx} (rerecord)")
            st.rerun()

    if st.button("학습 방식 다시 선택", use_container_width=True, key=f"mm_back_saved_{q_idx}"):
        reset_to_learning_portal()
        st.rerun()


def render_mini_mock_ready_for_report_screen(mx: dict) -> None:
    from utils.mini_mock_state import count_mini_mock_saved_answers

    _mini_mock_debug("render_ready_for_report_screen")
    saved_n = count_mini_mock_saved_answers()
    render_top_bar("5분 진단", back_href="?nav=MOCK", eyebrow="미니 모의고사 · 저장 완료")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(
        """
        <section class="continue-card continue-card--resume mx-landing-card" role="status">
          <div class="cc-eyebrow">저장 완료</div>
          <div class="cc-title">3개 답변이 모두 저장되었어요</div>
          <div class="cc-meta">이제 묘사, 경험, 롤플레이 답변을 바탕으로 5분 진단 리포트를 만들 수 있습니다.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="mx-record-saved">저장된 답변 {saved_n}개</p>',
        unsafe_allow_html=True,
    )
    if st.button(
        "AI 진단 리포트 받기",
        type="primary",
        use_container_width=True,
        key="mini_mock_get_report_btn",
    ):
        try:
            logger.info("[MINI_MOCK_REPORT_BUTTON_CLICK]")
        except Exception:
            pass
        _mini_mock_debug("report_button_clicked")
        st.session_state["mini_mock_report_status"] = "answers_saved"
        _mini_mock_begin_report_analysis()
        st.rerun()
    if st.button("학습 방식 다시 선택", use_container_width=True, key="mm_ready_back_portal"):
        reset_to_learning_portal()
        st.rerun()


def render_mini_mock_question_page(mx: dict) -> None:
    from data.mini_mock_questions import get_mini_mock_question
    from utils.mini_mock_state import (
        find_mini_mock_row_by_index,
        get_mini_mock_answer_blob,
        get_mini_mock_recordings,
        mini_mock_audio_key,
    )

    q_idx = _mini_mock_question_index()
    question = get_mini_mock_question(q_idx)
    if not question:
        st.warning("문항을 불러올 수 없습니다.")
        if st.button("학습하기로 돌아가기", key="mm_missing_back"):
            reset_to_learning_portal()
            st.rerun()
        return

    question_id = str(question.get("question_id") or "")
    audio_key = mini_mock_audio_key(question_id)
    saved_row = find_mini_mock_row_by_index(q_idx)
    if saved_row and get_mini_mock_answer_blob(saved_row):
        if _mini_mock_is_last_saved_question(q_idx):
            st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
            st.session_state["mini_mock_report_status"] = "answers_saved"
            try:
                logger.info(
                    "[MINI_MOCK_READY_FOR_REPORT] reason=question_page_last_saved q_index=%s",
                    q_idx,
                )
            except Exception:
                pass
        else:
            st.session_state["mini_mock_page"] = "SAVED"
        st.rerun()
        return

    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow=f"미니 모의고사 · Q{q_idx + 1}/3",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_mini_mock_question_body(question, q_idx)

    recordings = get_mini_mock_recordings()
    timer_key, mic_key = build_recording_keys("mini_mock", question_id, q_idx)
    if st.session_state.get(_MINI_MOCK_SPEECH_RECOVERY_Q_IDX_KEY) == q_idx:
        is_last = _mini_mock_is_last_saved_question(q_idx)
        next_label = "다음 문항으로" if not is_last else "AI 진단 리포트 받기"

        def _mm_recovery_clear() -> None:
            st.session_state.pop(_MINI_MOCK_SPEECH_RECOVERY_Q_IDX_KEY, None)

        def _mm_recovery_next() -> None:
            if is_last:
                st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
                st.session_state["mini_mock_report_status"] = "answers_saved"
                try:
                    logger.info(
                        "[MINI_MOCK_READY_FOR_REPORT] reason=speech_recovery_last q_index=%s",
                        q_idx,
                    )
                except Exception:
                    pass
            else:
                st.session_state["mini_mock_question_index"] = q_idx + 1
                reset_mini_mock_recording_for_question(q_idx + 1, mx)
                st.session_state["mini_mock_page"] = "QUESTION"
            st.rerun()

        _render_pre_analysis_speech_recovery(
            mx,
            mode="mini_mock",
            question_id=question_id,
            question_index=q_idx,
            audio_key=audio_key,
            mic_key=mic_key,
            recordings=recordings,
            next_label=next_label,
            on_next=_mm_recovery_next,
            retry_key=f"mm_speech_retry_{q_idx}",
            next_key=f"mm_speech_next_{q_idx}",
            clear_recovery_flag=_mm_recovery_clear,
        )
        if st.button("학습 방식 다시 선택", use_container_width=True, key=f"mm_back_portal_recovery_{q_idx}"):
            reset_to_learning_portal()
            st.rerun()
        return

    st.session_state["recording_active_audio_key"] = audio_key
    if not get_saved_audio_for_key(recordings, audio_key):
        mx["audio_bytes"] = None

    open_record_stage(compact=True)

    def _mm_on_recording_complete(_blob: bytes) -> bool:
        return _mini_mock_commit_saved_answer(
            mx,
            q_idx=q_idx,
            question=question,
            audio_key=audio_key,
        )

    _render_answer_recording_stage(
        mx,
        question_key=timer_key,
        mic_key=mic_key,
        audio_key=audio_key,
        recordings=recordings,
        analyzing=False,
        on_recording_complete=_mm_on_recording_complete,
        mode="mini_mock",
        question_index=q_idx,
    )
    close_record_stage()
    if st.button("학습 방식 다시 선택", use_container_width=True, key=f"mm_back_portal_{q_idx}"):
        reset_to_learning_portal()
        st.rerun()


def render_mini_mock_report_page(mx: dict) -> None:
    from components.mini_mock_report_ui import (
        render_mini_mock_report,
        render_mini_mock_report_actions,
        render_mini_mock_report_download,
    )
    from services.feedback.mini_mock_report import build_mini_mock_report_data
    from utils.mini_mock_state import count_mini_mock_analysis_completed, mini_mock_rows_sorted

    completed_n = count_mini_mock_analysis_completed()
    if completed_n != _MINI_MOCK_QUESTION_COUNT:
        st.session_state["mini_mock_page"] = "REPORT_PENDING"
        st.session_state["mini_mock_report_status"] = "pending_retry"
        _mini_mock_clear_analysis_guards()
        st.rerun()
        return

    if _mini_mock_detect_quota_failure():
        st.session_state["mini_mock_page"] = "REPORT_PENDING"
        st.session_state["mini_mock_report_status"] = "pending_retry"
        _mini_mock_mark_quota_pending()
        _mini_mock_clear_analysis_guards()
        st.rerun()
        return

    if st.session_state.pop("_mm_retry_pending", None):
        _mini_mock_begin_report_analysis(retrying=True)
        st.rerun()
        return

    render_top_bar("5분 진단", back_href="?nav=MOCK", eyebrow="미니 진단 리포트")
    st.markdown('<div class="mx-landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    rows = mini_mock_rows_sorted()
    report = build_mini_mock_report_data(rows)
    render_mini_mock_report(report)
    render_mini_mock_report_download(report, rows)
    render_mini_mock_report_actions(on_retry_pending=bool(report.get("has_pending")))

    if st.button("학습 방식 다시 선택", use_container_width=True, key="mm_report_back_portal"):
        reset_to_learning_portal()
        st.rerun()


def render_mini_mock_report_pending_page(mx: dict) -> None:
    if _is_mini_mock_v2_active():
        try:
            logger.debug("[MINI_MOCK_LEGACY] report_pending skipped — V2 active")
        except Exception:
            pass
        return
    from utils.mini_mock_state import count_mini_mock_saved_answers

    _mini_mock_clear_analysis_guards()
    render_top_bar("5분 진단", back_href="?nav=MOCK", eyebrow="미니 진단 리포트")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    saved_n = count_mini_mock_saved_answers()
    reason = str(st.session_state.get("mini_mock_pending_reason") or "")
    is_soft_delay = (
        reason in ("quota", "analysis_timeout", "stuck_analyzing")
        or _mini_mock_detect_quota_failure()
    )
    if _mini_mock_detect_quota_failure() and reason not in ("analysis_timeout", "stuck_analyzing"):
        st.session_state["mini_mock_pending_reason"] = "quota"
    title = "AI 분석 요청이 잠시 많아요"
    if is_soft_delay:
        body = (
            "3개 답변은 모두 안전하게 저장되어 있습니다.<br/>"
            "현재 AI 분석 요청이 많거나 응답이 지연되어 리포트 생성이 잠시 멈췄어요.<br/>"
            "잠시 후 다시 분석을 눌러 5분 진단 리포트를 받아보세요."
        )
        back_label = "학습하기로 돌아가기"
    else:
        title = "AI 분석을 다시 시도해야 해요"
        body = (
            "3개 답변은 모두 안전하게 저장되어 있습니다.<br/>"
            "현재 AI 분석 요청이 정상적으로 완료되지 않았어요.<br/>"
            "잠시 후 다시 분석을 눌러 5분 진단 리포트를 받아보세요."
        )
        back_label = "학습 방식 다시 선택"
    st.markdown(
        f"""
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">AI 분석</div>
          <div class="rv-title">{html.escape(title)}</div>
          <div class="rv-body">{body}</div>
          <div class="rv-meta"><span>저장된 답변 {saved_n}개</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if is_soft_delay:
        st.caption(
            "지금은 답변이 사라진 것이 아니라, AI 분석 요청만 잠시 대기 중입니다."
        )
    _render_mini_mock_saved_answers_list()
    _render_mini_mock_question_status_list()
    _render_mini_mock_api_debug_panel()
    if st.button(
        "AI 분석 다시 시도",
        type="primary",
        use_container_width=True,
        key="mm_report_retry_analysis",
    ):
        _mini_mock_begin_report_analysis(retrying=True)
        st.rerun()
    if st.button(back_label, use_container_width=True, key="mm_pending_back_portal"):
        reset_to_learning_portal()
        st.rerun()


def render_mini_mock_flow(mx: dict) -> None:
    """Legacy mini mock flow — bypassed when Mini Mock V2 is active. Kept, not deleted."""
    if _is_mini_mock_v2_active():
        from views.mini_mock_v2 import render_mini_mock_v2

        try:
            logger.debug("[MINI_MOCK_LEGACY] flow bypassed — V2 active")
        except Exception:
            pass
        render_mini_mock_v2()
        return
    ensure_mini_mock_state()
    _mirror_mini_mock_to_mx(mx)
    page = _mini_mock_page()
    q_idx = _mini_mock_question_index()
    _log_mini_mock_state(page=page, q_idx=q_idx)

    if q_idx >= _MINI_MOCK_QUESTION_COUNT and page in ("QUESTION", "SAVED"):
        if page not in ("READY_FOR_REPORT", "ANALYZING_REPORT", "REPORT", "REPORT_PENDING"):
            st.session_state["mini_mock_question_index"] = _MINI_MOCK_QUESTION_COUNT - 1
            st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
            st.session_state["mini_mock_report_status"] = "answers_saved"
            try:
                logger.info("[MINI_MOCK_READY_FOR_REPORT] reason=question_index_overflow")
            except Exception:
                pass
            st.rerun()
            return

    if page == "SAVED":
        render_mini_mock_saved_screen(mx)
        return
    if page == "READY_FOR_REPORT":
        render_mini_mock_ready_for_report_screen(mx)
        return
    if page == "ANALYZING_REPORT":
        _mini_mock_ensure_analyzing_clock()
        if _mini_mock_abort_analyzing_if_needed(mx):
            st.rerun()
            return
        try:
            logger.debug(
                "[MINI_MOCK_ANALYZING_ENTER] attempt=%s elapsed=%.1f",
                st.session_state.get(_MINI_MOCK_ANALYSIS_ATTEMPT_KEY),
                _mini_mock_analyzing_elapsed(),
            )
        except Exception:
            pass
        render_mini_mock_analyzing_screen(mx)
        run_mini_mock_report_analysis_once(mx)
        return
    if page == "REPORT_PENDING":
        render_mini_mock_report_pending_page(mx)
        return
    if page == "REPORT":
        render_mini_mock_report_page(mx)
        return
    if page == "QUESTION":
        render_mini_mock_question_page(mx)
        return

    try:
        logger.warning("[MINI_MOCK_STATE] unknown page=%s -> QUESTION", page)
    except Exception:
        pass
    render_mini_mock_question_page(mx)


def render_topic_practice_flow(mx: dict) -> None:
    from utils.topic_practice_state import all_topic_answers_saved

    ensure_topic_practice_state()
    _mirror_topic_practice_to_mx(mx)
    step = _normalize_topic_practice_step(_topic_practice_step() or "select_topic")
    _log_topic_state(step=step)

    if step == "select_topic":
        render_topic_selection(mx)
        return
    if step == "question":
        render_topic_practice_question_page(mx)
        return
    if step == "saved":
        render_topic_saved_screen(mx)
        return
    if step == "answers_saved":
        render_topic_answers_saved_page(mx)
        return
    if step == "analyzing_report":
        render_topic_analyzing_screen(mx)
        run_topic_report_analysis_once(mx)
        return
    if step == "report_pending":
        render_topic_report_pending_screen(mx)
        return
    if step == "report":
        render_topic_report(mx)
        return

    try:
        logger.warning("[TOPIC_STATE] unknown step=%s — recovering", step)
    except Exception:
        pass
    topic_id = st.session_state.get("selected_topic_id")
    if topic_id and all_topic_answers_saved(str(topic_id)):
        st.session_state["topic_practice_step"] = "answers_saved"
    else:
        st.session_state["topic_practice_step"] = "select_topic"
    st.rerun()


def render_resumable_landing(mx: dict) -> None:
    mode = _mock_mode(mx)
    mode_label = _mock_mode_label(mode)
    render_top_bar("모의고사", back_href="?nav=HOME", eyebrow=format_mock_attempt_label(mx))
    st.markdown('<div class="mx-landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_learning_portal_back_button(mx)

    st.markdown(
        f"""
        <section class="continue-card continue-card--resume mx-landing-card" role="region"
                 aria-label="모의고사 이어하기">
          <div class="cc-row-top">
            <div class="cc-eyebrow">이어하기</div>
          </div>
          <div class="cc-title">진행 중인 {html.escape(mode_label)}이 있어요.</div>
          <div class="cc-meta">중단한 지점부터 이어서 풀거나, 새로 시작할 수 있어요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("이어서 하기", type="primary", use_container_width=True, key="mx_resume_continue"):
            if mode:
                _set_mock_mode(mx, mode)
            mx["_resume_confirmed"] = True
            page = str(mx.get("mock_page") or "TEST").upper()
            if page not in ("TEST", "REPORT", "SURVEY"):
                page = "TEST"
            mx["mock_page"] = page
            try:
                st.query_params.clear()
                st.query_params["nav"] = "MOCK"
                st.query_params["mock"] = page
            except Exception:
                pass
            st.rerun()
    with c2:
        if st.button("새로 시작하기", use_container_width=True, key="mx_resume_fresh"):
            mx.pop("_resume_confirmed", None)
            _clear_in_progress_for_mode_pick(mx)
            _clear_mock_mode(mx)
            clear_mock_question_tts_keys()
            sync_user_progress(st.session_state)
            st.rerun()


def _is_analysis_failed(result, last_error: str) -> bool:
    if result is None:
        return True
    if not isinstance(result, dict):
        return True
    if (result.get("error") or "").strip():
        return True
    if result.get("diagnosis_status") == "api_error":
        return True
    if str(result.get("analysis_status") or "").lower() == "failed":
        return True
    return False


def _is_pending_result(res: dict) -> bool:
    if not isinstance(res, dict):
        return False
    if str(res.get("analysis_status") or "").lower() == "pending":
        return True
    return res.get("diagnosis_status") == "analysis_pending" or bool(res.get("analysis_pending"))


def _resolve_speech_issue_kind(lr: dict, mx: dict, audio_key: str) -> str:
    """Map stored result + preserved audio to ``no_audio`` | ``unclear_speech`` | ``no_speech``."""
    dst = str(lr.get("diagnosis_status") or "").lower()
    ast = str(lr.get("analysis_status") or "").lower()
    if dst == "no_audio" or ast == "no_audio":
        return "no_audio"
    if dst == "unclear_speech" or ast == "unclear_speech":
        return "unclear_speech"
    if dst in ("non_english", "language_mismatch") or ast == "non_english":
        return "non_english"
    if dst == "needs_review" or ast == "needs_review":
        return "needs_review"
    blob = mx.get("audio_bytes") or (mx.get("recordings") or {}).get(audio_key)
    nbytes = int(lr.get("source_audio_size_bytes") or 0) or recording_byte_length(blob)
    if dst == "no_speech" or ast == "no_speech" or lr.get("no_speech_detected"):
        return (
            "unclear_speech"
            if has_substantial_recording(blob) or nbytes >= MIN_RECORDED_AUDIO_BYTES
            else "no_speech"
        )
    if not is_real_speech_transcript((lr.get("transcript") or "").strip()):
        return (
            "unclear_speech"
            if has_substantial_recording(blob) or nbytes >= MIN_RECORDED_AUDIO_BYTES
            else "no_audio"
        )
    return "ok"


def _render_speech_issue_hero(
    mx: dict,
    audio_key: str,
    lr: dict,
    *,
    q_label: int | None = None,
    blob: bytes | None = None,
    q_index: int | None = None,
) -> str:
    """Recovery / feedback card for no-audio vs unclear speech. Returns issue kind."""
    issue = _resolve_speech_issue_kind(lr, mx, audio_key)
    if issue == "ok":
        issue = "no_speech"
    if issue == "non_english":
        from utils.language_detection import language_mismatch_body, language_mismatch_title

        kind = str(lr.get("language_mismatch_kind") or "korean")
        eyebrow, title, body = (
            "언어 안내",
            language_mismatch_title(kind),
            language_mismatch_body(kind),
        )
    else:
        eyebrow, title, body = speech_issue_copy(issue)
    nbytes = int(lr.get("source_audio_size_bytes") or 0) or recording_byte_length(
        blob or mx.get("audio_bytes") or (mx.get("recordings") or {}).get(audio_key)
    )
    q_part = f"Q{q_label} · " if q_label is not None else ""
    meta_html = ""
    if issue in ("unclear_speech", "needs_review", "non_english", "no_speech", "no_audio") and nbytes > 0 and st.session_state.get("show_dev_debug"):
        meta_html = (
            f'<div class="mx-rh-meta">'
            f'<span class="mx-rh-chip">[dev] 녹음 저장됨 · {html.escape(f"{nbytes:,}")} bytes</span>'
            f"</div>"
        )
    st.markdown(
        f"""
        <section class="mx-report-hero" role="alert">
          <p class="mx-rh-eyebrow">{html.escape(q_part)}{html.escape(eyebrow)}</p>
          <div class="mx-rh-title">{html.escape(title)}</div>
          <div class="mx-rh-transcript">{html.escape(body)}</div>
          {meta_html}
        </section>
        """,
        unsafe_allow_html=True,
    )
    if issue == "non_english":
        render_language_mismatch_preview(lr)
    render_recording_debug_block(mx, audio_key, lr, q_index=q_index, blob=blob)
    return issue


def _go_to_next_question(mx: dict, q_id: int) -> None:
    """Advance after a saved answer (pending or completed) without losing data."""
    if _is_real_mock(mx):
        go_to_next_real_mock_question(mx, from_q_id=int(q_id))
        return

    from components.answer_recording import reset_recording_ui_for_question

    reset_recording_timer()
    reconcile_mock_exam_pointer(mx)
    mx["audio_bytes"] = None
    mx["preview_transcript"] = None
    clear_pending_recovery(mx)
    if is_last_mock_question(mx, q_id):
        mark_mock_exam_completed(mx, st.session_state)
    else:
        mx["mock_page"] = "TEST"
        st.session_state["mock_page"] = "TEST"
    st.rerun()


def retry_stored_answer_analysis(mx: dict, q_id: int) -> None:
    """Re-run Gemini for one saved row (final report / pending card). No duplicate rows."""
    row = find_result_row(mx, int(q_id))
    if not row:
        st.warning("저장된 답변을 찾을 수 없습니다.")
        return
    exam = mx.get("current_exam") or mx.get("exam") or []
    q = None
    for item in exam:
        if isinstance(item, dict) and int(item.get("id", -1)) == int(q_id):
            q = item
            break
    if not q:
        st.warning("문항 정보를 찾을 수 없습니다.")
        return
    audio_key = (row.get("audio_key") or f"q_{q_id}").strip()
    api_key = get_gemini_api_key()
    if not api_key:
        st.error("Gemini API Key가 없어 다시 시도할 수 없습니다.")
        return
    blob = stored_audio_for_row(mx, row)
    if not blob:
        st.warning("저장된 녹음이 없어 다시 분석할 수 없습니다.")
        return
    mx["audio_bytes"] = blob
    _run_analysis(mx, q, int(q_id), audio_key, api_key, from_retry=True)


def _mock_query_param() -> str | None:
    v = st.query_params.get("mock")
    if isinstance(v, list):
        return v[0] if v else None
    return v


def _should_show_completed_final_report(mx: dict) -> bool:
    """True when the user explicitly opens the final report (not the completion card)."""
    if mx.get("_final_report_demo"):
        return True
    view_flag = bool(
        mx.get("_view_completed_report")
        or st.session_state.get("_view_completed_report")
    )
    if not view_flag:
        return False
    if is_completed_mock(mx):
        return True
    return bool(mx.get("results") or mx.get("analytics_cache"))


def _open_completed_final_report(mx: dict) -> None:
    """User chose 최종 리포트 보기 — keep attempt data, open full report."""
    try:
        logger.debug("[REAL_MOCK_COMPLETE] final_report_button_clicked")
    except Exception:
        pass
    mark_real_mock_exam_completed(mx, st.session_state, preserve_report_view=True)
    mx["_view_completed_report"] = True
    st.session_state["_view_completed_report"] = True
    try:
        st.query_params.clear()
        st.query_params["nav"] = "MOCK"
        st.query_params["mock"] = "FINAL"
    except Exception:
        pass


def _return_to_learning_portal_from_complete(mx: dict) -> None:
    """Leave completion/report UI without wiping the saved attempt."""
    try:
        logger.debug("[REAL_MOCK_COMPLETE] returning_to_portal")
    except Exception:
        pass
    mx.pop("_view_completed_report", None)
    st.session_state.pop("_view_completed_report", None)
    reset_to_learning_portal()


def render_completed_exam_landing(mx: dict) -> None:
    """After a full mock exam — start a new attempt or open the previous report."""
    att = int(mx.get("attempt_no") or 1)
    render_top_bar("모의고사", back_href="?nav=HOME", eyebrow=format_mock_attempt_label(mx))
    st.markdown('<div class="mx-landing-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    st.markdown(
        f"""
        <section class="continue-card continue-card--start mx-landing-card" role="region"
                 aria-label="모의고사 완료">
          <div class="cc-row-top">
            <div class="cc-eyebrow">완료</div>
          </div>
          <div class="cc-title">이전 연습이 완료되었습니다.</div>
          <div class="cc-meta">{att}회 모의고사를 마쳤어요. 새 연습을 시작하거나 이전 리포트를 볼 수 있어요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if st.button("새 연습 시작하기", type="primary", use_container_width=True, key="mx_landing_new_attempt"):
        if _begin_new_practice_from_completed(mx):
            clear_mock_question_tts_keys()
            sync_user_progress(st.session_state)
            try:
                st.query_params.clear()
                st.query_params["nav"] = "MOCK"
                st.query_params["mock"] = "PICK"
            except Exception:
                pass
            st.rerun()
        else:
            st.error("설문 데이터가 없으면 새 시험을 시작할 수 없습니다. 설정에서 설문을 다시 진행해 주세요.")

    if st.button("이전 리포트 보기", use_container_width=True, key="mx_landing_prev_report"):
        mx["_view_completed_report"] = True
        st.session_state["_view_completed_report"] = True
        mx["mock_page"] = "FINAL"
        st.session_state["mock_page"] = "FINAL"
        try:
            st.query_params.clear()
            st.query_params["nav"] = "MOCK"
            st.query_params["mock"] = "FINAL"
        except Exception:
            pass
        st.rerun()


def render_mock_exam_shell() -> None:
    mx = mock_session()
    _sync_mock_routing_state(mx)

    page = _get_mock_page(mx)
    if page not in {
        "PICK",
        "TOPIC",
        "TOPIC_V2",
        "MINI_MOCK",
        "SURVEY",
        "TEST",
        "REPORT",
        "FINAL",
    }:
        _set_mock_page(mx, "PICK")
        page = "PICK"

    if page == "SURVEY" and not _practice_portal_selected():
        _set_mock_page(mx, "PICK")
        page = "PICK"

    if page == "TOPIC" and not _practice_portal_selected():
        _set_mock_page(mx, "PICK")
        page = "PICK"

    if page == "MINI_MOCK" and not _practice_portal_selected():
        _set_mock_page(mx, "PICK")
        page = "PICK"

    mock_q = _mock_query_param()
    if mock_q == "PICK" and not _practice_portal_selected():
        _set_mock_page(mx, "PICK")

    if (
        _get_mock_page(mx) == "SURVEY"
        and has_resumable_exam(mx)
        and _mock_mode(mx) == "real_mock"
        and _practice_portal_selected()
    ):
        _set_mock_page(mx, "TEST")

    if mx.get("current_exam") and not is_completed_mock(mx):
        if _is_real_mock(mx):
            if not _real_mock_defer_reconcile():
                reconcile_mock_exam_pointer(mx)
        else:
            reconcile_mock_exam_pointer(mx)

    if "mock_data" not in st.session_state:
        st.session_state.mock_data = {"recording_active": False}
    _active_key = st.session_state.get("recording_active_audio_key")
    _rec = mx.get("recordings") if isinstance(mx.get("recordings"), dict) else {}
    st.session_state.mock_data["recording_active"] = bool(
        _active_key and get_saved_audio_for_key(_rec, str(_active_key))
    )


def render_mock_flow() -> None:
    mx = mock_session()
    _sync_mock_routing_state(mx)
    sync_settings_to_legacy(st.session_state)

    _pv = st.query_params.get("preview_final")
    if isinstance(_pv, list):
        _pv = _pv[0] if _pv else None
    if _pv == "1" and not mx.get("_demo_preview_loaded"):
        from services.final_report_demo import open_demo_final_report

        open_demo_final_report(mx)
        mx["_demo_preview_loaded"] = True
        try:
            del st.query_params["preview_final"]
        except Exception:
            pass
        st.rerun()

    if not _practice_portal_selected():
        render_learning_portal(mx)
        return

    if _redirect_hidden_coaching_mode():
        return

    mode = _session_mock_mode() or _mock_mode(mx)

    if mode == "script_coaching":
        from views.script_coaching import render_script_coaching

        render_script_coaching()
        return

    if mode == "topic_practice_v2":
        from views.topic_practice_v2 import render_topic_practice_v2

        render_topic_practice_v2()
        return

    if mode == "topic_practice":
        render_topic_practice_flow(mx)
        return

    if _is_mini_mock_v2_active() or mode == "mini_mock":
        from views.mini_mock_v2 import (
            begin_mini_mock_v2_session,
            render_mini_mock_v2,
        )

        if mode == "mini_mock" and not _is_mini_mock_v2_active():
            begin_mini_mock_v2_session(mx)
        render_mini_mock_v2()
        return

    if mode == "mock_v2":
        from views.mock_v2 import render_mock_v2

        render_mock_v2()
        return

    if mode == "real_mock":
        _rm_page = _real_mock_page()
        if (
            is_completed_mock(mx)
            and not _should_show_completed_final_report(mx)
            and _rm_page not in (
                "FINAL_PREVIEW",
                "FINAL_ANALYZING",
                "FINAL_READY",
                "ANSWER_SAVED",
                "SPEECH_RECOVERY",
                "ANALYSIS_PENDING",
                "QUESTION",
                "RECOVERY",
            )
            and _get_mock_page(mx) != "FINAL"
        ):
            render_completed_exam_landing(mx)
            return
        _render_real_mock_flow(mx)
        return

    # Legacy / unknown mode — show portal again.
    st.session_state["practice_portal_selected"] = False
    render_learning_portal(mx)


def _render_survey(mx: dict) -> None:
    _render_learning_portal_back_button(mx)
    st.title("📋 Background Survey")
    st.write("당신의 상황에 맞는 답변을 선택해주세요. 이 선택에 따라 문제가 출제됩니다.")
    # The "final report preview" button seeds synthetic demo transcripts
    # into the session — useful for developers iterating on the report UI
    # but a trust risk in production (users could mistake demo content for
    # their own results). Gate behind ``OPIC_DEBUG_DEMO=1`` so the button
    # is hidden from real users while the ``?preview_final=1`` URL still
    # works for the developer who knows about it.
    import os

    if os.getenv("OPIC_DEBUG_DEMO") == "1":
        d1, d2 = st.columns([1, 2])
        with d1:
            if st.button(
                "📋 종합 리포트 미리보기 (데모)",
                help="녹음·시험 없이 최종 진단 리포트 화면만 확인합니다.",
                key="btn_preview_final_demo",
            ):
                from services.final_report_demo import open_demo_final_report

                open_demo_final_report(mx)
                st.rerun()
        with d2:
            st.caption("모의고사 탭에서 주소 끝에 `?preview_final=1` 을 붙여도 같은 미리보기로 이동합니다.")

    with st.container(border=True):
        st.subheader("🎚️ Self-Assessment (난이도 설정)")
        _sett = settings_session()
        difficulty = st.radio(
            "난이도",
            [5, 6],
            index=0 if int(_sett.get("difficulty", 5)) == 5 else 1,
            format_func=lambda v: (
                "레벨 5 (IH 목표): 유창한 발화와 시제 관리를 집중적으로 훈련합니다."
                if v == 5
                else "레벨 6 (AL 목표): 완벽한 시제 일관성과 고난도 시사 이슈 대응력을 평가합니다."
            ),
            horizontal=True,
            key="difficulty_survey",
        )
        _sett["difficulty"] = int(difficulty)
        sync_settings_to_legacy(st.session_state)

        col_left, col_right = st.columns(2)

        with col_left:
            st.markdown("<p class='survey-label'>1. 현재 귀하는 어느 분야에 종사하고 계십니까?</p>", unsafe_allow_html=True)
            work = st.radio(
                "직업/신분",
                ["사업·회사원", "교직자", "학생(학위 과정 중)", "군인", "일하지 않음"],
                label_visibility="collapsed",
                key="survey_work",
            )

            st.markdown("<p class='survey-label'>2. 현재 귀하는 어디에 살고 계십니까?</p>", unsafe_allow_html=True)
            housing = st.radio(
                "주거",
                ["홀로 거주", "가족과 함께 거주", "친구/룸메이트와 거주"],
                label_visibility="collapsed",
                key="survey_housing",
            )

            _leisure_opts = [
                "영화 보기",
                "클럽/나이트클럽 가기",
                "공연 보기",
                "콘서트 보기",
                "박물관 가기",
                "공원 가기",
                "캠핑 하기",
                "해변 가기",
                "게임 하기",
                "SNS/블로그에 글 올리기",
                "피규어 만들기",
            ]
            if "survey_leisure" not in st.session_state:
                st.session_state["survey_leisure"] = ["영화 보기", "공원 가기"]

            def _survey_leisure_body() -> None:
                st.multiselect(
                    "여가 활동",
                    _leisure_opts,
                    default=st.session_state.get("survey_leisure", ["영화 보기", "공원 가기"]),
                    key="survey_leisure",
                )

            render_collapsible_section(
                "3) 여가 활동",
                "survey_leisure",
                _survey_leisure_body,
                default_open=True,
                css_scope="mx-survey",
            )
            leisure = list(st.session_state.get("survey_leisure") or [])

        with col_right:
            if "survey_interests" not in st.session_state:
                st.session_state["survey_interests"] = ["음악 감상하기", "요리하기"]

            def _survey_interests_body() -> None:
                st.multiselect(
                    "취미/관심사",
                    ["음악 감상하기", "악기 연주하기", "요리하기", "혼자 노래 부르기", "글쓰기", "그림 그리기"],
                    default=st.session_state.get("survey_interests", []),
                    key="survey_interests",
                )

            render_collapsible_section(
                "4) 취미/관심사",
                "survey_interests",
                _survey_interests_body,
                default_open=True,
                css_scope="mx-survey",
            )
            interests = list(st.session_state.get("survey_interests") or [])

            if "survey_sports" not in st.session_state:
                st.session_state["survey_sports"] = ["조깅", "걷기"]

            def _survey_sports_body() -> None:
                st.multiselect(
                    "운동",
                    [
                        "조깅",
                        "걷기",
                        "자전거",
                        "수영",
                        "테니스",
                        "축구",
                        "농구",
                        "야구",
                        "골프",
                        "헬스(Gym)",
                        "요가",
                        "운동을 전혀 하지 않음",
                    ],
                    default=st.session_state.get("survey_sports", []),
                    key="survey_sports",
                )

            render_collapsible_section(
                "5) 운동",
                "survey_sports",
                _survey_sports_body,
                default_open=True,
                css_scope="mx-survey",
            )
            sports = list(st.session_state.get("survey_sports") or [])

            if "survey_travel" not in st.session_state:
                st.session_state["survey_travel"] = ["국내 여행"]

            def _survey_travel_body() -> None:
                st.multiselect(
                    "여행",
                    ["국내 여행", "해외 여행", "집에서 보내는 휴가(스테이케이션)"],
                    default=st.session_state.get("survey_travel", []),
                    key="survey_travel",
                )

            render_collapsible_section(
                "6) 여행",
                "survey_travel",
                _survey_travel_body,
                default_open=True,
                css_scope="mx-survey",
            )
            travel = list(st.session_state.get("survey_travel") or [])

    selected_count = len(leisure) + len(interests) + len(sports) + len(travel)
    st.info(f"현재 선택한 항목 개수: **{selected_count} / 12**")
    enough_selected = selected_count >= 12
    if not enough_selected:
        st.warning("항목을 12개 이상 선택해야 시험을 시작할 수 있습니다.")

    if st.button("시험지 생성 및 시험 시작", disabled=not enough_selected):
        mx["audio_bytes"] = None
        mx["exam_finished"] = False
        mx.pop("_final_report_demo", None)
        mx.pop("_demo_preview_loaded", None)
        # Defensive: a failed analysis from a previous attempt should never
        # carry into a freshly generated exam. ``reset_exam_state`` would
        # also clear this, but the survey-start path is reached from inside
        # the mock view (no URL reset) so we wipe it here explicitly.
        clear_pending_recovery(mx)
        for k in (
            "final_report_generated",
            "overall_estimated_level",
            "analytics_cache",
            "downloadable_report_bytes",
            "_analytics_sig",
            "_show_exam_celebration",
        ):
            mx.pop(k, None)
        mx["survey_results"] = {
            "work": work,
            "housing": housing,
            "leisure": leisure,
            "interests": interests,
            "sports": sports,
            "travel": travel,
            "difficulty": int(settings_session()["difficulty"]),
        }
        mx["survey_completed"] = True
        mx.setdefault("attempt_no", 1)
        _exam = generate_test_set(
            mx["survey_results"],
            difficulty=int(settings_session()["difficulty"]),
        )
        mx["current_exam"] = _exam
        mx["exam"] = _exam
        mx["current_idx"] = 0
        mx["results"] = []
        mx["last_result"] = None
        mx["question_play_counts"] = {}
        mx["exam_listen_nonce"] = secrets.token_hex(8)
        # Resume-mode timestamps — the home "이어하기" card uses these.
        _now = iso_now()
        mx["exam_started_at"] = _now
        mx["exam_last_seen_at"] = _now
        clear_mock_question_tts_keys()
        mx["mock_page"] = "TEST"
        st.rerun()


def _mock_tts_session_keys(q_id: int, voice_id: str) -> tuple[str, str, str]:
    mock_err_key = f"_mock_q_tts_err_{q_id}"
    pref_key = f"_mock_tts_pref_{q_id}_{voice_id}"
    fail_key = f"_mock_pref_fail_{q_id}"
    return mock_err_key, pref_key, fail_key


def _load_mock_question_tts(q_text: str, voice_id: str, q_id: int) -> dict | None:
    """Fetch question TTS into session state. Call only from button/fragment — never block first paint."""
    mock_err_key, pref_key, fail_key = _mock_tts_session_keys(q_id, voice_id)
    cached = st.session_state.get(pref_key)
    if isinstance(cached, dict) and cached.get("audio_bytes"):
        return cached
    if st.session_state.get(fail_key):
        return None
    try:
        payload = tts_audio_cached(
            q_text,
            voice_id,
            DEFAULT_TTS_SPEAKING_RATE,
            DEFAULT_TTS_PITCH,
        )
        st.session_state[pref_key] = payload
        st.session_state.pop(mock_err_key, None)
        return payload if isinstance(payload, dict) else None
    except Exception as e:
        st.session_state[fail_key] = True
        st.session_state[mock_err_key] = str(e)
        logger.warning("Mock exam TTS load failed: %s: %s", type(e).__name__, e)
        return None


def _render_mock_question_audio_when_ready(
    mx: dict,
    q_id: int,
    payload: dict,
    *,
    compact: bool = False,
) -> None:
    if not compact:
        st.markdown(
            '<p class="mx-listen-ready-label">질문 듣기</p>',
            unsafe_allow_html=True,
        )
    render_exam_question_audio_player(
        payload["audio_bytes"],
        payload.get("audio_format", "audio/mp3"),
        str(mx["exam_listen_nonce"]),
        int(q_id),
        max_plays=2,
    )


def _render_mock_question_text_only(q: dict) -> None:
    """Text-only question body — live question TTS disabled until static mp3 is added."""
    question_en = html.escape(str(q.get("question") or q.get("question_en") or ""))
    question_ko = html.escape(
        str(q.get("question_ko") or q.get("question_hint") or q.get("helper_ko") or "")
    )
    ko_row = f'<p class="tq-question-ko">{question_ko}</p>' if question_ko else ""
    st.markdown(
        f"""
        <div class="mx-question-card mx-question-text-only" role="region" aria-label="문항">
          <p class="mx-question-topic">{question_en or "—"}</p>
          {ko_row}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_mock_question_listen_stage(
    mx: dict, q: dict, q_id: int, *, compact: bool = False
) -> None:
    """Listen UI — never blocks the record stage; TTS loads lazily."""
    q_text = q["question"]
    voice_id = neural2_voice_for_session()
    mock_err_key, pref_key, fail_key = _mock_tts_session_keys(q_id, voice_id)

    if compact:
        st.markdown(
            '<div class="mx-listen-compact" role="region" aria-label="질문 음성">',
            unsafe_allow_html=True,
        )
        st.markdown(
            '<p class="mx-listen-compact-label">질문 음성</p>',
            unsafe_allow_html=True,
        )
        err_msg = st.session_state.get(mock_err_key)
        if err_msg:
            if st.button("▶ 질문 듣기", key=f"mock_listen_retry_{q_id}"):
                st.session_state.pop(fail_key, None)
                st.session_state.pop(pref_key, None)
                st.session_state.pop(mock_err_key, None)
                st.session_state.pop(f"_mock_tts_frag_pass_{q_id}_{voice_id}", None)
                st.rerun()
        else:
            payload = st.session_state.get(pref_key)
            if isinstance(payload, dict) and payload.get("audio_bytes"):
                _render_mock_question_audio_when_ready(
                    mx, q_id, payload, compact=True
                )
            else:
                st.caption("질문 음성 불러오는 중...")
                if st.button("▶ 질문 듣기", key=f"mock_listen_load_{q_id}"):
                    with st.spinner("질문 음성 불러오는 중…"):
                        _load_mock_question_tts(q_text, voice_id, q_id)
                    st.rerun()
                _maybe_auto_prefetch_mock_question_tts(mx, q_id, q_text, voice_id)
        st.caption("최대 2회 재생 가능")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    st.markdown(
        '<div class="mx-listen-stage">'
        '<span class="mx-stage-eyebrow">음성 듣기 · 최대 2회</span>',
        unsafe_allow_html=True,
    )

    err_msg = st.session_state.get(mock_err_key)
    if err_msg:
        st.markdown(
            f'<div class="mx-status mx-status--error">'
            f'<span class="mx-status-icon">⚠️</span>'
            f'<span>질문 음성을 만들 수 없습니다.<br>{html.escape(err_msg)}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        if st.button("다시 시도", key=f"mock_tts_retry_{q_id}"):
            st.session_state.pop(fail_key, None)
            st.session_state.pop(pref_key, None)
            st.session_state.pop(mock_err_key, None)
            st.session_state.pop(f"_mock_tts_frag_pass_{q_id}_{voice_id}", None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        return

    payload = st.session_state.get(pref_key)
    if isinstance(payload, dict) and payload.get("audio_bytes"):
        _render_mock_question_audio_when_ready(mx, q_id, payload)
    else:
        st.markdown(
            '<div class="mx-listen-prep">'
            "질문 음성을 준비 중이에요. 잠시 후 다시 눌러 주세요."
            "</div>",
            unsafe_allow_html=True,
        )
        if st.button("질문 듣기", key=f"mock_listen_load_{q_id}"):
            with st.spinner("질문 음성을 준비하는 중…"):
                _load_mock_question_tts(q_text, voice_id, q_id)
            st.rerun()
        _maybe_auto_prefetch_mock_question_tts(mx, q_id, q_text, voice_id)

    st.markdown("</div>", unsafe_allow_html=True)


def _maybe_auto_prefetch_mock_question_tts(
    mx: dict,
    q_id: int,
    q_text: str,
    voice_id: str,
) -> None:
    """Background TTS in a fragment so the main page (recorder) paints first."""
    if _is_real_mock(mx) and _real_mock_defer_reconcile():
        return
    if not hasattr(st, "fragment"):
        return
    _, pref_key, fail_key = _mock_tts_session_keys(q_id, voice_id)
    if pref_key in st.session_state or st.session_state.get(fail_key):
        return
    try:
        from datetime import timedelta

        run_every = timedelta(milliseconds=800)
    except Exception:
        return

    pass_key = f"_mock_tts_frag_pass_{q_id}_{voice_id}"

    def _auto_prefetch_listen_audio() -> None:
        _, pref_key, fail_key = _mock_tts_session_keys(q_id, voice_id)
        payload = st.session_state.get(pref_key)
        if isinstance(payload, dict) and payload.get("audio_bytes"):
            return
        if st.session_state.get(fail_key):
            return
        passes = int(st.session_state.get(pass_key) or 0)
        st.session_state[pass_key] = passes + 1
        if passes < 1:
            return
        with st.spinner("질문 음성을 준비하는 중…"):
            loaded = _load_mock_question_tts(q_text, voice_id, q_id)
        if isinstance(loaded, dict) and loaded.get("audio_bytes"):
            return

    try:
        frag = st.fragment(run_every=run_every)(_auto_prefetch_listen_audio)
    except TypeError:
        return
    frag()


def _real_mock_maybe_post_record_empty_fallback(
    mx: dict,
    q: dict,
    q_id: int,
    audio_key: str,
    *,
    q_index: int,
    timer_key: str,
    mic_key: str,
    rec: dict,
) -> bool:
    """Safety net when mic stop produced no blob and component path did not commit."""
    if _real_mock_page() != "QUESTION":
        return False
    if find_result_row(mx, int(q_id)):
        return False
    if get_saved_audio_for_key(rec, audio_key):
        return False
    active = st.session_state.get("recording_active_audio_key")
    if active and str(active) != str(audio_key):
        return False
    guard = real_mock_empty_commit_guard_key(timer_key, audio_key)
    has_saved = bool(get_saved_audio_for_key(rec, audio_key))
    ui_state = get_recording_ui_state(timer_key, has_saved=has_saved)
    stale_saved_ui = ui_state == STATE_SAVED and not has_saved
    if st.session_state.get(guard) and not stale_saved_ui:
        return False
    if st.session_state.get(guard) and stale_saved_ui:
        st.session_state.pop(guard, None)

    mic_stop_completed = bool(st.session_state.get(f"{timer_key}_mic_stop_completed"))
    mic_had_return = bool(st.session_state.get(f"{timer_key}_mic_had_return"))
    try:
        mount_id = int(st.session_state.get(f"{timer_key}_mic_id_at_mount") or 0)
        current_id = int(st.session_state.get("_last_mic_recorder_audio_id") or 0)
    except (TypeError, ValueError):
        mount_id = 0
        current_id = 0
    id_advanced = current_id > mount_id

    if not stale_saved_ui and not mic_stop_completed and not id_advanced and not mic_had_return:
        return False
    if (
        not stale_saved_ui
        and ui_state not in (STATE_RECORDED, STATE_SAVED)
        and not mic_stop_completed
        and not id_advanced
        and not mic_had_return
    ):
        return False

    try:
        logger.warning(
            "[REAL_MOCK_EMPTY_COMMIT_FALLBACK] q_idx=%s q_id=%s reason=post_record_no_blob_fallback "
            "ui_state=%s mic_stop=%s id_advanced=%s",
            q_index,
            q_id,
            ui_state,
            mic_stop_completed,
            id_advanced,
        )
    except Exception:
        pass
    st.session_state[guard] = True
    try:
        _real_mock_commit_empty_audio(
            mx,
            q,
            q_id,
            audio_key,
            q_index=q_index,
            reason="post_record_no_blob_fallback",
            blob=b"",
        )
    except Exception:
        st.session_state.pop(guard, None)
        raise
    st.rerun()
    return True


def _real_mock_commit_empty_audio(
    mx: dict,
    q: dict,
    q_id: int,
    audio_key: str,
    *,
    q_index: int | None = None,
    reason: str = "empty_audio",
    blob: bytes | None = None,
) -> bool:
    """Persist no-audio / insufficient row and route to SPEECH_RECOVERY — no Gemini."""
    from components.answer_recording import STATE_SAVED, set_recording_ui_state

    q_index = int(q_index if q_index is not None else mx.get("current_idx") or 0)
    safe_blob = bytes(blob) if blob else b""
    nbytes = recording_byte_length(safe_blob)
    try:
        logger.warning(
            "[REAL_MOCK_EMPTY_AUDIO] q_idx=%s q_id=%s audio_key=%s blob_none=%s "
            "audio_len=%s reason=%s",
            q_index,
            q_id,
            audio_key,
            blob is None,
            nbytes,
            reason,
        )
    except Exception:
        pass

    rec = mx.setdefault("recordings", {})
    if not isinstance(rec, dict):
        rec = {}
        mx["recordings"] = rec
    if nbytes > 0:
        rec[audio_key] = safe_blob
        mx["audio_bytes"] = safe_blob
    else:
        mx["audio_bytes"] = None

    timer_key, _ = build_recording_keys("real_mock", str(q_id), q_index)
    set_recording_ui_state(timer_key, STATE_SAVED)
    _set_real_mock_saved_q_id(mx, int(q_id))
    st.session_state.pop(_real_mock_saved_confirm_key(int(q_id)), None)
    st.session_state[real_mock_empty_commit_guard_key(timer_key, audio_key)] = True

    if nbytes == 0:
        apply_no_audio_result(
            mx,
            q,
            q_id=int(q_id),
            question_index=q_index,
            audio_key=audio_key,
            source_audio_size_bytes=0,
        )
        row0 = find_result_row(mx, int(q_id))
        if isinstance(row0, dict):
            res0 = row0.get("result")
            if isinstance(res0, dict):
                res0["estimated_level"] = "응답 부족"
                res0["estimated_level_display"] = "응답 부족"
                res0["is_gradable"] = False
                res0["is_answered"] = True
    else:
        save_real_mock_unanalyzed_answer(
            mx,
            q,
            q_id=int(q_id),
            question_index=q_index,
            audio_key=audio_key,
            audio_bytes=safe_blob,
        )
        apply_insufficient_response_result(
            mx,
            q,
            q_id=int(q_id),
            question_index=q_index,
            audio_key=audio_key,
            source_audio_size_bytes=nbytes,
        )

    clear_pending_recovery(mx)
    _arm_real_mock_post_save(mx, "SPEECH_RECOVERY")
    _set_mock_page(mx, "TEST")
    st.session_state["mock_page"] = "TEST"
    try:
        logger.debug(
            "[REAL_MOCK_EMPTY_COMMIT] q_idx=%s q_id=%s page=SPEECH_RECOVERY "
            "result_saved=True",
            q_index,
            q_id,
        )
    except Exception:
        pass
    return True


def _real_mock_commit_saved_answer(
    mx: dict,
    q: dict,
    q_id: int,
    audio_key: str,
    blob: bytes,
) -> bool:
    from components.answer_recording import STATE_SAVED, set_recording_ui_state

    q_index = int(mx.get("current_idx") or 0)
    nbytes = recording_byte_length(blob)
    rec = mx.setdefault("recordings", {})
    if not isinstance(rec, dict):
        rec = {}
        mx["recordings"] = rec
    rec[audio_key] = blob
    mx["audio_bytes"] = blob
    timer_key, _ = build_recording_keys("real_mock", str(q_id), q_index)
    set_recording_ui_state(timer_key, STATE_SAVED)
    _set_real_mock_saved_q_id(mx, int(q_id))
    st.session_state.pop(_real_mock_saved_confirm_key(int(q_id)), None)

    if classify_pre_analysis_blob(blob) == "no_audio":
        apply_no_audio_result(
            mx,
            q,
            q_id=int(q_id),
            question_index=q_index,
            audio_key=audio_key,
            source_audio_size_bytes=nbytes,
        )
        mark_pending_recovery(
            mx,
            q_id=int(q_id),
            audio_key=audio_key,
            error_message=NO_AUDIO_ERROR_SENTINEL,
            attempts=0,
        )
        _arm_real_mock_post_save(mx, "SPEECH_RECOVERY")
        try:
            logger.debug(
                "[REAL_MOCK_SPEECH_RECOVERY] q_idx=%s audio_len=%s reason=no_audio",
                q_index,
                nbytes,
            )
        except Exception:
            pass
        return True

    if classify_pre_gemini_speech(blob) == "no_speech":
        save_real_mock_unanalyzed_answer(
            mx,
            q,
            q_id=int(q_id),
            question_index=q_index,
            audio_key=audio_key,
            audio_bytes=blob,
        )
        apply_insufficient_response_result(
            mx,
            q,
            q_id=int(q_id),
            question_index=q_index,
            audio_key=audio_key,
            source_audio_size_bytes=nbytes,
        )
        from utils.exam_state import apply_stt_to_mock_exam_saved_row
        from utils.speech_recording import resolve_mime_for_analysis

        apply_stt_to_mock_exam_saved_row(
            mx,
            q,
            q_id=int(q_id),
            question_index=q_index,
            audio_key=audio_key,
            audio_bytes=blob,
            mime_type=resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key),
        )
        clear_pending_recovery(mx)
        _arm_real_mock_post_save(mx, "SPEECH_RECOVERY")
        try:
            logger.debug(
                "[REAL_MOCK_SPEECH_RECOVERY] q_idx=%s audio_len=%s reason=no_speech",
                q_index,
                nbytes,
            )
        except Exception:
            pass
        return True

    save_real_mock_unanalyzed_answer(
        mx,
        q,
        q_id=int(q_id),
        question_index=q_index,
        audio_key=audio_key,
        audio_bytes=blob,
    )
    from utils.exam_state import apply_stt_to_mock_exam_saved_row
    from utils.speech_recording import resolve_mime_for_analysis

    apply_stt_to_mock_exam_saved_row(
        mx,
        q,
        q_id=int(q_id),
        question_index=q_index,
        audio_key=audio_key,
        audio_bytes=blob,
        mime_type=resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key),
    )
    clear_pending_recovery(mx)
    _arm_real_mock_post_save(mx, "ANSWER_SAVED")
    try:
        logger.debug(
            "[REAL_MOCK_RECORD] q_id=%s audio_len=%s route=ANSWER_SAVED",
            q_id,
            nbytes,
        )
    except Exception:
        pass
    return True


def _real_mock_current_question(mx: dict) -> tuple[dict, dict, int, str] | None:
    exam = mx.get("current_exam") or mx.get("exam") or []
    if not exam:
        return None
    q_index = int(mx.get("current_idx") or 0)
    q = exam[min(q_index, len(exam) - 1)]
    if not isinstance(q, dict):
        return None
    q_id = int(q.get("id", q_index + 1))
    return q, q, q_id, f"q_{q_id}"


def _real_mock_ctx_from_result_row(
    mx: dict, row: dict, exam: list
) -> tuple[dict, dict, int, str] | None:
    if not isinstance(row, dict) or not exam:
        return None
    try:
        q_id = int(row.get("q_id", 0))
    except (TypeError, ValueError):
        q_id = 0
    if q_id <= 0:
        return None
    for i, item in enumerate(exam):
        if not isinstance(item, dict):
            continue
        try:
            item_id = int(item.get("id", i + 1))
        except (TypeError, ValueError):
            continue
        if item_id == q_id:
            return item, item, q_id, f"q_{q_id}"
    try:
        q_index = int(row.get("question_index", 0))
    except (TypeError, ValueError):
        q_index = 0
    if 0 <= q_index < len(exam) and isinstance(exam[q_index], dict):
        q = exam[q_index]
        return q, q, q_id, f"q_{q_id}"
    return None


def _real_mock_screen_question_ctx(mx: dict) -> tuple[dict, dict, int, str] | None:
    """Question for SPEECH_RECOVERY / ANSWER_SAVED — prefer last saved q_id over current_idx."""
    exam = mx.get("current_exam") or mx.get("exam") or []
    if not isinstance(exam, list) or not exam:
        results = mx.get("results") or []
        if isinstance(results, list) and results:
            last = results[-1]
            if isinstance(last, dict):
                return _real_mock_ctx_from_result_row(mx, last, exam)
        return None

    saved_q = _get_real_mock_saved_q_id(mx)
    if saved_q is not None:
        for i, item in enumerate(exam):
            if not isinstance(item, dict):
                continue
            try:
                q_id = int(item.get("id", i + 1))
            except (TypeError, ValueError):
                continue
            if q_id == int(saved_q):
                return item, item, q_id, f"q_{q_id}"
        row = find_result_row(mx, int(saved_q))
        ctx = _real_mock_ctx_from_result_row(mx, row, exam) if isinstance(row, dict) else None
        if ctx:
            return ctx

    return _real_mock_current_question(mx)


def _real_mock_post_save_ctx_missing_log(mx: dict, page: str) -> None:
    try:
        results = mx.get("results") or []
        results_count = len(results) if isinstance(results, list) else 0
        tag = (
            "[REAL_MOCK_EMPTY_AUDIO_CTX_MISSING]"
            if page == "SPEECH_RECOVERY"
            else "[REAL_MOCK_POST_SAVE_CTX_MISSING]"
        )
        logger.warning(
            "%s page=%s saved_q=%s current_idx=%s results_count=%s mock_page=%s",
            tag,
            page,
            _get_real_mock_saved_q_id(mx),
            mx.get("current_idx"),
            results_count,
            _get_mock_page(mx),
        )
    except Exception:
        logger.debug("[REAL_MOCK_POST_SAVE_CTX_MISSING] log failed", exc_info=True)


def _render_real_mock_post_save_dispatch(mx: dict, page: str) -> bool:
    """Render post-save screen from saved_q — never current_idx alone. Returns True if rendered."""
    if page in _REAL_MOCK_POST_SAVE_PAGES:
        _arm_real_mock_post_save(mx, page)
    ctx = _real_mock_screen_question_ctx(mx)
    if ctx is None:
        return False
    q, _, q_id, audio_key = ctx
    try:
        logger.debug(
            "[REAL_MOCK_POST_SAVE_RENDER] page=%s saved_q=%s q_id=%s current_idx=%s",
            page,
            _get_real_mock_saved_q_id(mx),
            q_id,
            mx.get("current_idx"),
        )
    except Exception:
        pass
    if page == "SPEECH_RECOVERY":
        _render_real_mock_speech_recovery(mx, q, int(q_id), audio_key)
        return True
    if page == "ANSWER_SAVED":
        _render_real_mock_answer_saved(mx, q, int(q_id), audio_key)
        return True
    if page == "ANALYSIS_PENDING":
        _render_real_mock_analysis_pending(mx, q, int(q_id), audio_key)
        return True
    return False


def _render_real_mock_analysis_pending(mx: dict, q: dict, q_id: int, audio_key: str) -> None:
    """API delay during real mock — answer saved; user may continue."""
    exam = mx.get("current_exam") or mx.get("exam") or []
    total = len(exam) if isinstance(exam, list) and exam else get_mock_total_questions(mx)
    q_index = int(mx.get("current_idx") or 0)
    row = find_result_row(mx, int(q_id))
    lr = (row or {}).get("result", {}) if isinstance(row, dict) else {}
    reason = str(lr.get("analysis_error_kind") or lr.get("pending_reason") or "api_delay")
    try:
        logger.debug(
            "[REAL_MOCK_PENDING] q_idx=%s reason=%s",
            q_index,
            reason,
        )
    except Exception:
        pass

    render_top_bar(
        f"Q{q_id} · {q.get('topic', '')}".strip(" ·"),
        back_href="?nav=MOCK&mock=SURVEY",
        eyebrow=f"{_mock_mode_label(_mock_mode(mx))} · {format_mock_attempt_label(mx, q_id=q_id, total=total)}",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_learning_portal_back_button(mx)
    st.markdown(
        """
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">AI 분석</div>
          <div class="rv-title">AI 분석이 잠시 지연되고 있어요</div>
          <div class="rv-body">답변은 저장되었습니다.<br/>
            다음 문항으로 넘어가도 괜찮아요. 나중에 다시 분석할 수 있어요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    saved_audio = mx.get("audio_bytes") or (mx.get("recordings") or {}).get(audio_key)
    audio_size = recording_byte_length(saved_audio)
    if audio_size > 0 and st.session_state.get("show_dev_debug"):
        st.caption(f"녹음 {audio_size:,} bytes 보존됨")

    in_flight = _get_analysis_in_flight("real_mock")
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "다시 분석하기",
            type="primary",
            use_container_width=True,
            key=f"real_mock_pending_retry_{q_id}",
            disabled=in_flight,
        ):
            api_key = get_gemini_api_key()
            if not api_key:
                st.error("Gemini API Key가 없어 다시 시도할 수 없습니다.")
            else:
                clear_pending_recovery(mx)
                if saved_audio:
                    mx["audio_bytes"] = saved_audio
                _run_analysis(mx, q, int(q_id), audio_key, api_key, from_retry=True)
    with c2:
        if st.button(
            "다음 문제로 넘어가기",
            use_container_width=True,
            key=f"real_mock_pending_next_{q_id}",
        ):
            go_to_next_real_mock_question(mx, from_q_id=int(q_id))


def _render_real_mock_speech_recovery(mx: dict, q: dict, q_id: int, audio_key: str) -> None:
    """Short/silent answer — saved; retry or continue without blank screen."""
    exam = mx.get("current_exam") or mx.get("exam") or []
    total = len(exam) if isinstance(exam, list) and exam else get_mock_total_questions(mx)
    q_index = _real_mock_q_index_for_id(mx, int(q_id))
    row = find_result_row(mx, int(q_id))
    if not isinstance(row, dict):
        try:
            logger.warning(
                "[REAL_MOCK_SPEECH_RECOVERY_RENDER] q_idx=%s q_id=%s row_exists=False "
                "creating_no_audio_row",
                q_index,
                q_id,
            )
        except Exception:
            pass
        apply_no_audio_result(
            mx,
            q,
            q_id=int(q_id),
            question_index=q_index,
            audio_key=audio_key,
            source_audio_size_bytes=0,
        )
        row = find_result_row(mx, int(q_id))
        if isinstance(row, dict):
            res_fix = row.get("result")
            if isinstance(res_fix, dict):
                res_fix["estimated_level"] = "응답 부족"
                res_fix["estimated_level_display"] = "응답 부족"
                res_fix["is_gradable"] = False
                res_fix["is_answered"] = True
        if not isinstance(row, dict):
            _render_real_mock_recovery(mx)
            return
    lr = (row or {}).get("result", {}) if isinstance(row, dict) else {}
    if not isinstance(lr, dict):
        lr = {}
    nbytes = int(lr.get("source_audio_size_bytes") or 0)
    if not nbytes:
        blob = mx.get("audio_bytes") or (mx.get("recordings") or {}).get(audio_key)
        if blob:
            nbytes = recording_byte_length(blob)
    try:
        logger.debug(
            "[REAL_MOCK_SPEECH_RECOVERY_RENDER] q_idx=%s q_id=%s audio_len=%s "
            "row_exists=%s reason=%s",
            q_index,
            q_id,
            nbytes,
            isinstance(row, dict),
            lr.get("diagnosis_status") or lr.get("analysis_status"),
        )
    except Exception:
        pass

    render_top_bar(
        f"Q{q_id} · {q.get('topic', '')}".strip(" ·"),
        back_href="?nav=MOCK&mock=SURVEY",
        eyebrow=f"{_mock_mode_label(_mock_mode(mx))} · {format_mock_attempt_label(mx, q_id=q_id, total=total)}",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_learning_portal_back_button(mx)
    st.markdown(
        """
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">응답 부족</div>
          <div class="rv-title">응답이 충분하지 않았어요</div>
          <div class="rv-body">말소리가 충분히 인식되지 않아 이 문항은 자세한 피드백을 제공하기 어렵습니다.<br/>
            다시 말하거나 다음 문항으로 넘어갈 수 있어요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if nbytes > 0 and st.session_state.get("show_dev_debug"):
        st.caption(f"녹음 저장됨 · {nbytes:,} bytes")

    _, mic_key = build_recording_keys("real_mock", str(q_id), q_index)
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "같은 질문 다시 말하기",
            type="primary",
            use_container_width=True,
            key=f"real_mock_speech_retry_{q_id}",
        ):
            _real_mock_retry_same_question(mx, int(q_id), audio_key=audio_key, mic_key=mic_key)
    with c2:
        if st.button(
            "다음 문제로 넘어가기",
            use_container_width=True,
            key=f"real_mock_speech_next_{q_id}",
        ):
            go_to_next_real_mock_question(mx, from_q_id=int(q_id))


def _render_real_mock_answer_saved(mx: dict, q: dict, q_id: int, audio_key: str) -> None:
    exam = mx.get("current_exam") or mx.get("exam") or []
    total = len(exam) if isinstance(exam, list) and exam else get_mock_total_questions(mx)
    render_top_bar(
        f"Q{q_id} · {q.get('topic', '')}".strip(" ·"),
        back_href="?nav=MOCK&mock=SURVEY",
        eyebrow=f"{_mock_mode_label(_mock_mode(mx))} · {format_mock_attempt_label(mx, q_id=q_id, total=total)}",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_learning_portal_back_button(mx)

    row = find_result_row(mx, int(q_id))
    nbytes = 0
    if row:
        res = row.get("result") if isinstance(row.get("result"), dict) else {}
        nbytes = int(res.get("source_audio_size_bytes") or 0)
    if not nbytes:
        blob = mx.get("audio_bytes") or (mx.get("recordings") or {}).get(audio_key)
        if blob:
            nbytes = recording_byte_length(blob)

    q_index = int(mx.get("current_idx") or 0)
    is_last = q_index >= total - 1

    st.markdown(
        """
        <section class="continue-card continue-card--resume mx-landing-card" role="status">
          <div class="cc-eyebrow">저장 완료</div>
          <div class="cc-title">답변이 저장되었어요</div>
          <div class="cc-meta">녹음이 안전하게 저장되었습니다.<br/>
            AI 분석은 15문항을 모두 마친 뒤 최종 리포트에서 진행됩니다.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if row and st.session_state.get("show_dev_debug"):
        from services.stt_service import render_stt_dev_debug_capsule

        res_dbg = row.get("result") if isinstance(row.get("result"), dict) else {}
        render_stt_dev_debug_capsule(res_dbg, key_suffix=f"real_saved_{q_id}")
        if nbytes > 0:
            st.caption(f"[dev] audio_len={nbytes:,}")

    with st.expander("내 답변 다시 듣기", expanded=False):
        blob = stored_audio_for_row(mx, row) if row else None
        if not blob:
            blob = mx.get("audio_bytes") or (mx.get("recordings") or {}).get(audio_key)
        if blob:
            st.audio(blob, format="audio/wav")
        else:
            st.caption("재생할 녹음이 없습니다.")

    btn_label = "최종 리포트로 넘어가기" if is_last else "다음 문제로 넘어가기"
    if st.button(
        btn_label,
        type="primary",
        use_container_width=True,
        key=f"real_mock_next_{q_id}",
    ):
        go_to_next_real_mock_question(mx, from_q_id=int(q_id))


def _render_real_mock_final_ready(mx: dict) -> None:
    total = get_mock_total_questions(mx)
    saved_n = _count_real_mock_saved_answers(mx)
    render_top_bar(
        "실전 모의고사",
        back_href="?nav=MOCK",
        eyebrow=format_mock_attempt_label(mx),
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <section class="continue-card continue-card--start mx-landing-card" role="region">
          <div class="cc-eyebrow">저장 완료</div>
          <div class="cc-title">실전 모의고사가 완료되었어요</div>
          <div class="cc-meta">{total}개 문항의 답변이 모두 저장되었습니다.<br/>
            이제 전체 답변 흐름을 바탕으로 최종 리포트를 받아볼 수 있어요.</div>
          <div class="cc-meta" style="margin-top:8px;">저장된 답변 {saved_n}개</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    c_view, c_batch = st.columns(2)
    with c_view:
        if st.button(
            "최종 리포트 보기",
            type="primary",
            use_container_width=True,
            key="real_mock_open_final_from_ready",
        ):
            _open_completed_final_report(mx)
            st.rerun()
    with c_batch:
        if st.button(
            "최종 리포트 받기",
            use_container_width=True,
            key="real_mock_final_report_btn",
        ):
            st.session_state[_REAL_MOCK_PAGE_KEY] = "FINAL_ANALYZING"
            st.rerun()
    if st.button("학습 방식 다시 선택", use_container_width=True, key="real_mock_ready_back"):
        reset_to_learning_portal()
        st.rerun()


def _compute_real_mock_shared_overall_level(mx: dict) -> None:
    """Re-grade the headline level with the shared OPIc rubric (Mock V2 path).

    The per-question hybrid engine over-grades (no shared gates, quantity raises the
    level). This runs the shared rubric over the 15 transcripts and stores the
    authoritative overall level on the attempt for the final report to display.
    """
    try:
        from services.mock_v2_analysis import analyze_real_mock_overall_level

        rows = [r for r in (mx.get("results") or []) if isinstance(r, dict)]
        if not rows:
            return
        shared = analyze_real_mock_overall_level(rows)
        if not isinstance(shared, dict) or not shared.get("ok"):
            logger.warning(
                "[REAL_MOCK_SHARED_LEVEL] skipped category=%s",
                (shared or {}).get("error_category") if isinstance(shared, dict) else "—",
            )
            return
        level = str(shared.get("overall_level") or "").strip()
        if not level:
            return
        mx["shared_overall_level"] = level
        mx["shared_score_breakdown"] = shared.get("score_breakdown") or {}
        try:
            from services.exam_analytics import parse_level_to_token

            mx["shared_overall_raw"] = parse_level_to_token(level) or ""
        except Exception:
            mx["shared_overall_raw"] = ""
        logger.info("[REAL_MOCK_SHARED_LEVEL] overall_level=%s", level)
    except Exception:
        logger.exception("[REAL_MOCK_SHARED_LEVEL] failed")


def _run_real_mock_final_analysis(mx: dict) -> None:
    """Analyze all saved answers once — only after user clicks 최종 리포트 받기."""
    api_key = get_gemini_api_key()
    if not api_key:
        st.warning("Gemini API Key가 없습니다. 설정 후 다시 시도해 주세요.")
        st.session_state[_REAL_MOCK_PAGE_KEY] = "FINAL_READY"
        st.rerun()
        return

    exam = mx.get("current_exam") or mx.get("exam") or []
    if not exam:
        st.session_state[_REAL_MOCK_PAGE_KEY] = "FINAL_READY"
        st.rerun()
        return

    if st.session_state.get(_REAL_MOCK_FINAL_BATCH_IN_FLIGHT_KEY):
        return

    st.session_state[_REAL_MOCK_FINAL_BATCH_IN_FLIGHT_KEY] = True
    submission_id = secrets.token_hex(4)
    wait_slot = st.empty()

    def _show_wait(label: str = "") -> None:
        with wait_slot.container():
            render_ai_analysis_waiting(
                submission_id,
                title="AI가 15개 답변을 분석하고 있어요",
                subtitle=(
                    "전체 답변 흐름을 바탕으로 최종 리포트를 준비하는 중입니다.<br/>"
                    "조금 시간이 걸릴 수 있어요."
                ),
                stage_label=label or None,
            )

    try:
        _show_wait()
        from services.transcript_analysis_service import analyze_real_mock_transcripts
        from utils.exam_state import apply_completed_analysis_result

        results_rows = mx.get("results") or []
        batch = analyze_real_mock_transcripts(
            [r for r in results_rows if isinstance(r, dict)],
            difficulty=int(settings_session()["difficulty"]),
            api_key=api_key,
        )
        if batch.get("timed_out"):
            logger.warning("[REAL_MOCK_FINAL] transcript batch timeout")
            st.session_state[_REAL_MOCK_PAGE_KEY] = "FINAL_READY"
            st.rerun()
            return
        if batch.get("quota") or not batch.get("ok"):
            logger.warning(
                "[REAL_MOCK_FINAL] transcript batch failed category=%s",
                batch.get("error_category"),
            )
            st.session_state[_REAL_MOCK_PAGE_KEY] = "FINAL_READY"
            st.rerun()
            return

        for item in batch.get("per_question") or []:
            if not isinstance(item, dict):
                continue
            q_idx = int(item.get("question_index") or 0)
            q = exam[q_idx] if q_idx < len(exam) and isinstance(exam[q_idx], dict) else {}
            q_id = int(q.get("id", q_idx + 1))
            audio_key = str(item.get("audio_key") or f"q_{q_id}")
            status = str(item.get("status") or "")
            result = item.get("result")
            if status in ("completed", "insufficient") and isinstance(result, dict):
                apply_completed_analysis_result(
                    mx,
                    q,
                    q_id=q_id,
                    question_index=q_idx,
                    audio_key=audio_key,
                    result=cache_analysis_payload(dict(result)),
                )
            elif status in ("failed", "pending"):
                from utils.exam_state import apply_pending_analysis_result

                apply_pending_analysis_result(
                    mx,
                    q,
                    q_id=q_id,
                    question_index=q_idx,
                    audio_key=audio_key,
                    error_message=str(item.get("error") or "stt_pending"),
                    attempts=0,
                )
        _compute_real_mock_shared_overall_level(mx)
        try:
            from utils.history_sync import save_real_mock_report

            saved_rows = [
                r for r in (mx.get("results") or []) if isinstance(r, dict)
            ]
            save_real_mock_report(
                sig=f"{mx.get('attempt_no') or 1}_{submission_id}",
                overall_level=str(mx.get("shared_overall_level") or ""),
                score_breakdown=mx.get("shared_score_breakdown") or {},
                content={
                    "overall_level": mx.get("shared_overall_level") or "",
                    "shared_overall_raw": mx.get("shared_overall_raw") or "",
                    "score_breakdown": mx.get("shared_score_breakdown") or {},
                    "results": saved_rows,
                },
            )
        except Exception:
            pass
        mark_real_mock_exam_completed(mx, st.session_state)
        st.session_state[_REAL_MOCK_PAGE_KEY] = "FINAL_PREVIEW"
        _set_mock_page(mx, "TEST")
    except Exception:
        logger.exception("Real mock final batch analysis failed")
        st.session_state[_REAL_MOCK_PAGE_KEY] = "FINAL_READY"
    finally:
        finish_analysis_waiting_ui(wait_slot, submission_id)
        st.session_state[_REAL_MOCK_FINAL_BATCH_IN_FLIGHT_KEY] = False
        _set_analysis_in_flight("real_mock", False)
        _clear_legacy_analysis_in_flight()
    st.rerun()


def _render_real_mock_exam(mx: dict) -> None:
    """Real mock — save-only per question; batch AI after Q15."""
    _ensure_real_mock_page_state()
    page = _real_mock_page()
    try:
        results = mx.get("results") or []
        logger.debug(
            "[REAL_MOCK_EXAM_ENTER] page=%s saved_q=%s current_idx=%s mock_page=%s results_count=%s",
            page,
            _get_real_mock_saved_q_id(mx),
            mx.get("current_idx"),
            _get_mock_page(mx),
            len(results) if isinstance(results, list) else 0,
        )
    except Exception:
        pass
    _real_mock_log_flow(mx, page)

    if page == "SPEECH_RECOVERY" or st.session_state.get(_REAL_MOCK_POST_SAVE_LOCK_KEY) == "SPEECH_RECOVERY":
        if _real_mock_clear_stale_speech_recovery(mx):
            try:
                logger.info(
                    "[REAL_MOCK_QUESTION_RENDER_AFTER_RECOVERY] q_index=%s q_id=%s",
                    _get_current_real_mock_question_index(mx),
                    (_real_mock_current_question(mx) or (None, None, None, None))[2],
                )
            except Exception:
                pass
            _render_real_mock_question(mx)
            return

    if page in _REAL_MOCK_POST_SAVE_PAGES:
        if _render_real_mock_post_save_dispatch(mx, page):
            return
        _real_mock_post_save_ctx_missing_log(mx, page)
        _real_mock_blank_guard(mx, page)
        _render_real_mock_recovery(mx)
        return

    if _is_unsupported_real_mock_page(page):
        _real_mock_blank_guard(mx, page)
        _render_real_mock_recovery(mx)
        return

    try:
        if page == "FINAL_READY":
            _render_real_mock_final_ready(mx)
            return

        if page == "FINAL_ANALYZING":
            render_top_bar(
                "실전 모의고사",
                back_href="?nav=MOCK",
                eyebrow=format_mock_attempt_label(mx),
            )
            st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
            render_ai_analysis_waiting(
                secrets.token_hex(4),
                title="AI가 15개 답변을 분석하고 있어요",
                subtitle="최종 리포트를 준비하는 중입니다. 잠시만 기다려 주세요.",
            )
            _run_real_mock_final_analysis(mx)
            return

        if page in ("FINAL_PREVIEW", "FINAL_REPORT"):
            render_mock_exam_completion_screen(mx)
            return

        if page == "RECOVERY":
            _render_real_mock_recovery(mx)
            return

        if page == "QUESTION":
            exam = mx.get("current_exam") or mx.get("exam") or []
            if not exam:
                _real_mock_blank_guard(mx, page)
                _render_real_mock_recovery(mx)
                return
            q_index = _get_current_real_mock_question_index(mx)
            if q_index < 0 or q_index >= len(exam):
                _real_mock_blank_guard(mx, page)
                _render_real_mock_recovery(mx)
                return
            if _real_mock_all_questions_saved(mx) and not mx.get("exam_finished"):
                _set_real_mock_page("FINAL_READY")
                _render_real_mock_final_ready(mx)
                return
            _render_real_mock_question(mx)
            return

        _real_mock_blank_guard(mx, page)
        _render_real_mock_recovery(mx)
        return
    except Exception:
        logger.exception("[REAL_MOCK_ROUTE] render failed page=%s", page)
        _real_mock_blank_guard(mx, page)
        _render_real_mock_recovery(mx)


def _render_real_mock_question(mx: dict) -> None:
    page = _real_mock_page()
    if page in _REAL_MOCK_POST_SAVE_PAGES:
        if _render_real_mock_post_save_dispatch(mx, page):
            return
        _real_mock_post_save_ctx_missing_log(mx, page)
        _render_real_mock_recovery(mx)
        return

    api_key = get_gemini_api_key()
    if not api_key:
        st.warning("Gemini API Key가 없습니다. `.streamlit/secrets.toml` 또는 환경변수 `GEMINI_API_KEY`를 설정해주세요.")

    if not mx.get("exam_listen_nonce"):
        mx["exam_listen_nonce"] = secrets.token_hex(8)

    exam = mx.get("current_exam") or mx.get("exam") or []
    if not exam:
        post_p = _real_mock_page()
        if post_p in _REAL_MOCK_POST_SAVE_PAGES and _render_real_mock_post_save_dispatch(
            mx, post_p
        ):
            return
        if force_restore_mock_from_disk(mx):
            st.session_state[_REAL_MOCK_SKIP_RECONCILE_KEY] = True
            st.rerun()
        _real_mock_blank_guard(mx, "QUESTION")
        _render_real_mock_recovery(mx)
        return

    _maybe_reconcile_real_mock_pointer(mx)
    q_index = _get_current_real_mock_question_index(mx)
    if q_index < 0 or q_index >= len(exam):
        _render_real_mock_recovery(mx)
        return
    mx["exam_last_seen_at"] = iso_now()
    if not mx.get("exam_started_at"):
        mx["exam_started_at"] = mx["exam_last_seen_at"]

    q = exam[q_index]
    if not isinstance(q, dict):
        _render_real_mock_recovery(mx)
        return
    q_id = int(q.get("id", q_index + 1))
    audio_key = f"q_{q_id}"

    try:
        logger.debug(
            "[REAL_MOCK_QUESTION_RENDER_AFTER_RECOVERY] q_index=%s q_id=%s page=%s",
            q_index,
            q_id,
            _real_mock_page(),
        )
    except Exception:
        pass

    row = find_result_row(mx, int(q_id))
    res = (row or {}).get("result", {}) if isinstance(row, dict) else {}
    if _real_mock_page() == "QUESTION":
        if isinstance(res, dict) and _is_pending_result(res):
            _set_real_mock_saved_q_id(mx, int(q_id))
            _arm_real_mock_post_save(mx, "ANALYSIS_PENDING")
            _render_real_mock_analysis_pending(mx, q, q_id, audio_key)
            return
        if isinstance(res, dict):
            from services.exam_analytics import result_is_no_speech_row

            if result_is_no_speech_row(res) or str(res.get("diagnosis_status") or "") == "no_audio":
                _set_real_mock_saved_q_id(mx, int(q_id))
                _arm_real_mock_post_save(mx, "SPEECH_RECOVERY")
                _render_real_mock_speech_recovery(mx, q, q_id, audio_key)
                return
            ast = str(res.get("analysis_status") or "").lower()
            dst = str(res.get("diagnosis_status") or "").lower()
            if ast == "saved_unanalyzed" or dst == "saved_unanalyzed":
                _set_real_mock_saved_q_id(mx, int(q_id))
                _arm_real_mock_post_save(mx, "ANSWER_SAVED")
                _render_real_mock_answer_saved(mx, q, q_id, audio_key)
                return

    page_after_row = _real_mock_page()
    if page_after_row in _REAL_MOCK_POST_SAVE_PAGES:
        if _render_real_mock_post_save_dispatch(mx, page_after_row):
            return
        _real_mock_post_save_ctx_missing_log(mx, page_after_row)
        _render_real_mock_recovery(mx)
        return

    total = len(exam)
    timer_key, mic_key = build_recording_keys("real_mock", str(q_id), q_index)

    render_top_bar(
        f"Q{q_id} · {q.get('topic', '')}".strip(" ·"),
        back_href="?nav=MOCK&mock=SURVEY",
        eyebrow=f"{_mock_mode_label(_mock_mode(mx))} · {format_mock_attempt_label(mx, q_id=q_id, total=total)}",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    from services.final_report_preview import build_final_report_preview

    _prev = build_final_report_preview(mx.get("results") or [], total_count=total)
    render_real_mock_progress_chip(
        current_q=int(q_id),
        total_q=int(total),
        answered_count=int(_prev.get("answered_count") or 0),
        completed_count=int(_prev.get("completed_count") or 0),
    )
    _render_learning_portal_back_button(mx)

    _answered = _count_real_mock_saved_answers(mx)
    progress_pct = int(round((_answered / total) * 100)) if total else 0
    topic_safe = html.escape(q.get("topic", "") or "")
    type_safe = html.escape(q.get("type", "") or "")
    st.markdown(
        f"""
        <div class="mx-progress">
          <div class="mx-progress-meta">
            <span class="mx-progress-count">문항 <span class="mx-progress-num">{q_id}</span> <span class="mx-progress-of">/ {total}</span></span>
          </div>
          {('<div class="mx-progress-chip">' + type_safe + '</div>') if type_safe else (('<div class="mx-progress-chip">' + topic_safe + '</div>') if topic_safe else '')}
        </div>
        <div class="mx-progress-bar" aria-hidden="true">
          <span class="mx-progress-fill" style="width:{progress_pct}%"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="mx-question-card">
          <div class="mx-question-topic">{topic_safe or '주제 안내'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _render_mock_question_text_only(q)

    open_record_stage(compact=True)

    def _on_saved(_blob: bytes) -> bool:
        nbytes = recording_byte_length(_blob) if _blob else 0
        try:
            logger.debug(
                "[REAL_MOCK_ON_SAVED_ENTER] q_idx=%s q_id=%s blob_len=%s",
                q_index,
                q_id,
                nbytes,
            )
        except Exception:
            pass
        if not _blob or nbytes < MIN_RECORDED_AUDIO_BYTES:
            try:
                logger.debug(
                    "[REAL_MOCK_EMPTY_COMMIT_REACHED] q_idx=%s q_id=%s reason=%s",
                    q_index,
                    q_id,
                    "below_min" if _blob else "empty_blob",
                )
            except Exception:
                pass
            return _real_mock_commit_empty_audio(
                mx,
                q,
                q_id,
                audio_key,
                q_index=q_index,
                reason="below_min" if _blob else "empty_blob",
                blob=_blob if _blob else b"",
            )
        return _real_mock_commit_saved_answer(mx, q, q_id, audio_key, _blob)

    rec = mx.setdefault("recordings", {})
    st.session_state["recording_active_audio_key"] = audio_key
    if not get_saved_audio_for_key(rec, audio_key):
        mx["audio_bytes"] = None
    _render_answer_recording_stage(
        mx,
        question_key=timer_key,
        mic_key=mic_key,
        audio_key=audio_key,
        recordings=rec,
        analyzing=False,
        on_recording_complete=_on_saved,
        mode="real_mock",
        question_index=q_index,
    )
    if _real_mock_maybe_post_record_empty_fallback(
        mx,
        q,
        q_id,
        audio_key,
        q_index=q_index,
        timer_key=timer_key,
        mic_key=mic_key,
        rec=rec,
    ):
        return
    if _real_mock_page() == "QUESTION":
        _post_ui = get_recording_ui_state(
            timer_key, has_saved=bool(get_saved_audio_for_key(rec, audio_key))
        )
        if _post_ui == STATE_SAVED and not get_saved_audio_for_key(rec, audio_key):
            _real_mock_blank_guard(mx, "QUESTION_STALE_SAVED_UI")
            if _real_mock_maybe_post_record_empty_fallback(
                mx,
                q,
                q_id,
                audio_key,
                q_index=q_index,
                timer_key=timer_key,
                mic_key=mic_key,
                rec=rec,
            ):
                return
            _render_real_mock_recovery(mx)
            return
    close_record_stage()


def _render_test(mx: dict) -> None:
    api_key = get_gemini_api_key()
    if not api_key:
        st.warning("Gemini API Key가 없습니다. `.streamlit/secrets.toml` 또는 환경변수 `GEMINI_API_KEY`를 설정해주세요.")

    if not mx.get("exam_listen_nonce"):
        mx["exam_listen_nonce"] = secrets.token_hex(8)

    _exam_run = mx.get("current_exam") or mx["exam"]
    if not _exam_run:
        # Last-ditch restore: ``maybe_restore_mock_from_disk`` already ran
        # earlier in ``app.py`` but might have been bypassed (e.g. mx had
        # leftover ``results`` from a previous flow). Try once more —
        # disk has the canonical exam payload in 100% of resume cases.
        if force_restore_mock_from_disk(mx):
            st.rerun()
        st.warning("시험지가 없습니다. 설문에서 「시험지 생성 및 시험 시작」을 눌러 주세요.")
        mx["mock_page"] = "SURVEY"
        mx["current_idx"] = 0
        st.rerun()

    reconcile_mock_exam_pointer(mx)

    # Touch last-seen so the home "이어하기" card knows when the user was here.
    mx["exam_last_seen_at"] = iso_now()
    if not mx.get("exam_started_at"):
        mx["exam_started_at"] = mx["exam_last_seen_at"]

    q = _exam_run[mx["current_idx"]]
    q_id = q["id"]
    audio_key = f"q_{q_id}"
    total = len(_exam_run)
    _mode_lbl = _mock_mode_label(_mock_mode(mx))
    _progress_lbl = format_mock_attempt_label(mx, q_id=int(q_id), total=int(total))
    render_top_bar(
        f"Q{q_id} · {q.get('topic', '')}".strip(" ·"),
        back_href="?nav=MOCK&mock=SURVEY",
        eyebrow=f"{_mode_lbl} · {_progress_lbl}",
    )

    # Marker — activates the ``section.main:has(.mx-marker)`` Streamlit-widget
    # overrides in ``ui/styles.py`` (progress bar hidden, primary button
    # styled, expander cards). Stays invisible (``display:none`` via empty
    # element) so it only acts as a CSS sentinel.
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    if _is_real_mock(mx):
        from services.final_report_preview import build_final_report_preview

        _prev = build_final_report_preview(mx.get("results") or [], total_count=total)
        render_real_mock_progress_chip(
            current_q=int(q_id),
            total_q=int(total),
            answered_count=int(_prev.get("answered_count") or 0),
            completed_count=int(_prev.get("completed_count") or 0),
        )
    _render_learning_portal_back_button(mx)

    # --- Pending recovery branch -----------------------------------------
    # When a previous analysis attempt failed for THIS question, we never
    # destroyed the current question state — the audio + question are still
    # in ``mx``. Show the recovery panel only, hiding the regular test UI
    # (mic recorder, analyze button) so the user can't accidentally
    # over-record their preserved answer.
    if has_pending_recovery_for(mx, q_id):
        _render_recovery_panel(mx, q, q_id, audio_key)
        return

    # 1) Top progress strip — custom HTML replaces ``st.progress`` (which is
    # hidden by the scoped CSS) so the visual hierarchy matches HOME/PATTERN.
    _answered = count_completed_exam_prefix(mx)
    progress_pct = int(round((_answered / total) * 100)) if total else 0
    topic_safe = html.escape(q.get("topic", "") or "")
    type_safe = html.escape(q.get("type", "") or "")
    st.markdown(
        f"""
        <div class="mx-progress">
          <div class="mx-progress-meta">
            <span class="mx-progress-count">문항 <span class="mx-progress-num">{q_id}</span> <span class="mx-progress-of">/ {total}</span></span>
          </div>
          {('<div class="mx-progress-chip">' + type_safe + '</div>') if type_safe else (('<div class="mx-progress-chip">' + topic_safe + '</div>') if topic_safe else '')}
        </div>
        <div class="mx-progress-bar" aria-hidden="true">
          <span class="mx-progress-fill" style="width:{progress_pct}%"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2) Question card — type chip + topic + text (live question TTS disabled).
    st.markdown(
        f"""
        <div class="mx-question-card">
          <div class="mx-question-topic">{topic_safe or '주제 안내'}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_mock_question_text_only(q)

    open_record_stage(compact=True)
    timer_key, mic_key = build_recording_keys("coaching_mock", str(q_id), mx.get("current_idx"))
    in_flight = _get_analysis_in_flight("coaching")
    rec = mx.setdefault("recordings", {})
    st.session_state["recording_active_audio_key"] = audio_key
    if not get_saved_audio_for_key(rec, audio_key):
        mx["audio_bytes"] = None
    _render_answer_recording_stage(
        mx,
        question_key=timer_key,
        mic_key=mic_key,
        audio_key=audio_key,
        recordings=rec,
        analyzing=in_flight,
        mode="coaching_mock",
        question_index=int(mx.get("current_idx") or 0),
    )
    close_record_stage()

    # 5) Status / error messages — same logic as before, just calmer cards.
    if mx["analysis_status"]:
        st.markdown(
            f'<div class="mx-status mx-status--info">'
            f'<span class="mx-status-icon">💡</span>'
            f'<span>{html.escape(str(mx["analysis_status"]))}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    if mx["analysis_error_msg"]:
        st.markdown(
            f'<div class="mx-status mx-status--error">'
            f'<span class="mx-status-icon">⚠️</span>'
            f'<span>{html.escape(str(mx["analysis_error_msg"]))}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        mx["analysis_error_msg"] = ""
    if mx["analysis_done"]:
        mx["analysis_done"] = False

    def _mock_analyze() -> None:
        _run_analysis(mx, q, q_id, audio_key, api_key)

    render_post_record_actions(
        mx,
        question_key=timer_key,
        audio_key=audio_key,
        mic_key=mic_key,
        recordings=rec,
        on_analyze=_mock_analyze,
        analyze_key=f"mock_analyze_{q_id}",
        rerecord_key=f"mock_rerecord_{q_id}",
        analyze_disabled=(not bool(api_key)) or in_flight,
        mode="coaching_mock",
        question_index=int(mx.get("current_idx") or 0),
        question_id=str(q_id),
    )
    if in_flight:
        return


def _run_analysis(
    mx: dict,
    q: dict,
    q_id: int,
    audio_key: str,
    api_key: str,
    *,
    from_retry: bool = False,
    defer_navigation: bool = False,
) -> None:
    """Save answer first, then analyze — API failure never blocks progress."""
    analysis_mode = _mock_mode(mx) or "coaching"
    if _get_analysis_in_flight(analysis_mode):
        return

    _set_analysis_in_flight(analysis_mode, True)

    def _finish_analysis_nav() -> None:
        if defer_navigation:
            return
        _nav_after_question_analysis(mx, int(q["id"]))
        reconcile_mock_exam_pointer(mx)
        mx["analysis_done"] = True
        clear_pending_recovery(mx)
        st.rerun()

    def _maybe_rerun() -> None:
        if not defer_navigation:
            st.rerun()

    try:
        stop_recording_timer()
        mx["analysis_result"] = None
        mx["analysis_error_msg"] = ""
        mx["analysis_done"] = False
        mx["analysis_status"] = ""
        mx["preview_transcript"] = None

        blob = mx["audio_bytes"] or mx["recordings"].get(audio_key)
        q_index = int(mx.get("current_idx") or 0)
        if not blob:
            st.error("오디오 데이터가 유실되었습니다. 다시 녹음해주세요.")
            apply_no_audio_result(
                mx,
                q,
                q_id=int(q_id),
                question_index=q_index,
                audio_key=audio_key,
                source_audio_size_bytes=0,
            )
            mark_pending_recovery(
                mx,
                q_id=int(q_id),
                audio_key=audio_key,
                error_message=NO_AUDIO_ERROR_SENTINEL,
                attempts=0,
            )
            _maybe_rerun()
            return

        nbytes = recording_byte_length(blob)
        if classify_pre_analysis_blob(blob) == "no_audio":
            if not from_retry:
                save_answer_placeholder_before_ai(
                    mx,
                    q,
                    q_id=int(q_id),
                    question_index=q_index,
                    audio_key=audio_key,
                    audio_bytes=blob,
                )
            apply_no_audio_result(
                mx,
                q,
                q_id=int(q_id),
                question_index=q_index,
                audio_key=audio_key,
                source_audio_size_bytes=nbytes,
            )
            mark_pending_recovery(
                mx,
                q_id=int(q_id),
                audio_key=audio_key,
                error_message=NO_AUDIO_ERROR_SENTINEL,
                attempts=0,
            )
            _maybe_rerun()
            return

        pre_speech = classify_pre_gemini_speech(blob)
        if pre_speech == "no_speech":
            try:
                logger.debug(
                    "[NO_SPEECH_CLASSIFY] q_idx=%s audio_len=%s threshold=%s status=no_speech",
                    q_index,
                    nbytes,
                    VERY_SMALL_SPEECH_AUDIO_BYTES,
                )
            except Exception:
                pass
            if not from_retry:
                save_answer_placeholder_before_ai(
                    mx,
                    q,
                    q_id=int(q_id),
                    question_index=q_index,
                    audio_key=audio_key,
                    audio_bytes=blob,
                )
            mime_pre = resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key)
            ns = apply_insufficient_response_result(
                mx,
                q,
                q_id=int(q_id),
                question_index=q_index,
                audio_key=audio_key,
                source_audio_size_bytes=nbytes,
                audio_mime_guess=mime_pre,
            )
            mx["analysis_result"] = ns
            mx["last_result"] = ns
            clear_pending_recovery(mx)
            _finish_analysis_nav()
            return

        if not from_retry and not defer_navigation:
            save_answer_placeholder_before_ai(
                mx,
                q,
                q_id=int(q_id),
                question_index=q_index,
                audio_key=audio_key,
                audio_bytes=blob,
            )

        difficulty = int(settings_session()["difficulty"])
        result: dict | None = None
        last_error = ""
        attempts = 0

        submission_id = secrets.token_hex(4)
        wait_slot = st.empty()

        def _show_analysis_wait(label: str = "AI가 발화를 진단 중입니다…") -> None:
            with wait_slot.container():
                render_ai_analysis_waiting(submission_id, stage_label=label)

        try:
            _show_analysis_wait()

            def _on_status(stage: str, label: str) -> None:
                _show_analysis_wait(label)

            mime_for_gemini = resolve_mime_for_analysis(
                blob, mx=mx, audio_key=audio_key
            )
            audio_pipeline_diag.log_before_gemini(
                q_index=q_index,
                audio_bytes=blob,
                mime_type=mime_for_gemini,
            )
            result, last_error, attempts = analyze_audio_with_retry(
                blob,
                q["question"],
                api_key,
                difficulty,
                mime_guess=mime_for_gemini,
                on_status=_on_status,
                q_label=f"Q{q_id}",
                diag={
                    "submission_id": submission_id,
                    "question_index": q_index,
                    "question_id": q_id,
                    "q_label": f"Q{q_id}",
                    "mock_mode": _mock_mode(mx),
                    "attempt_id": mx.get("attempt_no"),
                    "mock_page": mx.get("mock_page"),
                    "caller": "mock_exam._run_analysis",
                    "mime_type": mime_for_gemini,
                },
            )
        except Exception as exc:
            logger.exception("Gemini analysis unexpected failure q_id=%s", q_id)
            last_error = f"{type(exc).__name__}: {exc}"
            result = None
            attempts = max(attempts, 1)
        finally:
            finish_analysis_waiting_ui(wait_slot, submission_id)

        if _is_analysis_failed(result, last_error):
            err_kind = classify_analysis_error(last_error)
            logger.warning(
                "Gemini analysis failed q_id=%s attempts=%s kind=%s",
                q.get("id"),
                attempts,
                err_kind,
            )
            logger.warning("Gemini last_error detail (server log): %s", last_error)
            if should_treat_analysis_failure_as_no_speech(
                blob, result, last_error, audio_len=nbytes
            ):
                try:
                    logger.debug(
                        "[NO_SPEECH_CLASSIFY] q_idx=%s audio_len=%s threshold=%s status=no_speech",
                        q_index,
                        nbytes,
                        VERY_SMALL_SPEECH_AUDIO_BYTES,
                    )
                except Exception:
                    pass
                ns = apply_insufficient_response_result(
                    mx,
                    q,
                    q_id=int(q_id),
                    question_index=q_index,
                    audio_key=audio_key,
                    source_audio_size_bytes=nbytes,
                    audio_mime_guess=mime_for_gemini,
                )
                mx["analysis_result"] = ns
                mx["last_result"] = ns
                clear_pending_recovery(mx)
                if _is_real_mock(mx) and not defer_navigation:
                    _set_real_mock_page("SPEECH_RECOVERY")
                    _set_mock_page(mx, "TEST")
                    _maybe_rerun()
                    return
                _finish_analysis_nav()
                return
            _empty_resp = bool(
                (last_error and "비어" in last_error)
                or (
                    isinstance(result, dict)
                    and str(result.get("error") or "").strip()
                    and "비어" in str(result.get("error"))
                )
            )
            pending = apply_pending_analysis_result(
                mx,
                q,
                q_id=int(q_id),
                question_index=q_index,
                audio_key=audio_key,
                error_message=last_error or "AI 분석 실패",
                attempts=attempts,
                mode=_mock_mode(mx) or "",
                mime_type=mime_for_gemini,
                model=str((result or {}).get("model_used") or ""),
                audio_bytes_len=nbytes,
                empty_response=_empty_resp,
            )
            mx["analysis_result"] = pending
            mx["last_result"] = pending
            mark_pending_recovery(
                mx,
                q_id=int(q_id),
                audio_key=audio_key,
                error_message=last_error or "AI 분석 실패",
                attempts=attempts,
                pending_meta={
                    "analysis_error_category": pending.get("analysis_error_category"),
                    "analysis_error_short": pending.get("analysis_error_short"),
                    "analysis_error_type": pending.get("analysis_error_type"),
                    "mime_type": mime_for_gemini,
                    "model": pending.get("model_used") or "",
                    "pending_audio_bytes": nbytes,
                    "retry_count": attempts,
                },
            )
            reconcile_mock_exam_pointer(mx)
            mx["preview_transcript"] = None
            if _is_real_mock(mx) and not defer_navigation:
                _set_real_mock_page("ANALYSIS_PENDING")
                _set_mock_page(mx, "TEST")
                _maybe_rerun()
                return
            _finish_analysis_nav()
            return

        speech_issue = classify_post_analysis_issue(blob, result)
        audio_pipeline_diag.log_no_speech_gate(
            q_index=q_index,
            audio_bytes=blob,
            transcript=(result or {}).get("transcript") or "",
            trust_result=audio_pipeline_diag.trust_result_label(result),
            status=speech_issue,
        )
        if speech_issue != "ok":
            mime_guess = resolve_mime_for_debug(
                blob, mx=mx, audio_key=audio_key, result=result
            )
            if speech_issue == "no_audio":
                apply_no_audio_result(
                    mx,
                    q,
                    q_id=int(q_id),
                    question_index=q_index,
                    audio_key=audio_key,
                    source_audio_size_bytes=nbytes,
                )
                mark_pending_recovery(
                    mx,
                    q_id=int(q_id),
                    audio_key=audio_key,
                    error_message=NO_AUDIO_ERROR_SENTINEL,
                    attempts=attempts,
                )
            elif speech_issue == "non_english":
                preview = (result or {}).get("non_english_preview") or ""
                kind = (result or {}).get("language_mismatch_kind") or "korean"
                apply_non_english_result(
                    mx,
                    q,
                    q_id=int(q_id),
                    question_index=q_index,
                    audio_key=audio_key,
                    source_audio_size_bytes=nbytes,
                    audio_mime_guess=mime_guess,
                    non_english_preview=preview,
                    language_mismatch_kind=kind,
                )
                mark_pending_recovery(
                    mx,
                    q_id=int(q_id),
                    audio_key=audio_key,
                    error_message=NON_ENGLISH_ERROR_SENTINEL,
                    attempts=attempts,
                )
            elif speech_issue == "needs_review":
                apply_needs_review_result(
                    mx,
                    q,
                    q_id=int(q_id),
                    question_index=q_index,
                    audio_key=audio_key,
                    source_audio_size_bytes=nbytes,
                    audio_mime_guess=mime_guess,
                )
                mark_pending_recovery(
                    mx,
                    q_id=int(q_id),
                    audio_key=audio_key,
                    error_message=NEEDS_REVIEW_ERROR_SENTINEL,
                    attempts=attempts,
                )
            elif speech_issue == "no_speech":
                ns = apply_insufficient_response_result(
                    mx,
                    q,
                    q_id=int(q_id),
                    question_index=q_index,
                    audio_key=audio_key,
                    source_audio_size_bytes=nbytes,
                    audio_mime_guess=mime_guess,
                )
                mx["analysis_result"] = ns
                mx["last_result"] = ns
                clear_pending_recovery(mx)
                if _is_real_mock(mx) and not defer_navigation:
                    _set_real_mock_page("SPEECH_RECOVERY")
                    _set_mock_page(mx, "TEST")
                    _maybe_rerun()
                    return
                _finish_analysis_nav()
                return
            else:
                apply_unclear_speech_result(
                    mx,
                    q,
                    q_id=int(q_id),
                    question_index=q_index,
                    audio_key=audio_key,
                    source_audio_size_bytes=nbytes,
                    audio_mime_guess=mime_guess,
                )
                mark_pending_recovery(
                    mx,
                    q_id=int(q_id),
                    audio_key=audio_key,
                    error_message=UNCLEAR_SPEECH_ERROR_SENTINEL,
                    attempts=attempts,
                )
            _maybe_rerun()
            return

        _transcript_raw = (result.get("transcript") or "").strip()
        result_to_store = cache_analysis_payload(result)
        result_to_store = apply_completed_analysis_result(
            mx,
            q,
            q_id=int(q_id),
            question_index=q_index,
            audio_key=audio_key,
            result=result_to_store,
        )
        try:
            from utils.grade_debug import grade_debug, log_saved_result

            q_type = str(q.get("type") or "")
            grade_debug(
                f"Q{q_id} question_type={q_type!r} "
                f"analysis_function=_run_analysis "
                f"prompt_template_name=semantic_evaluation"
            )
            log_saved_result(f"Q{q_id}", result_to_store)
        except Exception:
            pass
        mx["preview_transcript"] = _transcript_raw
        mx["analysis_result"] = result_to_store
        raw_parse_failed = (result_to_store.get("raw_text_parse_failed") or "").strip()
        if raw_parse_failed:
            st.error(raw_parse_failed)
        mx["last_result"] = result_to_store
        _finish_analysis_nav()
    finally:
        _set_analysis_in_flight(analysis_mode, False)


# ---------------------------------------------------------------------------
# Recovery panel — surfaced only while ``pending_recovery`` is set for the
# current question. Three actions; never destructive.
# ---------------------------------------------------------------------------

_RECOVERY_COPY: dict[str, tuple[str, str]] = {
    "no_audio": (
        "녹음이 제대로 저장되지 않았어요",
        "마이크 권한을 확인하고, 조용한 환경에서 3초 이상 다시 녹음해 주세요. "
        "진행 상황과 다른 문항의 답변은 그대로 안전하게 보관됩니다.",
    ),
    "unclear_speech": (
        "말소리가 정확히 인식되지 않았어요",
        "녹음은 저장되었지만, AI가 답변을 충분히 읽지 못했어요. "
        "조금 더 또렷하게 다시 말하거나, 저장하고 다음 문항으로 넘어갈 수 있어요.",
    ),
    "needs_review": (
        "답변 일부가 불명확하게 인식되었어요",
        "녹음은 저장되었지만, AI가 답변 전체를 확신 있게 읽지 못했어요. "
        "조금 더 또렷하게 다시 말하거나, 같은 녹음으로 다시 분석할 수 있어요.",
    ),
    "non_english": (
        "영어로 답변해 주세요",
        "녹음은 정상적으로 저장되었지만, 답변이 영어가 아닌 언어로 인식되었어요. "
        "오픽 연습에서는 영어로 답변해야 AI 코칭을 받을 수 있어요.",
    ),
    "no_speech": (
        "음성이 감지되지 않았어요 🙏",
        "이번 답변에서 인식된 발화가 없어요. 마이크가 켜져 있는지 확인하고 "
        "조용한 환경에서 또렷한 목소리로 다시 한 번 답변해 보세요. "
        "진행 상황과 다른 문항의 답변은 그대로 안전하게 보관됩니다.",
    ),
    "overload": (
        "AI 분석 서버가 잠시 혼잡해요 🙏",
        "잠시 후 다시 시도하면 대부분 정상적으로 진행돼요. "
        "녹음과 진행 상황은 안전하게 보관 중입니다.",
    ),
    "rate_limit": (
        "잠시 후 다시 시도해 주세요 🙏",
        "잠깐 쉬어 가는 동안 녹음과 진행 상황은 안전하게 보관됩니다. "
        "약 1~2분 뒤에 다시 시도해 주세요.",
    ),
    "timeout": (
        "AI 분석이 잠시 지연되고 있어요 🙏",
        "네트워크가 잠깐 지연되는 상황이에요. 녹음은 그대로 남아 있으니 "
        "다시 분석하기를 눌러 같은 답변으로 재시도할 수 있어요.",
    ),
    "engine_path": (
        "AI 엔진 경로를 재설정 중이에요",
        "내부 모델 라우팅이 잠깐 흔들리는 상황이에요. "
        "‘다시 분석하기’를 한 번 더 눌러 주세요.",
    ),
    "unknown": (
        "AI 분석이 잠시 지연되고 있어요",
        "답변은 저장되었습니다. "
        "다음 문항으로 넘어가도 괜찮아요. 나중에 다시 분석할 수 있어요.",
    ),
}


def _render_api_delay_recovery_card(mx: dict, q: dict, q_id: int, audio_key: str) -> None:
    """Recovery UI when Gemini/API failed but the answer is already saved."""
    saved_audio = mx.get("audio_bytes") or mx.get("recordings", {}).get(audio_key)
    audio_size = len(saved_audio) if saved_audio else 0
    st.markdown(
        f"""
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">AI 분석 지연</div>
          <div class="rv-title">AI 분석이 잠시 지연되고 있어요</div>
          <div class="rv-body">답변은 저장되었습니다.<br/>
            다음 문항으로 넘어가도 괜찮아요. 나중에 다시 분석할 수 있어요.</div>
          <div class="rv-meta"><span>녹음 {html.escape(f"{audio_size:,}")} bytes 보존됨</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    row = find_result_row(mx, int(q_id))
    lr = (row or {}).get("result", {}) if isinstance(row, dict) else {}
    from utils.ai_pending_diag import render_ai_pending_dev_expander

    render_ai_pending_dev_expander(
        lr if isinstance(lr, dict) else {},
        pending_recovery=mx.get("pending_recovery"),
    )
    in_flight = _get_analysis_in_flight(_mock_mode(mx) or "coaching")
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "다시 분석하기",
            key=f"report_api_retry_{q_id}",
            type="primary",
            use_container_width=True,
            disabled=(audio_size == 0) or in_flight,
        ):
            api_key = get_gemini_api_key()
            if not api_key:
                st.error("Gemini API Key가 없어 다시 시도할 수 없습니다.")
            else:
                clear_pending_recovery(mx)
                if saved_audio:
                    mx["audio_bytes"] = saved_audio
                _run_analysis(mx, q, q_id, audio_key, api_key, from_retry=True)
    with c2:
        if st.button(
            "다음 문제로 넘어가기",
            key=f"report_api_next_{q_id}",
            use_container_width=True,
        ):
            _go_to_next_question(mx, q_id)


def _render_recovery_panel(mx: dict, q: dict, q_id: int, audio_key: str) -> None:
    """Friendly fallback UI shown when Gemini analysis has failed.

    Critical invariant: this view only mutates ``pending_recovery``. It
    never touches ``current_idx``, ``results``, ``current_exam``,
    ``audio_bytes``, or ``recordings`` — every retry path reads from the
    audio that was already preserved when the analysis first failed.
    """
    pr: dict = mx.get("pending_recovery") or {}
    err_kind = str(pr.get("error_kind") or "unknown")
    title, body = _RECOVERY_COPY.get(err_kind, _RECOVERY_COPY["unknown"])
    attempts = int(pr.get("attempts") or 0)
    saved_audio = mx.get("audio_bytes") or mx.get("recordings", {}).get(audio_key)
    audio_size = recording_byte_length(saved_audio)
    is_no_audio = err_kind == "no_audio"
    is_unclear = err_kind == "unclear_speech"
    is_needs_review = err_kind == "needs_review"
    is_non_english = err_kind == "non_english"
    is_legacy_no_speech = err_kind == "no_speech"
    if is_legacy_no_speech and audio_size >= MIN_RECORDED_AUDIO_BYTES:
        is_unclear = True
        is_legacy_no_speech = False
    is_speech_issue = (
        is_no_audio or is_unclear or is_needs_review or is_non_english or is_legacy_no_speech
    )

    if is_no_audio:
        eyebrow_text = "녹음 저장 실패"
    elif is_non_english:
        eyebrow_text = "언어 안내"
    elif is_unclear:
        eyebrow_text = "말소리 인식 어려움"
    elif is_needs_review:
        eyebrow_text = "인식 검토 필요"
    elif is_legacy_no_speech:
        eyebrow_text = "음성 미감지"
    else:
        eyebrow_text = "AI 분석 일시 지연"

    if (is_unclear or is_needs_review or is_non_english) and audio_size > 0:
        audio_meta = (
            f"[dev] 녹음 저장됨 · {audio_size:,} bytes"
            if st.session_state.get("show_dev_debug")
            else ""
        )
    elif is_no_audio:
        audio_meta = (
            (f"[dev] 녹음 {audio_size:,} bytes" if audio_size else "녹음 데이터 없음")
            if st.session_state.get("show_dev_debug")
            else ("녹음 데이터 없음" if not audio_size else "")
        )
    elif is_legacy_no_speech:
        audio_meta = "녹음 음성 미감지"
    else:
        audio_meta = (
            f"[dev] 녹음 {audio_size:,} bytes 보존됨"
            if st.session_state.get("show_dev_debug")
            else ""
        )

    st.markdown(
        f"""
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">{html.escape(eyebrow_text)}</div>
          <div class="rv-title">{html.escape(title)}</div>
          <div class="rv-body">{html.escape(body)}</div>
          <div class="rv-meta">
            <span>시도 횟수 {attempts}회</span>
            <span class="rv-sep">·</span>
            <span>{html.escape(audio_meta)}</span>
            <span class="rv-sep">·</span>
            <span>Q{q_id} 위치 유지</span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if is_speech_issue:
        row = find_result_row(mx, int(q_id))
        lr = (row or {}).get("result", {}) if isinstance(row, dict) else {}
        render_recording_debug_block(
            mx,
            audio_key,
            lr if isinstance(lr, dict) else {},
            q_index=int(mx.get("current_idx") or 0),
            blob=saved_audio,
        )
    else:
        row = find_result_row(mx, int(q_id))
        lr = (row or {}).get("result", {}) if isinstance(row, dict) else {}
        from utils.ai_pending_diag import render_ai_pending_dev_expander

        render_ai_pending_dev_expander(
            lr if isinstance(lr, dict) else {},
            pending_recovery=pr,
        )

    in_flight = _get_analysis_in_flight(_mock_mode(mx) or "coaching")
    c1, c2, c3 = st.columns(3)

    if is_unclear or is_needs_review or is_non_english:
        if is_non_english:
            row = find_result_row(mx, int(q_id))
            lr = (row or {}).get("result", {}) if isinstance(row, dict) else {}
            render_language_mismatch_preview(lr if isinstance(lr, dict) else {})
        with c1:
            if st.button(
                "같은 질문 다시 말하기",
                key=f"recover_rerecord_{q_id}",
                type="primary",
                use_container_width=True,
            ):
                reset_recording_timer()
                mx["audio_bytes"] = None
                mx["recordings"].pop(audio_key, None)
                mx["preview_transcript"] = None
                clear_pending_recovery(mx)
                st.rerun()
        with c2:
            if st.button(
                "다시 분석하기",
                key=f"recover_reanalyze_{q_id}",
                use_container_width=True,
                disabled=(audio_size == 0) or in_flight,
            ):
                api_key = get_gemini_api_key()
                if not api_key:
                    st.error("Gemini API Key가 없어 다시 시도할 수 없습니다.")
                else:
                    clear_pending_recovery(mx)
                    if saved_audio:
                        mx["audio_bytes"] = saved_audio
                    _run_analysis(mx, q, q_id, audio_key, api_key, from_retry=True)
        with c3:
            if st.button(
                "다음 문제로 넘어가기",
                key=f"recover_next_{q_id}",
                use_container_width=True,
            ):
                _go_to_next_question(mx, q_id)
        return

    if is_no_audio or is_legacy_no_speech:
        with c1:
            if st.button(
                "같은 질문 다시 말하기",
                key=f"recover_rerecord_na_{q_id}",
                type="primary",
                use_container_width=True,
            ):
                reset_recording_timer()
                mx["audio_bytes"] = None
                mx["recordings"].pop(audio_key, None)
                mx["preview_transcript"] = None
                clear_pending_recovery(mx)
                st.rerun()
        with c2:
            if st.button(
                "다음 문제로 넘어가기",
                key=f"recover_speech_next_{q_id}",
                use_container_width=True,
            ):
                _go_to_next_question(mx, q_id)
        with c3:
            if st.button(
                "🏠 홈으로",
                key=f"recover_home_{q_id}",
                use_container_width=True,
            ):
                st.session_state.page = "HOME"
                try:
                    st.query_params["nav"] = "HOME"
                except Exception:  # pragma: no cover
                    logger.debug("query_params set failed; ignoring")
                st.rerun()
        return

    with c1:
        if st.button(
            "🔄 다시 분석하기",
            key=f"recover_retry_{q_id}",
            type="primary",
            use_container_width=True,
            disabled=(audio_size == 0) or in_flight,
            help=(
                "AI 분석이 진행 중이에요. 잠시만 기다려 주세요."
                if in_flight
                else None
            ),
        ):
            api_key = get_gemini_api_key()
            if not api_key:
                st.error("Gemini API Key가 없어 다시 시도할 수 없습니다. 설정에서 키를 등록해 주세요.")
            else:
                clear_pending_recovery(mx)
                _run_analysis(mx, q, q_id, audio_key, api_key, from_retry=True)
    with c2:
        if st.button(
            "다음 문제로 넘어가기",
            key=f"recover_next_{q_id}",
            use_container_width=True,
        ):
            _go_to_next_question(mx, q_id)
    with c3:
        if st.button(
            "🏠 홈으로",
            key=f"recover_home_{q_id}",
            use_container_width=True,
        ):
            # Keep ``pending_recovery`` set so coming back to TEST shows
            # the same panel — the user explicitly paused mid-failure.
            st.session_state.page = "HOME"
            st.query_params.clear()
            st.query_params["nav"] = "HOME"
            st.rerun()

    preview = (pr.get("transcript_preview") or "").strip()
    if preview:

        def _preview_body() -> None:
            st.write(preview)

        render_collapsible_section(
            "복원된 발화 미리보기",
            f"mx_pr_preview_q{q_id}",
            _preview_body,
            css_scope="mx-col",
        )

    # Last-resort technical detail, collapsed by default so it doesn't
    # crowd the friendly copy.
    err_msg = (pr.get("error_message") or "").strip()
    if err_msg:

        def _tech_detail_body() -> None:
            st.code(err_msg, language="text")

        render_collapsible_section(
            "기술 상세",
            f"mx_pr_tech_q{q_id}",
            _tech_detail_body,
            css_scope="mx-col",
        )


def _render_precision_section(mx: dict) -> None:
    """Render optional precision analysis section safely."""
    results = mx.get("results") or mx.get("answers") or []
    if not results:
        return

    st.caption("문항별 세부 분석을 확인할 수 있어요.")
    for idx, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue
        res = item.get("result") if isinstance(item.get("result"), dict) else {}
        src = res if res else item
        status = (
            str(src.get("analysis_status") or src.get("diagnosis_status") or item.get("analysis_status") or "")
        )
        level = (
            src.get("estimated_level_display")
            or src.get("estimated_level")
            or item.get("estimated_level_display")
            or item.get("estimated_level")
            or "분석 대기"
        )
        transcript = str(src.get("transcript") or item.get("transcript") or "")

        qnum = item.get("q_id", idx)
        st.markdown(f"**Q{qnum}. {level}**")
        from services.exam_analytics import result_is_no_speech_row

        if result_is_no_speech_row(res) or status in ("no_speech", "insufficient_response"):
            st.info(
                "응답이 충분하지 않았어요. 이 문항은 말소리가 충분히 인식되지 않아 "
                "문법·표현 피드백을 제공하기 어렵습니다."
            )
        elif status in ["pending", "analysis_pending", "api_error", "failed"]:
            st.info("AI 분석 대기 중입니다. 나중에 다시 시도할 수 있어요.")
        elif transcript:
            st.caption(transcript[:300])
        else:
            st.caption("표시할 답변 내용이 없습니다.")


def _render_report(mx: dict) -> None:
    if (
        _is_real_mock(mx)
        and _real_mock_all_questions_saved(mx)
        and not mx.get("_view_completed_report")
        and not mx.get("exam_finished")
    ):
        _set_mock_page(mx, "TEST")
        _set_real_mock_page("FINAL_READY")
        _render_real_mock_final_ready(mx)
        return

    _mode = _mock_mode(mx)
    _report_title = "문항 리포트" if _is_real_mock(mx) else "말하기 코칭"
    _eyebrow_suffix = _mock_mode_label(_mode)
    render_top_bar(
        _report_title,
        back_href="?nav=MOCK&mock=TEST",
        eyebrow=f"{format_mock_attempt_label(mx)} · {_eyebrow_suffix}",
    )

    # Marker for the scoped Streamlit-widget overrides (button + expander).
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_learning_portal_back_button(mx)

    _exam_run = mx.get("current_exam") or mx["exam"]
    if _exam_run:
        if _is_real_mock(mx):
            if not _real_mock_defer_reconcile():
                reconcile_mock_exam_pointer(mx)
        else:
            reconcile_mock_exam_pointer(mx)

    _latest_ok_coaching = False
    _last_i = -1
    _is_pending = False
    if mx["results"]:
        _last_i = len(mx["results"]) - 1
        _lr = mx["results"][-1].get("result", {})
        _lq = mx["results"][-1].get("q_id")
        _heard_raw = (_lr.get("transcript") or "").strip()
        # Trust gate: AI-emitted no_speech OR sanitizer rejection both lead
        # to the friendly empty-state hero. We never render unknown text
        # as if it were the user's recorded speech.
        _has_real_speech = bool(_heard_raw) and is_real_speech_transcript(_heard_raw)
        _latest_ok_coaching = (
            _has_real_speech
            and _lr.get("diagnosis_status") == "ok"
            and not _is_pending_result(_lr)
        )
        _is_pending = _is_pending_result(_lr)
        _q_row = mx["results"][-1] if mx["results"] else {}
        _audio_key = (_q_row.get("audio_key") or f"q_{_lq}").strip()
        _q_obj = None
        for _eq in _exam_run:
            if isinstance(_eq, dict) and int(_eq.get("id", -1)) == int(_lq):
                _q_obj = _eq
                break

        if _is_pending and _q_obj and not _is_real_mock(mx):
            _render_api_delay_recovery_card(mx, _q_obj, int(_lq), _audio_key)
        elif _is_real_mock(mx) and (_latest_ok_coaching or _is_pending):
            _rm_sub = (
                "AI 분석이 잠시 지연되고 있어요. 다음 문항으로 넘어가도 괜찮아요."
                if _is_pending
                else "AI 분석은 최종 리포트에서 확인할 수 있어요."
            )
            st.markdown(
                f"""
                <section class="mx-report-hero">
                  <p class="mx-rh-eyebrow">Q{_lq} · 저장 완료</p>
                  <div class="mx-rh-title">Q{_lq} 답변이 저장되었습니다.</div>
                  <div class="mx-rh-transcript">{html.escape(_rm_sub)}</div>
                </section>
                """,
                unsafe_allow_html=True,
            )

        if _has_real_speech and not _is_real_mock(mx):
            _wpm = _lr.get("wpm")
            _sent = _lr.get("sentence_count", 0)
            _words = _lr.get("word_count", 0)
            meta_chips = []
            if isinstance(_wpm, (int, float)):
                meta_chips.append(f'<span class="mx-rh-chip">WPM {_wpm}</span>')
            meta_chips.append(f'<span class="mx-rh-chip">문장 {_sent}</span>')
            meta_chips.append(f'<span class="mx-rh-chip">단어 {_words}</span>')
            meta_html = f'<div class="mx-rh-meta">{"".join(meta_chips)}</div>'

            transcript_html = html.escape(_heard_raw)
            st.markdown(
                f"""
                <section class="mx-report-hero">
                  <p class="mx-rh-eyebrow">Q{_lq} · 복원 발화</p>
                  <div class="mx-rh-title">방금 말씀하신 흐름을 그대로 옮겨 적었어요</div>
                  <div class="mx-rh-transcript">{transcript_html}</div>
                  {meta_html}
                </section>
                """,
                unsafe_allow_html=True,
            )
            st.text_area(
                f"Q{_lq} 텍스트 (복사·수정용)",
                value=_heard_raw,
                height=140,
                key=f"restored_transcript_q_{_lq}",
            )
        elif _is_pending:
            pass
        elif not _has_real_speech:
            _render_speech_issue_hero(
                mx, _audio_key, _lr, q_label=int(_lq), q_index=int(mx.get("current_idx") or 0)
            )

        if (_latest_ok_coaching or _has_real_speech) and not _is_real_mock(mx):
            render_structured_coaching_report(
                _lr,
                _heard_raw,
                _lq,
                show_hero=True,
                question_text=str(q.get("question") or ""),
            )
        elif _lr.get("diagnosis_status") == "analysis_pending":
            pass
        else:
            _sum_rehab = (_lr.get("summary_speech_rehab") or "").strip()
            if _sum_rehab:

                def _ai_summary_body() -> None:
                    st.write(_sum_rehab)

                render_collapsible_section(
                    "AI 총평 보기",
                    f"mx_report_ai_sum_q{_lq}",
                    _ai_summary_body,
                    css_scope="mx-col",
                )

        _raw_parse_failed = (_lr.get("raw_text_parse_failed") or "").strip()
        if _raw_parse_failed:
            st.markdown(
                f'<div class="mx-status mx-status--error">'
                f'<span class="mx-status-icon">⚠️</span>'
                f'<span>{html.escape(_raw_parse_failed)}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )

    api_error_count = sum(
        1 for item in mx["results"] if item.get("result", {}).get("diagnosis_status") == "api_error"
    )
    if api_error_count:
        st.markdown(
            f'<div class="mx-status mx-status--warn">'
            f'<span class="mx-status-icon">⚠️</span>'
            f"<span>API 오류로 실패한 문항: <b>{api_error_count}개</b></span>"
            f"</div>",
            unsafe_allow_html=True,
        )

    if not _is_real_mock(mx):
        st.markdown('<div class="mx-section-h">이번 세션 문항 기록</div>', unsafe_allow_html=True)
        for i, item in enumerate(mx["results"]):
            if i == _last_i and _latest_ok_coaching:
                continue
            result = item.get("result", {})
            qid = item.get("q_id")
            label = clean_visible_label(
                f"Q{qid} | {item.get('type', '')} {item.get('topic', '')}".strip(),
                f"Q{qid}",
            )

            def _history_body(it=item) -> None:
                res = it.get("result") or {}
                q = it.get("q_id")
                if res.get("diagnosis_status") == "no_audio":
                    st.error(res.get("error", "녹음 데이터 없음"))
                    return
                if res.get("diagnosis_status") == "api_error":
                    st.error(res.get("error", "API 오류"))
                    return
                if res.get("diagnosis_status") == "analysis_pending":
                    st.info(
                        (res.get("summary_speech_rehab") or "").strip()
                        + " "
                        + (res.get("prescription") or "").strip()
                    )
                    return
                if "error" in res:
                    st.error(res["error"])
                    return
                st.caption(it.get("question", "") or "")
                if q == 1:
                    st.info("몸 풀기 단계입니다. 본인의 바이브를 잘 점검해 보세요.")
                render_history_expander_coaching(it)

            render_collapsible_section(
                label or f"Q{qid}",
                f"mx_hist_q{qid}",
                _history_body,
                css_scope="mx-col",
            )

    _answered_report = count_completed_exam_prefix(mx)
    has_next = (_answered_report < len(_exam_run)) and not mx.get("exam_finished")

    if not (_is_real_mock(mx) or _is_pending):
        render_coaching_retry_banner(has_next=has_next)
        render_coaching_cta_preamble(has_next=has_next)

    if has_next:
        col_secondary, col_primary = st.columns([1, 1])
        with col_primary:
            _next_label = "다음 문제로" if (_is_real_mock(mx) or _is_pending) else "다음 단계로 계속하기"
            if st.button(
                _next_label,
                type="primary",
                use_container_width=True,
                key="report_next_q",
            ):
                if _is_real_mock(mx) and _lq is not None:
                    go_to_next_real_mock_question(mx, from_q_id=int(_lq))
                    return
                if _is_pending and _lq is not None:
                    _go_to_next_question(mx, int(_lq))
                    return
                reset_recording_timer()
                reconcile_mock_exam_pointer(mx)
                mx["audio_bytes"] = None
                mx["preview_transcript"] = None
                mx["mock_page"] = "TEST"
                st.rerun()
        with col_secondary:
            if st.button(
                "홈에서 잠깐 쉬기",
                use_container_width=True,
                key="report_restart",
            ):
                reset_exam_state(mx, st.session_state)
                clear_mock_question_tts_keys()
                st.session_state.page = "HOME"
                st.query_params.clear()
                st.query_params["nav"] = "HOME"
                st.rerun()
    else:
        if _is_real_mock(mx):
            _ensure_real_mock_completion_state(mx)
            from services.final_report_preview import build_final_report_preview

            total = get_mock_total_questions(mx)
            preview = build_final_report_preview(mx.get("results") or [], total_count=total)
            st.markdown(
                """
                <section class="continue-card continue-card--start mx-landing-card" role="region"
                         aria-label="실전 모의고사 완료">
                  <div class="cc-eyebrow">완료</div>
                  <div class="cc-title">실전 모의고사가 완료되었어요</div>
                  <div class="cc-meta">모든 문항 답변이 저장되었습니다.<br/>
                    최종 리포트 미리보기를 확인한 뒤 전체 리포트를 열어 보세요.</div>
                </section>
                """,
                unsafe_allow_html=True,
            )
            render_final_report_preview_card(preview)
            c_final, c_back = st.columns(2)
            with c_final:
                if st.button(
                    "최종 리포트 보기",
                    type="primary",
                    use_container_width=True,
                    key="report_open_final_report",
                ):
                    _open_completed_final_report(mx)
                    st.rerun()
            with c_back:
                if st.button(
                    "학습하기로 돌아가기",
                    use_container_width=True,
                    key="report_back_portal",
                ):
                    _return_to_learning_portal_from_complete(mx)
                    st.rerun()
        elif st.button(
            "홈에서 잠깐 쉬기",
            use_container_width=True,
            key="report_restart",
        ):
            reset_exam_state(mx, st.session_state)
            clear_mock_question_tts_keys()
            st.session_state.page = "HOME"
            st.query_params.clear()
            st.query_params["nav"] = "HOME"
            st.rerun()

    if not _is_real_mock(mx):
        render_collapsible_section(
            "더 깊은 분석 (선택)",
            "mx_deep_precision",
            lambda: _render_precision_section(mx),
            css_scope="mx-col",
        )
        st.subheader("🧪 에릭의 발화 정밀 처방전")
        st.caption("FACT 기반 냉철 분석 모드: 어휘 · 논리 · 내용 중복 · 문법")
    for idx, item in enumerate(mx["results"]):
        if _is_real_mock(mx):
            continue
        result = item.get("result", {})
        if result.get("diagnosis_status") != "ok":
            continue

        qid = item.get("q_id")
        transcript = (result.get("transcript") or "").strip()
        if not transcript:
            continue

        def _precision_q_body(
            result=result,
            transcript=transcript,
            item=item,
            qid=qid,
        ) -> None:
            lines = []
            lower = transcript.lower()

            for weak, better in PRECISION_MAP.items():
                if re.search(rf"\b{re.escape(weak)}\b", lower):
                    lines.append(
                        {
                            "axis": "어휘 (Precision)",
                            "current": f"'{weak}'와 같은 평이한 단어 반복",
                            "recommend": f"{better} 같은 정밀 어휘로 교체해 표현 밀도를 높이세요.",
                        }
                    )

            text_type_score = (result.get("fact_scores") or {}).get("text_type", 0)
            marker_hit = any(m.lower() in lower for m in [m.lower() for m in DISCOURSE_MARKERS])
            if text_type_score < 60 or not marker_hit:
                lines.append(
                    {
                        "axis": "논리 (Text Type)",
                        "current": "문장 연결이 단조롭거나 구조 전개가 약함",
                        "recommend": f"{', '.join(DISCOURSE_MARKERS[:4])} 등을 활용해 문장 간 전개를 분명히 하세요.",
                    }
                )

            cur_keys = keywords(transcript)
            overlap_warned = False
            for prev in mx["results"][:idx]:
                prev_t = (prev.get("result", {}) or {}).get("transcript", "")
                prev_keys = keywords(prev_t)
                if not prev_keys:
                    continue
                inter = cur_keys & prev_keys
                ratio = len(inter) / max(1, min(len(cur_keys), len(prev_keys)))
                if ratio >= 0.45:
                    lines.append(
                        {
                            "axis": "내용 중복 (Repetition)",
                            "current": f"Q{prev.get('q_id')}와 소재/표현이 상당히 겹침",
                            "recommend": "동일한 소재의 반복은 평가에서 불리할 수 있습니다. 새로운 관점(인물·장소·갈등·결과)을 추가하세요.",
                        }
                    )
                    overlap_warned = True
                    break
            if not overlap_warned and len(cur_keys) < 8:
                lines.append(
                    {
                        "axis": "내용 중복 (Repetition)",
                        "current": "핵심 소재 풀이 좁아 반복 위험이 높음",
                        "recommend": "소재 축을 넓혀 주세요: 감정 변화, 예외 상황, 교훈, 비교 관점을 하나씩 추가하세요.",
                    }
                )

            breakdown = (result.get("breakdown") or "").strip()
            if breakdown and breakdown != "없음":
                lines.append(
                    {
                        "axis": "문법 (Accuracy)",
                        "current": breakdown[:120] + ("..." if len(breakdown) > 120 else ""),
                        "recommend": "시제 붕괴/수 일치를 먼저 고정하세요. 핵심 동사 시제를 문단 끝까지 유지하는 훈련이 필요합니다.",
                    }
                )

            wpm = result.get("wpm", 0)
            if isinstance(wpm, (int, float)) and wpm >= 200 and len(cur_keys) < 10:
                lines.append(
                    {
                        "axis": "냉철 코멘트",
                        "current": "속도는 높지만 어휘·내용 밀도가 낮음",
                        "recommend": "단어 사용이 똑같고 논리 구조 미흡합니다. 속도보다 정보 밀도(근거/장면/결과)를 우선 보강하세요.",
                    }
                )

            # When no specific finding triggered, surface only a quiet status
            # caption — replaces the old "표현 다양성만 소폭 확장" generic
            # boilerplate that fired on every clean answer.
            if not lines:
                st.caption("이 답변에서는 별도의 정밀 처방 항목이 감지되지 않았습니다.")
                return

            for row in lines:
                st.markdown(
                    f"- **{row['axis']}** | 현재 발화: {row['current']} | 에릭의 추천: {row['recommend']}"
                )

        render_collapsible_section(
            f"Q{qid} 정밀 처방",
            f"mx_precision_q{qid}",
            _precision_q_body,
            css_scope="mx-col",
        )
