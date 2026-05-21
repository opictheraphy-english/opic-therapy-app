"""Topic Practice V2 — isolated shell (OPIc question bank v2 + recording/STT/feedback)."""

from __future__ import annotations

import base64
import logging
import uuid
import zlib
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from components.navigation import navigate_to
from components.topbar import render_top_bar
from data.opic_question_bank_v2 import (
    ROLEPLAY_PRACTICE_SETS,
    TOPIC_PRACTICE_TOPICS,
    get_roleplay_practice_set,
    get_topic_practice_set,
    get_topic_title,
)
from services.stt_service import count_english_words
from utils.session_state import ensure_mock, mock_session

logger = logging.getLogger(__name__)

_KEY_AUDIO_BLOBS = "topic_v2_audio_blobs"
_MIN_SAVED_WORDS = 5

MOCK_MODE_TOPIC_V2 = "topic_practice_v2"
MOCK_SUBPAGE_TOPIC_V2_HISTORY = "TOPIC_V2_HISTORY"

_KEY_STEP = "topic_v2_step"
_KEY_PAGE = "topic_v2_page"
_KEY_TOPIC = "topic_v2_topic"
_KEY_Q_INDEX = "topic_v2_question_index"
_KEY_CURRENT_Q = "topic_v2_current_question"
_KEY_QUESTIONS = "topic_v2_questions"
_KEY_MODE = "topic_v2_mode"
_KEY_ROLEPLAY_SET_ID = "topic_v2_roleplay_set_id"
_KEY_ANSWERS = "topic_v2_answers"
_KEY_FEEDBACK = "topic_v2_feedback"
_KEY_DRAFT_TRANSCRIPT = "topic_v2_practice_transcript"
_KEY_HISTORY = "topic_v2_practice_history"
_KEY_SINGLE_RETRY = "topic_v2_single_question_retry"
_KEY_LAST_HISTORY_DEBUG = "topic_v2_last_history_debug"
# Temporary UI flag for history diagnosis (no terminal logs needed).
_KEY_DEBUG_PANEL = "topic_v2_debug_panel"

# Future: persist practice history to database when user accounts are added.

_HISTORY_LIMIT = 50

_TOPIC_V2_FEEDBACK_FAIL_USER_MESSAGE = (
    "AI 피드백이 잠시 지연되고 있어요.\n\n"
    "답변은 안전하게 저장되어 있습니다.\n\n"
    "잠시 후 다시 시도해 주세요."
)

_FB_FALLBACK_SUMMARY = "답변을 분석했어요."
_FB_FALLBACK_STRENGTH = "질문에 맞춰 답변하려는 시도가 좋았어요."
_FB_FALLBACK_CORRECTION_FOCUS = (
    "다음 답변에서는 구체적인 이유나 예시를 한 문장 더 추가해 보세요."
)
_FB_FALLBACK_PRACTICE_MISSION = (
    "같은 질문에 한 번 더 답하면서 이유를 한 문장 추가해 보세요."
)
_EMPTY_FIELD_PLACEHOLDER = "—"

_VALID_STEPS = frozenset(
    {"select_topic", "question", "saved", "feedback", "pending", "insufficient", "history"}
)

_OPIC_TYPE_LABELS: Dict[str, str] = {
    "Q1": "Q1 유형 · 묘사",
    "Q2": "Q2 유형 · 루틴",
    "Q3": "Q3 유형 · 경험",
    "Q4": "Q4 유형 · 문제/경험",
    "Q6": "Q6 유형 · 질문하기",
    "Q7": "Q7 유형 · 문제 해결",
    "Q8": "Q8 유형 · 관련 경험",
}

_TOPIC_V2_STATUS_LABELS: Dict[str, str] = {
    "saved": "답변 저장됨",
    "insufficient_response": "답변이 짧아요 (조금 더 말해 보세요)",
    "stt_pending": "음성 인식 처리 중",
    "stt_failed": "음성 인식에 실패했어요",
    "recording_failed": "녹음에 문제가 있었어요",
    "manual_text": "텍스트로 저장됨",
}

_HISTORY_STATUS_LABELS: Dict[str, str] = {
    "saved": "저장 완료",
    "insufficient_response": "응답 짧음",
    "stt_failed": "음성 저장됨 · 인식 실패",
    "stt_pending": "음성 저장됨 · AI 인식 대기",
    "recording_failed": "녹음 실패",
    "manual_text": "텍스트 답변",
}


def _topic_v2_answers_count() -> int:
    raw = st.session_state.get(_KEY_ANSWERS)
    return len(raw) if isinstance(raw, list) else 0


def _history_status_label(status: str, *, stt_status: str = "") -> str:
    s = str(status or "").strip()
    if s == "manual_text" or str(stt_status or "").strip() == "manual_text":
        return _HISTORY_STATUS_LABELS["manual_text"]
    if s in _HISTORY_STATUS_LABELS:
        return _HISTORY_STATUS_LABELS[s]
    if s:
        return s
    return "상태 확인 중"


def _topic_v2_answer_status_label(row: Optional[Dict[str, Any]]) -> str:
    if not isinstance(row, dict):
        return "답변 없음"
    if str(row.get("source") or "") == "manual_text" or str(
        row.get("stt_status") or ""
    ) == "manual_text":
        return _TOPIC_V2_STATUS_LABELS["manual_text"]
    status = str(row.get("status") or "").strip()
    if status in _TOPIC_V2_STATUS_LABELS:
        return _TOPIC_V2_STATUS_LABELS[status]
    if status:
        return status
    return "상태 확인 중"


# Legacy local topic list is no longer active. Topic Practice V2 uses data/opic_question_bank_v2.py.
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


def _tpv2_answer_ids_csv() -> str:
    ids: List[str] = []
    for row in _answers_store():
        aid = str(row.get("answer_id") or "").strip()
        if aid:
            ids.append(aid)
    return ",".join(ids) if ids else "-"


def _tpv2_history_answer_ids_csv() -> str:
    ids: List[str] = []
    for ent in _history_store():
        aid = str(ent.get("answer_id") or "").strip()
        if aid:
            ids.append(aid)
    return ",".join(ids) if ids else "-"


def _tpv2_latest_answer_id() -> str:
    answers = _answers_store()
    if not answers:
        return "-"
    return str(answers[-1].get("answer_id") or "").strip() or "-"


def _tpv2_latest_history_answer_id() -> str:
    items = _history_store()
    if not items:
        return "-"
    return str(items[0].get("answer_id") or "").strip() or "-"


def _log_tpv2_state_clear(phase: str, function: str) -> None:
    try:
        logger.info(
            "[TPV2_STATE_CLEAR_%s] function=%s answers_count=%s history_count=%s "
            "audio_blobs_count=%s step=%s page=%s",
            phase,
            function,
            _get_topic_v2_answers_count(),
            _history_count(),
            _audio_blobs_count(),
            str(st.session_state.get(_KEY_STEP) or "").strip() or "-",
            str(st.session_state.get(_KEY_PAGE) or "").strip() or "-",
        )
    except Exception:
        pass


def _tpv2_debug_panel_visible() -> bool:
    return bool(st.session_state.get("show_dev_debug")) or bool(
        st.session_state.get(_KEY_DEBUG_PANEL, True)
    )


def _update_topic_v2_last_history_debug(
    *,
    action: str,
    reason: str = "",
    answer_row: Optional[Dict[str, Any]] = None,
) -> None:
    row = answer_row if isinstance(answer_row, dict) else {}
    student_answer, transcript = _answer_text_fields_from_row(row)
    st.session_state[_KEY_LAST_HISTORY_DEBUG] = {
        "action": str(action or "").strip(),
        "reason": str(reason or "").strip(),
        "answers_count": _get_topic_v2_answers_count(),
        "history_count": _get_topic_v2_history_count(),
        "answer_id": str(row.get("answer_id") or "").strip(),
        "student_answer_len": len(student_answer),
        "transcript_len": len(transcript),
        "audio_saved": bool(row.get("audio_saved")),
    }


def _render_tpv2_debug_panel(location: str) -> None:
    """Visible history/answer diagnostics (saved + history screens)."""
    if not _tpv2_debug_panel_visible():
        return
    dbg = st.session_state.get(_KEY_LAST_HISTORY_DEBUG)
    if not isinstance(dbg, dict):
        dbg = {}
    action = str(dbg.get("action") or "").strip() or "-"
    reason = str(dbg.get("reason") or "").strip() or "-"
    skip_reason = reason if action == "skip" else "-"
    with st.container(border=True):
        st.markdown("**TPV2 Debug**")
        st.caption(f"screen: {location}")
        st.markdown(f"- answers_count: `{_get_topic_v2_answers_count()}`")
        st.markdown(f"- history_count: `{_get_topic_v2_history_count()}`")
        st.markdown(f"- latest_answer_id: `{_tpv2_latest_answer_id()}`")
        st.markdown(f"- latest_history_answer_id: `{_tpv2_latest_history_answer_id()}`")
        st.markdown(f"- student_answer_len: `{dbg.get('student_answer_len', '-')}`")
        st.markdown(f"- transcript_len: `{dbg.get('transcript_len', '-')}`")
        st.markdown(f"- audio_saved: `{dbg.get('audio_saved', '-')}`")
        st.markdown(f"- last_history_save_action: `{action}`")
        st.markdown(f"- last_history_skip_reason: `{skip_reason}`")
        st.markdown(
            f"- answer_id (last save): `{str(dbg.get('answer_id') or '').strip() or '-'}`"
        )


def clear_topic_v2_session() -> None:
    """Remove Topic Practice V2 practice keys (portal / reset).

    Preserves ``topic_v2_practice_history``, ``topic_v2_last_history_debug``,
    and ``topic_v2_debug_panel`` so recent history survives portal resets.
    """
    _log_tpv2_state_clear("ENTER", "clear_topic_v2_session")
    for k in (
        _KEY_PAGE,
        _KEY_STEP,
        _KEY_TOPIC,
        _KEY_Q_INDEX,
        _KEY_CURRENT_Q,
        _KEY_QUESTIONS,
        _KEY_MODE,
        _KEY_ROLEPLAY_SET_ID,
        _KEY_ANSWERS,
        _KEY_FEEDBACK,
        _KEY_DRAFT_TRANSCRIPT,
        _KEY_AUDIO_BLOBS,
    ):
        st.session_state.pop(k, None)
    _log_tpv2_state_clear("EXIT", "clear_topic_v2_session")


def _topic_id_valid(topic_id: str) -> bool:
    tid = str(topic_id or "").strip()
    return bool(tid) and bool(get_topic_title(tid))


def _topic_display_title(topic_id: str) -> str:
    tid = str(topic_id or "").strip()
    title = get_topic_title(tid)
    return title if title else tid


