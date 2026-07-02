"""Isolated 5-minute mini mock V2 — Gemini report after save; no legacy mini_mock flow."""

from __future__ import annotations

import base64
import html
import logging
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

import re

from components.answer_countdown_timer import (
    DEFAULT_DURATION_SEC,
    build_answer_timer_id,
    dismiss_answer_timer_signal,
    handle_answer_timer_expiry,
    render_answer_countdown_timer,
)
from components.exam_question_screen import (
    build_progress_segments_html,
    opic_type_badge_label,
    render_exam_answer_card_top,
    render_exam_question_shell,
    render_exam_wave_mic_observer,
)
from components.exam_saved_screen import render_saved_transcript
from components.feedback_loading_card import render_feedback_loading_card
from components.recovery_card import (
    render_analysis_recovery_card,
    render_recovery_retry_caption_html,
)
from components.final_report_hero import (
    collect_hero_display_metrics,
    render_final_report_completion_hero_html,
)
from components.score_donut_bars import render_score_donut_bars_html
from components.topbar import render_top_bar
from utils.analysis_request_guard import (
    button_state as guard_button_state,
    can_request as guard_can_request,
    clear_guard as guard_clear_guard,
    clear_stale_in_flight as guard_clear_stale_in_flight,
    key_in_flight as guard_key_in_flight,
    register_failure as guard_register_failure,
    reset_guard as guard_reset_guard,
    set_in_flight as guard_set_in_flight,
)
from utils.local_profile import iso_now

logger = logging.getLogger(__name__)

_MINI_MOCK_V2_ACTIVE_KEY = "mini_mock_v2_active"
ACTIVE_LEARNING_MODE_KEY = "active_learning_mode"
ACTIVE_LEARNING_MODE_MINI_V2 = "mini_mock_v2"
_QUESTION_COUNT = 3

_KEY_STEP = "mini_v2_step"
_KEY_INDEX = "mini_v2_index"
_KEY_ANSWERS = "mini_v2_answers"
_KEY_RECORDING_ACTIVE = "mini_v2_recording_active"
_KEY_LAST_SAVED = "mini_v2_last_saved_index"
_KEY_REPORT = "mini_v2_report_result"
_KEY_ANALYSIS_ATTEMPT = "mini_v2_analysis_attempt_id"
_KEY_ANALYSIS_STARTED = "mini_v2_analysis_started_at"
_KEY_ANALYSIS_STARTED_ATTEMPT = "mini_v2_analysis_started_attempt"
_KEY_ANALYSIS_FINISHED_ATTEMPT = "mini_v2_analysis_finished_attempt"
_KEY_RECORDINGS = "mini_v2_recordings"
_KEY_AUDIO_BLOBS = "mini_v2_audio_blobs"
_KEY_QUESTIONS = "mini_v2_questions"

_MIN_ANSWER_MIN_WORDS = 5
_MIN_TEXT_MIN_WORDS = 5

_ANALYSIS_TIMEOUT_SEC = 60

# Analysis burst-prevention guards (utils/analysis_request_guard.py).
_ANALYSIS_GUARD_PREFIX = "mini_v2_analysis"
_STT_RETRY_GUARD_PREFIX = "mini_v2_stt_retry"
_KEY_STT_RETRY_ACTIVE_QIDX = "mini_v2_stt_retry_active_q_idx"
_ANALYSIS_ENTITY_ID = "default"

_ANALYSIS_MAX_ATTEMPTS = 4
_ANALYSIS_STALE_SEC = 60
_ANALYSIS_COOLDOWN_BASE = 45
_ANALYSIS_COOLDOWN_STEP = 15
_ANALYSIS_COOLDOWN_MAX = 90

_STT_RETRY_MAX_ATTEMPTS = 4
_STT_RETRY_STALE_SEC = 30
_STT_RETRY_COOLDOWN_BASE = 10
_STT_RETRY_COOLDOWN_STEP = 5
_STT_RETRY_COOLDOWN_MAX = 30

_MINI_V2_ANALYSIS_LABELS: Dict[str, Any] = {
    "idle": "AI 진단 리포트 받기",
    "in_flight": "리포트 생성 중…",
    "cooldown": lambda rem: f"{rem}초 후 다시",
    "maxed": "잠시 후 다시 시도",
}
_MINI_V2_ANALYSIS_RETRY_LABELS: Dict[str, Any] = {
    "idle": "저장된 답변으로 다시 분석하기",
    "in_flight": "리포트 생성 중…",
    "cooldown": lambda rem: f"{rem}초 후 다시",
    "maxed": "잠시 후 다시 시도",
}
_STT_RETRY_IDLE_LABEL = "음성 인식 다시 시도"
_MINI_V2_STT_RETRY_LABELS: Dict[str, Any] = {
    "idle": _STT_RETRY_IDLE_LABEL,
    "in_flight": "인식 중…",
    "cooldown": lambda rem: f"{rem}초 후",
    "maxed": "잠시 후 다시 시도",
}

_VALID_STEPS = frozenset({
    "question",
    "recording",
    "saved",
    "ready_report",
    "analyzing",
    "report",
    "pending",
})

_SCORE_LABELS = {
    "response_amount": "답변량",
    "relevance": "질문 적합도",
    "structure": "답변 구조",
    "grammar": "문법",
    "vocabulary": "어휘",
    "naturalness": "자연스러움",
}

# Legacy mini mock session keys — cleared on V2 entry only.
_OLD_MINI_MOCK_SESSION_KEYS = (
    "mini_mock_page",
    "mini_mock_question_index",
    "mini_mock_results",
    "mini_mock_report_status",
    "mini_mock_report_result",
    "mini_mock_completed",
    "mini_mock_last_saved_q_idx",
    "mini_mock_analysis_started_at",
    "mini_mock_pending_reason",
    "mini_mock_analysis_in_flight",
    "mini_mock_analysis_in_progress",
    "mini_mock_analysis_attempt_id",
    "mini_mock_analysis_batch_finished",
    "_mini_mock_last_batch_attempts",
    "latest_mini_mock_api_debug",
    "mini_mock_last_api_error_category",
    "mini_mock_last_api_error_preview",
    "mini_mock_speech_recovery_q_idx",
)

_OLD_MINI_MOCK_MX_KEYS = (
    "mini_mock_page",
    "mini_mock_question_index",
    "mini_mock_results",
    "mini_mock_report_status",
    "mini_mock_last_saved_q_idx",
)


def _failure_category(result: Dict[str, Any]) -> str:
    cat = str(result.get("error_category") or "").strip()
    return cat or "api_error"


def _analysis_button_state(*, retry: bool = False) -> Tuple[bool, str]:
    labels = _MINI_V2_ANALYSIS_RETRY_LABELS if retry else _MINI_V2_ANALYSIS_LABELS
    guard_clear_stale_in_flight(
        st.session_state,
        _ANALYSIS_GUARD_PREFIX,
        stale_sec=_ANALYSIS_STALE_SEC,
    )
    return guard_button_state(
        st.session_state,
        _ANALYSIS_GUARD_PREFIX,
        _ANALYSIS_ENTITY_ID,
        labels=labels,
        max_attempts=_ANALYSIS_MAX_ATTEMPTS,
        stale_sec=_ANALYSIS_STALE_SEC,
    )


def _stt_retry_entity_id(q_idx: int) -> str:
    return str(int(q_idx))


def _stt_retry_button_state(q_idx: int) -> Tuple[bool, str]:
    entity_id = _stt_retry_entity_id(q_idx)
    guard_clear_stale_in_flight(
        st.session_state,
        _STT_RETRY_GUARD_PREFIX,
        stale_sec=_STT_RETRY_STALE_SEC,
    )
    disabled, guard_label = guard_button_state(
        st.session_state,
        _STT_RETRY_GUARD_PREFIX,
        entity_id,
        labels=_MINI_V2_STT_RETRY_LABELS,
        max_attempts=_STT_RETRY_MAX_ATTEMPTS,
        stale_sec=_STT_RETRY_STALE_SEC,
    )
    if not disabled:
        return False, _STT_RETRY_IDLE_LABEL
    if st.session_state.get(guard_key_in_flight(_STT_RETRY_GUARD_PREFIX)):
        active = str(st.session_state.get(_KEY_STT_RETRY_ACTIVE_QIDX) or "")
        if active == entity_id:
            return True, "인식 중…"
        return True, _STT_RETRY_IDLE_LABEL
    if guard_label != _STT_RETRY_IDLE_LABEL:
        return True, guard_label
    return True, _STT_RETRY_IDLE_LABEL


def _release_v2_analysis_guard(result: Dict[str, Any]) -> None:
    guard_set_in_flight(st.session_state, _ANALYSIS_GUARD_PREFIX, False)
    if result.get("ok"):
        guard_clear_guard(
            st.session_state, _ANALYSIS_GUARD_PREFIX, _ANALYSIS_ENTITY_ID
        )
    else:
        guard_register_failure(
            st.session_state,
            _ANALYSIS_GUARD_PREFIX,
            _ANALYSIS_ENTITY_ID,
            _failure_category(result),
            base_cooldown=_ANALYSIS_COOLDOWN_BASE,
            step=_ANALYSIS_COOLDOWN_STEP,
            max_cooldown=_ANALYSIS_COOLDOWN_MAX,
        )


