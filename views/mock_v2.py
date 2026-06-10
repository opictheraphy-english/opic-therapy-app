"""Isolated Mock V2 — survey + 15-question flow with direct mic recording and STT."""

from __future__ import annotations

import base64
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from components.answer_countdown_timer import (
    DEFAULT_DURATION_SEC,
    build_answer_timer_id,
    dismiss_answer_timer_signal,
    handle_answer_timer_expiry,
    render_answer_countdown_timer,
)
from components.audio_player import render_exam_question_audio_player
from components.exam_question_screen import (
    build_progress_segments_html,
    opic_type_badge_label,
    render_exam_answer_card_top,
    render_exam_question_shell,
    render_exam_wave_mic_observer,
)
from components.topbar import render_top_bar
from services.mock_v2_question_selector import build_mock_v2_exam
from services.stt_service import count_english_words
from utils.local_profile import iso_now
from utils.question_audio_assets import load_question_mp3_bytes, mock_v2_question_audio_id

logger = logging.getLogger(__name__)

_KEY_STEP = "mock_v2_step"
_KEY_SURVEY = "mock_v2_survey_results"
_KEY_QUESTIONS = "mock_v2_questions"
_KEY_INDEX = "mock_v2_index"
_KEY_ANSWERS = "mock_v2_answers"
_KEY_AUDIO_BLOBS = "mock_v2_audio_blobs"
_KEY_STARTED = "mock_v2_started_at"
_KEY_FINISHED = "mock_v2_finished_at"
_KEY_REPORT = "mock_v2_report"

_VALID_STEPS = frozenset({
    "survey",
    "question",
    "saved",
    "complete",
    "report_pending",
    "report",
})
_QUESTION_COUNT = 15
_MIN_ANSWER_WORDS = 5
_DEFAULT_MIME = "audio/webm"

_MOCK_V2_SESSION_KEYS = (
    _KEY_STEP,
    _KEY_SURVEY,
    _KEY_QUESTIONS,
    _KEY_INDEX,
    _KEY_ANSWERS,
    _KEY_AUDIO_BLOBS,
    _KEY_STARTED,
    _KEY_FINISHED,
    _KEY_REPORT,
)

_SCORE_LABELS = {
    "response_amount": "답변량",
    "relevance": "질문 적합도",
    "structure": "답변 구조",
    "grammar": "문법",
    "vocabulary": "어휘",
    "naturalness": "자연스러움",
}