def _opic_type_label(opic_type: str) -> str:
    key = str(opic_type or "").strip().upper()
    return _OPIC_TYPE_LABELS.get(key, f"{key} 유형")


def _topic_v2_mode() -> str:
    raw = str(st.session_state.get(_KEY_MODE) or "topic").strip()
    return raw if raw in ("topic", "roleplay") else "topic"


def _is_roleplay_mode() -> bool:
    return _topic_v2_mode() == "roleplay"


def _is_single_question_retry() -> bool:
    return bool(st.session_state.get(_KEY_SINGLE_RETRY))


def _migrate_topic_v2_history_keys() -> None:
    """Ensure history uses topic_v2_practice_history only (one-time safe init)."""
    if _KEY_HISTORY not in st.session_state:
        st.session_state[_KEY_HISTORY] = []
    raw = st.session_state.get(_KEY_HISTORY)
    if not isinstance(raw, list):
        st.session_state[_KEY_HISTORY] = []
        raw = []
    for legacy in (
        "topic_practice_history",
        "topic_v2_history",
        "practice_history",
        "topic_history",
    ):
        if legacy not in st.session_state:
            continue
        leg = st.session_state.get(legacy)
        if isinstance(leg, list) and leg and not raw:
            st.session_state[_KEY_HISTORY] = [
                dict(x) for x in leg if isinstance(x, dict)
            ]
            raw = st.session_state[_KEY_HISTORY]
        try:
            st.session_state.pop(legacy, None)
        except Exception:
            pass


def _history_store() -> List[Dict[str, Any]]:
    _migrate_topic_v2_history_keys()
    raw = st.session_state.get(_KEY_HISTORY)
    if not isinstance(raw, list):
        return []
    return [dict(x) for x in raw if isinstance(x, dict)]


def _history_count() -> int:
    return len(_history_store())


def _get_topic_v2_answers_count() -> int:
    try:
        return _answers_count()
    except Exception:
        return 0


def _get_topic_v2_history_count() -> int:
    """Real saved history length only — never inferred from topic_v2_answers."""
    try:
        return _history_count()
    except Exception:
        return 0


def _log_after_save_counts(row: Optional[Dict[str, Any]] = None) -> None:
    last = row if isinstance(row, dict) else None
    if last is None:
        answers = _answers_store()
        if answers:
            last = answers[-1]
    aid = str((last or {}).get("answer_id") or "").strip()
    status = str((last or {}).get("status") or "").strip()
    student_answer, transcript = _answer_text_fields_from_row(last or {})
    try:
        logger.info(
            "[TOPIC_V2_AFTER_SAVE_COUNTS] answers_count=%s history_count=%s "
            "latest_answer_id=%s latest_status=%s student_answer_len=%s "
            "transcript_len=%s audio_saved=%s",
            _get_topic_v2_answers_count(),
            _history_count(),
            aid or "-",
            status or "-",
            len(student_answer),
            len(transcript),
            bool((last or {}).get("audio_saved")),
        )
    except Exception:
        pass


def _answers_store() -> List[Dict[str, Any]]:
    raw = st.session_state.get(_KEY_ANSWERS)
    if not isinstance(raw, list):
        return []
    return [dict(x) for x in raw if isinstance(x, dict)]


def _answers_count() -> int:
    return len(_answers_store())


def _audio_blobs_count() -> int:
    raw = st.session_state.get(_KEY_AUDIO_BLOBS)
    if not isinstance(raw, dict):
        return 0
    return len(raw)


def _mode_for_answer_row(answer_row: Dict[str, Any]) -> str:
    raw = str(answer_row.get("mode") or "").strip()
    if raw in ("topic", "roleplay"):
        return raw
    opic = str(answer_row.get("opic_type") or "").strip().upper()
    if opic in ("Q6", "Q7", "Q8"):
        return "roleplay"
    return "topic"


def _topic_title_for_answer_row(answer_row: Dict[str, Any]) -> str:
    mode = _mode_for_answer_row(answer_row)
    topic_id = str(answer_row.get("topic") or "").strip()
    if mode == "roleplay" and topic_id:
        for ent in ROLEPLAY_PRACTICE_SETS:
            if not isinstance(ent, dict):
                continue
            if str(ent.get("topic_id") or "").strip() == topic_id:
                title_ko = str(ent.get("title_ko") or "").strip()
                if title_ko:
                    return title_ko
    if topic_id:
        return _topic_display_title(topic_id)
    return ""


def _roleplay_set_id_for_answer_row(answer_row: Dict[str, Any]) -> str:
    sid = str(answer_row.get("roleplay_set_id") or "").strip()
    if sid:
        return sid
    topic_id = str(answer_row.get("topic") or "").strip()
    if not topic_id:
        return ""
    for ent in ROLEPLAY_PRACTICE_SETS:
        if not isinstance(ent, dict):
            continue
        if str(ent.get("topic_id") or "").strip() == topic_id:
            return str(ent.get("set_id") or "").strip()
    return ""


def _feedback_for_answer_id(answer_id: str) -> Optional[Dict[str, Any]]:
    """Attach session feedback only when it belongs to the latest saved answer."""
    aid = str(answer_id or "").strip()
    if not aid:
        return None
    answers = _answers_store()
    if not answers:
        return None
    last = answers[-1]
    if not isinstance(last, dict):
        return None
    if str(last.get("answer_id") or "").strip() != aid:
        return None
    fb = st.session_state.get(_KEY_FEEDBACK)
    if isinstance(fb, dict) and fb.get("ok"):
        return dict(fb)
    return None


