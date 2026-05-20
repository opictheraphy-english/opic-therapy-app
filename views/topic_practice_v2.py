"""Topic Practice V2 — isolated shell (routing + static questions only)."""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from components.topbar import render_top_bar
from services.stt_service import count_english_words
from utils.session_state import ensure_mock, mock_session

logger = logging.getLogger(__name__)

_KEY_AUDIO_BLOBS = "topic_v2_audio_blobs"
_MIN_SAVED_WORDS = 5

MOCK_MODE_TOPIC_V2 = "topic_practice_v2"

_KEY_STEP = "topic_v2_step"
_KEY_TOPIC = "topic_v2_topic"
_KEY_Q_INDEX = "topic_v2_question_index"
_KEY_CURRENT_Q = "topic_v2_current_question"
_KEY_ANSWERS = "topic_v2_answers"
_KEY_FEEDBACK = "topic_v2_feedback"
_KEY_DRAFT_TRANSCRIPT = "topic_v2_practice_transcript"

_VALID_STEPS = frozenset({"select_topic", "question", "saved", "feedback", "pending"})

_TOPIC_PRACTICE_V2_CATALOG: List[Dict[str, Any]] = [
    {
        "title": "집",
        "questions": [
            {
                "en": "Tell me about your home.",
                "ko": "집에 대해 말해 보세요.",
            },
            {
                "en": "What do you like most about your home?",
                "ko": "집에서 가장 마음에 드는 점은 무엇인가요?",
            },
            {
                "en": "Tell me about a memorable day you spent at home.",
                "ko": "집에서 보낸 기억에 남는 하루를 말해 보세요.",
            },
        ],
    },
    {
        "title": "카페",
        "questions": [
            {
                "en": "Tell me about a cafe you often go to.",
                "ko": "자주 가는 카페에 대해 말해 보세요.",
            },
            {
                "en": "What do you usually do at that cafe?",
                "ko": "그 카페에서는 보통 무엇을 하면서 시간을 보내나요?",
            },
            {
                "en": "Tell me about a memorable experience you had at a cafe.",
                "ko": "카페에서 있었던 기억에 남는 경험을 말해 보세요.",
            },
        ],
    },
    {
        "title": "영화",
        "questions": [
            {
                "en": "What kind of movies do you enjoy?",
                "ko": "어떤 장르의 영화를 좋아하나요?",
            },
            {
                "en": "Tell me about a movie you watched recently.",
                "ko": "최근에 본 영화에 대해 말해 보세요.",
            },
            {
                "en": "Tell me about a movie that left a strong impression on you.",
                "ko": "인상 깊게 본 영화가 있다면 말해 보세요.",
            },
        ],
    },
    {
        "title": "공원",
        "questions": [
            {
                "en": "Tell me about a park you like to visit.",
                "ko": "자주 가는 공원에 대해 말해 보세요.",
            },
            {
                "en": "What do you usually do when you go to that park?",
                "ko": "그 공원에 가면 보통 무엇을 하나요?",
            },
            {
                "en": "Tell me about a memorable experience you had at a park.",
                "ko": "공원에서 있었던 기억에 남는 일을 말해 보세요.",
            },
        ],
    },
    {
        "title": "여행",
        "questions": [
            {
                "en": "Tell me about a trip you took recently.",
                "ko": "최근 다녀온 여행에 대해 말해 보세요.",
            },
            {
                "en": "Where would you like to travel next and why?",
                "ko": "다음에 가고 싶은 여행지와 이유를 말해 보세요.",
            },
            {
                "en": "Tell me about your most memorable travel experience.",
                "ko": "가장 기억에 남는 여행 경험을 말해 보세요.",
            },
        ],
    },
    {
        "title": "음악",
        "questions": [
            {
                "en": "What kind of music do you usually listen to?",
                "ko": "평소 어떤 음악을 듣나요?",
            },
            {
                "en": "Tell me about a concert or live performance you attended.",
                "ko": "들었던 콘서트나 라이브 공연에 대해 말해 보세요.",
            },
            {
                "en": "Tell me about a song that means a lot to you.",
                "ko": "특별한 의미가 있는 노래가 있다면 말해 보세요.",
            },
        ],
    },
    {
        "title": "음식",
        "questions": [
            {
                "en": "What is your favorite food?",
                "ko": "가장 좋아하는 음식은 무엇인가요?",
            },
            {
                "en": "Tell me about a restaurant you go to often.",
                "ko": "자주 가는 식당에 대해 말해 보세요.",
            },
            {
                "en": "Tell me about a memorable meal you had.",
                "ko": "인상 깊었던 식사 경험을 말해 보세요.",
            },
        ],
    },
    {
        "title": "쇼핑",
        "questions": [
            {
                "en": "Tell me about a place where you often shop.",
                "ko": "자주 가는 쇼핑 장소에 대해 말해 보세요.",
            },
            {
                "en": "What do you usually buy when you go shopping?",
                "ko": "쇼핑할 때 주로 무엇을 사나요?",
            },
            {
                "en": "Tell me about a memorable shopping experience.",
                "ko": "기억에 남는 쇼핑 경험을 말해 보세요.",
            },
        ],
    },
    {
        "title": "운동",
        "questions": [
            {
                "en": "How do you usually stay active or exercise?",
                "ko": "평소 어떻게 운동하나요?",
            },
            {
                "en": "Tell me about a sport or activity you enjoy.",
                "ko": "좋아하는 운동이나 활동에 대해 말해 보세요.",
            },
            {
                "en": "Tell me about a time you challenged yourself physically.",
                "ko": "체력적으로 스스로에게 도전했던 경험을 말해 보세요.",
            },
        ],
    },
    {
        "title": "기술",
        "questions": [
            {
                "en": "How do you use technology in your daily life?",
                "ko": "일상에서 기술을 어떻게 활용하나요?",
            },
            {
                "en": "Tell me about a gadget or app you find very useful.",
                "ko": "유용하게 쓰는 기기나 앱에 대해 말해 보세요.",
            },
            {
                "en": "Tell me about a time technology helped you solve a problem.",
                "ko": "기술이 문제 해결에 도움이 되었던 경험을 말해 보세요.",
            },
        ],
    },
]