def _try_start_v2_analysis(*, retry: bool = False) -> bool:
    """Guarded entry — blocks burst clicks before new attempt IDs are minted."""
    allowed, block_msg = guard_can_request(
        st.session_state,
        _ANALYSIS_GUARD_PREFIX,
        _ANALYSIS_ENTITY_ID,
        max_attempts=_ANALYSIS_MAX_ATTEMPTS,
        stale_sec=_ANALYSIS_STALE_SEC,
    )
    if not allowed:
        if block_msg:
            st.warning(block_msg)
        return False
    guard_set_in_flight(st.session_state, _ANALYSIS_GUARD_PREFIX, True)
    _begin_v2_analysis(retry=retry)
    return True


def _questions() -> List[Dict[str, Any]]:
    cached = st.session_state.get(_KEY_QUESTIONS)
    if isinstance(cached, list) and len(cached) >= _QUESTION_COUNT:
        return [dict(r) for r in cached[:_QUESTION_COUNT]]
    return _ensure_mini_v2_questions()


def _ensure_mini_v2_questions() -> List[Dict[str, Any]]:
    """Build or restore the 3-question set; persist in session for reruns/resume."""
    cached = st.session_state.get(_KEY_QUESTIONS)
    if isinstance(cached, list) and len(cached) >= _QUESTION_COUNT:
        return [dict(r) for r in cached[:_QUESTION_COUNT]]
    try:
        from services.mock_v2_question_selector import build_mini_mock_v2_questions

        rows = build_mini_mock_v2_questions()
    except Exception:
        logger.warning("[MINI_MOCK_V2] bank question build failed — fallback", exc_info=True)
        rows = _fallback_questions()
    if not isinstance(rows, list) or len(rows) < _QUESTION_COUNT:
        rows = _fallback_questions()
    st.session_state[_KEY_QUESTIONS] = [dict(r) for r in rows[:_QUESTION_COUNT]]
    return [dict(r) for r in st.session_state[_KEY_QUESTIONS]]


def _fallback_questions() -> List[Dict[str, Any]]:
    return [
        {
            "question_id": "mini_v2_q1",
            "question_index": 0,
            "type": "description",
            "type_label": "묘사",
            "question_en": "Tell me about a place you often go to.",
            "question_ko": "자주 가는 장소에 대해 말해 주세요.",
        },
        {
            "question_id": "mini_v2_q2",
            "question_index": 1,
            "type": "memorable_experience",
            "type_label": "기억에 남는 경험",
            "question_en": "Tell me about a memorable experience you had there.",
            "question_ko": "그곳에서 있었던 기억에 남는 경험을 말해 주세요.",
        },
        {
            "question_id": "mini_v2_q3",
            "question_index": 2,
            "type": "roleplay",
            "type_label": "롤플레이",
            "question_en": (
                "I'm your friend. Ask me two or three questions about visiting that place."
            ),
            "question_ko": "친구 역할로, 그곳을 방문하는 것에 대해 두세 가지 질문해 주세요.",
        },
    ]


def _question_at(index: int) -> Dict[str, Any]:
    qs = _questions()
    idx = max(0, min(_QUESTION_COUNT - 1, int(index)))
    return dict(qs[idx])


def is_mini_mock_v2_active() -> bool:
    """True when the student is in the isolated V2 flow (not legacy mini mock)."""
    mode = str(st.session_state.get(ACTIVE_LEARNING_MODE_KEY) or "").strip()
    if mode == ACTIVE_LEARNING_MODE_MINI_V2:
        return True
    return bool(st.session_state.get(_MINI_MOCK_V2_ACTIVE_KEY))


def _reset_mini_v2_analysis_guards() -> None:
    guard_reset_guard(st.session_state, _ANALYSIS_GUARD_PREFIX)
    guard_reset_guard(st.session_state, _STT_RETRY_GUARD_PREFIX)
    st.session_state.pop(_KEY_STT_RETRY_ACTIVE_QIDX, None)


def reset_mini_mock_v2() -> None:
    """Clear only V2 session keys."""
    from utils.v2_flow_persistence import clear_mini_v2_disk_snapshot

    clear_mini_v2_disk_snapshot(st.session_state)
    _reset_mini_v2_analysis_guards()
    st.session_state.pop(_KEY_STEP, None)
    st.session_state.pop(_KEY_INDEX, None)
    st.session_state.pop(_KEY_ANSWERS, None)
    st.session_state.pop(_KEY_RECORDING_ACTIVE, None)
    st.session_state.pop(_KEY_LAST_SAVED, None)
    st.session_state.pop(_MINI_MOCK_V2_ACTIVE_KEY, None)
    st.session_state.pop(ACTIVE_LEARNING_MODE_KEY, None)
    st.session_state.pop(_KEY_REPORT, None)
    st.session_state.pop(_KEY_ANALYSIS_ATTEMPT, None)
    st.session_state.pop(_KEY_ANALYSIS_STARTED, None)
    st.session_state.pop(_KEY_ANALYSIS_STARTED_ATTEMPT, None)
    st.session_state.pop(_KEY_ANALYSIS_FINISHED_ATTEMPT, None)
    st.session_state.pop(_KEY_RECORDINGS, None)
    st.session_state.pop(_KEY_AUDIO_BLOBS, None)
    st.session_state.pop(_KEY_QUESTIONS, None)
    st.session_state.pop("recording_active_audio_key", None)
    try:
        logger.info("[MINI_MOCK_V2] reset_mini_mock_v2")
    except Exception:
        pass


def clear_old_mini_mock_keys_for_v2() -> list[str]:
    """Drop legacy mini-mock session/mx keys when entering V2."""
    cleared: list[str] = []
    for key in _OLD_MINI_MOCK_SESSION_KEYS:
        if key in st.session_state:
            cleared.append(key)
        st.session_state.pop(key, None)
    for k in list(st.session_state.keys()):
        if isinstance(k, str) and (
            k.startswith("mm_saved_confirm_") or k.startswith("mini_mock_saved_confirm_")
        ):
            cleared.append(k)
            st.session_state.pop(k, None)
    mx = st.session_state.get("mock")
    if isinstance(mx, dict):
        for key in _OLD_MINI_MOCK_MX_KEYS:
            if key in mx:
                cleared.append(f"mx.{key}")
            mx.pop(key, None)
    try:
        from utils.mini_mock_state import clear_mini_mock_recordings

        clear_mini_mock_recordings()
    except Exception:
        logger.debug("[MINI_MOCK_V2] clear_mini_mock_recordings skipped", exc_info=True)
    try:
        logger.info("[MINI_MOCK_V2] clear_old_keys count=%s", len(cleared))
    except Exception:
        pass
    return cleared


def _init_v2_session() -> None:
    st.session_state[_KEY_STEP] = "question"
    st.session_state[_KEY_INDEX] = 0
    st.session_state[_KEY_ANSWERS] = []
    st.session_state[_KEY_RECORDING_ACTIVE] = False
    st.session_state.pop(_KEY_QUESTIONS, None)
    _ensure_mini_v2_questions()


def begin_mini_mock_v2_session(mx: dict) -> None:
    """Portal entry — legacy keys cleared, V2 state initialized."""
    clear_old_mini_mock_keys_for_v2()
    reset_mini_mock_v2()
    _init_v2_session()
    st.session_state["mock_mode"] = "mini_mock"
    st.session_state[ACTIVE_LEARNING_MODE_KEY] = ACTIVE_LEARNING_MODE_MINI_V2
    st.session_state[_MINI_MOCK_V2_ACTIVE_KEY] = True
    st.session_state["practice_portal_selected"] = True
    if isinstance(mx, dict):
        mx["mock_mode"] = "mini_mock"
        for key in _OLD_MINI_MOCK_MX_KEYS:
            mx.pop(key, None)
    try:
        logger.info("[MINI_MOCK_V2] session_started")
    except Exception:
        pass


def _answers() -> List[Dict[str, Any]]:
    raw = st.session_state.get(_KEY_ANSWERS)
    if not isinstance(raw, list):
        raw = []
        st.session_state[_KEY_ANSWERS] = raw
    return raw


def _answer_for_index(index: int) -> Optional[Dict[str, Any]]:
    for row in _answers():
        if not isinstance(row, dict):
            continue
        if int(row.get("question_index", -1)) == int(index):
            return row
    return None


def _mini_v2_count_words(text: str) -> int:
    """Count English-like words safely; ignore empty strings."""
    if not text or not str(text).strip():
        return 0
    return len(re.findall(r"[a-zA-Z']+", str(text)))


def _mini_v2_resolved_text(
    *,
    transcript: str = "",
    raw_transcript: str = "",
    student_answer: str = "",
) -> str:
    """Transcript text for status/metrics — transcript fields only, not WPM."""
    for part in (student_answer, transcript, raw_transcript):
        val = str(part or "").strip()
        if val:
            return val
    return ""