def _build_history_item_from_answer_row(
    answer_row: Dict[str, Any],
    feedback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build history entry from a saved answer row (no live question bank required)."""
    q_idx = int(answer_row.get("q_index", 0))
    topic_id = str(answer_row.get("topic") or "").strip()
    student_answer, transcript = _answer_text_fields_from_row(answer_row)
    stt_st = str(answer_row.get("stt_status") or "").strip()
    qid = str(answer_row.get("question_id") or "").strip()
    return {
        "history_id": str(uuid.uuid4()),
        "answer_id": str(answer_row.get("answer_id") or "").strip(),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "mode": _mode_for_answer_row(answer_row),
        "topic_id": topic_id,
        "topic_title": _topic_title_for_answer_row(answer_row),
        "roleplay_set_id": _roleplay_set_id_for_answer_row(answer_row),
        "question_index": q_idx,
        "opic_type": str(answer_row.get("opic_type") or "").strip(),
        "question_id": qid,
        "question_text": str(answer_row.get("en") or "").strip(),
        "ko_helper": str(answer_row.get("ko") or "").strip(),
        "student_answer": student_answer,
        "transcript": transcript,
        "word_count": int(answer_row.get("word_count") or 0),
        "audio_saved": bool(answer_row.get("audio_saved")),
        "audio_len": int(answer_row.get("audio_len") or 0),
        "mime_type": str(answer_row.get("mime_type") or "").strip(),
        "stt_status": stt_st,
        "status": str(answer_row.get("status") or "").strip(),
        "feedback": dict(feedback) if isinstance(feedback, dict) else None,
    }


def _recover_topic_v2_history_from_answers() -> int:
    """Rebuild missing history items from topic_v2_answers when history is empty or incomplete."""
    before = _history_count()
    answers = _answers_store()
    answers_n = len(answers)
    try:
        logger.info(
            "[TOPIC_V2_HISTORY_RECOVERY_START] history_count=%s answers_count=%s",
            before,
            answers_n,
        )
    except Exception:
        pass
    if not answers:
        try:
            logger.info(
                "[TOPIC_V2_HISTORY_RECOVERY_DONE] before=%s after=%s added=0",
                before,
                before,
            )
        except Exception:
            pass
        return 0

    items = _history_store()
    existing_by_aid: Dict[str, Dict[str, Any]] = {}
    for ent in items:
        aid = str(ent.get("answer_id") or "").strip()
        if aid:
            existing_by_aid[aid] = ent

    added = 0
    for row in answers:
        if not isinstance(row, dict):
            continue
        aid = str(row.get("answer_id") or "").strip()
        if not aid:
            continue
        if aid in existing_by_aid:
            continue
        student_answer, transcript = _answer_text_fields_from_row(row)
        if not student_answer and not transcript and not bool(row.get("audio_saved")):
            continue
        topic_id = str(row.get("topic") or "").strip()
        opic_type = str(row.get("opic_type") or "").strip()
        fb = _feedback_for_answer_id(aid)
        item = _build_history_item_from_answer_row(row, fb)
        items.insert(0, item)
        existing_by_aid[aid] = item
        added += 1
        try:
            logger.info(
                "[TOPIC_V2_HISTORY_RECOVERY_ADD] answer_id=%s topic_id=%s opic_type=%s "
                "student_answer_len=%s transcript_len=%s audio_saved=%s",
                aid,
                topic_id or "-",
                opic_type or "-",
                len(student_answer),
                len(transcript),
                bool(row.get("audio_saved")),
            )
        except Exception:
            pass

    if added:
        _persist_history_items(items)
    after = _history_count()
    try:
        logger.info(
            "[TOPIC_V2_HISTORY_RECOVERY_DONE] before=%s after=%s added=%s",
            before,
            after,
            added,
        )
    except Exception:
        pass
    return added


def _history_topic_title_for_save() -> str:
    if _is_roleplay_mode():
        t = _roleplay_set_title()
        if t:
            return t
    topic_id = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    return _topic_display_title(topic_id) if topic_id else ""


def _bank_question_at_index(q_index: int) -> Dict[str, Any]:
    qs = _session_question_set()
    if 0 <= q_index < len(qs) and isinstance(qs[q_index], dict):
        return dict(qs[q_index])
    return {}


def _build_history_item_for_save(
    answer_row: Dict[str, Any],
    feedback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Prefer live question bank when available; else use fields stored on answer_row."""
    q_idx = int(answer_row.get("q_index", 0))
    qs = _session_question_set()
    if qs and 0 <= q_idx < len(qs):
        return _build_history_item(answer_row, feedback)
    return _build_history_item_from_answer_row(answer_row, feedback)


def _build_history_item(
    answer_row: Dict[str, Any],
    feedback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    q_idx = int(answer_row.get("q_index", 0))
    bank_q = _bank_question_at_index(q_idx)
    topic_id = str(answer_row.get("topic") or st.session_state.get(_KEY_TOPIC) or "").strip()
    student_answer, transcript = _answer_text_fields_from_row(answer_row)
    stt_st = str(answer_row.get("stt_status") or "").strip()
    qid = str(
        bank_q.get("id") or bank_q.get("question_id") or answer_row.get("question_id") or ""
    ).strip()
    return {
        "history_id": str(uuid.uuid4()),
        "answer_id": str(answer_row.get("answer_id") or "").strip(),
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "mode": _topic_v2_mode(),
        "topic_id": topic_id,
        "topic_title": _history_topic_title_for_save(),
        "roleplay_set_id": str(st.session_state.get(_KEY_ROLEPLAY_SET_ID) or "").strip(),
        "question_index": q_idx,
        "opic_type": str(
            answer_row.get("opic_type") or bank_q.get("opic_type") or ""
        ).strip(),
        "question_id": qid,
        "question_text": str(
            answer_row.get("en") or bank_q.get("question_text") or ""
        ).strip(),
        "ko_helper": str(
            answer_row.get("ko") or bank_q.get("ko_helper") or ""
        ).strip(),
        "student_answer": student_answer,
        "transcript": transcript,
        "word_count": int(answer_row.get("word_count") or 0),
        "audio_saved": bool(answer_row.get("audio_saved")),
        "audio_len": int(answer_row.get("audio_len") or 0),
        "mime_type": str(answer_row.get("mime_type") or "").strip(),
        "stt_status": stt_st,
        "status": str(answer_row.get("status") or "").strip(),
        "feedback": dict(feedback) if isinstance(feedback, dict) else None,
    }


def _log_topic_v2_history_save(
    *,
    action: str,
    answer_id: str,
    student_answer_len: int,
    transcript_len: int,
    audio_saved: bool,
    status: str,
) -> None:
    try:
        logger.info(
            "[TOPIC_V2_HISTORY_SAVE] action=%s answer_id=%s history_count=%s "
            "student_answer_len=%s transcript_len=%s audio_saved=%s status=%s",
            action,
            answer_id or "-",
            _history_count(),
            student_answer_len,
            transcript_len,
            audio_saved,
            status or "-",
        )
    except Exception:
        pass


def _save_topic_v2_history(
    answer_row: Dict[str, Any],
    feedback: Optional[Dict[str, Any]] = None,
) -> bool:
    """Persist one history entry keyed by answer_id. Returns True if append/update succeeded."""
    try:
        _migrate_topic_v2_history_keys()
        has_row = isinstance(answer_row, dict)
        answer_id = str(answer_row.get("answer_id") or "").strip() if has_row else ""
        status = str(answer_row.get("status") or "").strip() if has_row else ""
        student_answer, transcript = (
            _answer_text_fields_from_row(answer_row) if has_row else ("", "")
        )
        audio_saved = bool(answer_row.get("audio_saved")) if has_row else False
        sa_len = len(student_answer)
        tr_len = len(transcript)
        try:
            logger.info(
                "[TPV2_HISTORY_SAVE_ENTER] answer_id=%s has_answer_row=%s "
                "student_answer_len=%s transcript_len=%s audio_saved=%s status=%s",
                answer_id or "-",
                has_row,
                sa_len,
                tr_len,
                audio_saved,
                status or "-",
            )
        except Exception:
            pass

        if not has_row:
            _log_topic_v2_history_save(
                action="skip",
                answer_id="-",
                student_answer_len=0,
                transcript_len=0,
                audio_saved=False,
                status="invalid_row",
            )
            try:
                logger.info(
                    "[TPV2_HISTORY_SAVE_SKIP] reason=invalid_row answer_id=- "
                    "student_answer_len=0 transcript_len=0 audio_saved=False status=invalid_row",
                )
            except Exception:
                pass
            _update_topic_v2_last_history_debug(
                action="skip", reason="invalid_row", answer_row=answer_row
            )
            return False

        if not answer_id:
            _log_topic_v2_history_save(
                action="skip",
                answer_id="-",
                student_answer_len=sa_len,
                transcript_len=tr_len,
                audio_saved=audio_saved,
                status="no_answer_id",
            )
            try:
                logger.info(
                    "[TPV2_HISTORY_SAVE_SKIP] reason=no_answer_id answer_id=- "
                    "student_answer_len=%s transcript_len=%s audio_saved=%s status=%s",
                    sa_len,
                    tr_len,
                    audio_saved,
                    status or "-",
                )
            except Exception:
                pass
            _update_topic_v2_last_history_debug(
                action="skip", reason="no_answer_id", answer_row=answer_row
            )
            return False

        if not student_answer and not transcript and not audio_saved:
            _log_topic_v2_history_save(
                action="skip",
                answer_id=answer_id,
                student_answer_len=sa_len,
                transcript_len=tr_len,
                audio_saved=audio_saved,
                status=status or "empty",
            )
            try:
                logger.info(
                    "[TPV2_HISTORY_SAVE_SKIP] reason=empty_content answer_id=%s "
                    "student_answer_len=%s transcript_len=%s audio_saved=%s status=%s",
                    answer_id,
                    sa_len,
                    tr_len,
                    audio_saved,
                    status or "-",
                )
            except Exception:
                pass
            _update_topic_v2_last_history_debug(
                action="skip", reason="empty_content", answer_row=answer_row
            )
            return False

        items = _history_store()
        for i, ent in enumerate(items):
            if str(ent.get("answer_id") or "").strip() != answer_id:
                continue
            if feedback is not None:
                ent["feedback"] = dict(feedback)
                items[i] = ent
                _persist_history_items(items)
                _log_topic_v2_history_save(
                    action="update",
                    answer_id=answer_id,
                    student_answer_len=sa_len,
                    transcript_len=tr_len,
                    audio_saved=audio_saved,
                    status=status,
                )
                try:
                    logger.info(
                        "[TPV2_HISTORY_SAVE_UPDATE] answer_id=%s history_count_after=%s",
                        answer_id,
                        _history_count(),
                    )
                except Exception:
                    pass
                _update_topic_v2_last_history_debug(
                    action="update",
                    reason="feedback_attach",
                    answer_row=answer_row,
                )
                return True

            prev = items[i]
            updated = _build_history_item_for_save(answer_row, prev.get("feedback"))
            updated["history_id"] = str(
                prev.get("history_id") or updated.get("history_id") or ""
            )
            updated["created_at"] = str(
                prev.get("created_at") or updated.get("created_at") or ""
            )
            if not updated.get("student_answer") and not updated.get("transcript"):
                prev_sa = str(prev.get("student_answer") or "").strip()
                prev_tr = str(prev.get("transcript") or "").strip()
                if prev_sa or prev_tr:
                    updated["student_answer"] = prev_sa
                    updated["transcript"] = prev_tr or prev_sa
            items[i] = updated
            _persist_history_items(items)
            _log_topic_v2_history_save(
                action="update",
                answer_id=answer_id,
                student_answer_len=sa_len,
                transcript_len=tr_len,
                audio_saved=audio_saved,
                status=status,
            )
            try:
                logger.info(
                    "[TPV2_HISTORY_SAVE_UPDATE] answer_id=%s history_count_after=%s",
                    answer_id,
                    _history_count(),
                )
            except Exception:
                pass
            _update_topic_v2_last_history_debug(
                action="update", reason="", answer_row=answer_row
            )
            return True

        item = _build_history_item_for_save(answer_row, feedback)
        items.insert(0, item)
        _persist_history_items(items)
        _log_topic_v2_history_save(
            action="append",
            answer_id=answer_id,
            student_answer_len=sa_len,
            transcript_len=tr_len,
            audio_saved=audio_saved,
            status=status,
        )
        try:
            logger.info(
                "[TPV2_HISTORY_SAVE_APPEND] answer_id=%s history_count_after=%s",
                answer_id,
                _history_count(),
            )
        except Exception:
            pass
        _update_topic_v2_last_history_debug(
            action="append", reason="", answer_row=answer_row
        )
        return True
    except Exception as exc:
        try:
            logger.exception(
                "[TPV2_HISTORY_SAVE_ERROR] error_type=%s error_preview=%s",
                type(exc).__name__,
                str(exc)[:120],
            )
        except Exception:
            pass
        _update_topic_v2_last_history_debug(
            action="error",
            reason=type(exc).__name__,
            answer_row=answer_row if isinstance(answer_row, dict) else None,
        )
        return False


def _history_had_answer_id(answer_id: str) -> bool:
    aid = str(answer_id or "").strip()
    if not aid:
        return False
    for ent in _history_store():
        if str(ent.get("answer_id") or "").strip() == aid:
            return True
    return False


def _verify_topic_v2_history_after_answer_save(
    answer_row: Dict[str, Any],
    *,
    history_count_before: int,
    had_in_history_before: bool,
) -> None:
    """Log when a new answer was saved but history count did not grow."""
    if not isinstance(answer_row, dict):
        return
    answer_id = str(answer_row.get("answer_id") or "").strip()
    if had_in_history_before:
        return
    count_after = _history_count()
    if count_after > history_count_before:
        return
    student_answer, transcript = _answer_text_fields_from_row(answer_row)
    try:
        logger.error(
            "[TOPIC_V2_HISTORY_SAVE_MISSED] answer_id=%s student_answer_len=%s "
            "transcript_len=%s audio_saved=%s history_before=%s history_after=%s",
            answer_id or "-",
            len(student_answer),
            len(transcript),
            bool(answer_row.get("audio_saved")),
            history_count_before,
            count_after,
        )
    except Exception:
        pass


def _persist_topic_v2_answer_and_history(row: Dict[str, Any]) -> None:
    """Upsert active answer row and mirror into topic_v2_practice_history."""
    history_before = _history_count()
    aid = str(row.get("answer_id") or "").strip() if isinstance(row, dict) else ""
    had_before = _history_had_answer_id(aid)
    try:
        logger.info(
            "[TPV2_TRACE_HISTORY_SAVE_BEFORE] history_count=%s answer_id=%s",
            history_before,
            aid or "-",
        )
    except Exception:
        pass
    _upsert_topic_v2_answer(row)
    _save_topic_v2_history(row, feedback=None)
    try:
        logger.info(
            "[TPV2_TRACE_HISTORY_SAVE_AFTER] history_count=%s answer_ids=%s",
            _history_count(),
            _tpv2_history_answer_ids_csv(),
        )
    except Exception:
        pass
    _verify_topic_v2_history_after_answer_save(
        row,
        history_count_before=history_before,
        had_in_history_before=had_before,
    )
    _log_after_save_counts(row)


def _update_topic_v2_history_feedback(
    answer_id: str,
    feedback: Dict[str, Any],
    *,
    answer_row_fallback: Optional[Dict[str, Any]] = None,
) -> None:
    aid = str(answer_id or "").strip()
    has_fb = bool(isinstance(feedback, dict) and feedback.get("ok"))
    items = _history_store()
    found = False
    if aid:
        for i, ent in enumerate(items):
            if str(ent.get("answer_id") or "").strip() == aid:
                ent["feedback"] = dict(feedback)
                items[i] = ent
                found = True
                break
    if found:
        _persist_history_items(items)
    elif isinstance(answer_row_fallback, dict):
        _save_topic_v2_history(answer_row_fallback, feedback=feedback)
        found = True
    try:
        logger.info(
            "[TOPIC_V2_HISTORY_FEEDBACK_ATTACHED] answer_id=%s found=%s has_feedback=%s history_count=%s",
            aid or "-",
            found,
            has_fb,
            _history_count(),
        )
    except Exception:
        pass


def _history_item_to_question_dict(item: Dict[str, Any]) -> Dict[str, Any]:
    qid = str(item.get("question_id") or item.get("id") or "").strip()
    out: Dict[str, Any] = {
        "id": qid,
        "question_id": qid,
        "opic_type": str(item.get("opic_type") or "").strip(),
        "topic_id": str(item.get("topic_id") or "").strip(),
        "question_text": str(item.get("question_text") or "").strip(),
        "ko_helper": str(item.get("ko_helper") or "").strip(),
        "en": str(item.get("question_text") or "").strip(),
        "ko": str(item.get("ko_helper") or "").strip(),
    }
    qk = str(item.get("question_kind") or "").strip()
    if qk:
        out["question_kind"] = qk
    return out


def _history_question_lines(item: Dict[str, Any]) -> Tuple[str, str]:
    """Question text for history card (stored fields, then question bank fallback)."""
    q_en = str(item.get("question_text") or item.get("en") or "").strip()
    ko = str(item.get("ko_helper") or item.get("ko") or "").strip()
    if q_en:
        return q_en, ko
    mode = str(item.get("mode") or "topic").strip()
    topic_id = str(item.get("topic_id") or "").strip()
    try:
        q_idx = int(item.get("question_index", 0))
    except (TypeError, ValueError):
        q_idx = 0
    bank_rows: List[Dict[str, Any]] = []
    if mode == "roleplay":
        sid = str(item.get("roleplay_set_id") or "").strip()
        if sid:
            bank_rows = get_roleplay_practice_set(sid)
    elif topic_id:
        bank_rows = get_topic_practice_set(topic_id)
    if 0 <= q_idx < len(bank_rows) and isinstance(bank_rows[q_idx], dict):
        row = bank_rows[q_idx]
        q_en = str(row.get("question_text") or row.get("en") or "").strip()
        if not ko:
            ko = str(row.get("ko_helper") or row.get("ko") or "").strip()
    return q_en, ko


def _history_answer_lines(item: Dict[str, Any]) -> Tuple[str, str]:
    """Primary answer text and optional STT/transcript line for display."""
    student = str(item.get("student_answer") or "").strip()
    transcript = str(item.get("transcript") or "").strip()
    if student:
        extra = transcript if transcript and transcript != student else ""
        return student, extra
    return transcript, ""


def _history_audio_for_item(item: Dict[str, Any]) -> Tuple[bytes, str]:
    """Resolve session audio for a history card (answer_id, then topic+q index)."""
    aid = str(item.get("answer_id") or "").strip()
    if aid:
        ab, mime = _get_topic_v2_audio_by_answer_id(aid)
        if len(ab) > 0:
            return ab, mime
    topic = str(item.get("topic_id") or "").strip()
    try:
        q_idx = int(item.get("question_index", 0))
    except (TypeError, ValueError):
        q_idx = 0
    return _get_topic_v2_audio_blob(topic, q_idx)


def _history_card_expander_label(item: Dict[str, Any]) -> str:
    title = str(item.get("topic_title") or item.get("topic_id") or "주제").strip()
    opic = str(item.get("opic_type") or "").strip()
    status_lbl = _history_status_label(
        str(item.get("status") or ""),
        stt_status=str(item.get("stt_status") or ""),
    )
    parts = [p for p in (title, opic, status_lbl) if p]
    attempt = item.get("attempt_number")
    if attempt is not None and str(attempt).strip() != "":
        try:
            parts.append(f"{int(attempt)}차 시도")
        except (TypeError, ValueError):
            parts.append(f"{attempt}차 시도")
    return " · ".join(parts)


def _render_history_feedback_block(fb: Any) -> None:
    if not isinstance(fb, dict) or not fb.get("ok"):
        st.caption("아직 AI 피드백이 없습니다.")
        return

    summary = _topic_v2_fb_text(fb, "summary", _FB_FALLBACK_SUMMARY)
    strength = _topic_v2_fb_text(fb, "strength", _FB_FALLBACK_STRENGTH)
    correction = _topic_v2_fb_text(fb, "correction_focus", _FB_FALLBACK_CORRECTION_FOCUS)
    better = str(fb.get("better_expression") or "").strip()
    better_disp = better if better else _EMPTY_FIELD_PLACEHOLDER
    upgrade = str(fb.get("upgrade_sample") or "").strip()
    upgrade_disp = upgrade if upgrade else _EMPTY_FIELD_PLACEHOLDER
    mission = _topic_v2_fb_text(fb, "practice_mission", _FB_FALLBACK_PRACTICE_MISSION)
    kwords = _topic_v2_fb_keywords(fb)

    st.markdown("##### 한 줄 총평")
    st.write(summary)
    st.markdown("##### 잘한 점")
    st.write(strength)
    st.markdown("##### 바로 고칠 점")
    st.write(correction)
    st.markdown("##### 더 자연스러운 표현")
    st.write(better_disp)
    st.markdown("##### 내 답변 업그레이드 예시")
    st.write(upgrade_disp)
    st.markdown("##### 다시 말하기 키워드")
    if kwords:
        st.markdown(" · ".join(f"`{w}`" for w in kwords))
    else:
        st.write(_EMPTY_FIELD_PLACEHOLDER)
    st.markdown("##### 다음 연습 미션")
    st.write(mission)


def _render_history_card_content(item: Dict[str, Any], idx: int) -> None:
    st.markdown("#### 질문")
    q_en, ko = _history_question_lines(item)
    if q_en:
        st.markdown(f"**{q_en}**")
    else:
        st.caption("질문 텍스트를 불러오지 못했습니다.")
    if ko:
        st.caption(ko)
    opic = str(item.get("opic_type") or "").strip()
    if opic:
        st.caption(_opic_type_label(opic))

    st.markdown("#### 내가 말한 답변")
    answer_text, transcript_extra = _history_answer_lines(item)
    if answer_text:
        st.markdown(f"> {answer_text}")
        if transcript_extra:
            st.caption(f"AI가 인식한 답변: {transcript_extra}")
    else:
        st.caption("저장된 답변 텍스트가 없습니다.")

    st.markdown("#### 내 녹음 다시 듣기")
    ab, mime = _history_audio_for_item(item)
    if len(ab) > 0:
        try:
            st.audio(ab, format=mime or "audio/webm")
        except Exception:
            st.audio(ab)
    elif bool(item.get("audio_saved")):
        st.caption(
            "이 답변은 녹음으로 저장되었지만, 현재 세션에서 재생 파일을 찾을 수 없습니다."
        )
    else:
        st.caption("텍스트 답변만 저장되었거나 녹음이 없습니다.")

    fb = item.get("feedback")
    if isinstance(fb, dict) and fb.get("ok"):
        st.markdown("#### AI 피드백")
        _render_history_feedback_block(fb)

    if st.button(
        "같은 질문 다시 말하기",
        use_container_width=True,
        key=f"topic_v2_history_retry_{idx}",
    ):
        _start_practice_from_history(item)
        st.rerun()


def _start_practice_from_history(item: Dict[str, Any]) -> None:
    _log_tpv2_state_clear("ENTER", "_start_practice_from_history")
    mode = str(item.get("mode") or "topic").strip()
    if mode not in ("topic", "roleplay"):
        mode = "topic"
    q_dict = _history_item_to_question_dict(item)
    st.session_state[_KEY_MODE] = mode
    st.session_state[_KEY_TOPIC] = str(item.get("topic_id") or "").strip()
    if mode == "roleplay":
        st.session_state[_KEY_ROLEPLAY_SET_ID] = str(
            item.get("roleplay_set_id") or ""
        ).strip()
    else:
        st.session_state.pop(_KEY_ROLEPLAY_SET_ID, None)
    st.session_state[_KEY_PAGE] = "practice"
    st.session_state[_KEY_SINGLE_RETRY] = True
    st.session_state[_KEY_QUESTIONS] = [q_dict]
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_CURRENT_Q] = _bank_row_to_current_q(q_dict)
    st.session_state[_KEY_ANSWERS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
    st.session_state[_KEY_STEP] = "question"
    try:
        logger.info(
            "[TOPIC_V2_HISTORY_RETRY] history_id=%s question_id=%s",
            str(item.get("history_id") or "").strip() or "-",
            str(item.get("question_id") or "").strip() or "-",
        )
    except Exception:
        pass
    _log_tpv2_state_clear("EXIT", "_start_practice_from_history")


def _roleplay_set_title() -> str:
    sid = str(st.session_state.get(_KEY_ROLEPLAY_SET_ID) or "").strip()
    for ent in ROLEPLAY_PRACTICE_SETS:
        if not isinstance(ent, dict):
            continue
        if str(ent.get("set_id") or "").strip() == sid:
            return str(ent.get("title_ko") or "").strip()
    return ""


def _practice_screen_title() -> str:
    if _is_roleplay_mode():
        rp_title = _roleplay_set_title()
        return f"롤플레이 연습 · {rp_title}" if rp_title else "롤플레이 연습"
    topic_id = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    return f"주제별 연습 · {_topic_display_title(topic_id)}"


def _session_valid_for_practice() -> bool:
    qs = _session_question_set()
    if _is_single_question_retry():
        return len(qs) >= 1
    if len(qs) < 3:
        return False
    if _is_roleplay_mode():
        return bool(str(st.session_state.get(_KEY_ROLEPLAY_SET_ID) or "").strip())
    topic_id = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    return _topic_id_valid(topic_id)


def _session_question_set() -> List[Dict[str, Any]]:
    raw = st.session_state.get(_KEY_QUESTIONS)
    if not isinstance(raw, list):
        return []
    return [dict(x) for x in raw if isinstance(x, dict)]


def _bank_row_to_current_q(row: Dict[str, Any]) -> Dict[str, str]:
    return {
        "en": str(row.get("question_text") or row.get("en") or "").strip(),
        "ko": str(row.get("ko_helper") or row.get("ko") or "").strip(),
        "opic_type": str(row.get("opic_type") or "").strip(),
    }


def _question_for_index(topic_id: str, q_index: int) -> Optional[Dict[str, str]]:
    qs = _session_question_set()
    if not qs and not _is_roleplay_mode() and _topic_id_valid(topic_id):
        qs = get_topic_practice_set(topic_id)
        if len(qs) >= 3:
            st.session_state[_KEY_QUESTIONS] = qs
    if q_index < 0 or q_index >= len(qs):
        return None
    return _bank_row_to_current_q(qs[q_index])


def _sync_current_question(q_index: int) -> Optional[Dict[str, str]]:
    topic_id = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q = _question_for_index(topic_id, q_index)
    if q:
        st.session_state[_KEY_CURRENT_Q] = q
    else:
        st.session_state[_KEY_CURRENT_Q] = {}
    return q


def _log_topic_v2_question_set(topic_id: str, questions: List[Dict[str, Any]]) -> None:
    try:
        types = ",".join(
            str((q or {}).get("opic_type") or "-") for q in questions if isinstance(q, dict)
        )
        logger.info(
            "[TOPIC_V2_QUESTION_SET] topic_id=%s question_count=%s types=%s",
            topic_id,
            len(questions),
            types or "-",
        )
    except Exception:
        pass


def _log_topic_v2_roleplay_set(set_id: str, questions: List[Dict[str, Any]]) -> None:
    try:
        types = ",".join(
            str((q or {}).get("opic_type") or "-") for q in questions if isinstance(q, dict)
        )
        logger.info(
            "[TOPIC_V2_ROLEPLAY_SET] set_id=%s question_count=%s types=%s",
            set_id,
            len(questions),
            types or "-",
        )
    except Exception:
        pass


def _log_topic_v2_mode(*, step: str, q_idx: int) -> None:
    try:
        logger.info(
            "[TOPIC_V2_MODE] mode=%s step=%s q_idx=%s",
            _topic_v2_mode(),
            step,
            q_idx,
        )
    except Exception:
        pass


def _start_topic_practice(topic_id: str) -> None:
    _log_tpv2_state_clear("ENTER", "_start_topic_practice")
    tid = str(topic_id or "").strip()
    qs = get_topic_practice_set(tid)
    _log_topic_v2_question_set(tid, qs)
    st.session_state[_KEY_MODE] = "topic"
    st.session_state.pop(_KEY_ROLEPLAY_SET_ID, None)
    st.session_state.pop(_KEY_SINGLE_RETRY, None)
    st.session_state[_KEY_TOPIC] = tid
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_ANSWERS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
    if len(qs) < 3:
        st.session_state[_KEY_QUESTIONS] = qs
        st.session_state[_KEY_CURRENT_Q] = {}
        st.session_state[_KEY_STEP] = "insufficient"
        return
    st.session_state[_KEY_QUESTIONS] = qs
    _sync_current_question(0)
    st.session_state[_KEY_STEP] = "question"
    _log_tpv2_state_clear("EXIT", "_start_topic_practice")


def _start_roleplay_practice(set_id: str) -> None:
    _log_tpv2_state_clear("ENTER", "_start_roleplay_practice")
    sid = str(set_id or "").strip()
    qs = get_roleplay_practice_set(sid)
    _log_topic_v2_roleplay_set(sid, qs)
    topic_id = ""
    for ent in ROLEPLAY_PRACTICE_SETS:
        if isinstance(ent, dict) and str(ent.get("set_id") or "").strip() == sid:
            topic_id = str(ent.get("topic_id") or "").strip()
            break
    st.session_state[_KEY_MODE] = "roleplay"
    st.session_state.pop(_KEY_SINGLE_RETRY, None)
    st.session_state[_KEY_ROLEPLAY_SET_ID] = sid
    st.session_state[_KEY_TOPIC] = topic_id
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_ANSWERS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
    if len(qs) < 3:
        st.session_state[_KEY_QUESTIONS] = qs
        st.session_state[_KEY_CURRENT_Q] = {}
        st.session_state[_KEY_STEP] = "insufficient"
        return
    st.session_state[_KEY_QUESTIONS] = qs
    _sync_current_question(0)
    st.session_state[_KEY_STEP] = "question"
    _log_tpv2_state_clear("EXIT", "_start_roleplay_practice")


def _topic_v2_blob_key(topic: str, q_idx: int) -> str:
    return f"{topic}\t{int(q_idx)}"


def _topic_v2_blob_store() -> Dict[str, Any]:
    if _KEY_AUDIO_BLOBS not in st.session_state:
        st.session_state[_KEY_AUDIO_BLOBS] = {}
    raw = st.session_state[_KEY_AUDIO_BLOBS]
    return raw if isinstance(raw, dict) else {}


def _audio_blob_entry(audio_bytes: bytes, mime_type: str) -> Dict[str, Any]:
    return {
        "audio_bytes": bytes(audio_bytes),
        "mime_type": (mime_type or "audio/webm").strip() or "audio/webm",
    }


def _save_topic_v2_audio_blob(
    topic: str,
    q_idx: int,
    audio_bytes: bytes,
    mime_type: str,
    *,
    answer_id: str = "",
) -> None:
    store = _topic_v2_blob_store()
    ent = _audio_blob_entry(audio_bytes, mime_type)
    store[_topic_v2_blob_key(topic, q_idx)] = ent
    aid = str(answer_id or "").strip()
    if aid:
        store[f"aid:{aid}"] = ent
    st.session_state[_KEY_AUDIO_BLOBS] = store


def _delete_topic_v2_audio_blob(topic: str, q_idx: int) -> None:
    store = _topic_v2_blob_store()
    store.pop(_topic_v2_blob_key(topic, q_idx), None)
    st.session_state[_KEY_AUDIO_BLOBS] = store


def _get_topic_v2_audio_blob(topic: str, q_idx: int) -> Tuple[bytes, str]:
    ent = _topic_v2_blob_store().get(_topic_v2_blob_key(topic, q_idx))
    return _audio_bytes_from_ent(ent)


def _get_topic_v2_audio_by_answer_id(answer_id: str) -> Tuple[bytes, str]:
    aid = str(answer_id or "").strip()
    if not aid:
        return b"", ""
    ent = _topic_v2_blob_store().get(f"aid:{aid}")
    return _audio_bytes_from_ent(ent)


def _audio_bytes_from_ent(ent: Any) -> Tuple[bytes, str]:
    if not isinstance(ent, dict):
        return b"", ""
    raw = ent.get("audio_bytes")
    try:
        blob = bytes(raw) if raw is not None else b""
    except (TypeError, ValueError):
        blob = b""
    mime = str(ent.get("mime_type") or "audio/webm").strip() or "audio/webm"
    return blob, mime


def _topic_catalog_index(topic_id: str) -> int:
    tid = (topic_id or "").strip()
    for i, row in enumerate(TOPIC_PRACTICE_TOPICS):
        if str(row.get("topic_id") or "").strip() == tid:
            return i
    return -1


def _topic_v2_mic_key(topic: str, q_idx: int) -> str:
    # Internal widget keys must never be rendered as labels.
    # Use them only as key=... arguments (or omit key for this component if the UI leaks it).
    """ASCII-only Streamlit widget key (avoid Unicode in topic titles leaking into UI)."""
    ti = _topic_catalog_index(topic)
    if ti < 0:
        try:
            logger.warning("[TOPIC_V2_MIC_KEY] unknown topic=%r — fallback key", topic)
        except Exception:
            pass
        mark = zlib.adler32(str(topic).encode("utf-8")) & 0xFFFFFFFF
        return f"topic_v2_mic_u{mark}_q{int(q_idx)}"
    return f"topic_v2_mic_t{ti}_q{int(q_idx)}"


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
    *,
    opic_type: str = "",
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
        "answer_id": str(uuid.uuid4()),
        "topic": topic,
        "q_index": int(q_idx),
        "en": q_en,
        "ko": q_ko,
        "opic_type": str(opic_type or "").strip(),
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
    try:
        logger.info(
            "[TPV2_TRACE_UPSERT_ANSWERS_BEFORE] answers_count=%s",
            _get_topic_v2_answers_count(),
        )
    except Exception:
        pass
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
    try:
        logger.info(
            "[TPV2_TRACE_UPSERT_ANSWERS_AFTER] answers_count=%s answer_ids=%s",
            _get_topic_v2_answers_count(),
            _tpv2_answer_ids_csv(),
        )
    except Exception:
        pass


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
    stt_result = _run_topic_v2_stt(topic, q_idx, q_en, blob, resolved_mime)
    cur_q = st.session_state.get(_KEY_CURRENT_Q)
    opic = str(cur_q.get("opic_type") or "") if isinstance(cur_q, dict) else ""
    row = _build_topic_v2_row_from_mic(
        topic,
        q_idx,
        q_en,
        q_ko,
        blob,
        resolved_mime,
        stt_result,
        opic_type=opic,
    )
    aid = str(row.get("answer_id") or "").strip()
    student_answer, transcript = _answer_text_fields_from_row(row)
    bank_q = _bank_question_at_index(q_idx)
    qid = str(
        bank_q.get("id") or bank_q.get("question_id") or row.get("question_id") or ""
    ).strip()
    try:
        logger.info(
            "[TPV2_TRACE_ANSWER_ROW_BUILT] answer_id=%s question_id=%s topic_id=%s "
            "opic_type=%s student_answer_len=%s transcript_len=%s audio_saved=%s "
            "audio_len=%s status=%s",
            aid or "-",
            qid or "-",
            str(topic or "").strip() or "-",
            str(row.get("opic_type") or "").strip() or "-",
            len(student_answer),
            len(transcript),
            bool(row.get("audio_saved")),
            int(row.get("audio_len") or 0),
            str(row.get("status") or "").strip() or "-",
        )
    except Exception:
        pass
    _save_topic_v2_audio_blob(topic, q_idx, blob, resolved_mime, answer_id=aid)
    _persist_topic_v2_answer_and_history(row)
    st.session_state[_KEY_STEP] = "saved"


def _commit_topic_v2_manual_text_draft(topic: str, q_idx: int, q: Dict[str, Any], draft: str) -> None:
    """Save text-only answer (optional expander UI; keep logic here for restore)."""
    wc = int(count_english_words(draft))
    row = {
        "answer_id": str(uuid.uuid4()),
        "topic": topic,
        "q_index": q_idx,
        "en": str(q.get("en") or ""),
        "ko": str(q.get("ko") or ""),
        "opic_type": str(q.get("opic_type") or "").strip(),
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
    _persist_topic_v2_answer_and_history(row)
    st.session_state[_KEY_STEP] = "saved"
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)


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
    opic = str(last.get("opic_type") or "").strip()
    row = _build_topic_v2_row_from_mic(
        topic,
        q_idx,
        q_en,
        q_ko,
        audio_bytes,
        mime_type or "audio/webm",
        stt_result,
        opic_type=opic,
    )
    prev_aid = str(last.get("answer_id") or "").strip()
    if prev_aid:
        row["answer_id"] = prev_aid
    aid = str(row.get("answer_id") or "").strip()
    if aid:
        _save_topic_v2_audio_blob(
            topic, q_idx, audio_bytes, mime_type or "audio/webm", answer_id=aid
        )
    _persist_topic_v2_answer_and_history(row)
    try:
        logger.info("[TOPIC_V2_STT_RETRY] topic=%s q=%s", topic, q_idx)
    except Exception:
        pass
    return True


def _transcript_from_row(row: Dict[str, Any]) -> str:
    student, transcript = _answer_text_fields_from_row(row)
    return transcript or student


def _answer_text_fields_from_row(answer_row: Dict[str, Any]) -> Tuple[str, str]:
    """Copy student_answer and transcript from answer_row (shared fallbacks)."""
    if not isinstance(answer_row, dict):
        return "", ""
    transcript = ""
    for key in ("transcript", "raw_transcript", "stt_transcript", "student_answer"):
        t = str(answer_row.get(key) or "").strip()
        if t:
            transcript = t
            break
    student = str(answer_row.get("student_answer") or "").strip()
    if not student:
        student = transcript
    if not transcript:
        transcript = student
    return student, transcript


def _persist_history_items(items: List[Dict[str, Any]]) -> None:
    st.session_state[_KEY_HISTORY] = items[:_HISTORY_LIMIT]


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


def _log_topic_v2_flow(*, step: str, topic: str, q_idx: int) -> None:
    try:
        latest = ""
        if 0 <= q_idx < 3:
            latest = str((_last_answer_row_for_q(q_idx) or {}).get("status") or "").strip()
        logger.info(
            "[TOPIC_V2_FLOW] step=%s topic=%s q_idx=%s answers_count=%s latest_answer_status=%s",
            step,
            topic or "-",
            q_idx,
            _topic_v2_answers_count(),
            latest or "-",
        )
    except Exception:
        pass


def _render_topic_v2_attempt_caption(*, topic: str, q_idx: int) -> None:
    if q_idx < 0 or q_idx >= 3:
        return
    last_row = _last_answer_row_for_q(q_idx)
    label = _topic_v2_answer_status_label(last_row)
    if _is_roleplay_mode():
        title = _roleplay_set_title() or _topic_display_title(topic)
    else:
        title = _topic_display_title(topic)
    st.caption("**현재 답변 시도**")
    st.caption(f"주제 · {title}")
    st.caption(f"질문 번호 · Q{q_idx + 1}/3")
    st.caption(f"답변 상태 · {label}")


def _log_topic_v2_feedback_ready(*, topic: str, q_idx: int, answer_id: str) -> None:
    try:
        logger.info(
            "[TOPIC_V2_FEEDBACK_READY] topic=%s q_idx=%s answer_id=%s",
            topic,
            q_idx,
            (answer_id or "").strip() or "-",
        )
    except Exception:
        pass


def _log_topic_v2_retry_same_question(*, topic: str, q_idx: int) -> None:
    try:
        logger.info("[TOPIC_V2_RETRY_SAME_QUESTION] topic=%s q_idx=%s", topic, q_idx)
    except Exception:
        pass


def _log_topic_v2_next_question(*, topic: str, from_q: int, to_q: int) -> None:
    try:
        logger.info(
            "[TOPIC_V2_NEXT_QUESTION] topic=%s from_q=%s to_q=%s",
            topic,
            from_q,
            to_q,
        )
    except Exception:
        pass


def _ensure_topic_v2_minimal_defaults() -> None:
    if _KEY_PAGE not in st.session_state:
        st.session_state[_KEY_PAGE] = "practice"
    _migrate_topic_v2_history_keys()


def _ensure_topic_v2_defaults() -> None:
    _ensure_topic_v2_minimal_defaults()
    if _KEY_STEP not in st.session_state:
        st.session_state[_KEY_STEP] = "select_topic"
    if _KEY_ANSWERS not in st.session_state:
        st.session_state[_KEY_ANSWERS] = []
    if _KEY_FEEDBACK not in st.session_state:
        st.session_state[_KEY_FEEDBACK] = None
    if _KEY_QUESTIONS not in st.session_state:
        st.session_state[_KEY_QUESTIONS] = []
    _migrate_topic_v2_history_keys()


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


def _log_tpv2_go_history(phase: str) -> None:
    try:
        logger.info(
            "[TPV2_GO_HISTORY_%s] answers_count=%s history_count=%s "
            "audio_blobs_count=%s page=%s step=%s",
            phase,
            _get_topic_v2_answers_count(),
            _get_topic_v2_history_count(),
            _audio_blobs_count(),
            str(st.session_state.get(_KEY_PAGE) or "").strip() or "-",
            str(st.session_state.get(_KEY_STEP) or "").strip() or "-",
        )
    except Exception:
        pass


def _go_topic_v2_history() -> None:
    """In-app history only — do not call navigate_to or reset portal."""
    _log_tpv2_go_history("BEFORE")
    _migrate_topic_v2_history_keys()
    st.session_state[_KEY_PAGE] = "history"
    st.session_state[_KEY_STEP] = "history"
    st.session_state["mock_mode"] = MOCK_MODE_TOPIC_V2
    st.session_state["mock_page"] = "TOPIC_V2"
    st.session_state["practice_portal_selected"] = True
    try:
        mx = mock_session()
        mx["mock_mode"] = MOCK_MODE_TOPIC_V2
        mx["mock_page"] = "TOPIC_V2"
        mx["mock_mode_label"] = "주제별 답변 연습"
    except Exception:
        pass
    _log_tpv2_go_history("AFTER")


def apply_topic_v2_history_route(mx: Optional[Dict[str, Any]] = None, *, source: str = "") -> None:
    """Enter Topic V2 history-only page without clearing session history."""
    _log_tpv2_state_clear("ENTER", f"apply_topic_v2_history_route:{source}")
    _migrate_topic_v2_history_keys()
    st.session_state[_KEY_PAGE] = "history"
    st.session_state[_KEY_STEP] = "history"
    st.session_state["mock_mode"] = MOCK_MODE_TOPIC_V2
    st.session_state["mock_page"] = "TOPIC_V2"
    st.session_state["practice_portal_selected"] = True
    if isinstance(mx, dict):
        mx["mock_mode"] = MOCK_MODE_TOPIC_V2
        mx["mock_page"] = "TOPIC_V2"
        mx["mock_mode_label"] = "주제별 답변 연습"
    try:
        logger.info(
            "[NAV_TOPIC_V2_HISTORY] source=%s page=MOCK mock=%s",
            str(source or "").strip() or "-",
            MOCK_SUBPAGE_TOPIC_V2_HISTORY,
        )
        logger.info(
            "[MOCK_ROUTE_TOPIC_V2_HISTORY] topic_v2_page=%s topic_v2_step=%s",
            st.session_state.get(_KEY_PAGE),
            st.session_state.get(_KEY_STEP),
        )
    except Exception:
        pass
    _log_tpv2_state_clear("EXIT", f"apply_topic_v2_history_route:{source}")


def enter_topic_v2_history_nav(*, source: str = "home") -> None:
    """Public entry for navigate_to / URL — history page only, no portal reset.

    # Persistent history requires DB storage; session_state may reset after
    # full page navigation (bottom nav location.assign, browser refresh).
    """
    apply_topic_v2_history_route(None, source=source)


def apply_topic_v2_practice_selection_route(mx: Optional[Dict[str, Any]] = None) -> None:
    """Return to Topic V2 topic selection (not global learning portal)."""
    st.session_state[_KEY_PAGE] = "practice"
    st.session_state[_KEY_STEP] = "select_topic"
    st.session_state["mock_mode"] = MOCK_MODE_TOPIC_V2
    st.session_state["mock_page"] = "TOPIC_V2"
    st.session_state["practice_portal_selected"] = True
    if isinstance(mx, dict):
        mx["mock_mode"] = MOCK_MODE_TOPIC_V2
        mx["mock_page"] = "TOPIC_V2"
        mx["mock_mode_label"] = "주제별 답변 연습"


def _go_topic_v2_practice() -> None:
    apply_topic_v2_practice_selection_route(None)


def _topic_v2_router_will_render(step: str) -> str:
    labels = {
        "history": "history",
        "select_topic": "selection",
        "question": "question",
        "saved": "saved",
        "feedback": "feedback",
        "pending": "pending",
        "insufficient": "insufficient",
    }
    return labels.get(step, "selection")


def _goto_topic_select() -> None:
    """Return to topic selection without clearing session answers, history, or audio blobs."""
    _log_tpv2_state_clear("ENTER", "_goto_topic_select")
    st.session_state[_KEY_PAGE] = "practice"
    st.session_state[_KEY_STEP] = "select_topic"
    st.session_state[_KEY_MODE] = "topic"
    st.session_state.pop(_KEY_ROLEPLAY_SET_ID, None)
    st.session_state.pop(_KEY_SINGLE_RETRY, None)
    st.session_state[_KEY_TOPIC] = ""
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_CURRENT_Q] = {}
    st.session_state[_KEY_QUESTIONS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
    _log_tpv2_state_clear("EXIT", "_goto_topic_select")


def _render_insufficient_questions() -> None:
    topic_id = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    title = _topic_display_title(topic_id)
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} · 준비 중")
    st.markdown(f"### 주제별 연습 · {title}")
    st.warning("이 주제의 문제가 아직 충분하지 않습니다.\n\n다른 주제를 선택해 주세요.")
    if st.button("주제 선택으로 돌아가기", type="primary", use_container_width=True, key="topic_v2_insufficient_back"):
        _goto_topic_select()
        st.rerun()


def _render_select_topic() -> None:
    if st.session_state.get(_KEY_PAGE) == "history":
        return
    if st.session_state.get(_KEY_STEP) == "history":
        return

    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow="주제 선택")
    st.markdown("### 주제별 연습")

    hist_n = _get_topic_v2_history_count()
    ans_n = _get_topic_v2_answers_count()
    step = str(st.session_state.get(_KEY_STEP) or "").strip()
    try:
        logger.info(
            "[TOPIC_V2_SELECTION_COUNTS] answers_count=%s history_count=%s step=%s",
            ans_n,
            hist_n,
            step or "-",
        )
    except Exception:
        pass

    if st.button(
        f"최근 연습 기록 보기 ({hist_n})",
        type="secondary",
        use_container_width=True,
        key="topic_v2_open_history",
    ):
        _go_topic_v2_history()
        st.rerun()

    st.markdown("#### 주제별 연습")
    st.caption("Q1 → Q2 → Q3 또는 Q4 순서로 연습합니다.")

    for row in TOPIC_PRACTICE_TOPICS:
        if not isinstance(row, dict):
            continue
        topic_id = str(row.get("topic_id") or "").strip()
        if not topic_id:
            continue
        title_ko = str(row.get("title_ko") or topic_id).strip()
        title_en = str(row.get("title_en") or "").strip()
        label = f"{title_ko} ({title_en})" if title_en else title_ko
        if st.button(label, use_container_width=True, key=f"topic_v2_pick_{topic_id}"):
            _start_topic_practice(topic_id)
            st.rerun()

    st.divider()
    st.markdown("#### 롤플레이 연습")
    st.caption("Q6 → Q7 → Q8 순서로 연습합니다.")

    for ent in ROLEPLAY_PRACTICE_SETS:
        if not isinstance(ent, dict):
            continue
        set_id = str(ent.get("set_id") or "").strip()
        if not set_id:
            continue
        title_ko = str(ent.get("title_ko") or set_id).strip()
        topic_id = str(ent.get("topic_id") or "").strip()
        topic_label = get_topic_title(topic_id) if topic_id else ""
        label = f"{title_ko}"
        if topic_label and topic_label not in title_ko:
            label = f"{title_ko} · {topic_label}"
        if st.button(label, use_container_width=True, key=f"topic_v2_roleplay_{set_id}"):
            _start_roleplay_practice(set_id)
            st.rerun()