def clear_topic_v2_session() -> None:
    """Remove Topic Practice V2 keys from Streamlit session (portal / reset)."""
    for k in (
        _KEY_STEP,
        _KEY_TOPIC,
        _KEY_Q_INDEX,
        _KEY_CURRENT_Q,
        _KEY_ANSWERS,
        _KEY_FEEDBACK,
        _KEY_DRAFT_TRANSCRIPT,
        _KEY_AUDIO_BLOBS,
    ):
        st.session_state.pop(k, None)


def _topic_pack(title: str) -> Optional[Dict[str, Any]]:
    for row in _TOPIC_PRACTICE_V2_CATALOG:
        if row.get("title") == title:
            return row
    return None


def _question_for(title: str, q_index: int) -> Optional[Dict[str, str]]:
    pack = _topic_pack(title)
    if not pack:
        return None
    qs = pack.get("questions") or []
    if q_index < 0 or q_index >= len(qs):
        return None
    q = qs[q_index]
    if not isinstance(q, dict):
        return None
    return {"en": str(q.get("en") or ""), "ko": str(q.get("ko") or "")}


def _topic_v2_blob_key(topic: str, q_idx: int) -> str:
    return f"{topic}\t{int(q_idx)}"


def _topic_v2_blob_store() -> Dict[str, Any]:
    if _KEY_AUDIO_BLOBS not in st.session_state:
        st.session_state[_KEY_AUDIO_BLOBS] = {}
    raw = st.session_state[_KEY_AUDIO_BLOBS]
    return raw if isinstance(raw, dict) else {}


