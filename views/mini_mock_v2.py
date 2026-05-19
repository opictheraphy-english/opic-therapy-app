"""Isolated 5-minute mini mock V2 — Gemini report after save; no legacy mini_mock flow."""

from __future__ import annotations

import html
import logging
import secrets
import time
from typing import Any, Dict, List, Optional

import streamlit as st

import re

from components.topbar import render_top_bar
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

_MIN_ANSWER_MIN_WORDS = 5
_MIN_TEXT_MIN_WORDS = 5

_ANALYSIS_TIMEOUT_SEC = 60

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


def _questions() -> List[Dict[str, Any]]:
    try:
        from data.mini_mock_questions import get_mini_mock_questions

        rows = get_mini_mock_questions()
        if isinstance(rows, list) and len(rows) >= _QUESTION_COUNT:
            return [dict(r) for r in rows[:_QUESTION_COUNT]]
    except Exception:
        logger.debug("[MINI_MOCK_V2] question import failed", exc_info=True)
    return _fallback_questions()


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


def reset_mini_mock_v2() -> None:
    """Clear only V2 session keys."""
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


def _english_word_count(text: str) -> int:
    return len(re.findall(r"[a-zA-Z']+", text or ""))


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


def _mini_v2_mic_key(q_idx: int) -> str:
    return f"mini_v2_mic_{q_idx}"


def _mini_v2_audio_storage_key(q_idx: int) -> str:
    return f"mini_v2_audio_{q_idx}"


def _extract_mini_v2_audio_bytes(mic_result: Any) -> tuple[bytes, str]:
    """Normalize streamlit_mic_recorder return value to (bytes, mime_type)."""
    if mic_result is None:
        return b"", ""
    if isinstance(mic_result, bytes):
        return mic_result, "audio/webm"
    if isinstance(mic_result, dict):
        mime_type = (
            str(mic_result.get("mime_type") or mic_result.get("type") or mic_result.get("format") or "")
            .strip()
        )
        for key in ("bytes", "audio", "blob"):
            raw = mic_result.get(key)
            if raw is None:
                continue
            if isinstance(raw, bytes):
                return raw, mime_type or "audio/webm"
            try:
                return bytes(raw), mime_type or "audio/webm"
            except (TypeError, ValueError):
                continue
        return b"", mime_type or ""
    return b"", ""


def _commit_mini_v2_recording_answer(
    q_idx: int,
    audio_bytes: bytes,
    mime_type: str,
) -> bool:
    """STT + persist row after mic returns audio; then route to saved."""
    idx = max(0, min(_QUESTION_COUNT - 1, int(q_idx)))
    question = _question_at(idx)
    question_id = str(question.get("question_id") or f"mini_v2_q{idx + 1}")
    question_text = str(question.get("question_en") or "")
    blob = bytes(audio_bytes) if audio_bytes else b""
    audio_len = len(blob)
    resolved_mime = (mime_type or "audio/webm").strip() or "audio/webm"

    if audio_len > 0:
        _v2_recordings()[_mini_v2_audio_storage_key(idx)] = blob

    from services.stt_service import transcribe_answer_audio

    stt_result: Dict[str, Any] = {}
    if audio_len > 0:
        stt_result = transcribe_answer_audio(
            blob,
            mime_type=resolved_mime,
            language_hint="en",
            question_text=question_text,
            mode="mini_mock_v2",
            question_id=question_id,
        )
    else:
        stt_result = {
            "ok": False,
            "transcript": "",
            "raw_transcript": "",
            "error_category": "empty_audio",
            "error_message": "empty_audio_bytes",
        }

    transcript = str(stt_result.get("transcript") or "").strip()
    raw_transcript = str(stt_result.get("raw_transcript") or transcript).strip()
    stt_error_category = str(stt_result.get("error_category") or "")
    stt_error_message = str(stt_result.get("error_message") or "")
    word_count = _english_word_count(transcript)

    if audio_len == 0:
        return False

    if stt_result.get("ok") and transcript:
        stt_status = "transcript_ready"
    elif stt_result.get("ok") and not transcript:
        stt_status = "stt_pending"
    elif not transcript:
        stt_status = "stt_pending"
    else:
        stt_status = "stt_error"

    if transcript and word_count >= _MIN_ANSWER_MIN_WORDS:
        row_status = "saved"
        if stt_status == "stt_error":
            stt_status = "transcript_ready"
    elif transcript:
        row_status = "insufficient_response"
        stt_status = "insufficient_response"
    else:
        row_status = "stt_pending"
        stt_status = "stt_pending"

    row = {
        "question_index": idx,
        "question_id": question_id,
        "question_type": str(question.get("type_label") or question.get("type") or ""),
        "question_text": question_text,
        "audio_saved": audio_len > 0,
        "audio_len": audio_len,
        "has_audio_bytes": audio_len > 0,
        "mime_type": resolved_mime,
        "transcript": transcript,
        "raw_transcript": raw_transcript or transcript,
        "student_answer": transcript,
        "stt_status": stt_status,
        "stt_error_category": stt_error_category,
        "stt_error_message": stt_error_message,
        "status": row_status,
        "created_at": iso_now(),
    }
    _upsert_v2_answer_row(row)
    _set_v2_step_saved(idx)
    try:
        logger.info(
            "[MINI_V2_RECORDING_SAVE] q=%s audio_len=%s transcript_len=%s "
            "student_answer_len=%s status=%s stt_status=%s",
            idx + 1,
            audio_len,
            len(transcript),
            len(transcript),
            row_status,
            stt_status,
        )
    except Exception:
        pass
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
            f"stt_status={row.get('stt_status')}"
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