def _render_topic_v2_history_page() -> None:
    """Dedicated review page — no topic selection, roleplay list, or shared practice top bar."""
    try:
        logger.info(
            "[TPV2_HISTORY_PAGE_ENTER] answers_count=%s history_count=%s "
            "audio_blobs_count=%s page=%s step=%s",
            _get_topic_v2_answers_count(),
            _history_count(),
            _audio_blobs_count(),
            str(st.session_state.get(_KEY_PAGE) or "").strip() or "-",
            str(st.session_state.get(_KEY_STEP) or "").strip() or "-",
        )
    except Exception:
        pass
    items = _history_store()
    added_by_recovery = 0
    if not items and _get_topic_v2_answers_count() > 0:
        try:
            added_by_recovery = _recover_topic_v2_history_from_answers()
        except Exception:
            try:
                logger.exception("[TOPIC_V2_HISTORY_RECOVERY] history_page_failed")
            except Exception:
                pass
        items = _history_store()
    try:
        logger.info(
            "[TPV2_HISTORY_PAGE_AFTER_RECOVERY] answers_count=%s history_count=%s "
            "added_by_recovery=%s",
            _get_topic_v2_answers_count(),
            len(items),
            added_by_recovery,
        )
    except Exception:
        pass
    ans_n = _get_topic_v2_answers_count()
    hist_n = len(items)
    try:
        logger.info(
            "[TOPIC_V2_HISTORY_PAGE_COUNTS] answers_count=%s history_count=%s audio_blobs_count=%s",
            ans_n,
            hist_n,
            _audio_blobs_count(),
        )
    except Exception:
        pass

    st.markdown("## 최근 연습 기록")
    st.markdown("이전에 말했던 답변과 AI 피드백을 다시 볼 수 있어요.")

    _render_tpv2_debug_panel("history")

    st.button(
        "주제별 연습으로 돌아가기",
        type="primary",
        use_container_width=True,
        key="topic_v2_history_back_to_practice",
        on_click=_go_topic_v2_practice,
    )

    if not items:
        try:
            logger.info(
                "[TPV2_HISTORY_EMPTY_STATE] answers_count=%s history_count=0 reason=no_items",
                ans_n,
            )
        except Exception:
            pass
        st.markdown(
            "아직 저장된 연습 기록이 없어요.\n\n"
            "주제별 연습을 한 번 완료하면 여기에 답변과 피드백이 저장됩니다."
        )
        return

    try:
        logger.info(
            "[TPV2_HISTORY_RENDER_CARDS] history_count=%s answer_ids=%s",
            hist_n,
            _tpv2_history_answer_ids_csv(),
        )
    except Exception:
        pass

    st.divider()
    for idx, item in enumerate(items):
        label = _history_card_expander_label(item)
        with st.expander(label, expanded=(idx == 0)):
            _render_history_card_content(item, idx)