def _save_topic_v2_audio_blob(topic: str, q_idx: int, audio_bytes: bytes, mime_type: str) -> None:
    store = _topic_v2_blob_store()
    store[_topic_v2_blob_key(topic, q_idx)] = {
        "audio_bytes": bytes(audio_bytes),
        "mime_type": (mime_type or "audio/webm").strip() or "audio/webm",
    }
    st.session_state[_KEY_AUDIO_BLOBS] = store


def _delete_topic_v2_audio_blob(topic: str, q_idx: int) -> None:
    store = _topic_v2_blob_store()
    store.pop(_topic_v2_blob_key(topic, q_idx), None)
    st.session_state[_KEY_AUDIO_BLOBS] = store


def _get_topic_v2_audio_blob(topic: str, q_idx: int) -> Tuple[bytes, str]:
    ent = _topic_v2_blob_store().get(_topic_v2_blob_key(topic, q_idx))
    if not isinstance(ent, dict):
        return b"", ""
    raw = ent.get("audio_bytes")
    try:
        blob = bytes(raw) if raw is not None else b""
    except (TypeError, ValueError):
        blob = b""
    mime = str(ent.get("mime_type") or "audio/webm").strip() or "audio/webm"
    return blob, mime


def _topic_v2_mic_key(topic: str, q_idx: int) -> str:
    return f"topic_v2_mic_{topic}_{int(q_idx)}"


def _topic_v2_mic_output_key(mic_key: str) -> str:
    return f"{mic_key}_output"


def _topic_v2_mime_from_mic_dict(mic_dict: Dict[str, Any], audio_bytes: bytes) -> str:
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


def _coerce_topic_v2_mic_payload_to_bytes(raw: Any) -> Tuple[bytes, str]:
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
            try:
                logger.debug("[TOPIC_V2_MIC] base64_decode_failed", exc_info=True)
            except Exception:
                pass
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


def _extract_topic_v2_audio_bytes(mic_result: Any, *, mic_key: str = "") -> Tuple[bytes, str]:
    """Normalize streamlit_mic_recorder output; optional session cache when just_once clears return."""
    sources: List[Any] = []
    if mic_result is not None:
        sources.append(mic_result)
    if mic_key:
        cached = st.session_state.get(_topic_v2_mic_output_key(mic_key))
        if cached is not None and cached is not mic_result:
            sources.append(cached)

    last_fail = "no_payload"
    for payload in sources:
        if isinstance(payload, (bytes, bytearray)):
            blob = bytes(payload)
            if blob:
                return blob, "audio/webm"
            last_fail = "empty_bytes"
            continue
        if not isinstance(payload, dict):
            last_fail = "unsupported_type"
            continue
        for key in ("bytes", "audio", "blob", "data", "audio_bytes"):
            if key not in payload:
                continue
            blob, fail = _coerce_topic_v2_mic_payload_to_bytes(payload.get(key))
            if fail:
                last_fail = fail
                continue
            if blob:
                resolved_mime = _topic_v2_mime_from_mic_dict(payload, blob)
                return blob, resolved_mime
        last_fail = "dict_no_audio_field"

    try:
        logger.warning("[TOPIC_V2_AUDIO_EXTRACT] failed category=%s", last_fail)
    except Exception:
        pass
    return b"", ""


def _normalize_topic_v2_stt(stt_result: Any) -> Dict[str, Any]:
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


def _compute_topic_v2_statuses(
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
            "recording_status": "recording_failed",
            "stt_status": "stt_skipped_no_audio",
            "status": "recording_failed",
            "student_answer": "",
            "word_count": 0,
        }

    recording_status = "recorded"
    if text:
        return {
            "recording_status": recording_status,
            "stt_status": "transcript_ready",
            "status": "saved" if wc >= _MIN_SAVED_WORDS else "insufficient_response",
            "student_answer": text,
            "word_count": wc,
        }

    if is_retryable_error(err_cat) or bool(stt_result.get("retry_exhausted")):
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