_LEISURE_OPTS = [
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
_INTERESTS_OPTS = [
    "음악 감상하기",
    "악기 연주하기",
    "요리하기",
    "혼자 노래 부르기",
    "글쓰기",
    "그림 그리기",
]
_SPORTS_OPTS = [
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
]
_TRAVEL_OPTS = ["국내 여행", "해외 여행", "집에서 보내는 휴가(스테이케이션)"]

_MOCK_V2_DIFFICULTY_OPTIONS = [3, 4, 5, 6]
_MOCK_V2_DIFFICULTY_LABELS = {
    3: "레벨 3 (IL-IM1 목표)",
    4: "레벨 4 (IM2 목표)",
    5: "레벨 5 (IH 목표)",
    6: "레벨 6 (AL 목표)",
}


def _mock_v2_difficulty_radio_index(current: Any) -> int:
    try:
        value = int(current)
    except (TypeError, ValueError):
        return _MOCK_V2_DIFFICULTY_OPTIONS.index(5)
    if value in _MOCK_V2_DIFFICULTY_OPTIONS:
        return _MOCK_V2_DIFFICULTY_OPTIONS.index(value)
    return _MOCK_V2_DIFFICULTY_OPTIONS.index(5)


def clear_mock_v2_session() -> None:
    from utils.v2_flow_persistence import clear_mock_v2_disk_snapshot

    clear_mock_v2_disk_snapshot(st.session_state)
    for key in _MOCK_V2_SESSION_KEYS:
        st.session_state.pop(key, None)
    for key in (
        "mock_v2_new_final_bundle",
        "mock_v2_new_final_sig",
        "mock_v2_new_final_pdf_bytes",
        "_final_report_demo",
        "_demo_preview_loaded",
    ):
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if not isinstance(key, str):
            continue
        if key.startswith("mock_v2_mic_") or key.startswith("mock_v2_audio_"):
            st.session_state.pop(key, None)


def begin_mock_v2_session() -> None:
    clear_mock_v2_session()
    st.session_state[_KEY_STEP] = "survey"
    st.session_state[_KEY_INDEX] = 0
    st.session_state[_KEY_ANSWERS] = []
    st.session_state[_KEY_AUDIO_BLOBS] = {}


def _survey_topic_count(survey: Optional[Dict[str, Any]]) -> int:
    if not isinstance(survey, dict):
        return 0
    total = 0
    for key in ("leisure", "interests", "sports", "travel"):
        vals = survey.get(key)
        if isinstance(vals, list):
            total += len(vals)
    return total


def _log_mock_v2_route() -> None:
    try:
        questions = st.session_state.get(_KEY_QUESTIONS)
        answers = st.session_state.get(_KEY_ANSWERS)
        q_count = len(questions) if isinstance(questions, list) else 0
        a_count = len(answers) if isinstance(answers, list) else 0
        logger.debug(
            "[MOCK_V2_ROUTE] step=%s index=%s questions_count=%s answers_count=%s",
            str(st.session_state.get(_KEY_STEP) or "").strip() or "-",
            st.session_state.get(_KEY_INDEX),
            q_count,
            a_count,
        )
    except Exception:
        pass


def _normalize_step() -> str:
    step = str(st.session_state.get(_KEY_STEP) or "").strip()
    if step not in _VALID_STEPS:
        st.session_state[_KEY_STEP] = "survey"
        return "survey"
    return step


def _questions_list() -> List[Dict[str, Any]]:
    raw = st.session_state.get(_KEY_QUESTIONS)
    if isinstance(raw, list):
        return [q for q in raw if isinstance(q, dict)]
    return []


def _current_question() -> Optional[Dict[str, Any]]:
    questions = _questions_list()
    if not questions:
        return None
    idx = int(st.session_state.get(_KEY_INDEX) or 0)
    if idx < 0 or idx >= len(questions):
        return None
    return questions[idx]


def _answers_list() -> List[Dict[str, Any]]:
    raw = st.session_state.get(_KEY_ANSWERS)
    if isinstance(raw, list):
        return [a for a in raw if isinstance(a, dict)]
    return []


def _answer_for_index(q_idx: int) -> Optional[Dict[str, Any]]:
    for row in _answers_list():
        if int(row.get("question_index", -1)) == int(q_idx):
            return row
    return None


def _saved_count() -> int:
    return len(_answers_list())


def _stt_ready_count() -> int:
    n = 0
    for row in _answers_list():
        if str(row.get("stt_status") or "") == "transcript_ready":
            n += 1
            continue
        text = str(row.get("student_answer") or row.get("transcript") or "").strip()
        if text:
            n += 1
    return n


def _upsert_mock_v2_answer(row: Dict[str, Any]) -> None:
    idx = int(row.get("question_index", -1))
    answers = [a for a in _answers_list() if int(a.get("question_index", -1)) != idx]
    answers.append(row)
    answers.sort(key=lambda a: int(a.get("question_index", 0)))
    st.session_state[_KEY_ANSWERS] = answers
    from utils.v2_flow_persistence import persist_v2_flows_now

    persist_v2_flows_now(st.session_state)


def _audio_blobs() -> Dict[str, Dict[str, Any]]:
    raw = st.session_state.get(_KEY_AUDIO_BLOBS)
    if not isinstance(raw, dict):
        raw = {}
        st.session_state[_KEY_AUDIO_BLOBS] = raw
    return raw


def _mock_v2_mic_key(question_id: str) -> str:
    return f"mock_v2_mic_{question_id}"


def _mock_v2_mic_output_key(mic_key: str) -> str:
    return f"{mic_key}_output"


def _mock_v2_mime_from_mic_dict(mic_dict: Dict[str, Any], audio_bytes: bytes) -> str:
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

    return resolve_audio_mime(audio_bytes, _DEFAULT_MIME)


def _coerce_mock_v2_mic_payload_to_bytes(raw: Any) -> Tuple[bytes, str]:
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


def _extract_mock_v2_audio_bytes(
    mic_result: Any,
    *,
    mic_key: str = "",
) -> Tuple[bytes, str]:
    """Normalize streamlit_mic_recorder output to (bytes, mime_type)."""
    sources: List[Any] = []
    if mic_result is not None:
        sources.append(mic_result)
    if mic_key:
        cached = st.session_state.get(_mock_v2_mic_output_key(mic_key))
        if cached is not None and cached is not mic_result:
            sources.append(cached)
        qid_suffix = mic_key.replace("mock_v2_mic_", "", 1)
        if qid_suffix:
            alt = st.session_state.get(f"mock_v2_audio_{qid_suffix}")
            if alt is not None and alt not in sources:
                sources.append(alt)

    last_fail = "no_payload"
    for payload in sources:
        if isinstance(payload, (bytes, bytearray)):
            blob = bytes(payload)
            if blob:
                return blob, _DEFAULT_MIME
            last_fail = "empty_bytes"
            continue
        if not isinstance(payload, dict):
            last_fail = "unsupported_type"
            continue
        for key in ("bytes", "audio", "blob", "data", "audio_bytes"):
            if key not in payload:
                continue
            blob, fail = _coerce_mock_v2_mic_payload_to_bytes(payload.get(key))
            if fail:
                last_fail = fail
                continue
            if blob:
                return blob, _mock_v2_mime_from_mic_dict(payload, blob)
        last_fail = "dict_no_audio_field"

    try:
        logger.warning("[MOCK_V2_AUDIO_EXTRACT] failed category=%s", last_fail)
    except Exception:
        pass
    return b"", ""


def _log_mock_v2_mic_result(
    question_number: int,
    mic_result: Any,
    *,
    audio_bytes: bytes,
    mime_type: str,
    source: str,
) -> None:
    try:
        result_type = type(mic_result).__name__ if mic_result is not None else "None"
        keys = (
            sorted(str(k) for k in mic_result.keys()) if isinstance(mic_result, dict) else []
        )
        logger.info(
            "[MOCK_V2_MIC_RESULT] q=%s type=%s keys=%s audio_len=%s mime_type=%s source=%s",
            question_number,
            result_type,
            keys,
            len(audio_bytes),
            mime_type or _DEFAULT_MIME,
            source or "—",
        )
    except Exception:
        pass


def _save_mock_v2_audio_blob(answer_id: str, audio_bytes: bytes, mime_type: str) -> None:
    aid = str(answer_id or "").strip()
    if not aid:
        return
    try:
        blob = bytes(audio_bytes) if audio_bytes else b""
    except (TypeError, ValueError):
        blob = b""
    if not blob:
        return
    resolved_mime = (mime_type or _DEFAULT_MIME).strip() or _DEFAULT_MIME
    _audio_blobs()[aid] = {
        "audio_bytes": blob,
        "mime_type": resolved_mime,
        "audio_len": len(blob),
        "created_at": iso_now(),
    }


def _get_mock_v2_audio_blob(answer_id: str) -> Tuple[bytes, str]:
    aid = str(answer_id or "").strip()
    if not aid:
        return b"", ""
    entry = _audio_blobs().get(aid)
    if not isinstance(entry, dict):
        return b"", ""
    raw = entry.get("audio_bytes")
    if raw is None:
        return b"", ""
    try:
        blob = bytes(raw)
    except (TypeError, ValueError):
        return b"", ""
    if not blob:
        return b"", ""
    mime = str(entry.get("mime_type") or _DEFAULT_MIME).strip() or _DEFAULT_MIME
    return blob, mime


def _normalize_mock_v2_stt(stt_result: Any) -> Dict[str, Any]:
    if isinstance(stt_result, str):
        text = stt_result.strip()
        return {
            "ok": bool(text),
            "transcript": text,
            "raw_transcript": text,
            "error_category": "" if text else "empty_response",
            "error_message": "" if text else "empty_stt_response",
        }
    if isinstance(stt_result, dict):
        out = dict(stt_result)
        text = str(
            out.get("transcript") or out.get("text") or out.get("raw_transcript") or ""
        ).strip()
        if text and not out.get("transcript"):
            out["transcript"] = text
        if text and not out.get("raw_transcript"):
            out["raw_transcript"] = text
        if text and not out.get("ok"):
            out["ok"] = True
        return out
    return {
        "ok": False,
        "transcript": "",
        "raw_transcript": "",
        "error_category": "invalid_stt_result",
        "error_message": "invalid_stt_result_type",
    }


def _compute_mock_v2_statuses(
    *,
    audio_len: int,
    stt_result: Dict[str, Any],
    transcript: str,
    raw_transcript: str,
) -> Dict[str, Any]:
    from services.api_retry_policy import is_retryable_error

    text = (transcript or "").strip() or (raw_transcript or "").strip()
    wc = int(count_english_words(text))
    err_cat = str(stt_result.get("error_category") or "").strip()

    if audio_len <= 0:
        return {
            "stt_status": "stt_skipped_no_audio",
            "status": "recording_failed",
            "student_answer": "",
            "word_count": 0,
        }

    if text:
        return {
            "stt_status": "transcript_ready",
            "status": "saved" if wc >= _MIN_ANSWER_WORDS else "insufficient_response",
            "student_answer": text,
            "word_count": wc,
        }

    if is_retryable_error(err_cat) or bool(stt_result.get("retry_exhausted")):
        return {
            "stt_status": "stt_pending",
            "status": "stt_pending",
            "student_answer": "",
            "word_count": 0,
        }

    return {
        "stt_status": "stt_failed",
        "status": "stt_failed",
        "student_answer": "",
        "word_count": 0,
    }


def _duration_from_mic_result(mic_result: Any) -> float:
    if not isinstance(mic_result, dict):
        return 0.0
    for key in ("duration_seconds", "duration", "seconds"):
        if key not in mic_result:
            continue
        try:
            val = float(mic_result[key])
        except (TypeError, ValueError):
            continue
        if val > 0:
            return val
    return 0.0


def _resolve_mock_v2_duration(
    mic_result: Any,
    audio_bytes: bytes,
    mime_type: str,
) -> float:
    dur = _duration_from_mic_result(mic_result)
    if dur > 0:
        return dur
    blob = bytes(audio_bytes) if audio_bytes else b""
    if not blob:
        return 0.0
    try:
        from services.evaluation.eval_audio import compute_audio_duration_seconds

        est_dur, _ = compute_audio_duration_seconds(blob, mime_type or "")
        if est_dur and float(est_dur) > 0:
            return float(est_dur)
    except Exception:
        logger.debug("[MOCK_V2_DURATION] estimate failed", exc_info=True)
    return 0.0


def _estimate_wpm(word_count: int, duration_seconds: float) -> float:
    try:
        dur = float(duration_seconds)
    except (TypeError, ValueError):
        dur = 0.0
    if dur <= 0 or word_count <= 0:
        return 0.0
    return round(int(word_count) / (dur / 60.0), 1)


def _run_mock_v2_stt(
    question_id: str,
    question_text: str,
    audio_bytes: bytes,
    mime_type: str,
) -> Dict[str, Any]:
    from services.stt_service import transcribe_answer_audio

    blob = bytes(audio_bytes) if audio_bytes else b""
    resolved_mime = (mime_type or _DEFAULT_MIME).strip() or _DEFAULT_MIME
    if len(blob) <= 0:
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
        mode="mock_v2",
        question_id=question_id,
    )