def _render_question() -> None:
    topic_id = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    _log_topic_v2_mode(step="question", q_idx=q_idx)
    if not _session_valid_for_practice():
        _goto_topic_select()
        st.rerun()
        return

    qs = _session_question_set()
    min_questions = 1 if _is_single_question_retry() else 3
    if len(qs) < min_questions:
        st.session_state[_KEY_STEP] = "insufficient"
        st.rerun()
        return

    q = _sync_current_question(q_idx)
    if not isinstance(q, dict) or not (q.get("en") or "").strip():
        _goto_topic_select()
        st.rerun()
        return

    screen_title = _practice_screen_title()
    opic_label = _opic_type_label(str(q.get("opic_type") or ""))
    eyebrow_tail = "롤플레이" if _is_roleplay_mode() else _topic_display_title(topic_id)

    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{eyebrow_tail} · 질문")
    st.markdown(f"### {screen_title}")
    if _is_single_question_retry():
        st.caption("기록에서 다시 연습 · Q1/1")
    else:
        st.caption(f"Q{q_idx + 1}/3")
    st.caption(opic_label)
    st.markdown(f"**{q.get('en', '')}**")
    st.caption(q.get("ko") or "")

    st.markdown("### 말로 답변하기")
    st.caption(
        "답변 시작을 누르고 영어로 말해 보세요. 녹음이 끝나면 AI가 텍스트로 인식합니다."
    )

    from streamlit_mic_recorder import mic_recorder

    # Do not pass key=... — some Streamlit / component builds surface internal keys as visible "key..." UI.
    mic_result = mic_recorder(
        start_prompt="🎤 답변 시작",
        stop_prompt="■ 녹음 완료",
        key=None,
        use_container_width=True,
        just_once=True,
    )

    if mic_result is not None:
        audio_bytes, mime_type = _extract_topic_v2_audio_bytes(mic_result, mic_key="")
        try:
            logger.info(
                "[TOPIC_V2_MIC_RESULT] topic=%s q=%s audio_len=%s mime_type=%s",
                topic_id,
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
                    topic_id,
                    q_idx,
                    str(q.get("en") or ""),
                    str(q.get("ko") or ""),
                    audio_bytes,
                    mime_type or "audio/webm",
                )
            st.rerun()

    # Text fallback expander is hidden: st.text_area + this flow surfaced internal keys as "key..." for
    # some students. Re-enable with st.text_area("영어 답변을 입력해 주세요", key=text_draft_key, ...) and
    # _commit_topic_v2_manual_text_draft(topic, q_idx, q, draft).