def _build_topic_v2_row_from_mic(
    topic: str,
    q_idx: int,
    q_en: str,
    q_ko: str,
    audio_bytes: bytes,
    mime_type: str,
    stt_result: Dict[str, Any],
) -> Dict[str, Any]:
    blob = bytes(audio_bytes) if audio_bytes else b""
    audio_len = len(blob)
    resolved_mime = (mime_type or "audio/webm").strip() or "audio/webm"
    stt_n = _normalize_topic_v2_stt(stt_result)
    transcript = str(stt_n.get("transcript") or "").strip()
    raw_transcript = str(stt_n.get("raw_transcript") or transcript).strip()
    stt_err_cat = str(stt_n.get("error_category") or "")
    stt_err_msg = str(stt_n.get("error_message") or "")
    statuses = _compute_topic_v2_statuses(
        audio_len=audio_len,
        stt_result=stt_n,
        transcript=transcript,
        raw_transcript=raw_transcript,
    )
    return {
        "topic": topic,
        "q_index": int(q_idx),
        "en": q_en,
        "ko": q_ko,
        "source": "mic",
        "audio_saved": audio_len > 0,
        "audio_len": audio_len,
        "mime_type": resolved_mime,
        "transcript": transcript or raw_transcript,
        "raw_transcript": raw_transcript or transcript,
        "student_answer": str(statuses.get("student_answer") or ""),
        "stt_status": str(statuses.get("stt_status") or ""),
        "stt_error_category": stt_err_cat,
        "stt_error_message": stt_err_msg,
        "recording_status": str(statuses.get("recording_status") or ""),
        "status": str(statuses.get("status") or ""),
        "word_count": int(statuses.get("word_count") or 0),
        "placeholder": False,
    }


def _upsert_topic_v2_answer(row: Dict[str, Any]) -> None:
    answers = st.session_state.get(_KEY_ANSWERS)
    if not isinstance(answers, list):
        answers = []
    try:
        q_idx = int(row.get("q_index", -1))
    except (TypeError, ValueError):
        q_idx = -1
    kept = [
        r
        for r in answers
        if not (
            isinstance(r, dict)
            and int(r.get("q_index", -2)) == q_idx
        )
    ]
    kept.append(row)
    st.session_state[_KEY_ANSWERS] = kept


def _run_topic_v2_stt(topic: str, q_idx: int, question_text: str, audio_bytes: bytes, mime_type: str) -> Dict[str, Any]:
    from services.stt_service import transcribe_answer_audio

    blob = bytes(audio_bytes) if audio_bytes else b""
    resolved_mime = (mime_type or "audio/webm").strip() or "audio/webm"
    qid = f"topic_v2_{topic}_q{int(q_idx)}"
    try:
        logger.info(
            "[TOPIC_V2_STT] topic=%s q=%s audio_len=%s mime=%s",
            topic,
            q_idx,
            len(blob),
            resolved_mime,
        )
    except Exception:
        pass
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
        mode="topic_practice_v2",
        question_id=qid,
    )


def _commit_topic_v2_recording(
    topic: str,
    q_idx: int,
    q_en: str,
    q_ko: str,
    audio_bytes: bytes,
    mime_type: str,
) -> None:
    blob = bytes(audio_bytes) if audio_bytes else b""
    audio_len = len(blob)
    resolved_mime = (mime_type or "audio/webm").strip() or "audio/webm"
    if audio_len <= 0:
        try:
            logger.info("[TOPIC_V2_RECORD_COMMIT] skip save audio_len=0 topic=%s q=%s", topic, q_idx)
        except Exception:
            pass
        return
    _save_topic_v2_audio_blob(topic, q_idx, blob, resolved_mime)
    stt_result = _run_topic_v2_stt(topic, q_idx, q_en, blob, resolved_mime)
    row = _build_topic_v2_row_from_mic(
        topic,
        q_idx,
        q_en,
        q_ko,
        blob,
        resolved_mime,
        stt_result,
    )
    _upsert_topic_v2_answer(row)
    st.session_state[_KEY_STEP] = "saved"