def _mini_v2_row_word_count(row: Optional[Dict[str, Any]]) -> int:
    if not row or not isinstance(row, dict):
        return 0
    return _mini_v2_count_words(
        _mini_v2_resolved_text(
            transcript=str(row.get("transcript") or ""),
            raw_transcript=str(row.get("raw_transcript") or ""),
            student_answer=str(row.get("student_answer") or ""),
        )
    )


def _mini_v2_saved_answer_label(row: Optional[Dict[str, Any]]) -> str:
    if not row or not isinstance(row, dict):
        return "미저장"
    status = str(row.get("status") or "").strip()
    if status == "saved":
        return "저장 완료"
    if status == "insufficient_response":
        return "응답 짧음"
    if status == "stt_failed":
        return "음성 저장됨 · 인식 실패"
    if status == "recording_failed":
        return "녹음 실패"
    if status == "stt_pending":
        return "음성 저장됨 · 인식 대기"
    wc = _mini_v2_row_word_count(row)
    if wc >= _MIN_ANSWER_MIN_WORDS:
        return "저장 완료"
    if wc >= 1:
        return "응답 짧음"
    if bool(row.get("audio_saved")) or int(row.get("audio_len") or 0) > 0:
        return "음성 저장됨 · 인식 실패"
    return "녹음 실패"


def _compute_mini_v2_statuses(
    *,
    audio_len: int,
    stt_result: Dict[str, Any],
    transcript: str,
    raw_transcript: str,
) -> Dict[str, Any]:
    """Derive recording_status, stt_status, status, student_answer from audio + STT."""
    text = _mini_v2_resolved_text(
        transcript=transcript,
        raw_transcript=raw_transcript,
        student_answer="",
    )
    if not text and raw_transcript.strip():
        text = raw_transcript.strip()
    word_count = _mini_v2_count_words(text)
    err_cat = str(stt_result.get("error_category") or "").strip()

    if audio_len <= 0:
        return {
            "recording_status": "recording_failed",
            "stt_status": "stt_skipped_no_audio",
            "status": "recording_failed",
            "student_answer": "",
            "word_count": 0,
        }

    recording_status = "recorded"
    from services.stt_service import is_stt_no_speech_result

    if is_stt_no_speech_result(stt_result):
        return {
            "recording_status": recording_status,
            "stt_status": "insufficient_response",
            "status": "insufficient_response",
            "student_answer": "",
            "word_count": 0,
        }

    if text:
        stt_status = "transcript_ready"
        status = "saved" if word_count >= _MIN_ANSWER_MIN_WORDS else "insufficient_response"
        return {
            "recording_status": recording_status,
            "stt_status": stt_status,
            "status": status,
            "student_answer": text,
            "word_count": word_count,
        }

    from services.api_retry_policy import is_retryable_error

    if is_retryable_error(err_cat) or stt_result.get("retry_exhausted"):
        stt_status = "stt_pending"
        status = "stt_pending"
    else:
        stt_status = "stt_failed"
        status = "stt_failed"

    return {
        "recording_status": recording_status,
        "stt_status": stt_status,
        "status": status,
        "student_answer": "",
        "word_count": 0,
    }


def _log_mini_v2_final_row_status(q_idx: int, row: Dict[str, Any]) -> None:
    try:
        logger.info(
            "[MINI_V2_FINAL_ROW_STATUS] q=%s status=%s recording_status=%s "
            "stt_status=%s word_count=%s",
            q_idx + 1,
            row.get("status"),
            row.get("recording_status"),
            row.get("stt_status"),
            row.get("word_count"),
        )
    except Exception:
        pass


def _mini_v2_estimate_wpm(word_count: int, duration_seconds: float) -> float:
    try:
        dur = float(duration_seconds)
    except (TypeError, ValueError):
        dur = 0.0
    if dur <= 0:
        return 0.0
    try:
        wc = int(word_count)
    except (TypeError, ValueError):
        wc = 0
    if wc <= 0:
        return 0.0
    return round(wc / (dur / 60.0), 1)


def _duration_from_mic_result(mic_result: Any) -> tuple[float, str]:
    """Extract duration from mic_recorder dict when present."""
    if not isinstance(mic_result, dict):
        return 0.0, "unavailable"
    for key in ("duration_seconds", "duration", "seconds"):
        if key not in mic_result:
            continue
        try:
            val = float(mic_result[key])
        except (TypeError, ValueError):
            continue
        if val > 0:
            return val, "mic_result"
    return 0.0, "unavailable"


def _resolve_mini_v2_duration(
    mic_result: Any,
    audio_bytes: bytes,
    mime_type: str,
) -> tuple[float, str]:
    """Mic metadata first, then audio byte estimate; never raises."""
    dur, method = _duration_from_mic_result(mic_result)
    if dur > 0:
        return dur, method
    blob = bytes(audio_bytes) if audio_bytes else b""
    if not blob:
        return 0.0, "unavailable"
    try:
        from services.evaluation.eval_audio import compute_audio_duration_seconds

        est_dur, _ = compute_audio_duration_seconds(blob, mime_type or "")
        if est_dur and float(est_dur) > 0:
            return float(est_dur), "audio_estimate"
    except Exception:
        logger.debug("[MINI_V2_DURATION] audio estimate failed", exc_info=True)
    return 0.0, "unavailable"


def _set_v2_step_saved(q_idx: int) -> None:
    st.session_state[_KEY_STEP] = "saved"
    st.session_state[_KEY_RECORDING_ACTIVE] = False
    st.session_state[_KEY_LAST_SAVED] = int(q_idx)


def _v2_recordings() -> Dict[str, bytes]:
    raw = st.session_state.get(_KEY_RECORDINGS)
    if not isinstance(raw, dict):
        raw = {}
        st.session_state[_KEY_RECORDINGS] = raw
    return raw


def _v2_audio_blobs() -> Dict[int, Dict[str, Any]]:
    raw = st.session_state.get(_KEY_AUDIO_BLOBS)
    if not isinstance(raw, dict):
        raw = {}
        st.session_state[_KEY_AUDIO_BLOBS] = raw
    return raw


def _save_v2_audio_blob(q_idx: int, audio_bytes: bytes, mime_type: str) -> None:
    """Persist playback audio per question — not stored on the answer row."""
    try:
        blob = bytes(audio_bytes) if audio_bytes else b""
    except (TypeError, ValueError):
        blob = b""
    if not blob:
        return
    idx = int(q_idx)
    resolved_mime = (mime_type or "audio/webm").strip() or "audio/webm"
    _v2_audio_blobs()[idx] = {
        "audio_bytes": blob,
        "mime_type": resolved_mime,
        "created_at": iso_now(),
    }
    # Single storage location — duplicate mini_v2_recordings copy removed to cut
    # session memory (~2× per question) and speed reruns on Render.


def _get_v2_audio_blob(q_idx: int) -> tuple[bytes, str]:
    """Return (audio_bytes, mime_type) for playback; empty if unavailable."""
    idx = int(q_idx)
    entry = _v2_audio_blobs().get(idx)
    if isinstance(entry, dict):
        raw = entry.get("audio_bytes")
        if raw is not None:
            try:
                blob = bytes(raw)
                if blob:
                    mime = str(entry.get("mime_type") or "audio/webm").strip() or "audio/webm"
                    return blob, mime
            except (TypeError, ValueError):
                pass
    legacy = _v2_recordings().get(_mini_v2_audio_storage_key(idx))
    if legacy is not None:
        try:
            blob = bytes(legacy)
            if blob:
                return blob, "audio/webm"
        except (TypeError, ValueError):
            pass
    return b"", ""


def _mini_v2_mic_key(q_idx: int) -> str:
    return f"mini_v2_mic_{q_idx}"


def _mini_v2_audio_storage_key(q_idx: int) -> str:
    return f"mini_v2_audio_{q_idx}"


def _mini_v2_mic_session_output_key(mic_key: str) -> str:
    return f"{mic_key}_output"


def _mini_v2_mime_from_mic_dict(mic_dict: Dict[str, Any], audio_bytes: bytes) -> str:
    for key in ("mime_type", "mimeType", "type"):
        val = str(mic_dict.get(key) or "").strip()
        if val:
            if "/" in val:
                return val
            from utils.audio_utils import mime_from_audio_format

            return mime_from_audio_format(val)
    fmt = str(mic_dict.get("format") or "").strip()
    if fmt:
        from utils.audio_utils import mime_from_audio_format

        return mime_from_audio_format(fmt)
    from services.evaluation.audio_mime import resolve_audio_mime

    return resolve_audio_mime(audio_bytes, "")


def _coerce_mic_payload_to_bytes(raw: Any) -> Tuple[bytes, str]:
    """Convert mic payload value to bytes; return (blob, failure_category)."""
    if raw is None:
        return b"", "missing"
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw), ""
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return b"", "empty_string"
        try:
            return base64.b64decode(text, validate=False), ""
        except Exception:
            logger.debug("[MINI_V2_AUDIO_EXTRACT] base64_decode_failed", exc_info=True)
            return b"", "base64_decode_failed"
    if isinstance(raw, list):
        try:
            return bytes(int(x) for x in raw), ""
        except (TypeError, ValueError):
            return b"", "list_int_convert_failed"
    try:
        return bytes(raw), ""
    except (TypeError, ValueError):
        return b"", "unsupported_type"