def _render_saved_normal(topic: str, q_idx: int) -> None:
    if _is_roleplay_mode():
        title = _roleplay_set_title() or _topic_display_title(topic)
        eyebrow = f"{title} · 저장"
    else:
        title = _topic_display_title(topic)
        eyebrow = f"{title} · 저장"
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=eyebrow)
    _render_topic_v2_attempt_caption(topic=topic, q_idx=q_idx)
    st.markdown("### 답변이 저장되었어요.")

    _render_tpv2_debug_panel("saved")
    ans_n = _get_topic_v2_answers_count()
    hist_n = _get_topic_v2_history_count()
    if st.button(
        "최근 연습 기록 보기",
        type="secondary",
        use_container_width=True,
        key="topic_v2_saved_open_history",
    ):
        _go_topic_v2_history()
        st.rerun()
    if hist_n > 0:
        st.caption(f"현재 세션 기록: {hist_n}개")
    elif ans_n > 0:
        try:
            _recover_topic_v2_history_from_answers()
        except Exception:
            pass
        hist_n = _get_topic_v2_history_count()
        if hist_n > 0:
            st.caption(f"현재 세션 기록: {hist_n}개")
        else:
            st.caption("답변은 저장되었지만 기록 화면 반영을 확인 중입니다.")
    else:
        st.caption(f"현재 세션 기록: {hist_n}개")

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

    if _is_single_question_retry():
        c1, c2, c3 = st.columns(3)
        with c1:
            if can_ai:
                if st.button(
                    "AI 짧은 피드백 받기",
                    type="primary",
                    use_container_width=True,
                    key="topic_v2_request_ai_feedback",
                ):
                    _run_topic_v2_feedback_request(topic, q_idx, last_row)
        with c2:
            if st.button(
                "같은 질문 다시 말하기",
                use_container_width=True,
                key="topic_v2_retry_same",
            ):
                _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
                st.session_state[_KEY_FEEDBACK] = None
                st.session_state[_KEY_STEP] = "question"
                st.rerun()
        with c3:
            if st.button(
                "최근 연습 기록으로 돌아가기",
                use_container_width=True,
                key="topic_v2_back_history",
            ):
                _go_topic_v2_history()
                st.rerun()
        if st.button("주제 선택으로 돌아가기", use_container_width=True, key="topic_v2_back_select"):
            _goto_topic_select()
            st.rerun()
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if can_ai:
            if st.button(
                "AI 짧은 피드백 받기",
                type="primary",
                use_container_width=True,
                key="topic_v2_request_ai_feedback",
            ):
                _run_topic_v2_feedback_request(topic, q_idx, last_row)
    with c2:
        if st.button("다음 질문", use_container_width=True, key="topic_v2_next_q"):
            if q_idx < 2:
                nxt = q_idx + 1
                _log_topic_v2_next_question(topic=topic, from_q=q_idx, to_q=nxt)
                st.session_state[_KEY_Q_INDEX] = nxt
                _sync_current_question(nxt)
                st.session_state[_KEY_STEP] = "question"
            else:
                _log_topic_v2_next_question(topic=topic, from_q=q_idx, to_q=3)
                st.session_state[_KEY_Q_INDEX] = 3
            st.rerun()
    with c3:
        if st.button("같은 질문 다시 말하기", use_container_width=True, key="topic_v2_retry_same"):
            _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
            st.session_state[_KEY_FEEDBACK] = None
            st.session_state[_KEY_STEP] = "question"
            st.rerun()
    with c4:
        if st.button("주제 선택으로 돌아가기", use_container_width=True, key="topic_v2_back_select"):
            _goto_topic_select()
            st.rerun()