def _retry_topic_v2_stt_for_current(topic: str, q_idx: int) -> bool:
    last = _last_answer_row_for_q(q_idx)
    if not isinstance(last, dict):
        return False
    q_en = str(last.get("en") or "")
    q_ko = str(last.get("ko") or "")
    audio_bytes, mime_type = _get_topic_v2_audio_blob(topic, q_idx)
    if len(audio_bytes) <= 0:
        return False
    stt_result = _run_topic_v2_stt(topic, q_idx, q_en, audio_bytes, mime_type)
    row = _build_topic_v2_row_from_mic(
        topic,
        q_idx,
        q_en,
        q_ko,
        audio_bytes,
        mime_type or "audio/webm",
        stt_result,
    )
    _upsert_topic_v2_answer(row)
    try:
        logger.info("[TOPIC_V2_STT_RETRY] topic=%s q=%s", topic, q_idx)
    except Exception:
        pass
    return True


def _transcript_from_row(row: Dict[str, Any]) -> str:
    if not isinstance(row, dict):
        return ""
    for key in ("transcript", "student_answer", "stt_transcript", "raw_transcript"):
        t = str(row.get(key) or "").strip()
        if t:
            return t
    return ""


def _last_answer_row_for_q(q_idx: int) -> Optional[Dict[str, Any]]:
    answers = st.session_state.get(_KEY_ANSWERS)
    if not isinstance(answers, list):
        return None
    for row in reversed(answers):
        if not isinstance(row, dict):
            continue
        try:
            ri = int(row.get("q_index", -1))
        except (TypeError, ValueError):
            continue
        if ri == q_idx:
            return row
    return None


def _pop_last_answer_for_q(q_idx: int) -> None:
    answers = st.session_state.get(_KEY_ANSWERS)
    if not isinstance(answers, list) or not answers:
        return
    for i in range(len(answers) - 1, -1, -1):
        row = answers[i]
        if not isinstance(row, dict):
            continue
        try:
            ri = int(row.get("q_index", -1))
        except (TypeError, ValueError):
            continue
        if ri == q_idx:
            answers.pop(i)
            st.session_state[_KEY_ANSWERS] = answers
            t = str(st.session_state.get(_KEY_TOPIC) or "").strip()
            if t:
                _delete_topic_v2_audio_blob(t, q_idx)
            return


def _ensure_topic_v2_defaults() -> None:
    if _KEY_STEP not in st.session_state:
        st.session_state[_KEY_STEP] = "select_topic"
    if _KEY_ANSWERS not in st.session_state:
        st.session_state[_KEY_ANSWERS] = []
    if _KEY_FEEDBACK not in st.session_state:
        st.session_state[_KEY_FEEDBACK] = None


def _normalize_step(raw: Any) -> str:
    s = str(raw or "").strip()
    if s in _VALID_STEPS:
        return s
    try:
        logger.warning("[TOPIC_V2] unknown step=%r — reset to select_topic", raw)
    except Exception:
        pass
    st.session_state[_KEY_STEP] = "select_topic"
    return "select_topic"


def _goto_topic_select() -> None:
    st.session_state[_KEY_STEP] = "select_topic"
    st.session_state[_KEY_TOPIC] = ""
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_CURRENT_Q] = {}
    st.session_state[_KEY_ANSWERS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
    st.session_state.pop(_KEY_AUDIO_BLOBS, None)


def _render_select_topic() -> None:
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow="주제 선택")
    st.markdown("### 주제별 연습")
    st.caption("연습할 주제를 선택해 주세요.")

    for row in _TOPIC_PRACTICE_V2_CATALOG:
        title = str(row.get("title") or "")
        if not title:
            continue
        if st.button(title, use_container_width=True, key=f"topic_v2_pick_{title}"):
            st.session_state[_KEY_TOPIC] = title
            st.session_state[_KEY_Q_INDEX] = 0
            st.session_state[_KEY_CURRENT_Q] = _question_for(title, 0) or {}
            st.session_state[_KEY_STEP] = "question"
            st.rerun()