def _begin_v2_analysis() -> None:
    attempt = secrets.token_hex(8)
    st.session_state[_KEY_ANALYSIS_ATTEMPT] = attempt
    st.session_state[_KEY_ANALYSIS_STARTED] = time.time()
    st.session_state.pop(_KEY_ANALYSIS_STARTED_ATTEMPT, None)
    st.session_state.pop(_KEY_ANALYSIS_FINISHED_ATTEMPT, None)
    st.session_state.pop(_KEY_REPORT, None)
    st.session_state[_KEY_STEP] = "analyzing"
    try:
        logger.info(
            "[MINI_MOCK_V2] analysis_begin attempt=%s step=analyzing answers=%s",
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

    if _analysis_timed_out():
        try:
            logger.warning("[MINI_MOCK_V2] analysis_timeout attempt=%s", attempt)
        except Exception:
            pass
        return "pending"

    started_attempt = str(st.session_state.get(_KEY_ANALYSIS_STARTED_ATTEMPT) or "")
    if started_attempt == attempt:
        if _analysis_timed_out():
            return "pending"
        return "analyzing"

    st.session_state[_KEY_ANALYSIS_STARTED_ATTEMPT] = attempt
    from services.mini_mock_v2_analysis import analyze_mini_mock_v2_answers

    result: Dict[str, Any]
    try:
        result = analyze_mini_mock_v2_answers(_answers())
    except Exception as exc:
        try:
            logger.exception(
                "[MINI_V2_ANALYSIS_ERROR] category=unexpected_error message=%s",
                str(exc)[:240],
            )
        except Exception:
            pass
        result = {
            "ok": False,
            "error_category": "unexpected_error",
            "error_message": str(exc)[:240],
        }
    st.session_state[_KEY_ANALYSIS_FINISHED_ATTEMPT] = attempt
    st.session_state[_KEY_REPORT] = result
    if result.get("ok"):
        return "report"
    try:
        logger.warning(
            "[MINI_V2_ANALYSIS_ERROR] category=%s message=%s",
            result.get("error_category") or "unknown",
            str(result.get("error_message") or "")[:240],
        )
    except Exception:
        pass
    return "pending"


def _render_progress_chip(q_idx: int) -> None:
    st.markdown(
        f"""
        <section class="continue-card continue-card--resume mx-landing-card" role="region"
                 aria-label="진행 상황">
          <div class="cc-eyebrow">미니 모의고사</div>
          <div class="cc-title">Q{q_idx + 1} <span class="cc-of">/ {_QUESTION_COUNT}</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_question_body(question: Dict[str, Any]) -> None:
    type_label = html.escape(str(question.get("type_label") or ""))
    question_en = html.escape(str(question.get("question_en") or ""))
    question_ko = html.escape(str(question.get("question_ko") or "").strip())
    ko_block = (
        f'<div class="mx-rh-transcript">{question_ko}</div>'
        if question_ko
        else ""
    )
    st.markdown(
        f"""
        <section class="mx-report-hero" role="region" aria-label="문항">
          <p class="mx-rh-eyebrow">{type_label}</p>
          <div class="mx-rh-title">{question_en}</div>
          {ko_block}
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_v2_question_header(q_idx: int) -> None:
    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow=f"미니 모의고사 · Q{q_idx + 1}/{_QUESTION_COUNT}",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_progress_chip(q_idx)
    _render_question_body(_question_at(q_idx))


def _render_question_step(q_idx: int) -> None:
    if _answer_for_index(q_idx) is not None:
        _set_v2_step_saved(q_idx)
        st.rerun()

    try:
        logger.info("[MINI_V2_QUESTION_RENDER] idx=%s step=question", q_idx)
    except Exception:
        pass

    _render_v2_question_header(q_idx)

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
        audio_bytes, mime_type = _extract_mini_v2_audio_bytes(mic_result)
        try:
            logger.info(
                "[MINI_V2_MIC_RESULT] q=%s result_type=%s audio_len=%s mime_type=%s",
                q_idx + 1,
                type(mic_result).__name__,
                len(audio_bytes),
                mime_type or "—",
            )
        except Exception:
            pass
        if len(audio_bytes) > 0:
            with st.spinner("답변을 저장하고 음성을 인식하고 있어요…"):
                _commit_mini_v2_recording_answer(q_idx, audio_bytes, mime_type)
            st.rerun()
        else:
            st.warning("음성이 저장되지 않았어요. 다시 녹음해 주세요.")


def _render_saved_step(q_idx: int) -> None:
    is_last = q_idx >= _QUESTION_COUNT - 1
    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow=f"미니 모의고사 · Q{q_idx + 1}/{_QUESTION_COUNT}",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    saved_row = _answer_for_index(q_idx)
    if saved_row and str(saved_row.get("status") or "") == "insufficient_response":
        st.caption(
            "답변이 짧거나 음성이 충분히 인식되지 않았지만, 답변 시도는 저장되었습니다."
        )

    if saved_row:
        transcript = str(
            saved_row.get("transcript") or saved_row.get("student_answer") or ""
        ).strip()
        st.markdown("##### 인식된 답변")
        if transcript:
            st.caption(transcript)
        else:
            st.caption("답변은 저장되었지만, 음성 인식이 지연되었어요.")

    if is_last:
        st.markdown(
            """
            <section class="continue-card continue-card--resume mx-landing-card" role="status">
              <div class="cc-eyebrow">저장 완료</div>
              <div class="cc-title">3개 답변이 모두 저장되었어요</div>
              <div class="cc-meta">AI 진단 리포트를 받을 수 있습니다.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "AI 진단 리포트 받기",
            type="primary",
            use_container_width=True,
            key="mini_v2_start_analysis",
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
            _begin_v2_analysis()
            st.rerun()
    else:
        st.markdown(
            """
            <section class="continue-card continue-card--resume mx-landing-card" role="status">
              <div class="cc-eyebrow">저장 완료</div>
              <div class="cc-title">답변이 저장되었어요</div>
              <div class="cc-meta">다음 문항으로 넘어갈 수 있습니다.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "다음 문항으로",
            type="primary",
            use_container_width=True,
            key=f"mini_v2_next_{q_idx}",
        ):
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
                return "응답 부족"
            return "분석 완료"
    row = _answer_for_index(q_num - 1)
    if row and str(row.get("status") or "") == "insufficient_response":
        return "응답 부족"
    if row:
        return "저장 완료"
    return "미저장"


def _render_analyzing_step() -> None:
    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow="미니 모의고사 · AI 분석",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    next_step = _maybe_run_v2_analysis()
    if next_step != "analyzing":
        st.session_state[_KEY_STEP] = next_step
        st.rerun()

    st.markdown(
        """
        <section class="continue-card continue-card--resume mx-landing-card" role="status">
          <div class="cc-eyebrow">AI 분석</div>
          <div class="cc-title">AI가 3개 답변을 분석하고 있어요</div>
          <div class="cc-meta">묘사·경험·롤플레이 답변을 바탕으로 진단 리포트를 만들고 있습니다.<br/>
          잠시만 기다려 주세요. (최대 60초)</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.spinner("분석 중…")


def _render_pending_step() -> None:
    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow="미니 모의고사 · 분석 대기",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    st.markdown(
        """
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">AI 분석</div>
          <div class="rv-title">AI 분석이 잠시 지연되고 있어요.</div>
          <div class="rv-body">답변은 안전하게 저장되어 있습니다.<br/>
          잠시 후 다시 시도해 주세요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### 저장된 답변")
    for i in range(_QUESTION_COUNT):
        row = _answer_for_index(i)
        if row and str(row.get("student_answer") or "").strip():
            label = "저장 완료"
        elif row:
            label = "응답 부족"
        else:
            label = "미저장"
        st.markdown(f"- Q{i + 1} {label}")

    if st.button(
        "저장된 답변으로 다시 분석하기",
        type="primary",
        use_container_width=True,
        key="mini_v2_retry_analysis",
    ):
        _begin_v2_analysis()
        st.rerun()

    if st.button(
        "학습하기로 돌아가기",
        use_container_width=True,
        key="mini_v2_pending_home",
    ):
        _exit_to_portal()

    if st.session_state.get("show_dev_debug"):
        result = _report_result()
        if result:
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

    level = html.escape(str(report.get("overall_level") or "—"))
    summary = html.escape(str(report.get("summary") or ""))
    st.markdown(
        f"""
        <section class="continue-card continue-card--start mx-landing-card" role="region">
          <div class="cc-eyebrow">5분 진단</div>
          <div class="cc-title">5분 진단 AI 리포트</div>
          <div class="cc-meta">예상 등급: <strong>{level}</strong></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if summary:
        st.markdown(
            f"""
            <section class="continue-card" role="region">
              <div class="cc-eyebrow">요약</div>
              <div class="cc-meta">{summary}</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    breakdown = report.get("score_breakdown")
    if isinstance(breakdown, dict) and breakdown:
        st.markdown("##### 점수 요약")
        for key, label in _SCORE_LABELS.items():
            try:
                score = int(breakdown.get(key) or 0)
            except (TypeError, ValueError):
                score = 0
            st.progress(max(0, min(100, score)) / 100.0)
            st.caption(f"{label}: {score}/100")

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
        mx = st.session_state.get("mock")
        begin_mini_mock_v2_session(mx if isinstance(mx, dict) else {})

    _normalize_v2_state()

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