def _run_topic_v2_feedback_request(
    topic: str, q_idx: int, last_row: Optional[Dict[str, Any]]
) -> None:
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
            "upgrade_sample": "",
            "keyword_drill": [],
            "practice_mission": "",
            "error_category": "exception",
            "error_message": _TOPIC_V2_FEEDBACK_FAIL_USER_MESSAGE,
        }
    st.session_state[_KEY_FEEDBACK] = result
    aid = str((row_in or {}).get("answer_id") or "").strip()
    if result.get("ok"):
        _log_topic_v2_feedback_ready(topic=topic, q_idx=q_idx, answer_id=aid)
        _update_topic_v2_history_feedback(aid, result, answer_row_fallback=row_in)
        st.session_state[_KEY_STEP] = "feedback"
    else:
        st.session_state[_KEY_STEP] = "pending"
    st.rerun()


def _render_saved_complete(topic: str) -> None:
    title = _topic_display_title(topic)
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} · 완료")
    st.markdown("### 이 주제 연습을 완료했어요.")
    if st.button("같은 주제 다시 연습", type="primary", use_container_width=True, key="topic_v2_restart_same_topic"):
        _start_topic_practice(topic)
        st.rerun()
    if st.button("다른 주제 선택", use_container_width=True, key="topic_v2_pick_other_topic"):
        _goto_topic_select()
        st.rerun()
    if st.button("학습하기로 돌아가기", use_container_width=True, key="topic_v2_back_to_learning"):
        navigate_to("MOCK")
        st.rerun()