def _render_question() -> None:
    topic = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    if not topic or not _topic_pack(topic):
        _goto_topic_select()
        st.rerun()
        return

    expected = _question_for(topic, q_idx)
    cur = st.session_state.get(_KEY_CURRENT_Q)
    if not isinstance(cur, dict) or cur != expected:
        st.session_state[_KEY_CURRENT_Q] = expected or {}

    q = st.session_state.get(_KEY_CURRENT_Q)
    if not isinstance(q, dict) or not (q.get("en") or "").strip():
        _goto_topic_select()
        st.rerun()
        return

    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{topic} · 질문")
    st.markdown(f"### 주제별 연습 · {topic}")
    st.caption(f"Q{q_idx + 1}/3")
    st.markdown(f"**{q.get('en', '')}**")
    st.caption(q.get("ko") or "")

    st.markdown("### 말로 답변하기")
    st.caption(
        "답변 시작을 누르고 영어로 말해 보세요. 녹음이 끝나면 AI가 텍스트로 인식합니다."
    )

    from streamlit_mic_recorder import mic_recorder

    mic_key = _topic_v2_mic_key(topic, q_idx)
    mic_result = mic_recorder(
        start_prompt="🎤 답변 시작",
        stop_prompt="■ 녹음 완료",
        key=mic_key,
        use_container_width=True,
        just_once=True,
    )

    if mic_result is not None:
        audio_bytes, mime_type = _extract_topic_v2_audio_bytes(mic_result, mic_key=mic_key)
        try:
            logger.info(
                "[TOPIC_V2_MIC_RESULT] topic=%s q=%s audio_len=%s mime_type=%s",
                topic,
                q_idx,
                len(audio_bytes),
                (mime_type or "audio/webm") or "audio/webm",
            )
        except Exception:
            pass
        if len(audio_bytes) <= 0:
            st.warning("녹음 파일이 저장되지 않았어요. 다시 시도해 주세요.")
        else:
            with st.spinner("답변을 저장하고 음성을 인식하고 있어요…"):
                _commit_topic_v2_recording(
                    topic,
                    q_idx,
                    str(q.get("en") or ""),
                    str(q.get("ko") or ""),
                    audio_bytes,
                    mime_type or "audio/webm",
                )
            st.rerun()

    with st.expander("녹음이 어려우면 텍스트로 연습하기"):
        st.caption("접근·디버그용 보조 수단이에요. 가능하면 말로 연습하는 것이 좋아요.")
        st.text_area(
            "텍스트 연습",
            height=100,
            key=_KEY_DRAFT_TRANSCRIPT,
            label_visibility="collapsed",
            placeholder="영어로 답변을 적어 보세요.",
        )
        if st.button("텍스트 답변 저장", type="secondary", use_container_width=True, key="topic_v2_text_fallback_save"):
            draft = ""
            try:
                draft = str(st.session_state.get(_KEY_DRAFT_TRANSCRIPT) or "").strip()
            except Exception:
                draft = ""
            wc = int(count_english_words(draft))
            row = {
                "topic": topic,
                "q_index": q_idx,
                "en": str(q.get("en") or ""),
                "ko": str(q.get("ko") or ""),
                "source": "manual_text",
                "student_answer": draft,
                "transcript": draft,
                "raw_transcript": draft,
                "stt_status": "manual_text",
                "recording_status": "manual_text",
                "audio_saved": False,
                "audio_len": 0,
                "mime_type": "",
                "stt_error_category": "",
                "stt_error_message": "",
                "word_count": wc,
                "status": "saved" if wc >= _MIN_SAVED_WORDS else "insufficient_response",
                "placeholder": False,
            }
            _delete_topic_v2_audio_blob(topic, q_idx)
            _upsert_topic_v2_answer(row)
            st.session_state[_KEY_STEP] = "saved"
            st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
            st.rerun()