def _build_mock_v2_answer_row(
    q: Dict[str, Any],
    *,
    audio_bytes: bytes,
    mime_type: str,
    stt_result: Dict[str, Any],
    mic_result: Any = None,
    prior_row: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    idx = int(q.get("question_index", 0))
    qnum = int(q.get("question_number") or (idx + 1))
    question_id = str(q.get("id") or f"mock_v2_q{qnum}")
    question_text = str(q.get("question_text") or "")

    blob = bytes(audio_bytes) if audio_bytes else b""
    audio_len = len(blob)
    resolved_mime = (mime_type or _DEFAULT_MIME).strip() or _DEFAULT_MIME

    stt_n = _normalize_mock_v2_stt(stt_result)
    transcript = str(stt_n.get("transcript") or "").strip()
    raw_transcript = str(stt_n.get("raw_transcript") or transcript).strip()
    stt_err_cat = str(stt_n.get("error_category") or "")
    stt_err_msg = str(stt_n.get("error_message") or "")
    statuses = _compute_mock_v2_statuses(
        audio_len=audio_len,
        stt_result=stt_n,
        transcript=transcript,
        raw_transcript=raw_transcript,
    )

    try:
        logger.info(
            "[MOCK_V2_STT_RESULT] question_number=%s ok=%s text_len=%s error_category=%s",
            qnum,
            bool(stt_n.get("ok")),
            len(transcript or raw_transcript),
            stt_err_cat or "—",
        )
    except Exception:
        pass

    duration_seconds = _resolve_mock_v2_duration(mic_result, blob, resolved_mime)
    if prior_row and duration_seconds <= 0:
        try:
            duration_seconds = float(prior_row.get("duration_seconds") or 0.0)
        except (TypeError, ValueError):
            duration_seconds = 0.0

    word_count = int(statuses.get("word_count") or 0)
    wpm = _estimate_wpm(word_count, duration_seconds) if duration_seconds > 0 else 0.0

    answer_id = str(prior_row.get("answer_id") or "").strip() if prior_row else ""
    if not answer_id:
        answer_id = str(uuid.uuid4())

    created_at = iso_now()
    if prior_row and str(prior_row.get("created_at") or "").strip():
        created_at = str(prior_row.get("created_at"))

    return {
        "answer_id": answer_id,
        "question_index": idx,
        "question_number": qnum,
        "question_id": question_id,
        "opic_type": str(q.get("opic_type") or ""),
        "combo": str(q.get("combo") or ""),
        "topic": str(q.get("topic") or ""),
        "question_text": question_text,
        "ko_helper": str(q.get("ko_helper") or ""),
        "audio_saved": audio_len > 0,
        "audio_len": audio_len,
        "has_audio_bytes": audio_len > 0,
        "mime_type": resolved_mime,
        "transcript": transcript or raw_transcript,
        "student_answer": str(statuses.get("student_answer") or ""),
        "word_count": word_count,
        "duration_seconds": duration_seconds,
        "wpm": wpm,
        "stt_status": str(statuses.get("stt_status") or ""),
        "stt_error_category": stt_err_cat,
        "stt_error_message": stt_err_msg,
        "status": str(statuses.get("status") or ""),
        "created_at": created_at,
    }


def _commit_mock_v2_recording(
    q: Dict[str, Any],
    audio_bytes: bytes,
    mime_type: str,
    mic_result: Any = None,
) -> bool:
    if st.session_state.get("_mock_v2_stt_in_flight"):
        try:
            logger.info("[MOCK_V2_STT_SKIP] reason=already_in_flight")
        except Exception:
            pass
        return False
    st.session_state["_mock_v2_stt_in_flight"] = True
    try:
        return _commit_mock_v2_recording_impl(q, audio_bytes, mime_type, mic_result)
    finally:
        st.session_state.pop("_mock_v2_stt_in_flight", None)


def _commit_mock_v2_recording_impl(
    q: Dict[str, Any],
    audio_bytes: bytes,
    mime_type: str,
    mic_result: Any = None,
) -> bool:
    blob = bytes(audio_bytes) if audio_bytes else b""
    audio_len = len(blob)
    resolved_mime = (mime_type or _DEFAULT_MIME).strip() or _DEFAULT_MIME
    qnum = int(q.get("question_number") or 1)
    question_id = str(q.get("id") or f"mock_v2_q{qnum}")

    if audio_len <= 0:
        return False

    try:
        logger.info(
            "[MOCK_V2_RECORDING_COMMIT] question_number=%s question_id=%s audio_len=%s mime_type=%s",
            qnum,
            question_id,
            audio_len,
            resolved_mime,
        )
    except Exception:
        pass

    idx = int(q.get("question_index", 0))
    prior = _answer_for_index(idx)
    answer_id = str(prior.get("answer_id") or "") if prior else str(uuid.uuid4())

    _save_mock_v2_audio_blob(answer_id, blob, resolved_mime)

    stt_result = _run_mock_v2_stt(
        question_id,
        str(q.get("question_text") or ""),
        blob,
        resolved_mime,
    )
    row = _build_mock_v2_answer_row(
        q,
        audio_bytes=blob,
        mime_type=resolved_mime,
        stt_result=stt_result,
        mic_result=mic_result,
        prior_row=prior,
    )
    row["answer_id"] = answer_id
    _upsert_mock_v2_answer(row)

    try:
        logger.info(
            "[MOCK_V2_ANSWER_SAVED] question_number=%s answers_count=%s status=%s "
            "audio_saved=%s student_answer_len=%s",
            qnum,
            _saved_count(),
            row.get("status"),
            bool(row.get("audio_saved")),
            len(str(row.get("student_answer") or "")),
        )
    except Exception:
        pass

    st.session_state[_KEY_STEP] = "saved"
    return True


def _commit_mock_v2_timer_expired(q: Dict[str, Any]) -> bool:
    """Fallback when the answer timer expires without usable mic audio."""
    idx = int(q.get("question_index", st.session_state.get(_KEY_INDEX) or 0))
    prior = _answer_for_index(idx)
    stt_result = {
        "ok": False,
        "transcript": "",
        "raw_transcript": "",
        "error_category": "timer_expired",
        "error_message": "answer_time_limit_reached",
        "provider": "",
    }
    row = _build_mock_v2_answer_row(
        q,
        audio_bytes=b"",
        mime_type=_DEFAULT_MIME,
        stt_result=stt_result,
        prior_row=prior,
    )
    if prior and str(prior.get("answer_id") or "").strip():
        row["answer_id"] = str(prior.get("answer_id"))
    row["source"] = "timer_expired"
    _upsert_mock_v2_answer(row)
    st.session_state[_KEY_STEP] = "saved"
    return True


def _retry_mock_v2_stt(q_idx: int) -> bool:
    row = _answer_for_index(q_idx)
    if not row:
        return False
    answer_id = str(row.get("answer_id") or "").strip()
    audio_bytes, mime_type = _get_mock_v2_audio_blob(answer_id)
    if not audio_bytes:
        return False

    q = _current_question()
    if q is None:
        questions = _questions_list()
        if 0 <= q_idx < len(questions):
            q = questions[q_idx]
    if q is None:
        return False

    with st.spinner("음성을 다시 인식하고 있어요…"):
        stt_result = _run_mock_v2_stt(
            str(row.get("question_id") or q.get("id") or ""),
            str(row.get("question_text") or q.get("question_text") or ""),
            audio_bytes,
            mime_type,
        )
        updated = _build_mock_v2_answer_row(
            q,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            stt_result=stt_result,
            prior_row=row,
        )
        updated["answer_id"] = answer_id
        _upsert_mock_v2_answer(updated)
    return True


def _render_mock_v2_survey() -> None:
    render_top_bar("실전 모의고사", back_href="?nav=MOCK", eyebrow="실전 모의고사")
    st.title("실전 모의고사 · Background Survey")
    st.write("OPIc 실전 흐름에 맞춰 15문항 시험지가 생성됩니다.")

    difficulty = st.radio(
        "난이도",
        _MOCK_V2_DIFFICULTY_OPTIONS,
        index=_mock_v2_difficulty_radio_index(st.session_state.get("mock_v2_difficulty", 5)),
        format_func=lambda v: _MOCK_V2_DIFFICULTY_LABELS[v],
        horizontal=True,
        key="mock_v2_difficulty",
    )

    col_left, col_right = st.columns(2)
    with col_left:
        work = st.radio(
            "직업/신분",
            ["사업·회사원", "교직자", "학생(학위 과정 중)", "군인", "일하지 않음"],
            key="mock_v2_work",
        )
        housing = st.radio(
            "주거",
            ["홀로 거주", "가족과 함께 거주", "친구/룸메이트와 거주"],
            key="mock_v2_housing",
        )
        if "mock_v2_leisure" not in st.session_state:
            st.session_state["mock_v2_leisure"] = ["영화 보기", "공원 가기"]
        st.multiselect("여가 활동", _LEISURE_OPTS, key="mock_v2_leisure")
    with col_right:
        if "mock_v2_interests" not in st.session_state:
            st.session_state["mock_v2_interests"] = ["음악 감상하기", "요리하기"]
        st.multiselect("취미/관심사", _INTERESTS_OPTS, key="mock_v2_interests")
        if "mock_v2_sports" not in st.session_state:
            st.session_state["mock_v2_sports"] = ["조깅", "걷기"]
        st.multiselect("운동", _SPORTS_OPTS, key="mock_v2_sports")
        if "mock_v2_travel" not in st.session_state:
            st.session_state["mock_v2_travel"] = ["국내 여행"]
        st.multiselect("여행", _TRAVEL_OPTS, key="mock_v2_travel")

    leisure = list(st.session_state.get("mock_v2_leisure") or [])
    interests = list(st.session_state.get("mock_v2_interests") or [])
    sports = list(st.session_state.get("mock_v2_sports") or [])
    travel = list(st.session_state.get("mock_v2_travel") or [])

    selected_count = len(leisure) + len(interests) + len(sports) + len(travel)
    st.info(f"현재 선택한 항목 개수: **{selected_count} / 12**")
    enough_selected = selected_count >= 12
    if not enough_selected:
        st.warning("항목을 12개 이상 선택해야 시험을 시작할 수 있습니다.")

    if st.button(
        "시험지 생성 및 시험 시작",
        type="primary",
        disabled=not enough_selected,
        key="mock_v2_start_exam",
    ):
        survey_results = {
            "work": work,
            "housing": housing,
            "leisure": leisure,
            "interests": interests,
            "sports": sports,
            "travel": travel,
            "difficulty": int(difficulty),
        }
        try:
            questions = build_mock_v2_exam(survey_results, difficulty=int(difficulty))
        except Exception as exc:
            logger.exception("[MOCK_V2_EXAM_BUILT] failed difficulty=%s", difficulty)
            st.error(f"시험지 생성에 실패했습니다: {exc}")
            return

        st.session_state[_KEY_SURVEY] = survey_results
        st.session_state[_KEY_QUESTIONS] = questions
        st.session_state[_KEY_INDEX] = 0
        st.session_state[_KEY_ANSWERS] = []
        st.session_state[_KEY_AUDIO_BLOBS] = {}
        st.session_state[_KEY_STARTED] = iso_now()
        st.session_state.pop(_KEY_FINISHED, None)
        st.session_state[_KEY_STEP] = "question"

        try:
            logger.info(
                "[MOCK_V2_EXAM_BUILT] questions_count=%s difficulty=%s survey_topic_count=%s",
                len(questions),
                int(difficulty),
                _survey_topic_count(survey_results),
            )
        except Exception:
            pass
        st.rerun()


def _render_mock_v2_question_listen(q: dict, qnum: int) -> None:
    """Play pre-built question MP3 when available (same pattern as topic_practice_v2)."""
    audio_id = mock_v2_question_audio_id(q)
    if not audio_id:
        return
    audio_bytes = load_question_mp3_bytes(audio_id)
    if not audio_bytes:
        return
    render_exam_question_audio_player(
        audio_bytes,
        "audio/mp3",
        f"mock_v2_{audio_id}",
        int(qnum),
        max_plays=2,
        accent="teal",
    )


def _render_mock_v2_question() -> None:
    q = _current_question()
    if q is None:
        st.warning("문항을 불러오지 못했습니다. 설문부터 다시 시작해 주세요.")
        if st.button("설문으로 돌아가기", key="mock_v2_fallback_survey"):
            st.session_state[_KEY_STEP] = "survey"
            st.rerun()
        return

    idx = int(q.get("question_index", st.session_state.get(_KEY_INDEX) or 0))
    if _answer_for_index(idx) is not None:
        st.session_state[_KEY_STEP] = "saved"
        st.rerun()
        return

    qnum = int(q.get("question_number") or 1)
    question_id = str(q.get("id") or f"mock_v2_q{qnum}")

    render_top_bar(
        f"Q{qnum}",
        back_href="?nav=MOCK",
        eyebrow="실전 모의고사",
    )

    render_exam_question_shell(
        eyebrow="실전 모의고사",
        progress_html=build_progress_segments_html(qnum, _QUESTION_COUNT),
        badge_label=opic_type_badge_label(str(q.get("opic_type") or "")),
        question_en=str(q.get("question_text") or ""),
        question_ko=str(q.get("ko_helper") or ""),
        accent="teal",
    )
    _render_mock_v2_question_listen(q, qnum)
    render_exam_answer_card_top(accent="teal")
    timer_id = build_answer_timer_id("mock_v2", question_id, str(idx))
    render_answer_countdown_timer(
        timer_id=timer_id,
        accent="teal",
        duration_sec=DEFAULT_DURATION_SEC,
    )
    render_exam_wave_mic_observer()

    from streamlit_mic_recorder import mic_recorder

    mic_key = _mock_v2_mic_key(question_id)
    mic_result = mic_recorder(
        start_prompt="🎤 답변 시작",
        stop_prompt="■ 녹음 완료",
        key=mic_key,
        use_container_width=True,
        just_once=True,
    )

    if mic_result is not None:
        dismiss_answer_timer_signal(timer_id)
        audio_bytes, mime_type = _extract_mock_v2_audio_bytes(mic_result, mic_key=mic_key)
        extraction_source = "mic_result" if audio_bytes else "empty"
        _log_mock_v2_mic_result(
            qnum,
            mic_result,
            audio_bytes=audio_bytes,
            mime_type=mime_type or _DEFAULT_MIME,
            source=extraction_source,
        )
        if len(audio_bytes) > 0:
            with st.spinner("답변을 저장하고 음성을 인식하고 있어요…"):
                if _commit_mock_v2_recording(q, audio_bytes, mime_type, mic_result=mic_result):
                    st.rerun()
        else:
            st.warning("음성이 저장되지 않았어요. 다시 녹음해 주세요.")

    def _commit_from_timer(audio_bytes: bytes, mime_type: str, mic_payload: Any) -> None:
        with st.spinner("답변을 저장하고 음성을 인식하고 있어요…"):
            _commit_mock_v2_recording(q, audio_bytes, mime_type, mic_result=mic_payload)

    if handle_answer_timer_expiry(
        timer_id,
        mic_result=mic_result,
        extract_audio=lambda: _extract_mock_v2_audio_bytes(None, mic_key=mic_key),
        commit_audio=_commit_from_timer,
        commit_empty=lambda: _commit_mock_v2_timer_expired(q),
    ):
        st.rerun()


def _render_mock_v2_saved() -> None:
    q = _current_question()
    if q is None:
        st.session_state[_KEY_STEP] = "survey"
        st.rerun()
        return

    idx = int(q.get("question_index", st.session_state.get(_KEY_INDEX) or 0))
    saved_row = _answer_for_index(idx)
    if saved_row is None:
        st.session_state[_KEY_STEP] = "question"
        st.rerun()
        return

    qnum = int(q.get("question_number") or 1)
    render_top_bar("저장됨", back_href="?nav=MOCK", eyebrow="실전 모의고사")
    st.title("답변이 저장되었어요.")

    answer_id = str(saved_row.get("answer_id") or "")
    audio_bytes, mime_type = _get_mock_v2_audio_blob(answer_id)

    st.markdown("##### 내 녹음 다시 듣기")
    if audio_bytes:
        try:
            st.audio(audio_bytes, format=mime_type or _DEFAULT_MIME)
        except Exception:
            st.audio(audio_bytes)
    else:
        st.caption("녹음 파일이 없습니다.")

    st.markdown("##### AI가 인식한 답변")
    transcript = str(
        saved_row.get("student_answer")
        or saved_row.get("transcript")
        or ""
    ).strip()
    stt_status = str(saved_row.get("stt_status") or "")
    has_audio = bool(saved_row.get("audio_saved")) or int(saved_row.get("audio_len") or 0) > 0

    row_status = str(saved_row.get("status") or "")
    if transcript:
        st.info(transcript)
    elif has_audio and (stt_status == "stt_pending" or row_status == "stt_pending"):
        st.warning("녹음은 저장되었지만, 음성 인식이 지연되었어요.")
    elif has_audio:
        st.warning("녹음은 저장되었지만, 음성 인식이 지연되었어요.")

    needs_stt_retry = bool(audio_bytes) and not transcript and has_audio
    if needs_stt_retry:
        if st.button(
            "AI 음성 인식 다시 시도",
            use_container_width=True,
            key=f"mock_v2_stt_retry_{qnum}",
        ):
            _retry_mock_v2_stt(idx)
            st.rerun()

    is_last = qnum >= _QUESTION_COUNT
    if not is_last:
        if st.button(
            "다음 문제",
            type="primary",
            use_container_width=True,
            key="mock_v2_next_question",
        ):
            st.session_state[_KEY_INDEX] = idx + 1
            st.session_state[_KEY_STEP] = "question"
            st.rerun()
    else:
        if st.button(
            "모의고사 완료",
            type="primary",
            use_container_width=True,
            key="mock_v2_finish_exam",
        ):
            st.session_state[_KEY_STEP] = "complete"
            st.session_state[_KEY_FINISHED] = iso_now()
            st.rerun()


def _run_mock_v2_report_generation() -> None:
    """Single button-triggered report attempt — not called on passive rerun."""
    from services.mock_v2_analysis import analyze_mock_v2_answers

    for key in (
        "mock_v2_new_final_bundle",
        "mock_v2_new_final_sig",
        "mock_v2_new_final_pdf_bytes",
    ):
        st.session_state.pop(key, None)

    with st.spinner("AI 리포트를 생성하고 있어요…"):
        result = analyze_mock_v2_answers(_answers_list(), _questions_list())
    st.session_state[_KEY_REPORT] = result
    if result.get("ok"):
        st.session_state[_KEY_STEP] = "report"
        try:
            from utils.history_sync import save_mock_v2_report

            sig = str(
                st.session_state.get(_KEY_FINISHED)
                or st.session_state.get(_KEY_STARTED)
                or ""
            )
            save_mock_v2_report(result, sig=sig)
        except Exception:
            pass
    else:
        st.session_state[_KEY_STEP] = "report_pending"
    st.rerun()


def _render_mock_v2_complete() -> None:
    render_top_bar("완료", back_href="?nav=MOCK", eyebrow="실전 모의고사")
    st.title("모의고사가 완료되었어요.")
    saved = _saved_count()
    stt_done = _stt_ready_count()
    st.markdown(f"저장된 답변: **{saved}/{_QUESTION_COUNT}**")
    st.markdown(f"음성 인식 완료: **{stt_done}/{_QUESTION_COUNT}**")

    if st.button("AI 최종 리포트 받기", type="primary", key="mock_v2_request_report"):
        _run_mock_v2_report_generation()

    c1, c2 = st.columns(2)
    with c1:
        if st.button("다시 시작", key="mock_v2_restart"):
            begin_mock_v2_session()
            st.rerun()
    with c2:
        if st.button("학습하기로 돌아가기", key="mock_v2_back_portal"):
            clear_mock_v2_session()
            st.session_state.pop("mock_mode", None)
            st.session_state["practice_portal_selected"] = False
            st.rerun()


def _render_mock_v2_report_pending() -> None:
    render_top_bar("리포트", back_href="?nav=MOCK", eyebrow="실전 모의고사")
    st.title("AI 리포트 생성이 잠시 지연되고 있어요.")
    st.write("답변은 저장되어 있습니다. 잠시 후 다시 시도해 주세요.")

    report = st.session_state.get(_KEY_REPORT)
    if isinstance(report, dict):
        err_cat = str(report.get("error_category") or "").strip()
        if err_cat:
            st.caption(f"오류 유형: {err_cat}")

    if st.button("리포트 다시 시도", type="primary", key="mock_v2_report_retry"):
        _run_mock_v2_report_generation()

    if st.button("완료 화면으로", key="mock_v2_back_complete"):
        st.session_state[_KEY_STEP] = "complete"
        st.rerun()


def _render_mock_v2_report() -> None:
    report = st.session_state.get(_KEY_REPORT)
    if not isinstance(report, dict) or not report.get("ok"):
        st.session_state[_KEY_STEP] = "report_pending"
        st.rerun()
        return

    from views.new_final_report import render_new_final_report

    is_demo = bool(st.session_state.get("_final_report_demo"))

    def _portal() -> None:
        if is_demo:
            from services.final_report_demo import exit_demo_final_report
            from views.mock_exam import mock_session

            exit_demo_final_report(mock_session())
        else:
            clear_mock_v2_session()
            st.session_state.pop("mock_mode", None)
            st.session_state["practice_portal_selected"] = False
        st.rerun()

    def _restart() -> None:
        if is_demo:
            from services.final_report_demo import (
                exit_demo_final_report,
                open_demo_final_report,
            )
            from views.mock_exam import mock_session

            mx = mock_session()
            exit_demo_final_report(mx)
            open_demo_final_report(mx)
        else:
            begin_mock_v2_session()
        st.rerun()

    render_new_final_report(
        report,
        _answers_list(),
        _questions_list(),
        attempt_no=1,
        is_demo=is_demo,
        on_restart=_restart,
        on_portal=_portal,
        on_retry_stt=_retry_mock_v2_stt if not is_demo else None,
    )


def render_mock_v2() -> None:
    if _KEY_STEP not in st.session_state:
        begin_mock_v2_session()

    if st.session_state.pop("_v2_user_resumed", None):
        st.info("저장된 답변을 불러왔어요. 이어서 진행해 주세요.")

    step = _normalize_step()
    _log_mock_v2_route()

    if step == "survey":
        _render_mock_v2_survey()
    elif step == "question":
        if not _questions_list():
            st.session_state[_KEY_STEP] = "survey"
            _render_mock_v2_survey()
        else:
            _render_mock_v2_question()
    elif step == "saved":
        if not _questions_list():
            st.session_state[_KEY_STEP] = "survey"
            _render_mock_v2_survey()
        else:
            _render_mock_v2_saved()
    elif step == "complete":
        _render_mock_v2_complete()
    elif step == "report_pending":
        _render_mock_v2_report_pending()
    elif step == "report":
        _render_mock_v2_report()
    else:
        st.session_state[_KEY_STEP] = "survey"
        _render_mock_v2_survey()