def _topic_v2_fb_text(fb: Any, key: str, default: str) -> str:
    if not isinstance(fb, dict):
        return default
    v = str(fb.get(key) or "").strip()
    return v if v else default


def _topic_v2_fb_keywords(fb: Any) -> List[str]:
    if not isinstance(fb, dict):
        return []
    kd = fb.get("keyword_drill")
    if not isinstance(kd, list):
        return []
    return [str(x or "").strip() for x in kd if str(x or "").strip()][:20]


def _render_saved() -> None:
    topic = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    _log_topic_v2_mode(step="saved", q_idx=q_idx)
    if not _session_valid_for_practice():
        _goto_topic_select()
        st.rerun()
        return
    if q_idx >= 3:
        if _is_roleplay_mode():
            _render_roleplay_complete()
        else:
            _render_saved_complete(topic)
    else:
        _render_saved_normal(topic, q_idx)


def _render_roleplay_complete() -> None:
    title = _roleplay_set_title() or "롤플레이"
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} · 완료")
    st.markdown("### 롤플레이 세트를 완료했어요.")
    set_id = str(st.session_state.get(_KEY_ROLEPLAY_SET_ID) or "").strip()
    if st.button("같은 롤플레이 다시 하기", type="primary", use_container_width=True, key="topic_v2_restart_same_roleplay"):
        if set_id:
            _start_roleplay_practice(set_id)
        st.rerun()
    if st.button("다른 롤플레이 선택", use_container_width=True, key="topic_v2_pick_other_roleplay"):
        _goto_topic_select()
        st.rerun()
    if st.button("주제별 연습으로 돌아가기", use_container_width=True, key="topic_v2_back_to_topic_practice"):
        _goto_topic_select()
        st.rerun()


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

    title = _topic_display_title(topic)
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} · 피드백")
    _render_topic_v2_attempt_caption(topic=topic, q_idx=q_idx)
    st.markdown("### AI 짧은 피드백")

    summary = _topic_v2_fb_text(fb, "summary", _FB_FALLBACK_SUMMARY)
    strength = _topic_v2_fb_text(fb, "strength", _FB_FALLBACK_STRENGTH)
    correction = _topic_v2_fb_text(fb, "correction_focus", _FB_FALLBACK_CORRECTION_FOCUS)
    better = str(fb.get("better_expression") or "").strip()
    better_disp = better if better else _EMPTY_FIELD_PLACEHOLDER
    upgrade = str(fb.get("upgrade_sample") or "").strip()
    upgrade_disp = upgrade if upgrade else _EMPTY_FIELD_PLACEHOLDER
    mission = _topic_v2_fb_text(fb, "practice_mission", _FB_FALLBACK_PRACTICE_MISSION)
    kwords = _topic_v2_fb_keywords(fb)

    st.markdown("#### 한 줄 총평")
    st.write(summary)
    st.markdown("#### 잘한 점")
    st.write(strength)
    st.markdown("#### 바로 고칠 점")
    st.write(correction)
    st.markdown("#### 더 자연스러운 표현")
    st.write(better_disp)
    st.markdown("#### 내 답변 업그레이드 예시")
    st.write(upgrade_disp)
    st.markdown("#### 다시 말하기 키워드")
    if kwords:
        st.markdown(" · ".join(f"`{w}`" for w in kwords))
    else:
        st.write(_EMPTY_FIELD_PLACEHOLDER)
    st.markdown("#### 다음 연습 미션")
    st.write(mission)

    st.divider()
    if _is_single_question_retry():
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button(
                "같은 질문 다시 말하기",
                use_container_width=True,
                key="topic_v2_fb_retry_same",
            ):
                _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
                st.session_state[_KEY_FEEDBACK] = None
                st.session_state[_KEY_STEP] = "question"
                st.rerun()
        with c2:
            if st.button(
                "최근 연습 기록으로 돌아가기",
                use_container_width=True,
                key="topic_v2_fb_back_history",
            ):
                st.session_state[_KEY_FEEDBACK] = None
                _go_topic_v2_history()
                st.rerun()
        with c3:
            if st.button(
                "주제 선택으로 돌아가기",
                use_container_width=True,
                key="topic_v2_fb_other_topic",
            ):
                st.session_state[_KEY_FEEDBACK] = None
                _goto_topic_select()
                st.rerun()
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "같은 질문 다시 말하기",
            use_container_width=True,
            key="topic_v2_fb_retry_same",
        ):
            _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
            st.session_state[_KEY_FEEDBACK] = None
            st.session_state[_KEY_STEP] = "question"
            st.rerun()
    with c2:
        if st.button("다음 질문", use_container_width=True, key="topic_v2_fb_next"):
            st.session_state[_KEY_FEEDBACK] = None
            if q_idx < 2:
                nxt = q_idx + 1
                _log_topic_v2_next_question(topic=topic, from_q=q_idx, to_q=nxt)
                st.session_state[_KEY_Q_INDEX] = nxt
                _sync_current_question(nxt)
                st.session_state[_KEY_STEP] = "question"
            else:
                _log_topic_v2_next_question(topic=topic, from_q=q_idx, to_q=3)
                st.session_state[_KEY_Q_INDEX] = 3
                st.session_state[_KEY_STEP] = "saved"
            st.rerun()
    with c3:
        if st.button(
            "다른 주제 선택",
            use_container_width=True,
            key="topic_v2_fb_other_topic",
        ):
            st.session_state[_KEY_FEEDBACK] = None
            _goto_topic_select()
            st.rerun()


def _render_pending_ui() -> None:
    topic = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    if not topic:
        _goto_topic_select()
        st.rerun()
        return
    fb = st.session_state.get(_KEY_FEEDBACK)
    msg = _TOPIC_V2_FEEDBACK_FAIL_USER_MESSAGE
    if isinstance(fb, dict):
        cat = str(fb.get("error_category") or "")
        em = str(fb.get("error_message") or "").strip()
        if cat in ("api_key", "insufficient_text") and em:
            msg = em

    title = _topic_display_title(topic)
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} · 피드백")
    _render_topic_v2_attempt_caption(topic=topic, q_idx=q_idx)
    st.markdown("### AI 피드백")
    st.info(msg)
    if isinstance(fb, dict) and st.session_state.get("show_dev_debug"):
        st.caption(f"(debug) error_category={fb.get('error_category')!r}")

    st.divider()
    if _is_single_question_retry():
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button(
                "피드백 다시 받기",
                type="primary",
                use_container_width=True,
                key="topic_v2_pending_retry_feedback",
            ):
                st.session_state[_KEY_FEEDBACK] = None
                st.session_state[_KEY_STEP] = "saved"
                st.rerun()
        with c2:
            if st.button(
                "같은 질문 다시 말하기",
                use_container_width=True,
                key="topic_v2_pending_retry_speak",
            ):
                _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
                st.session_state[_KEY_FEEDBACK] = None
                st.session_state[_KEY_STEP] = "question"
                st.rerun()
        with c3:
            if st.button(
                "최근 연습 기록으로 돌아가기",
                use_container_width=True,
                key="topic_v2_pending_back_history",
            ):
                st.session_state[_KEY_FEEDBACK] = None
                _go_topic_v2_history()
                st.rerun()
        if st.button("주제 선택으로 돌아가기", use_container_width=True, key="topic_v2_pending_back_select"):
            st.session_state[_KEY_FEEDBACK] = None
            _goto_topic_select()
            st.rerun()
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "피드백 다시 받기",
            type="primary",
            use_container_width=True,
            key="topic_v2_pending_retry_feedback",
        ):
            st.session_state[_KEY_FEEDBACK] = None
            st.session_state[_KEY_STEP] = "saved"
            st.rerun()
    with c2:
        if st.button(
            "같은 질문 다시 말하기",
            use_container_width=True,
            key="topic_v2_pending_retry_speak",
        ):
            _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
            st.session_state[_KEY_FEEDBACK] = None
            st.session_state[_KEY_STEP] = "question"
            st.rerun()
    with c3:
        if st.button("다음 질문", use_container_width=True, key="topic_v2_pending_next_q"):
            st.session_state[_KEY_FEEDBACK] = None
            if q_idx < 2:
                nxt = q_idx + 1
                _log_topic_v2_next_question(topic=topic, from_q=q_idx, to_q=nxt)
                st.session_state[_KEY_Q_INDEX] = nxt
                _sync_current_question(nxt)
                st.session_state[_KEY_STEP] = "question"
            else:
                _log_topic_v2_next_question(topic=topic, from_q=q_idx, to_q=3)
                st.session_state[_KEY_Q_INDEX] = 3
                st.session_state[_KEY_STEP] = "saved"
            st.rerun()


def render_topic_practice_v2() -> None:
    """Entry: learning portal → Topic Practice V2 (isolated session keys)."""
    _ensure_topic_v2_minimal_defaults()
    page = str(st.session_state.get(_KEY_PAGE) or "practice").strip()
    step = str(st.session_state.get(_KEY_STEP) or "select_topic").strip()
    try:
        logger.info(
            "[TPV2_RENDER_ENTER] answers_count=%s history_count=%s "
            "audio_blobs_count=%s page=%s step=%s",
            _get_topic_v2_answers_count(),
            _get_topic_v2_history_count(),
            _audio_blobs_count(),
            page or "-",
            step or "-",
        )
    except Exception:
        pass

    if page == "history":
        try:
            logger.info(
                "[TOPIC_V2_PAGE_ROUTER] page=history step=%s will_render=history_page",
                step,
            )
        except Exception:
            pass
        _render_topic_v2_history_page()
        return

    ensure_mock(st.session_state)
    mock_session()
    _ensure_topic_v2_defaults()

    if step == "history":
        st.session_state[_KEY_PAGE] = "history"
        try:
            logger.info(
                "[TOPIC_V2_PAGE_ROUTER] page=history step=history will_render=history_page",
            )
        except Exception:
            pass
        _render_topic_v2_history_page()
        return

    step = _normalize_step(step)
    will_render = _topic_v2_router_will_render(step)
    try:
        logger.info(
            "[TOPIC_V2_PAGE_ROUTER] page=practice step=%s will_render=practice_page",
            step,
        )
        logger.info("[TOPIC_V2_ROUTER] step=%s will_render=%s", step, will_render)
    except Exception:
        pass

    topic_log = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx_log = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    _log_topic_v2_flow(step=step, topic=topic_log, q_idx=q_idx_log)
    _log_topic_v2_mode(step=step, q_idx=q_idx_log)

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
    elif step == "insufficient":
        _render_insufficient_questions()
    else:
        try:
            logger.warning("[TOPIC_V2] fallthrough step=%r — select_topic UI", step)
        except Exception:
            pass
        st.session_state[_KEY_STEP] = "select_topic"
        _render_select_topic()