def _render_saved_normal(topic: str, q_idx: int) -> None:
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{topic} · 저장")
    st.markdown("### 답변이 저장되었어요.")

    last_row = _last_answer_row_for_q(q_idx)
    tr = _transcript_from_row(last_row) if last_row else ""
    ab, _ = _get_topic_v2_audio_blob(topic, q_idx)
    has_audio = len(ab) > 0
    is_manual = bool(
        last_row
        and (
            str(last_row.get("stt_status") or "") == "manual_text"
            or str(last_row.get("source") or "") == "manual_text"
        )
    )

    if has_audio:
        st.markdown("#### 내 녹음 다시 듣기")
        try:
            st.audio(ab, format="audio/webm")
        except Exception:
            st.audio(ab)
    elif is_manual:
        st.caption("텍스트 답변으로 저장되었습니다.")

    st.markdown("#### AI가 인식한 답변")
    if tr:
        st.markdown(f"> {tr}")
    else:
        st.caption("(인식된 텍스트가 아직 없어요.)")

    if has_audio and not (tr or "").strip():
        if st.button(
            "AI 음성 인식 다시 시도",
            type="secondary",
            use_container_width=True,
            key="topic_v2_retry_stt",
        ):
            _retry_topic_v2_stt_for_current(topic, q_idx)
            st.rerun()

    can_ai = bool(tr and count_english_words(tr) >= _MIN_SAVED_WORDS)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if can_ai:
            if st.button(
                "AI 짧은 피드백 받기",
                type="primary",
                use_container_width=True,
                key="topic_v2_request_ai_feedback",
            ):
                from services.topic_practice_v2_analysis import analyze_topic_practice_v2_answer

                row_in = last_row if isinstance(last_row, dict) else {}
                try:
                    result = analyze_topic_practice_v2_answer(dict(row_in))
                except Exception as exc:
                    try:
                        logger.exception("[TOPIC_V2_FEEDBACK] analyze_failed: %s", exc)
                    except Exception:
                        pass
                    result = {
                        "ok": False,
                        "summary": "",
                        "strength": "",
                        "correction_focus": "",
                        "better_expression": "",
                        "practice_mission": "",
                        "error_category": "exception",
                        "error_message": f"처리 중 오류가 났어요. 다시 시도해 주세요. ({type(exc).__name__})",
                    }
                st.session_state[_KEY_FEEDBACK] = result
                if result.get("ok"):
                    st.session_state[_KEY_STEP] = "feedback"
                else:
                    st.session_state[_KEY_STEP] = "pending"
                st.rerun()
    with c2:
        if st.button("다음 질문", use_container_width=True, key="topic_v2_next_q"):
            if q_idx < 2:
                nxt = q_idx + 1
                st.session_state[_KEY_Q_INDEX] = nxt
                st.session_state[_KEY_CURRENT_Q] = _question_for(topic, nxt) or {}
                st.session_state[_KEY_STEP] = "question"
            else:
                st.session_state[_KEY_Q_INDEX] = 3
            st.rerun()
    with c3:
        if st.button("같은 질문 다시 하기", use_container_width=True, key="topic_v2_retry_same"):
            _pop_last_answer_for_q(q_idx)
            st.session_state[_KEY_FEEDBACK] = None
            st.session_state[_KEY_STEP] = "question"
            st.rerun()
    with c4:
        if st.button("주제 선택으로 돌아가기", use_container_width=True, key="topic_v2_back_select"):
            _goto_topic_select()
            st.rerun()


def _render_saved_complete(topic: str) -> None:
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{topic} · 완료")
    st.markdown("### 이 주제 연습을 완료했어요.")
    if st.button("같은 주제 다시 연습", type="primary", use_container_width=True, key="topic_v2_restart_same_topic"):
        st.session_state[_KEY_Q_INDEX] = 0
        st.session_state[_KEY_CURRENT_Q] = _question_for(topic, 0) or {}
        st.session_state[_KEY_ANSWERS] = []
        st.session_state.pop(_KEY_AUDIO_BLOBS, None)
        st.session_state[_KEY_STEP] = "question"
        st.rerun()
    if st.button("다른 주제 선택", use_container_width=True, key="topic_v2_pick_other_topic"):
        _goto_topic_select()
        st.rerun()