def _extract_mini_v2_audio_bytes(
    mic_result: Any,
    *,
    mic_key: str = "",
) -> Tuple[bytes, str, str]:
    """
    Normalize streamlit_mic_recorder return value to (bytes, mime_type, source).
    Falls back to session_state[mic_key + '_output'] when just_once clears return.
    """
    sources: List[Any] = []
    if mic_result is not None:
        sources.append(mic_result)
    if mic_key:
        cached = st.session_state.get(_mini_v2_mic_session_output_key(mic_key))
        if cached is not None and cached is not mic_result:
            sources.append(cached)

    last_fail = "no_payload"
    for payload in sources:
        if isinstance(payload, (bytes, bytearray)):
            blob = bytes(payload)
            if blob:
                return blob, "audio/webm", "raw_bytes"
            last_fail = "empty_bytes"
            continue
        if not isinstance(payload, dict):
            last_fail = "unsupported_type"
            continue
        mime_type = _mini_v2_mime_from_mic_dict(payload, b"")
        for key in ("bytes", "audio", "blob", "data", "audio_bytes"):
            if key not in payload:
                continue
            blob, fail = _coerce_mic_payload_to_bytes(payload.get(key))
            if fail:
                last_fail = fail
                continue
            if blob:
                resolved_mime = _mini_v2_mime_from_mic_dict(payload, blob)
                return blob, resolved_mime, f"dict_{key}"
        last_fail = "dict_no_audio_field"

    try:
        logger.warning("[MINI_V2_AUDIO_EXTRACT] failed category=%s", last_fail)
    except Exception:
        pass
    return b"", "", last_fail


def _log_mini_v2_mic_result(
    q_idx: int,
    mic_result: Any,
    *,
    audio_bytes: bytes,
    mime_type: str,
    extraction_source: str,
) -> None:
    try:
        result_type = type(mic_result).__name__ if mic_result is not None else "None"
        keys = (
            sorted(str(k) for k in mic_result.keys()) if isinstance(mic_result, dict) else []
        )
        has_bytes = len(audio_bytes) > 0
        logger.info(
            "[MINI_V2_MIC_RESULT] q=%s type=%s keys=%s has_bytes=%s audio_len=%s "
            "mime_type=%s extraction_source=%s",
            q_idx + 1,
            result_type,
            keys,
            has_bytes,
            len(audio_bytes),
            mime_type or "—",
            extraction_source or "—",
        )
    except Exception:
        pass


def _normalize_mini_v2_stt_result(stt_result: Any) -> Dict[str, Any]:
    """Accept dict or legacy string STT return."""
    if isinstance(stt_result, str):
        text = stt_result.strip()
        return {
            "ok": bool(text),
            "transcript": text,
            "raw_transcript": text,
            "text": text,
            "error_category": "" if text else "empty_response",
            "error_message": "" if text else "empty_stt_response",
            "provider": "",
        }
    if isinstance(stt_result, dict):
        out = dict(stt_result)
        if out.get("rejected_as_no_speech"):
            out["transcript"] = ""
            out["raw_transcript"] = ""
            out["text"] = ""
            return out
        text = str(
            out.get("transcript")
            or out.get("text")
            or out.get("raw_transcript")
            or ""
        ).strip()
        if text and not out.get("transcript"):
            out["transcript"] = text
        if text and not out.get("raw_transcript"):
            out["raw_transcript"] = text
        out["text"] = text
        if text and not out.get("ok"):
            out["ok"] = True
        return out
    return {
        "ok": False,
        "transcript": "",
        "raw_transcript": "",
        "text": "",
        "error_category": "invalid_stt_result",
        "error_message": "invalid_stt_result_type",
        "provider": "",
    }


def _run_mini_v2_stt(
    q_idx: int,
    audio_bytes: bytes,
    mime_type: str,
    *,
    duration_seconds: float | None = None,
) -> Dict[str, Any]:
    """Call STT when audio exists; short clips are rejected inside stt_service."""
    from services.stt_service import transcribe_answer_audio

    idx = max(0, min(_QUESTION_COUNT - 1, int(q_idx)))
    question = _question_at(idx)
    question_id = str(question.get("question_id") or f"mini_v2_q{idx + 1}")
    question_text = str(question.get("question_en") or "")
    blob = bytes(audio_bytes) if audio_bytes else b""
    audio_len = len(blob)
    resolved_mime = (mime_type or "audio/webm").strip() or "audio/webm"

    try:
        logger.info(
            "[MINI_V2_STT_ATTEMPT] q=%s audio_len=%s mime_type=%s duration=%s",
            idx + 1,
            audio_len,
            resolved_mime,
            duration_seconds,
        )
    except Exception:
        pass

    if audio_len <= 0:
        try:
            logger.info("[MINI_V2_STT_SKIP] q=%s reason=no_audio", idx + 1)
        except Exception:
            pass
        return {
            "ok": False,
            "transcript": "",
            "raw_transcript": "",
            "error_category": "empty_audio",
            "error_message": "empty_audio_bytes",
        }

    return transcribe_answer_audio(
        blob,
        mime_type=resolved_mime,
        language_hint="en",
        question_text=question_text,
        mode="mini_mock_v2",
        question_id=question_id,
        duration_seconds=duration_seconds,
    )


def _build_mini_v2_row_from_stt(
    q_idx: int,
    *,
    audio_bytes: bytes,
    mime_type: str,
    stt_result: Dict[str, Any],
    mic_result: Any = None,
    prior_row: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    idx = max(0, min(_QUESTION_COUNT - 1, int(q_idx)))
    question = _question_at(idx)
    question_id = str(question.get("question_id") or f"mini_v2_q{idx + 1}")
    question_text = str(question.get("question_en") or "")
    blob = bytes(audio_bytes) if audio_bytes else b""
    audio_len = len(blob)
    resolved_mime = (mime_type or "audio/webm").strip() or "audio/webm"

    stt_result = _normalize_mini_v2_stt_result(stt_result)
    transcript = str(stt_result.get("transcript") or "").strip()
    raw_transcript = str(stt_result.get("raw_transcript") or transcript).strip()
    stt_error_category = str(stt_result.get("error_category") or "")
    stt_error_message = str(stt_result.get("error_message") or "")
    stt_provider = str(stt_result.get("provider") or "gemini")

    statuses = _compute_mini_v2_statuses(
        audio_len=audio_len,
        stt_result=stt_result,
        transcript=transcript,
        raw_transcript=raw_transcript,
    )
    word_count = int(statuses.get("word_count") or 0)
    student_answer = str(statuses.get("student_answer") or "")

    try:
        logger.info(
            "[MINI_V2_STT_RESULT] q=%s stt_status=%s transcript_len=%s word_count=%s "
            "error_category=%s status=%s",
            idx + 1,
            statuses.get("stt_status"),
            len(transcript or raw_transcript),
            word_count,
            stt_error_category or "—",
            statuses.get("status"),
        )
        show_full = False
        try:
            show_full = bool(st.session_state.get("show_dev_debug"))
        except Exception:
            pass
        if show_full and (transcript or raw_transcript):
            logger.debug(
                "[MINI_V2_STT_RESULT] q=%s transcript_preview=%s",
                idx + 1,
                (transcript or raw_transcript)[:500],
            )
    except Exception:
        pass

    duration_seconds, duration_method = _resolve_mini_v2_duration(
        mic_result, blob, resolved_mime
    )
    if prior_row and duration_seconds <= 0:
        try:
            duration_seconds = float(prior_row.get("duration_seconds") or 0.0)
        except (TypeError, ValueError):
            duration_seconds = 0.0
        if duration_seconds > 0:
            duration_method = str(prior_row.get("duration_method") or "unavailable")

    if duration_seconds > 0 and word_count > 0:
        wpm = _mini_v2_estimate_wpm(word_count, duration_seconds)
        wpm_available = True
    else:
        wpm = 0.0
        wpm_available = False

    try:
        logger.info(
            "[MINI_V2_WPM_METRICS] q=%s duration_seconds=%s duration_method=%s "
            "wpm=%s wpm_available=%s",
            idx + 1,
            duration_seconds,
            duration_method,
            wpm,
            wpm_available,
        )
    except Exception:
        pass

    created_at = iso_now()
    if prior_row and str(prior_row.get("created_at") or "").strip():
        created_at = str(prior_row.get("created_at"))

    row = {
        "question_index": idx,
        "question_id": question_id,
        "question_type": str(question.get("type_label") or question.get("type") or ""),
        "question_text": question_text,
        "audio_saved": audio_len > 0,
        "audio_len": audio_len,
        "has_audio_bytes": audio_len > 0,
        "recording_status": statuses.get("recording_status"),
        "mime_type": resolved_mime,
        "transcript": transcript or raw_transcript,
        "raw_transcript": raw_transcript or transcript,
        "student_answer": student_answer,
        "stt_status": statuses.get("stt_status"),
        "stt_error_category": stt_error_category,
        "stt_error_message": stt_error_message,
        "stt_provider": stt_provider,
        "status": statuses.get("status"),
        "created_at": created_at,
        "duration_seconds": duration_seconds,
        "duration_method": duration_method,
        "word_count": word_count,
        "wpm": wpm,
        "wpm_available": wpm_available,
    }
    _log_mini_v2_final_row_status(idx, row)
    return row


def _retry_mini_v2_stt_impl(q_idx: int) -> Tuple[bool, Dict[str, Any]]:
    """Re-run STT from stored audio; update existing answer row."""
    idx = max(0, min(_QUESTION_COUNT - 1, int(q_idx)))
    audio_bytes, mime_type = _get_v2_audio_blob(idx)
    prior = _answer_for_index(idx)
    try:
        logger.info(
            "[MINI_V2_STT_RETRY] q=%s has_audio=%s audio_len=%s mime_type=%s",
            idx + 1,
            bool(audio_bytes),
            len(audio_bytes),
            mime_type or "—",
        )
    except Exception:
        pass
    if not audio_bytes:
        return False, {}
    stt_result = _run_mini_v2_stt(idx, audio_bytes, mime_type)
    row = _build_mini_v2_row_from_stt(
        idx,
        audio_bytes=audio_bytes,
        mime_type=mime_type,
        stt_result=stt_result,
        prior_row=prior,
    )
    _upsert_v2_answer_row(row)
    transcript = str(
        row.get("student_answer") or row.get("transcript") or ""
    ).strip()
    ok = bool(stt_result.get("ok")) and bool(transcript)
    return ok, stt_result if isinstance(stt_result, dict) else {}


def _retry_mini_v2_stt(q_idx: int) -> bool:
    """Re-run STT with per-question burst guard (separate from commit in_flight)."""
    idx = max(0, min(_QUESTION_COUNT - 1, int(q_idx)))
    entity_id = _stt_retry_entity_id(idx)

    allowed, block_msg = guard_can_request(
        st.session_state,
        _STT_RETRY_GUARD_PREFIX,
        entity_id,
        max_attempts=_STT_RETRY_MAX_ATTEMPTS,
        stale_sec=_STT_RETRY_STALE_SEC,
    )
    if not allowed:
        if block_msg:
            st.warning(block_msg)
        return False

    st.session_state[_KEY_STT_RETRY_ACTIVE_QIDX] = entity_id
    guard_set_in_flight(st.session_state, _STT_RETRY_GUARD_PREFIX, True)
    stt_result: Dict[str, Any] = {}
    ok = False
    try:
        with st.spinner("음성을 다시 인식하고 있어요…"):
            ok, stt_result = _retry_mini_v2_stt_impl(idx)
    except Exception as exc:
        try:
            logger.exception("[MINI_V2_STT_RETRY] failed q_idx=%s: %s", idx, exc)
        except Exception:
            pass
        stt_result = {"ok": False, "error_category": "exception"}
    finally:
        guard_set_in_flight(st.session_state, _STT_RETRY_GUARD_PREFIX, False)
        st.session_state.pop(_KEY_STT_RETRY_ACTIVE_QIDX, None)

    if ok:
        guard_clear_guard(st.session_state, _STT_RETRY_GUARD_PREFIX, entity_id)
    else:
        guard_register_failure(
            st.session_state,
            _STT_RETRY_GUARD_PREFIX,
            entity_id,
            _failure_category(stt_result),
            base_cooldown=_STT_RETRY_COOLDOWN_BASE,
            step=_STT_RETRY_COOLDOWN_STEP,
            max_cooldown=_STT_RETRY_COOLDOWN_MAX,
        )
    return ok


def _commit_mini_v2_recording_answer(
    q_idx: int,
    audio_bytes: bytes,
    mime_type: str,
    mic_result: Any = None,
) -> bool:
    """STT + persist row after mic returns audio; then route to saved."""
    if st.session_state.get("_mini_v2_stt_in_flight"):
        try:
            logger.info("[MINI_V2_STT_SKIP] reason=already_in_flight q=%s", int(q_idx) + 1)
        except Exception:
            pass
        return False
    st.session_state["_mini_v2_stt_in_flight"] = True
    try:
        return _commit_mini_v2_recording_answer_impl(
            q_idx, audio_bytes, mime_type, mic_result=mic_result
        )
    finally:
        st.session_state.pop("_mini_v2_stt_in_flight", None)


def _commit_mini_v2_recording_answer_impl(
    q_idx: int,
    audio_bytes: bytes,
    mime_type: str,
    mic_result: Any = None,
) -> bool:
    """STT + persist row after mic returns audio; then route to saved."""
    idx = max(0, min(_QUESTION_COUNT - 1, int(q_idx)))
    blob = bytes(audio_bytes) if audio_bytes else b""
    audio_len = len(blob)
    resolved_mime = (mime_type or "audio/webm").strip() or "audio/webm"

    try:
        logger.info(
            "[MINI_V2_RECORDING_STATUS] q=%s audio_len=%s recording_status=%s",
            idx + 1,
            audio_len,
            "recorded" if audio_len > 0 else "recording_failed",
        )
    except Exception:
        pass

    if audio_len == 0:
        return False

    _save_v2_audio_blob(idx, blob, resolved_mime)
    dur, _dur_method = _resolve_mini_v2_duration(mic_result, blob, resolved_mime)
    stt_result = _run_mini_v2_stt(
        idx,
        blob,
        resolved_mime,
        duration_seconds=dur if dur > 0 else None,
    )
    row = _build_mini_v2_row_from_stt(
        idx,
        audio_bytes=blob,
        mime_type=resolved_mime,
        stt_result=stt_result,
        mic_result=mic_result,
    )
    _upsert_v2_answer_row(row)
    _set_v2_step_saved(idx)
    try:
        logger.info(
            "[MINI_V2_RECORDING_SAVE] q=%s audio_len=%s transcript_len=%s "
            "student_answer_len=%s status=%s stt_status=%s recording_status=%s "
            "word_count=%s wpm=%s wpm_available=%s",
            idx + 1,
            audio_len,
            len(str(row.get("transcript") or "")),
            len(str(row.get("student_answer") or "")),
            row.get("status"),
            row.get("stt_status"),
            row.get("recording_status"),
            row.get("word_count"),
            row.get("wpm"),
            row.get("wpm_available"),
        )
    except Exception:
        pass
    return True


def _commit_mini_v2_timer_expired(q_idx: int) -> bool:
    """Fallback when the answer timer expires without usable mic audio."""
    idx = max(0, min(_QUESTION_COUNT - 1, int(q_idx)))
    prior = _answer_for_index(idx)
    stt_result = {
        "ok": False,
        "transcript": "",
        "raw_transcript": "",
        "error_category": "timer_expired",
        "error_message": "answer_time_limit_reached",
        "provider": "",
    }
    row = _build_mini_v2_row_from_stt(
        idx,
        audio_bytes=b"",
        mime_type="audio/webm",
        stt_result=stt_result,
        prior_row=prior,
    )
    row["source"] = "timer_expired"
    _upsert_v2_answer_row(row)
    _set_v2_step_saved(idx)
    return True


def _upsert_v2_answer_row(row: Dict[str, Any]) -> Dict[str, Any]:
    index = int(row.get("question_index") or 0)
    answers = [r for r in _answers() if int(r.get("question_index", -1)) != index]
    answers.append(row)
    answers.sort(key=lambda x: int(x.get("question_index") or 0))
    st.session_state[_KEY_ANSWERS] = answers
    try:
        logger.info(
            "[MINI_MOCK_V2] answer_saved index=%s status=%s stt_status=%s "
            "audio_len=%s transcript_len=%s student_answer_len=%s total=%s",
            index,
            row.get("status"),
            row.get("stt_status"),
            row.get("audio_len"),
            len(str(row.get("transcript") or "")),
            len(str(row.get("student_answer") or "")),
            len(answers),
        )
    except Exception:
        pass
    from utils.recording_blob_memory import trim_mini_v2_audio_blobs

    trim_mini_v2_audio_blobs(st.session_state)
    from utils.v2_flow_persistence import persist_v2_flows_now

    persist_v2_flows_now(st.session_state)
    return row



def _answer_row_audio_len(row: Dict[str, Any]) -> int:
    try:
        n = int(row.get("audio_len") or 0)
    except (TypeError, ValueError):
        n = 0
    if n > 0:
        return n
    blob = row.get("audio_bytes")
    if blob is not None:
        try:
            return len(blob)
        except Exception:
            return 0
    return 0


def _render_v2_answers_dev_debug() -> None:
    """Dev-only snapshot of mini_v2_answers — not shown to students."""
    if not st.session_state.get("show_dev_debug"):
        return
    st.markdown("##### mini_v2_answers debug")
    rows = _answers()
    if not rows:
        st.caption("(no answers saved)")
        return
    for row in sorted(rows, key=lambda x: int(x.get("question_index") or 0)):
        if not isinstance(row, dict):
            continue
        q_idx = int(row.get("question_index") or 0)
        transcript = str(row.get("transcript") or "")
        student_answer = str(row.get("student_answer") or "")
        st.markdown(
            f"**Q{q_idx + 1}** · audio_len={_answer_row_audio_len(row)} · "
            f"transcript_len={len(transcript)} · "
            f"student_answer_len={len(student_answer)} · "
            f"stt_status={row.get('stt_status')} · "
            f"word_count={row.get('word_count')} · "
            f"duration_seconds={row.get('duration_seconds')} · "
            f"wpm={row.get('wpm')} · "
            f"duration_method={row.get('duration_method')}"
        )


def _normalize_v2_state() -> None:
    """No blank branch — repair invalid step/index before render."""
    if _KEY_ANSWERS not in st.session_state or not isinstance(
        st.session_state.get(_KEY_ANSWERS), list
    ):
        st.session_state[_KEY_ANSWERS] = []

    step = str(st.session_state.get(_KEY_STEP) or "").strip()
    if step not in _VALID_STEPS:
        try:
            logger.warning("[MINI_MOCK_V2] unknown step=%s -> question", step or "—")
        except Exception:
            pass
        st.session_state[_KEY_STEP] = "question"
        st.session_state[_KEY_INDEX] = 0
        st.session_state[_KEY_RECORDING_ACTIVE] = False
        return

    try:
        idx = int(st.session_state.get(_KEY_INDEX) or 0)
    except (TypeError, ValueError):
        idx = 0

    step = str(st.session_state.get(_KEY_STEP) or "")
    if step == "recording":
        st.session_state[_KEY_STEP] = "question"
        step = "question"
    if step in ("question", "recording") and _answer_for_index(idx) is not None:
        _set_v2_step_saved(idx)
        return

    answers = _answers()
    if idx < 0 or idx >= _QUESTION_COUNT:
        try:
            logger.warning(
                "[MINI_MOCK_V2] index_out_of_range index=%s answers=%s",
                idx,
                len(answers),
            )
        except Exception:
            pass
        if len(answers) >= _QUESTION_COUNT:
            st.session_state[_KEY_INDEX] = _QUESTION_COUNT - 1
            cur = str(st.session_state.get(_KEY_STEP) or "")
            if cur not in ("analyzing", "pending", "report"):
                st.session_state[_KEY_STEP] = (
                    "report" if _report_result() else "ready_report"
                )
        else:
            st.session_state[_KEY_INDEX] = 0
            if st.session_state.get(_KEY_STEP) not in (
                "report",
                "ready_report",
                "analyzing",
                "pending",
            ):
                st.session_state[_KEY_STEP] = "question"
        st.session_state[_KEY_RECORDING_ACTIVE] = False


def _report_result() -> Optional[Dict[str, Any]]:
    raw = st.session_state.get(_KEY_REPORT)
    return raw if isinstance(raw, dict) else None


def _analysis_timed_out() -> bool:
    started = st.session_state.get(_KEY_ANALYSIS_STARTED)
    if started is None:
        return False
    try:
        return (time.time() - float(started)) > _ANALYSIS_TIMEOUT_SEC
    except (TypeError, ValueError):
        return False


def _analysis_error_result(category: str, message: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "overall_level": "",
        "summary": "",
        "score_breakdown": {k: 0 for k in _SCORE_LABELS},
        "question_feedback": [],
        "practice_mission": "",
        "strengths": [],
        "weaknesses": [],
        "sample_upgrade_direction": "",
        "error_category": category,
        "error_message": message,
        "all_insufficient": False,
    }


def _log_analysis_error(category: str, message: str) -> None:
    try:
        logger.warning(
            "[MINI_V2_ANALYSIS_ERROR] category=%s message=%s",
            category or "unknown",
            str(message or "")[:240],
        )
    except Exception:
        pass


def _finalize_v2_analysis_attempt(attempt: str, result: Dict[str, Any]) -> None:
    st.session_state[_KEY_ANALYSIS_FINISHED_ATTEMPT] = attempt
    st.session_state[_KEY_REPORT] = result


def _begin_v2_analysis(*, retry: bool = False) -> None:
    attempt = secrets.token_hex(8)
    st.session_state[_KEY_ANALYSIS_ATTEMPT] = attempt
    st.session_state[_KEY_ANALYSIS_STARTED] = time.time()
    st.session_state.pop(_KEY_ANALYSIS_STARTED_ATTEMPT, None)
    st.session_state.pop(_KEY_ANALYSIS_FINISHED_ATTEMPT, None)
    st.session_state.pop(_KEY_REPORT, None)
    st.session_state[_KEY_STEP] = "analyzing"
    try:
        tag = "[MINI_V2_ANALYSIS_RETRY]" if retry else "[MINI_MOCK_V2]"
        logger.info(
            "%s analysis_begin attempt=%s step=analyzing answers=%s",
            tag,
            attempt,
            len(_answers()),
        )
    except Exception:
        pass


def _maybe_run_v2_analysis() -> str:
    """
    At most one Gemini call per analysis attempt.
    Returns target step: analyzing | report | pending.
    """
    attempt = str(st.session_state.get(_KEY_ANALYSIS_ATTEMPT) or "")
    if not attempt:
        return "pending"

    if st.session_state.get(_KEY_ANALYSIS_FINISHED_ATTEMPT) == attempt:
        result = _report_result()
        if result and result.get("ok"):
            return "report"
        return "pending"

    started_attempt = str(st.session_state.get(_KEY_ANALYSIS_STARTED_ATTEMPT) or "")
    if started_attempt == attempt:
        if _analysis_timed_out():
            if st.session_state.get(_KEY_ANALYSIS_FINISHED_ATTEMPT) != attempt:
                timeout_result = _analysis_error_result("timeout", "analysis_timeout")
                _finalize_v2_analysis_attempt(attempt, timeout_result)
                _log_analysis_error("timeout", "analysis_timeout")
                _release_v2_analysis_guard(timeout_result)
            else:
                guard_set_in_flight(st.session_state, _ANALYSIS_GUARD_PREFIX, False)
            return "pending"
        return "analyzing"

    if _analysis_timed_out():
        if st.session_state.get(_KEY_ANALYSIS_FINISHED_ATTEMPT) != attempt:
            timeout_result = _analysis_error_result("timeout", "analysis_timeout")
            _finalize_v2_analysis_attempt(attempt, timeout_result)
            _log_analysis_error("timeout", "analysis_timeout")
            _release_v2_analysis_guard(timeout_result)
        else:
            guard_set_in_flight(st.session_state, _ANALYSIS_GUARD_PREFIX, False)
        return "pending"

    st.session_state[_KEY_ANALYSIS_STARTED_ATTEMPT] = attempt
    from services.mini_mock_v2_analysis import analyze_mini_mock_v2_answers

    guard_set_in_flight(st.session_state, _ANALYSIS_GUARD_PREFIX, True)
    try:
        result = analyze_mini_mock_v2_answers(_answers())
    except Exception as exc:
        msg = str(exc)[:240]
        try:
            logger.exception(
                "[MINI_V2_ANALYSIS_ERROR] category=unexpected_error message=%s",
                msg,
            )
        except Exception:
            pass
        result = _analysis_error_result("unexpected_error", msg)
    else:
        if not result.get("ok"):
            _log_analysis_error(
                str(result.get("error_category") or "unknown"),
                str(result.get("error_message") or ""),
            )
    finally:
        guard_set_in_flight(st.session_state, _ANALYSIS_GUARD_PREFIX, False)

    _finalize_v2_analysis_attempt(attempt, result)
    _release_v2_analysis_guard(result)
    if result.get("ok"):
        return "report"
    return "pending"


def _render_question_step(q_idx: int) -> None:
    if _answer_for_index(q_idx) is not None:
        _set_v2_step_saved(q_idx)
        st.rerun()

    try:
        logger.info("[MINI_V2_QUESTION_RENDER] idx=%s step=question", q_idx)
    except Exception:
        pass

    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow=f"미니 모의고사 · Q{q_idx + 1}/{_QUESTION_COUNT}",
    )

    question = _question_at(q_idx)
    render_exam_question_shell(
        eyebrow="5분 모의고사",
        progress_html=build_progress_segments_html(
            q_idx + 1,
            _QUESTION_COUNT,
            badge_label=opic_type_badge_label(str(question.get("opic_type") or "")),
        ),
        badge_label=str(question.get("type_label") or ""),
        question_en=str(question.get("question_en") or ""),
        question_ko=str(question.get("question_ko") or ""),
        accent="teal",
    )
    render_exam_answer_card_top(accent="teal")
    timer_id = build_answer_timer_id("mini_v2", str(q_idx))
    render_answer_countdown_timer(
        timer_id=timer_id,
        accent="teal",
        duration_sec=DEFAULT_DURATION_SEC,
    )
    render_exam_wave_mic_observer()

    from streamlit_mic_recorder import mic_recorder

    mic_key = _mini_v2_mic_key(q_idx)
    mic_result = mic_recorder(
        start_prompt="🎤 답변 시작",
        stop_prompt="■ 녹음 완료",
        key=mic_key,
        use_container_width=True,
        just_once=True,
    )

    if mic_result is not None:
        dismiss_answer_timer_signal(timer_id)
        audio_bytes, mime_type, extraction_source = _extract_mini_v2_audio_bytes(
            mic_result, mic_key=mic_key
        )
        _log_mini_v2_mic_result(
            q_idx,
            mic_result,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            extraction_source=extraction_source,
        )
        if len(audio_bytes) > 0:
            with st.spinner("답변을 저장하고 음성을 인식하고 있어요…"):
                _commit_mini_v2_recording_answer(
                    q_idx, audio_bytes, mime_type, mic_result=mic_result
                )
            st.rerun()
        else:
            st.warning("음성이 저장되지 않았어요. 다시 녹음해 주세요.")

    def _commit_from_timer(audio_bytes: bytes, mime_type: str, mic_payload: Any) -> None:
        with st.spinner("답변을 저장하고 음성을 인식하고 있어요…"):
            _commit_mini_v2_recording_answer(
                q_idx, audio_bytes, mime_type, mic_result=mic_payload
            )

    if handle_answer_timer_expiry(
        timer_id,
        mic_result=mic_result,
        extract_audio=lambda: _extract_mini_v2_audio_bytes(None, mic_key=mic_key),
        commit_audio=_commit_from_timer,
        commit_empty=lambda: _commit_mini_v2_timer_expired(q_idx),
    ):
        st.rerun()