def _render_saved() -> None:
    topic = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    if not topic:
        _goto_topic_select()
        st.rerun()
        return
    if q_idx >= 3:
        _render_saved_complete(topic)
    else:
        _render_saved_normal(topic, q_idx)


def _render_feedback_ui() -> None:
    topic = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    if not topic:
        _goto_topic_select()
        st.rerun()
        return
    fb = st.session_state.get(_KEY_FEEDBACK)
    if not isinstance(fb, dict) or not fb.get("ok"):
        st.session_state[_KEY_STEP] = "saved"
        st.rerun()
        return

    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{topic} · 피드백")
    st.markdown("### AI 짧은 피드백")
    st.markdown(f"**요약**  \n{fb.get('summary') or '—'}")
    st.markdown(f"**강점**  \n{fb.get('strength') or '—'}")
    st.markdown(f"**바로 고칠 점**  \n{fb.get('correction_focus') or '—'}")
    st.markdown(f"**더 자연스러운 표현**  \n{fb.get('better_expression') or '—'}")
    st.markdown(f"**다음 연습 미션**  \n{fb.get('practice_mission') or '—'}")

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("같은 질문 다시 하기", use_container_width=True, key="topic_v2_fb_retry_same"):
            _pop_last_answer_for_q(q_idx)
            st.session_state[_KEY_FEEDBACK] = None
            st.session_state[_KEY_STEP] = "question"
            st.rerun()
    with c2:
        if st.button("다음 질문", use_container_width=True, key="topic_v2_fb_next"):
            st.session_state[_KEY_FEEDBACK] = None
            if q_idx < 2:
                nxt = q_idx + 1
                st.session_state[_KEY_Q_INDEX] = nxt
                st.session_state[_KEY_CURRENT_Q] = _question_for(topic, nxt) or {}
                st.session_state[_KEY_STEP] = "question"
            else:
                st.session_state[_KEY_Q_INDEX] = 3
                st.session_state[_KEY_STEP] = "saved"
            st.rerun()
    with c3:
        if st.button("다른 주제 선택", use_container_width=True, key="topic_v2_fb_other_topic"):
            st.session_state[_KEY_FEEDBACK] = None
            _goto_topic_select()
            st.rerun()


def _render_pending_ui() -> None:
    topic = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    if not topic:
        _goto_topic_select()
        st.rerun()
        return
    fb = st.session_state.get(_KEY_FEEDBACK)
    msg = "피드백을 불러오지 못했어요."
    if isinstance(fb, dict) and fb.get("error_message"):
        msg = str(fb.get("error_message"))

    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{topic} · 재시도")
    st.markdown("### 피드백을 완료하지 못했어요")
    st.warning(msg)
    st.caption("답변은 그대로 저장되어 있어요. 잠시 후 다시 시도해 주세요.")

    if st.button("다시 시도", type="primary", use_container_width=True, key="topic_v2_pending_retry"):
        st.session_state[_KEY_FEEDBACK] = None
        st.session_state[_KEY_STEP] = "saved"
        st.rerun()


def render_topic_practice_v2() -> None:
    """Entry: learning portal → Topic Practice V2 (isolated session keys)."""
    ensure_mock(st.session_state)
    mock_session()
    _ensure_topic_v2_defaults()
    step = _normalize_step(st.session_state.get(_KEY_STEP))

    if step == "select_topic":
        _render_select_topic()
    elif step == "question":
        _render_question()
    elif step == "saved":
        _render_saved()
    elif step == "feedback":
        _render_feedback_ui()
    elif step == "pending":
        _render_pending_ui()
    else:
        try:
            logger.warning("[TOPIC_V2] fallthrough step=%r — select_topic UI", step)
        except Exception:
            pass
        st.session_state[_KEY_STEP] = "select_topic"
        _render_select_topic()