def _render_v2_saved_status_card(
    saved_row: Optional[Dict[str, Any]],
    *,
    is_last: bool,
) -> None:
    status = str(saved_row.get("status") or "") if saved_row else ""
    if status == "saved":
        eyebrow = "저장 완료"
        title = (
            "3개 답변이 모두 저장되었어요" if is_last else "답변이 저장되었어요."
        )
        meta = (
            "AI 진단 리포트를 받을 수 있습니다."
            if is_last
            else "다음 문항으로 넘어갈 수 있습니다."
        )
    elif status == "insufficient_response":
        eyebrow = "응답 짧음"
        title = "답변이 인식되었지만, 평가하기에는 조금 짧아요."
        meta = "20초 이상 말해 보세요."
    elif status == "stt_pending":
        eyebrow = "AI 인식 대기"
        title = "녹음은 저장되었어요. AI 음성 인식이 잠시 지연되고 있어요."
        meta = "잠시 후 음성 인식 다시 시도를 눌러 주세요."
    elif status == "stt_failed":
        eyebrow = "음성 저장됨"
        title = "녹음은 저장되었지만, AI 음성 인식에 실패했어요."
        meta = "음성 인식 다시 시도를 눌러 보세요."
    elif status == "recording_failed":
        eyebrow = "녹음 실패"
        title = "녹음 파일이 저장되지 않았어요."
        meta = "다시 녹음해 주세요."
    else:
        eyebrow = "저장 완료"
        title = "답변이 저장되었어요."
        meta = "다음 문항으로 넘어갈 수 있습니다." if not is_last else ""

    st.markdown(
        f"""
        <section class="continue-card continue-card--resume mx-landing-card" role="status">
          <div class="cc-eyebrow">{html.escape(eyebrow)}</div>
          <div class="cc-title">{html.escape(title)}</div>
          <div class="cc-meta">{html.escape(meta)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_v2_saved_audio_preview(q_idx: int, saved_row: Optional[Dict[str, Any]]) -> None:
    audio_bytes, mime_type = _get_v2_audio_blob(q_idx)
    st.markdown("##### 내 녹음 다시 듣기")
    if audio_bytes:
        try:
            st.audio(audio_bytes, format=mime_type or "audio/webm")
        except Exception:
            logger.debug(
                "[MINI_V2_AUDIO_PLAYBACK] failed q=%s audio_len=%s",
                q_idx + 1,
                len(audio_bytes),
                exc_info=True,
            )
            st.caption("녹음 파일을 다시 들을 수 없습니다.")
    else:
        st.warning("녹음 파일이 저장되지 않았어요.")


def _render_v2_saved_transcript_preview(saved_row: Optional[Dict[str, Any]]) -> None:
    if not saved_row or not isinstance(saved_row, dict):
        st.markdown("##### AI가 인식한 답변")
        st.caption("녹음 파일이 없어 인식할 수 없습니다.")
        return

    status = str(saved_row.get("status") or "")
    stt_status = str(saved_row.get("stt_status") or "")
    has_audio = bool(saved_row.get("audio_saved")) or int(saved_row.get("audio_len") or 0) > 0
    transcript = str(
        saved_row.get("student_answer")
        or saved_row.get("transcript")
        or saved_row.get("raw_transcript")
        or ""
    ).strip()

    if transcript:
        render_saved_transcript(transcript=transcript, accent="teal")
        if _mini_v2_row_word_count(saved_row) < _MIN_ANSWER_MIN_WORDS:
            st.caption(
                "답변은 인식되었지만, 평가하기에는 너무 짧아요. 20초 이상 말해 보세요."
            )
        elif status == "saved":
            st.caption(
                "오픽 답변은 보통 20초 이상 말하면 더 안정적으로 평가됩니다."
            )
        return

    st.markdown("##### AI가 인식한 답변")
    if not has_audio or status == "recording_failed":
        st.caption("녹음 파일이 없어 인식할 수 없습니다.")
    elif stt_status == "stt_pending" or status == "stt_pending":
        st.warning("녹음은 저장되었어요. AI 음성 인식이 잠시 지연되고 있어요.")
        _render_v2_stt_beta_diagnostic(saved_row)
    elif has_audio:
        st.warning("녹음은 저장되었지만, AI 음성 인식에 실패했어요.")
        _render_v2_stt_beta_diagnostic(saved_row)
    else:
        st.caption("녹음 파일이 없어 인식할 수 없습니다.")


def _render_v2_stt_beta_diagnostic(saved_row: Optional[Dict[str, Any]]) -> None:
    if not saved_row or not isinstance(saved_row, dict):
        return
    st.caption(
        f"진단: audio_len={saved_row.get('audio_len')} · "
        f"mime_type={saved_row.get('mime_type') or '—'} · "
        f"stt_status={saved_row.get('stt_status') or '—'} · "
        f"stt_error_category={saved_row.get('stt_error_category') or '—'}"
    )


def _render_v2_saved_dev_debug(q_idx: int, saved_row: Optional[Dict[str, Any]]) -> None:
    if not st.session_state.get("show_dev_debug"):
        return
    audio_bytes, _ = _get_v2_audio_blob(q_idx)
    transcript = ""
    if saved_row and isinstance(saved_row, dict):
        transcript = str(
            saved_row.get("student_answer")
            or saved_row.get("transcript")
            or saved_row.get("raw_transcript")
            or ""
        )
    st.caption(
        f"[dev] audio_len={len(audio_bytes)} · transcript_len={len(transcript)} · "
        f"word_count={saved_row.get('word_count') if saved_row else 0} · "
        f"wpm={saved_row.get('wpm') if saved_row else 0} · "
        f"status={saved_row.get('status') if saved_row else '—'} · "
        f"recording_status={saved_row.get('recording_status') if saved_row else '—'} · "
        f"stt_status={saved_row.get('stt_status') if saved_row else '—'}"
    )


def _render_saved_step(q_idx: int) -> None:
    is_last = q_idx >= _QUESTION_COUNT - 1
    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow=f"미니 모의고사 · Q{q_idx + 1}/{_QUESTION_COUNT}",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    saved_row = _answer_for_index(q_idx)
    _render_v2_saved_status_card(saved_row, is_last=is_last)

    _render_v2_saved_audio_preview(q_idx, saved_row)
    _render_v2_saved_transcript_preview(saved_row)
    _render_v2_saved_dev_debug(q_idx, saved_row)

    stt_status = str(saved_row.get("stt_status") or "") if saved_row else ""
    row_status = str(saved_row.get("status") or "") if saved_row else ""
    audio_bytes, _ = _get_v2_audio_blob(q_idx)
    needs_stt_retry = bool(audio_bytes) and (
        row_status in ("stt_failed", "stt_pending")
        or stt_status in ("stt_failed", "stt_pending")
    )
    if needs_stt_retry:
        stt_disabled, stt_label = _stt_retry_button_state(q_idx)
        if st.button(
            stt_label,
            use_container_width=True,
            key=f"mini_v2_stt_retry_{q_idx}",
            disabled=stt_disabled,
        ):
            _retry_mini_v2_stt(q_idx)
            st.rerun()

    if is_last:
        analysis_disabled, analysis_label = _analysis_button_state()
        if st.button(
            analysis_label,
            type="primary",
            use_container_width=True,
            key="mini_v2_start_analysis",
            disabled=analysis_disabled,
        ):
            rows = _answers()
            try:
                logger.info(
                    "[MINI_V2_ANALYSIS_BUTTON_CLICKED] answers_count=%s answer_lengths=%s",
                    len(rows),
                    [
                        len(str(r.get("student_answer") or r.get("transcript") or ""))
                        for r in rows
                        if isinstance(r, dict)
                    ],
                )
            except Exception:
                pass
            if _try_start_v2_analysis():
                st.rerun()
    else:
        if st.button(
            "다음 문항으로",
            type="primary",
            use_container_width=True,
            key=f"mini_v2_next_{q_idx}",
        ):
            from utils.recording_blob_memory import trim_mini_v2_audio_blobs

            trim_mini_v2_audio_blobs(st.session_state)
            next_idx = q_idx + 1
            st.session_state[_KEY_INDEX] = next_idx
            st.session_state[_KEY_STEP] = "question"
            st.session_state[_KEY_RECORDING_ACTIVE] = False
            try:
                logger.info(
                    "[MINI_MOCK_V2] next_question from_index=%s to_index=%s",
                    q_idx,
                    next_idx,
                )
            except Exception:
                pass
            st.rerun()

    if st.button(
        "학습 방식 다시 선택",
        use_container_width=True,
        key=f"mini_v2_portal_saved_{q_idx}",
    ):
        _exit_to_portal()


def _render_ready_report_step() -> None:
    """Optional bridge step — same intent as last saved screen."""
    st.session_state[_KEY_INDEX] = _QUESTION_COUNT - 1
    _render_saved_step(_QUESTION_COUNT - 1)


def _question_analysis_status_label(q_num: int, report: Dict[str, Any]) -> str:
    for item in report.get("question_feedback") or []:
        if not isinstance(item, dict):
            continue
        if int(item.get("question_index") or 0) == q_num:
            st_status = str(item.get("status") or "").lower()
            if st_status == "insufficient_response":
                return "응답 짧음"
            return "분석 완료"
    row = _answer_for_index(q_num - 1)
    return _mini_v2_saved_answer_label(row)


def _render_analyzing_step() -> None:
    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow="미니 모의고사 · AI 분석",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    render_feedback_loading_card(
        message="AI가 3개 답변을 분석하고 있어요. 잠시만 기다려 주세요. (최대 60초)",
    )
    with st.spinner("분석 중…"):
        next_step = _maybe_run_v2_analysis()
    if next_step != "analyzing":
        st.session_state[_KEY_STEP] = next_step
        st.rerun()


def _render_pending_step() -> None:
    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow="미니 모의고사 · 분석 대기",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    st.markdown(render_analysis_recovery_card(), unsafe_allow_html=True)

    st.markdown("##### 저장된 답변")
    for i in range(_QUESTION_COUNT):
        row = _answer_for_index(i)
        st.markdown(f"- Q{i + 1} {_mini_v2_saved_answer_label(row)}")

    retry_disabled, retry_label = _analysis_button_state(retry=True)
    if st.button(
        retry_label,
        type="primary",
        use_container_width=True,
        key="mini_v2_retry_analysis",
        disabled=retry_disabled,
    ):
        if _try_start_v2_analysis(retry=True):
            st.rerun()
    st.markdown(render_recovery_retry_caption_html(), unsafe_allow_html=True)

    if st.button(
        "학습하기로 돌아가기",
        use_container_width=True,
        key="mini_v2_pending_home",
    ):
        _exit_to_portal()

    if st.session_state.get("show_dev_debug"):
        result = _report_result()
        if result:
            err_cat = str(result.get("error_category") or "").strip()
            if err_cat:
                st.caption(f"[dev] error_category: {err_cat}")
            st.json(result)


def _render_report_step() -> None:
    report = _report_result()
    if not report or not report.get("ok"):
        st.session_state[_KEY_STEP] = "pending"
        _render_pending_step()
        return

    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow="미니 모의고사 · AI 진단 리포트",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    hero_metrics = collect_hero_display_metrics([], _answers())
    st.markdown(
        render_final_report_completion_hero_html(
            answered_count=hero_metrics["answered"],
            overall_display=str(report.get("overall_level") or ""),
            pending_count=0,
            total_words=hero_metrics.get("total_words"),
            total_duration=hero_metrics.get("total_duration"),
            note=str(report.get("summary") or ""),
            eyebrow="5분 진단 완료",
        ),
        unsafe_allow_html=True,
    )

    breakdown = report.get("score_breakdown")
    score_html = render_score_donut_bars_html(
        breakdown if isinstance(breakdown, dict) else {},
        _SCORE_LABELS,
        str(report.get("overall_level") or ""),
    )
    if score_html:
        st.markdown("##### 점수 요약")
        st.markdown(score_html, unsafe_allow_html=True)

    st.markdown("##### 문항별 피드백")
    for item in report.get("question_feedback") or []:
        if not isinstance(item, dict):
            continue
        qn = int(item.get("question_index") or 0)
        fb = html.escape(str(item.get("feedback") or "").strip())
        better = html.escape(str(item.get("better_direction") or "").strip())
        if not fb and not better:
            continue
        st.markdown(f"**Q{qn}**")
        if fb:
            st.markdown(fb)
        if better:
            st.caption(f"개선 방향: {better}")

    strengths = report.get("strengths") or []
    weaknesses = report.get("weaknesses") or []
    if strengths:
        st.markdown("##### 강점")
        for s in strengths:
            st.markdown(f"- {html.escape(str(s))}")
    if weaknesses:
        st.markdown("##### 보완점")
        for w in weaknesses:
            st.markdown(f"- {html.escape(str(w))}")

    mission = str(report.get("practice_mission") or "").strip()
    if mission:
        st.markdown("##### 다음 연습 미션")
        st.info(mission)

    upgrade = str(report.get("sample_upgrade_direction") or "").strip()
    if upgrade:
        st.markdown("##### 답변 업그레이드 방향")
        st.caption(upgrade)

    st.markdown("##### 저장된 답변")
    for i in range(1, _QUESTION_COUNT + 1):
        st.markdown(f"- Q{i} {_question_analysis_status_label(i, report)}")

    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "새 5분 진단 시작",
            type="primary",
            use_container_width=True,
            key="mini_v2_restart",
        ):
            clear_old_mini_mock_keys_for_v2()
            reset_mini_mock_v2()
            _init_v2_session()
            st.rerun()
    with c2:
        if st.button(
            "학습하기로 돌아가기",
            use_container_width=True,
            key="mini_v2_home",
        ):
            _exit_to_portal()

    if st.session_state.get("show_dev_debug"):
        st.json(report)



def _exit_to_portal() -> None:
    from views.mock_exam import reset_to_learning_portal

    reset_mini_mock_v2()
    reset_to_learning_portal()


def render_mini_mock_v2() -> None:
    """Main V2 router — question (mic+STT) → saved → analyzing → report | pending."""
    if not is_mini_mock_v2_active():
        has_saved = bool(st.session_state.get(_KEY_ANSWERS))
        has_step = bool(str(st.session_state.get(_KEY_STEP) or "").strip())
        if has_saved or has_step:
            st.session_state[_MINI_MOCK_V2_ACTIVE_KEY] = True
            st.session_state[ACTIVE_LEARNING_MODE_KEY] = ACTIVE_LEARNING_MODE_MINI_V2
            st.session_state.setdefault("mock_mode", "mini_mock")
            st.session_state.setdefault("practice_portal_selected", True)
            mx = st.session_state.get("mock")
            if isinstance(mx, dict):
                mx.setdefault("mock_mode", "mini_mock")
                mx.setdefault("mock_page", "MINI_MOCK")
        else:
            mx = st.session_state.get("mock")
            begin_mini_mock_v2_session(mx if isinstance(mx, dict) else {})

    _normalize_v2_state()

    if st.session_state.pop("_v2_user_resumed", None):
        st.info("저장된 답변을 불러왔어요. 이어서 진행해 주세요.")
    step = str(st.session_state.get(_KEY_STEP) or "question")
    try:
        q_idx = int(st.session_state.get(_KEY_INDEX) or 0)
    except (TypeError, ValueError):
        q_idx = 0
    q_idx = max(0, min(_QUESTION_COUNT - 1, q_idx))

    try:
        logger.debug(
            "[MINI_MOCK_V2] render step=%s index=%s answers=%s",
            step,
            q_idx,
            len(_answers()),
        )
    except Exception:
        pass

    if step == "report":
        _render_report_step()
    elif step == "pending":
        _render_pending_step()
    elif step == "analyzing":
        _render_analyzing_step()
    elif step == "ready_report":
        _render_ready_report_step()
    elif step == "saved":
        _render_saved_step(q_idx)
    elif step in ("question", "recording"):
        _render_question_step(q_idx)
    else:
        st.session_state[_KEY_STEP] = "question"
        st.session_state[_KEY_INDEX] = 0
        _render_question_step(0)

    _render_v2_answers_dev_debug()


def render_mini_mock_v2_flow(mx: dict) -> None:
    """Called from mock_exam.render_mock_flow — thin wrapper."""
    if isinstance(mx, dict) and not is_mini_mock_v2_active():
        begin_mini_mock_v2_session(mx)
    render_mini_mock_v2()
