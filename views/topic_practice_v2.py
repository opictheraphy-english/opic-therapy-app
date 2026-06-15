"""Topic Practice V2 — isolated shell (OPIc question bank v2 + recording/STT/feedback)."""

from __future__ import annotations

import base64
import html
import logging
import time
import uuid
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

from components.answer_countdown_timer import (
    DEFAULT_DURATION_SEC,
    build_answer_timer_id,
    dismiss_answer_timer_signal,
    handle_answer_timer_expiry,
    render_answer_countdown_timer,
)
from components.audio_player import (
    render_exam_question_audio_player,
    render_recording_playback_player,
)
from components.exam_feedback_screen import (
    render_feedback_keyword_chips,
    render_feedback_label,
    render_feedback_section_card,
    render_feedback_summary,
    render_keyword_constraint_feedback,
)
from components.exam_saved_screen import (
    render_saved_recording_header,
    render_saved_status,
    render_saved_transcript,
)
from components.navigation import navigate_to
from components.recovery_card import (
    ANALYSIS_RECOVERY_EYEBROW,
    ANALYSIS_RECOVERY_TITLE,
    render_analysis_recovery_card,
    render_recovery_card_html,
    render_recovery_retry_caption_html,
)
from components.topbar import render_top_bar
from data.keyword_constraint_sets import (
    get_keyword_constraint_practice_set,
    list_keyword_constraint_sets,
    list_keyword_constraint_sets_by_category,
)
from data.opic_question_bank_v2 import (
    ROLEPLAY_PRACTICE_SETS,
    TOPIC_PRACTICE_TOPICS,
    get_roleplay_practice_set,
    get_topic_practice_set,
    get_topic_title,
)
from services.mock_exam.mock_exam_test_set_generator import (
    get_advanced_practice_set,
    list_advanced_sets,
)
from services.stt_service import count_english_words
from utils.session_state import ensure_mock, mock_session
from views.topic_icons import TOPIC_ICONS

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_QUESTION_AUDIO_DIR = _ROOT / "assets" / "question_audio"

_KEY_AUDIO_BLOBS = "topic_v2_audio_blobs"
_MIN_SAVED_WORDS = 5

MOCK_MODE_TOPIC_V2 = "topic_practice_v2"
ENTRY_SOURCE_PORTAL_KEYWORD = "portal_keyword"
ENTRY_SOURCE_TOPIC_HUB = "topic_hub"

_KEY_STEP = "topic_v2_step"
_KEY_PAGE = "topic_v2_page"
_KEY_TOPIC = "topic_v2_topic"
_KEY_Q_INDEX = "topic_v2_question_index"
_KEY_CURRENT_Q = "topic_v2_current_question"
_KEY_QUESTIONS = "topic_v2_questions"
_KEY_MODE = "topic_v2_mode"
_KEY_ROLEPLAY_SET_ID = "topic_v2_roleplay_set_id"
_KEY_ADVANCED_SET_ID = "topic_v2_advanced_set_id"
_KEY_KEYWORD_CONSTRAINT_SET_ID = "topic_v2_keyword_constraint_set_id"
_KEY_ENTRY_SOURCE = "topic_v2_entry_source"
_KEY_ANSWERS = "topic_v2_answers"
_KEY_FEEDBACK = "topic_v2_feedback"
_KEY_DRAFT_TRANSCRIPT = "topic_v2_practice_transcript"
_KEY_SINGLE_RETRY = "topic_v2_single_question_retry"
_KEY_FB_IN_FLIGHT = "topic_v2_feedback_in_flight"
_KEY_FB_COOLDOWN_UNTIL = "topic_v2_feedback_cooldown_until"
_KEY_FB_ATTEMPTS = "topic_v2_feedback_attempts"
_KEY_FB_NOTICE = "topic_v2_feedback_user_notice"
_KEY_PRACTICE_SIG = "topic_v2_practice_sig"
_KEY_FEEDBACK_BY_Q = "topic_v2_feedback_by_q"

_FEEDBACK_COOLDOWN_BASE_SEC = 45
_FEEDBACK_COOLDOWN_STEP_SEC = 15
_FEEDBACK_COOLDOWN_MAX_SEC = 90
_FEEDBACK_MAX_ATTEMPTS_PER_ANSWER = 4

_TOPIC_V2_FEEDBACK_FAIL_USER_MESSAGE = (
    "AI 피드백 서버가 잠시 바빠요.\n\n"
    "답변은 이미 저장되어 있습니다.\n\n"
    "45초 정도 지난 뒤 「피드백 다시 받기」를 한 번만 눌러 주세요. "
    "연속으로 누르면 같은 오류가 반복되고 API 사용량만 늘어납니다."
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
    {
        "select_topic",
        "select_keyword_set",
        "question",
        "saved",
        "feedback",
        "pending",
        "insufficient",
    }
)

_KEY_TOPIC_SEARCH = "topic_v2_topic_search"
_KEY_TOPIC_CATEGORY = "topic_v2_topic_category"
_KEY_ROLEPLAY_EXPAND = "topic_v2_roleplay_expand"
_KEY_ADVANCED_EXPAND = "topic_v2_advanced_expand"
_KEY_KEYWORD_CONSTRAINT_EXPAND = "topic_v2_keyword_constraint_expand"

_RECOMMENDED_TOPIC_IDS: Tuple[str, ...] = (
    "home",
    "cafe",
    "movies_tv",
    "music",
    "travel",
    "restaurant",
)

_TOPIC_V2_CATEGORY_LABELS: Tuple[str, ...] = ("일상", "취미", "운동", "여행", "사회", "전체")

_TOPIC_V2_CATEGORY_TOPIC_IDS: Dict[str, Tuple[str, ...]] = {
    "일상": (
        "home",
        "family_home",
        "neighborhood",
        "cafe",
        "restaurant",
        "food",
        "shopping",
        "holidays",
        "gatherings",
    ),
    "취미": (
        "movies_tv",
        "performances",
        "music",
        "singing",
        "instruments",
        "cooking",
        "books",
        "free_time",
    ),
    "운동": ("walking", "jogging", "gym", "sports", "health"),
    "여행": (
        "travel",
        "vacation",
        "beach",
        "hotels",
        "transportation",
        "country_places",
    ),
    "사회": (
        "technology",
        "phone",
        "internet",
        "industry",
        "bank",
        "appointments",
        "recycling",
        "weather",
        "fashion",
    ),
    "전체": (),
}


def _feedback_answer_id(
    row: Optional[Dict[str, Any]], *, topic: str, q_idx: int
) -> str:
    if isinstance(row, dict):
        aid = str(row.get("answer_id") or "").strip()
        if aid:
            return aid
    return f"{topic}_{q_idx}"


def _feedback_attempt_counts() -> Dict[str, int]:
    raw = st.session_state.get(_KEY_FB_ATTEMPTS)
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[str(k)] = max(0, int(v))
        except (TypeError, ValueError):
            continue
    return out


def _cooldown_seconds_remaining() -> int:
    try:
        until = float(st.session_state.get(_KEY_FB_COOLDOWN_UNTIL) or 0.0)
    except (TypeError, ValueError):
        until = 0.0
    return max(0, int(until - time.time()))


def _feedback_fail_sets_cooldown(category: str) -> bool:
    return str(category or "").strip() not in (
        "api_key",
        "insufficient_text",
        "cooldown",
        "blocked",
    )


def _register_feedback_failure(category: str, answer_id: str) -> None:
    counts = _feedback_attempt_counts()
    n = counts.get(answer_id, 0) + 1
    counts[answer_id] = n
    st.session_state[_KEY_FB_ATTEMPTS] = counts
    if not _feedback_fail_sets_cooldown(category):
        return
    cd = min(
        _FEEDBACK_COOLDOWN_MAX_SEC,
        _FEEDBACK_COOLDOWN_BASE_SEC + _FEEDBACK_COOLDOWN_STEP_SEC * max(0, n - 1),
    )
    st.session_state[_KEY_FB_COOLDOWN_UNTIL] = time.time() + cd


def _clear_feedback_guard(answer_id: str) -> None:
    st.session_state.pop(_KEY_FB_COOLDOWN_UNTIL, None)
    st.session_state.pop(_KEY_FB_NOTICE, None)
    counts = _feedback_attempt_counts()
    counts.pop(answer_id, None)
    st.session_state[_KEY_FB_ATTEMPTS] = counts


def _can_request_topic_v2_feedback(answer_id: str) -> Tuple[bool, str]:
    if st.session_state.get(_KEY_FB_IN_FLIGHT):
        return False, "피드백을 생성 중입니다. 완료될 때까지 잠시만 기다려 주세요."
    rem = _cooldown_seconds_remaining()
    if rem > 0:
        return (
            False,
            f"서버가 잠시 바빠요. {rem}초 후에 「피드백 다시 받기」를 눌러 주세요. "
            "연속으로 누르면 API 호출만 늘고 같은 오류가 반복될 수 있어요.",
        )
    n = _feedback_attempt_counts().get(answer_id, 0)
    if n >= _FEEDBACK_MAX_ATTEMPTS_PER_ANSWER:
        return (
            False,
            "이 답변에 대한 자동 피드백 시도 횟수에 도달했어요. "
            "같은 질문을 다시 말한 뒤 새 답변으로 피드백을 받아 보세요.",
        )
    return True, ""


def _feedback_request_button_state(answer_id: str) -> Tuple[bool, str]:
    """(disabled, label) for AI feedback buttons."""
    if st.session_state.get(_KEY_FB_IN_FLIGHT):
        return True, "피드백 생성 중…"
    rem = _cooldown_seconds_remaining()
    if rem > 0:
        return True, f"피드백 다시 받기 ({rem}초 후)"
    n = _feedback_attempt_counts().get(answer_id, 0)
    if n >= _FEEDBACK_MAX_ATTEMPTS_PER_ANSWER:
        return True, "피드백 시도 한도 도달"
    return False, "AI 짧은 피드백 받기"


def _render_feedback_guard_notice() -> None:
    notice = str(st.session_state.get(_KEY_FB_NOTICE) or "").strip()
    if notice:
        st.warning(notice)
    rem = _cooldown_seconds_remaining()
    if rem > 0 and not notice:
        st.info(
            f"AI 서버가 잠시 바빠요. {rem}초 후에 「피드백 다시 받기」를 한 번만 눌러 주세요."
        )


_OPIC_TYPE_LABELS: Dict[str, str] = {
    "Q1": "Q1 유형 · 묘사",
    "Q2": "Q2 유형 · 루틴",
    "Q3": "Q3 유형 · 경험",
    "Q4": "Q4 유형 · 문제/경험",
    "Q6": "Q6 유형 · 질문하기",
    "Q7": "Q7 유형 · 문제 해결",
    "Q8": "Q8 유형 · 관련 경험",
    "COMPARISON": "Comparison · 비교·변화",
    "NEWS/ISSUE": "News/Issue · 사회 이슈",
    "KEYWORD": "Keyword · 표현 제약",
}

_OPIC_TYPE_BADGE_LABELS: Dict[str, str] = {
    "Q1": "Q1 · 묘사하기",
    "Q2": "Q2 · 루틴하기",
    "Q3": "Q3 · 경험하기",
    "Q4": "Q4 · 문제/경험",
    "Q6": "Q6 · 질문하기",
    "Q7": "Q7 · 문제 해결",
    "Q8": "Q8 · 관련 경험",
    "COMPARISON": "Comparison · 비교·변화",
    "NEWS/ISSUE": "News/Issue · 사회 이슈",
    "KEYWORD": "Keyword · 표현 제약",
}

_TOPIC_ACCENT_NAMES: Tuple[str, ...] = (
    "teal",
    "blue",
    "purple",
    "pink",
    "amber",
    "coral",
)

_TOPIC_V2_STATUS_LABELS: Dict[str, str] = {
    "saved": "답변 저장됨",
    "insufficient_response": "답변이 짧아요 (조금 더 말해 보세요)",
    "stt_pending": "음성 인식 처리 중",
    "stt_failed": "음성 인식에 실패했어요",
    "recording_failed": "녹음에 문제가 있었어요",
    "manual_text": "텍스트로 저장됨",
}

def _topic_v2_answers_count() -> int:
    raw = st.session_state.get(_KEY_ANSWERS)
    return len(raw) if isinstance(raw, list) else 0


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




def _log_tpv2_state_clear(phase: str, function: str) -> None:
    try:
        logger.info(
            "[TPV2_STATE_CLEAR_%s] function=%s answers_count=%s "
            "audio_blobs_count=%s step=%s page=%s",
            phase,
            function,
            _get_topic_v2_answers_count(),
            _audio_blobs_count(),
            str(st.session_state.get(_KEY_STEP) or "").strip() or "-",
            str(st.session_state.get(_KEY_PAGE) or "").strip() or "-",
        )
    except Exception:
        pass








def clear_topic_v2_session() -> None:
    """Remove Topic Practice V2 practice keys (portal / reset)."""
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
        _KEY_ADVANCED_SET_ID,
        _KEY_KEYWORD_CONSTRAINT_SET_ID,
        _KEY_ENTRY_SOURCE,
        _KEY_ANSWERS,
        _KEY_FEEDBACK,
        _KEY_FEEDBACK_BY_Q,
        _KEY_PRACTICE_SIG,
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
    if title:
        return title
    for ent in list_advanced_sets():
        if str(ent.get("set_id") or "").strip() == tid:
            adv = str(ent.get("title_ko") or "").strip()
            if adv:
                return adv
    return tid


def _opic_type_label(opic_type: str) -> str:
    key = str(opic_type or "").strip().upper()
    return _OPIC_TYPE_LABELS.get(key, f"{key} 유형")


def _opic_type_badge_label(opic_type: str) -> str:
    raw = str(opic_type or "").strip()
    if raw.startswith("Keyword"):
        return raw
    key = raw.upper()
    return _OPIC_TYPE_BADGE_LABELS.get(key, _opic_type_label(opic_type))


def _topic_visual_for_id(topic_id: str) -> Dict[str, str]:
    """Topic catalog row for question-screen chips (icon, accent, titles)."""
    tid = str(topic_id or "").strip()
    rows = _topic_rows_by_ids((tid,))
    if rows:
        row = rows[0]
        accent = str(row.get("accent") or "teal").strip().lower()
        if accent not in _TOPIC_ACCENT_NAMES:
            accent = "teal"
        return {
            "title_ko": str(row.get("title_ko") or "").strip() or tid,
            "title_en": str(row.get("title_en") or "").strip(),
            "icon": str(row.get("icon") or "circle").strip() or "circle",
            "accent": accent,
        }
    return {
        "title_ko": _topic_display_title(tid),
        "title_en": "",
        "icon": "circle",
        "accent": "teal",
    }


def _topic_v2_mode() -> str:
    raw = str(st.session_state.get(_KEY_MODE) or "topic").strip()
    return (
        raw
        if raw in ("topic", "roleplay", "advanced", "keyword_constraint")
        else "topic"
    )


def _is_roleplay_mode() -> bool:
    return _topic_v2_mode() == "roleplay"


def _is_advanced_mode() -> bool:
    return _topic_v2_mode() == "advanced"


def _is_keyword_constraint_mode() -> bool:
    return _topic_v2_mode() == "keyword_constraint"


def _topic_v2_entry_source() -> str:
    return str(st.session_state.get(_KEY_ENTRY_SOURCE) or "").strip()


def _is_portal_keyword_entry() -> bool:
    return _topic_v2_entry_source() == ENTRY_SOURCE_PORTAL_KEYWORD


def _return_to_learning_portal() -> None:
    from views.mock_exam import reset_to_learning_portal

    reset_to_learning_portal()
    try:
        st.query_params.clear()
        st.query_params["nav"] = "MOCK"
    except Exception:
        pass


def _goto_keyword_set_select() -> None:
    """Return to keyword topic picker (portal or topic hub)."""
    _log_tpv2_state_clear("ENTER", "_goto_keyword_set_select")
    st.session_state[_KEY_PAGE] = "practice"
    st.session_state[_KEY_STEP] = "select_keyword_set"
    st.session_state[_KEY_MODE] = "topic"
    st.session_state.pop(_KEY_KEYWORD_CONSTRAINT_SET_ID, None)
    st.session_state.pop(_KEY_SINGLE_RETRY, None)
    st.session_state[_KEY_TOPIC] = ""
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_CURRENT_Q] = {}
    st.session_state[_KEY_QUESTIONS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
    _log_tpv2_state_clear("EXIT", "_goto_keyword_set_select")


def _goto_keyword_back() -> None:
    """Keyword practice back: portal entry → set picker; topic hub → select screen."""
    if _is_portal_keyword_entry():
        _goto_keyword_set_select()
    else:
        _goto_topic_select()


def _question_back_handler() -> None:
    if _is_keyword_constraint_mode() and _is_portal_keyword_entry():
        _goto_keyword_set_select()
    elif _is_keyword_constraint_mode():
        _goto_topic_select()
    else:
        _goto_topic_select()


def _session_question_total() -> int:
    qs = _session_question_set()
    if qs:
        return len(qs)
    if _is_keyword_constraint_mode():
        sid = str(st.session_state.get(_KEY_KEYWORD_CONSTRAINT_SET_ID) or "").strip()
        if sid:
            return len(get_keyword_constraint_practice_set(sid))
        return 1
    if _is_advanced_mode():
        return 2
    return 3


def _last_question_index() -> int:
    return max(0, _session_question_total() - 1)


def _is_at_practice_complete(q_idx: int) -> bool:
    return int(q_idx) >= _session_question_total()


def _session_min_questions() -> int:
    if _is_single_question_retry():
        return 1
    if _is_keyword_constraint_mode():
        return _session_question_total()
    if _is_advanced_mode():
        return 2
    return 3


def _topic_v2_progress_total() -> int:
    if _is_keyword_constraint_mode() or _is_advanced_mode() or _is_roleplay_mode():
        return _session_question_total()
    return 3


def _keyword_combo_label(q_idx: int) -> str:
    bank = _bank_question_at_index(q_idx)
    return str(bank.get("combo_ko") or "").strip()


def _advance_after_question(topic: str, q_idx: int) -> None:
    """Move to the next question or the completion sentinel index."""
    last_idx = _last_question_index()
    if q_idx < last_idx:
        nxt = q_idx + 1
        _log_topic_v2_next_question(topic=topic, from_q=q_idx, to_q=nxt)
        st.session_state[_KEY_Q_INDEX] = nxt
        _sync_current_question(nxt)
        st.session_state[_KEY_STEP] = "question"
        return
    done_idx = _session_question_total()
    _log_topic_v2_next_question(topic=topic, from_q=q_idx, to_q=done_idx)
    st.session_state[_KEY_Q_INDEX] = done_idx
    st.session_state[_KEY_STEP] = "saved"


def _is_single_question_retry() -> bool:
    return bool(st.session_state.get(_KEY_SINGLE_RETRY))








def _get_topic_v2_answers_count() -> int:
    try:
        return _answers_count()
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
            "[TOPIC_V2_AFTER_SAVE_COUNTS] answers_count=%s "
            "latest_answer_id=%s latest_status=%s student_answer_len=%s "
            "transcript_len=%s audio_saved=%s",
            _get_topic_v2_answers_count(),
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
















def _bank_question_at_index(q_index: int) -> Dict[str, Any]:
    qs = _session_question_set()
    if 0 <= q_index < len(qs) and isinstance(qs[q_index], dict):
        return dict(qs[q_index])
    return {}


def _keyword_constraint_set_meta(q_idx: int) -> Dict[str, Any]:
    bank = _bank_question_at_index(q_idx)
    return {
        "set_id": str(st.session_state.get(_KEY_KEYWORD_CONSTRAINT_SET_ID) or "").strip(),
        "combo": str(bank.get("combo") or "").strip(),
        "combo_ko": str(bank.get("combo_ko") or "").strip(),
        "question_text": str(bank.get("question_text") or bank.get("en") or "").strip(),
        "ko_helper": str(bank.get("ko_helper") or bank.get("ko") or "").strip(),
        "target_expressions": list(bank.get("target_expressions") or []),
        "banned_expressions": list(bank.get("banned_expressions") or []),
        "patterns": list(bank.get("patterns") or []),
    }














def _persist_topic_v2_answer(row: Dict[str, Any]) -> None:
    """Upsert active answer row for saved screen, feedback, and retry flow."""
    _upsert_topic_v2_answer(row)
    from utils.recording_blob_memory import trim_topic_v2_audio_blobs

    trim_topic_v2_audio_blobs(st.session_state)
    _log_after_save_counts(row)




















def _roleplay_set_title() -> str:
    sid = str(st.session_state.get(_KEY_ROLEPLAY_SET_ID) or "").strip()
    for ent in ROLEPLAY_PRACTICE_SETS:
        if not isinstance(ent, dict):
            continue
        if str(ent.get("set_id") or "").strip() == sid:
            return str(ent.get("title_ko") or "").strip()
    return ""


def _advanced_set_title() -> str:
    sid = str(st.session_state.get(_KEY_ADVANCED_SET_ID) or "").strip()
    if not sid:
        return ""
    for ent in list_advanced_sets():
        if str(ent.get("set_id") or "").strip() == sid:
            return str(ent.get("title_ko") or "").strip()
    return sid


def _keyword_constraint_set_title() -> str:
    sid = str(st.session_state.get(_KEY_KEYWORD_CONSTRAINT_SET_ID) or "").strip()
    if not sid:
        return ""
    for ent in list_keyword_constraint_sets():
        if str(ent.get("set_id") or "").strip() == sid:
            return str(ent.get("title_ko") or "").strip()
    return sid


def _practice_chip_title(topic_id: str) -> str:
    """Header chip label — roleplay/advanced show set name, topic shows catalog title."""
    if _is_roleplay_mode():
        return _roleplay_set_title() or _topic_display_title(topic_id)
    if _is_advanced_mode():
        return _advanced_set_title() or _topic_display_title(topic_id)
    if _is_keyword_constraint_mode():
        return _keyword_constraint_set_title() or _topic_display_title(topic_id)
    return _topic_display_title(topic_id)


def _practice_eyebrow(suffix: str) -> str:
    tid = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    name = _practice_chip_title(tid)
    if _is_keyword_constraint_mode():
        combo = _keyword_combo_label(int(st.session_state.get(_KEY_Q_INDEX) or 0))
        if name and combo:
            return f"{name} · {combo} · {suffix}"
    return f"{name} · {suffix}" if name else suffix


def _back_to_select_label() -> str:
    if _is_roleplay_mode():
        return "롤플레이·주제 선택"
    if _is_advanced_mode():
        return "AL 고난도·주제 선택"
    if _is_keyword_constraint_mode():
        if _is_portal_keyword_entry():
            return "다른 주제 선택"
        return "키워드 표현·주제 선택"
    return "주제 선택으로 돌아가기"


def _other_practice_label() -> str:
    if _is_roleplay_mode():
        return "다른 롤플레이 선택"
    if _is_advanced_mode():
        return "다른 AL 세트 선택"
    if _is_keyword_constraint_mode():
        return "다른 키워드 세트 선택"
    return "다른 주제 선택"


def _practice_screen_title() -> str:
    if _is_roleplay_mode():
        rp_title = _roleplay_set_title()
        return f"롤플레이 연습 · {rp_title}" if rp_title else "롤플레이 연습"
    if _is_advanced_mode():
        adv_title = _advanced_set_title()
        return f"AL 고난도 · {adv_title}" if adv_title else "AL 고난도"
    if _is_keyword_constraint_mode():
        kc_title = _keyword_constraint_set_title()
        return f"키워드 제약 · {kc_title}" if kc_title else "키워드 제약 연습"
    topic_id = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    return f"주제별 연습 · {_topic_display_title(topic_id)}"


def _session_valid_for_practice() -> bool:
    qs = _session_question_set()
    if _is_single_question_retry():
        return len(qs) >= 1
    min_q = _session_min_questions()
    if len(qs) < min_q:
        return False
    if _is_roleplay_mode():
        return bool(str(st.session_state.get(_KEY_ROLEPLAY_SET_ID) or "").strip())
    if _is_advanced_mode():
        return bool(str(st.session_state.get(_KEY_ADVANCED_SET_ID) or "").strip())
    if _is_keyword_constraint_mode():
        return bool(str(st.session_state.get(_KEY_KEYWORD_CONSTRAINT_SET_ID) or "").strip())
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
    if (
        not qs
        and not _is_roleplay_mode()
        and not _is_advanced_mode()
        and not _is_keyword_constraint_mode()
        and _topic_id_valid(topic_id)
    ):
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


def _log_topic_v2_advanced_set(set_id: str, questions: List[Dict[str, Any]]) -> None:
    try:
        types = ",".join(
            str((q or {}).get("opic_type") or "-") for q in questions if isinstance(q, dict)
        )
        logger.info(
            "[TOPIC_V2_ADVANCED_SET] set_id=%s question_count=%s types=%s",
            set_id,
            len(questions),
            types or "-",
        )
    except Exception:
        pass


def _log_topic_v2_keyword_constraint_set(set_id: str, questions: List[Dict[str, Any]]) -> None:
    try:
        types = ",".join(
            str((q or {}).get("opic_type") or "-") for q in questions if isinstance(q, dict)
        )
        logger.info(
            "[TOPIC_V2_KEYWORD_CONSTRAINT_SET] set_id=%s question_count=%s types=%s",
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
    st.session_state.pop(_KEY_ADVANCED_SET_ID, None)
    st.session_state.pop(_KEY_KEYWORD_CONSTRAINT_SET_ID, None)
    st.session_state.pop(_KEY_SINGLE_RETRY, None)
    st.session_state[_KEY_TOPIC] = tid
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_ANSWERS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state[_KEY_FEEDBACK_BY_Q] = {}
    st.session_state[_KEY_PRACTICE_SIG] = uuid.uuid4().hex
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
    st.session_state.pop(_KEY_ADVANCED_SET_ID, None)
    st.session_state.pop(_KEY_KEYWORD_CONSTRAINT_SET_ID, None)
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


def _start_advanced_practice(set_id: str) -> None:
    _log_tpv2_state_clear("ENTER", "_start_advanced_practice")
    sid = str(set_id or "").strip()
    qs = get_advanced_practice_set(sid)
    _log_topic_v2_advanced_set(sid, qs)
    st.session_state[_KEY_MODE] = "advanced"
    st.session_state.pop(_KEY_SINGLE_RETRY, None)
    st.session_state.pop(_KEY_ROLEPLAY_SET_ID, None)
    st.session_state.pop(_KEY_KEYWORD_CONSTRAINT_SET_ID, None)
    st.session_state[_KEY_ADVANCED_SET_ID] = sid
    st.session_state[_KEY_TOPIC] = sid
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_ANSWERS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state[_KEY_FEEDBACK_BY_Q] = {}
    st.session_state[_KEY_PRACTICE_SIG] = uuid.uuid4().hex
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
    if len(qs) < 2:
        st.session_state[_KEY_QUESTIONS] = qs
        st.session_state[_KEY_CURRENT_Q] = {}
        st.session_state[_KEY_STEP] = "insufficient"
        return
    st.session_state[_KEY_QUESTIONS] = qs
    _sync_current_question(0)
    st.session_state[_KEY_STEP] = "question"
    _log_tpv2_state_clear("EXIT", "_start_advanced_practice")


def _start_keyword_constraint_practice(set_id: str) -> None:
    _log_tpv2_state_clear("ENTER", "_start_keyword_constraint_practice")
    sid = str(set_id or "").strip()
    qs = get_keyword_constraint_practice_set(sid)
    _log_topic_v2_keyword_constraint_set(sid, qs)
    if _topic_v2_entry_source() != ENTRY_SOURCE_PORTAL_KEYWORD:
        st.session_state[_KEY_ENTRY_SOURCE] = ENTRY_SOURCE_TOPIC_HUB
    st.session_state[_KEY_MODE] = "keyword_constraint"
    st.session_state.pop(_KEY_SINGLE_RETRY, None)
    st.session_state.pop(_KEY_ROLEPLAY_SET_ID, None)
    st.session_state.pop(_KEY_ADVANCED_SET_ID, None)
    st.session_state[_KEY_KEYWORD_CONSTRAINT_SET_ID] = sid
    st.session_state[_KEY_TOPIC] = sid
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_ANSWERS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state[_KEY_FEEDBACK_BY_Q] = {}
    st.session_state[_KEY_PRACTICE_SIG] = uuid.uuid4().hex
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
    if len(qs) < 1:
        st.session_state[_KEY_QUESTIONS] = qs
        st.session_state[_KEY_CURRENT_Q] = {}
        st.session_state[_KEY_STEP] = "insufficient"
        return
    st.session_state[_KEY_QUESTIONS] = qs
    _sync_current_question(0)
    st.session_state[_KEY_STEP] = "question"
    _log_tpv2_state_clear("EXIT", "_start_keyword_constraint_practice")


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
    duration_seconds: float = 0.0,
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
    wc = int(statuses.get("word_count") or 0)
    try:
        dur = float(duration_seconds or 0.0)
    except (TypeError, ValueError):
        dur = 0.0
    from services.speech_rate_scoring import build_per_answer_speech_metrics, count_content_words

    speech = build_per_answer_speech_metrics(count_content_words(transcript or raw_transcript), dur)
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
        "word_count": wc,
        "duration_seconds": dur,
        "wpm": speech.get("wpm"),
        "wpm_available": speech.get("wpm_available"),
        "words_normalized_90s": speech.get("words_normalized_90s"),
        "speech_rate_level": speech.get("speech_rate_level"),
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


def _commit_topic_v2_recording(
    topic: str,
    q_idx: int,
    q_en: str,
    q_ko: str,
    audio_bytes: bytes,
    mime_type: str,
    *,
    mic_result: Any = None,
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
        duration_seconds=_duration_from_mic_result(mic_result),
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
    _persist_topic_v2_answer(row)
    st.session_state[_KEY_STEP] = "saved"


def _commit_topic_v2_timer_expired(
    topic: str,
    q_idx: int,
    q_en: str,
    q_ko: str,
) -> None:
    """Fallback when the 2-minute timer expires but mic audio is unavailable."""
    stt_result = {
        "ok": False,
        "transcript": "",
        "raw_transcript": "",
        "error_category": "timer_expired",
        "error_message": "answer_time_limit_reached",
    }
    cur_q = st.session_state.get(_KEY_CURRENT_Q)
    opic = str(cur_q.get("opic_type") or "") if isinstance(cur_q, dict) else ""
    row = _build_topic_v2_row_from_mic(
        topic,
        q_idx,
        q_en,
        q_ko,
        b"",
        "audio/webm",
        stt_result,
        opic_type=opic,
        duration_seconds=float(DEFAULT_DURATION_SEC),
    )
    row["source"] = "timer_expired"
    _persist_topic_v2_answer(row)
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
    _persist_topic_v2_answer(row)
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
    _persist_topic_v2_answer(row)
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
        if 0 <= q_idx < _session_question_total():
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
    total = _session_question_total()
    if q_idx < 0 or q_idx >= total:
        return
    last_row = _last_answer_row_for_q(q_idx)
    label = _topic_v2_answer_status_label(last_row)
    title = _practice_chip_title(topic)
    st.caption("**현재 답변 시도**")
    st.caption(f"주제 · {title}")
    st.caption(f"질문 번호 · Q{q_idx + 1}/{total}")
    st.caption(f"답변 상태 · {label}")


def _render_topic_v2_accent_scope(accent: str) -> None:
    """Plant a per-screen accent marker so primary buttons follow the topic
    color (scoped CSS in ``ui/styles.py`` overrides the global teal primary)."""
    key = str(accent or "teal").strip().lower()
    if key not in ("teal", "blue", "purple", "pink", "amber", "coral"):
        key = "teal"
    st.markdown(
        f'<div class="tq-accent-scope tq-accent-scope--{key}" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


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
    from utils.recording_blob_memory import trim_topic_v2_audio_blobs

    trim_topic_v2_audio_blobs(st.session_state, topic=topic)
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


def _normalize_step(raw: Any) -> str:
    s = str(raw or "").strip()
    if s == "history":
        try:
            logger.info("[TOPIC_V2] stale history step — reset to select_topic")
        except Exception:
            pass
        st.session_state[_KEY_PAGE] = "practice"
        st.session_state[_KEY_STEP] = "select_topic"
        return "select_topic"
    if s in _VALID_STEPS:
        return s
    try:
        logger.warning("[TOPIC_V2] unknown step=%r — reset to select_topic", raw)
    except Exception:
        pass
    st.session_state[_KEY_STEP] = "select_topic"
    return "select_topic"










def _topic_v2_router_will_render(step: str) -> str:
    labels = {
        "select_topic": "selection",
        "select_keyword_set": "keyword_selection",
        "question": "question",
        "saved": "saved",
        "feedback": "feedback",
        "pending": "pending",
        "insufficient": "insufficient",
    }
    return labels.get(step, "selection")


def _goto_topic_select() -> None:
    """Return to topic selection without clearing session answers or audio blobs."""
    _log_tpv2_state_clear("ENTER", "_goto_topic_select")
    st.session_state[_KEY_PAGE] = "practice"
    st.session_state[_KEY_STEP] = "select_topic"
    st.session_state[_KEY_MODE] = "topic"
    st.session_state.pop(_KEY_ROLEPLAY_SET_ID, None)
    st.session_state.pop(_KEY_ADVANCED_SET_ID, None)
    st.session_state.pop(_KEY_KEYWORD_CONSTRAINT_SET_ID, None)
    st.session_state.pop(_KEY_ENTRY_SOURCE, None)
    st.session_state.pop(_KEY_SINGLE_RETRY, None)
    st.session_state[_KEY_TOPIC] = ""
    st.session_state[_KEY_Q_INDEX] = 0
    st.session_state[_KEY_CURRENT_Q] = {}
    st.session_state[_KEY_QUESTIONS] = []
    st.session_state[_KEY_FEEDBACK] = None
    st.session_state.pop(_KEY_DRAFT_TRANSCRIPT, None)
    _log_tpv2_state_clear("EXIT", "_goto_topic_select")


def _all_topic_catalog_rows() -> List[Dict[str, Any]]:
    return [
        dict(row)
        for row in TOPIC_PRACTICE_TOPICS
        if isinstance(row, dict) and str(row.get("topic_id") or "").strip()
    ]


def _topic_rows_by_ids(topic_ids: Tuple[str, ...]) -> List[Dict[str, Any]]:
    by_id = {
        str(row.get("topic_id") or "").strip(): dict(row)
        for row in TOPIC_PRACTICE_TOPICS
        if isinstance(row, dict) and str(row.get("topic_id") or "").strip()
    }
    out: List[Dict[str, Any]] = []
    for tid in topic_ids:
        row = by_id.get(str(tid or "").strip())
        if row:
            out.append(row)
    return out


def _filter_topics_by_search(
    rows: List[Dict[str, Any]], query: str
) -> List[Dict[str, Any]]:
    q = str(query or "").strip().lower()
    if not q:
        return list(rows)
    matched: List[Dict[str, Any]] = []
    for row in rows:
        tid = str(row.get("topic_id") or "").strip().lower()
        title_ko = str(row.get("title_ko") or "").strip().lower()
        title_en = str(row.get("title_en") or "").strip().lower()
        if q in tid or q in title_ko or q in title_en:
            matched.append(row)
    return matched


def _topics_for_category_label(category: str) -> List[Dict[str, Any]]:
    label = str(category or "").strip()
    if label not in _TOPIC_V2_CATEGORY_TOPIC_IDS:
        label = "일상"
    if label == "전체":
        return _all_topic_catalog_rows()
    return _topic_rows_by_ids(_TOPIC_V2_CATEGORY_TOPIC_IDS[label])


def _render_topic_v2_empty_state() -> None:
    st.info("해당 주제를 찾을 수 없어요.\n다른 검색어를 입력해 주세요.")


def _render_tp_card_html(
    *,
    title_ko: str,
    title_en: str,
    icon: str,
    accent: str,
) -> None:
    """Shared topic-practice card surface (``.tp-card``) for topic + roleplay grids."""
    svg = TOPIC_ICONS.get(icon, TOPIC_ICONS["circle"])
    sub_html = (
        f'<span class="tp-card-sub">{html.escape(title_en)}</span>'
        if title_en
        else ""
    )
    st.markdown(
        f'<div class="tp-card tp-card--{html.escape(accent)}" '
        f'aria-label="{html.escape(title_ko)}">'
        f'<span class="tp-card-ico">{svg}</span>'
        f'<div class="tp-card-body">'
        f'<span class="tp-card-title">{html.escape(title_ko)}</span>'
        f"{sub_html}"
        "</div>"
        '<span class="tp-card-chevron" aria-hidden="true">'
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
        '<polyline points="9 6 15 12 9 18"></polyline></svg>'
        "</span>"
        "</div>",
        unsafe_allow_html=True,
    )


def _render_topic_practice_card(row: Dict[str, Any], *, key_prefix: str) -> None:
    topic_id = str(row.get("topic_id") or "").strip()
    if not topic_id:
        return
    title_ko = str(row.get("title_ko") or topic_id).strip()
    title_en = str(row.get("title_en") or "").strip()
    icon = str(row.get("icon") or "circle").strip()
    accent = str(row.get("accent") or "teal").strip()
    _render_tp_card_html(
        title_ko=title_ko,
        title_en=title_en,
        icon=icon,
        accent=accent,
    )
    if st.button(
        f"{title_ko} 연습 시작",
        use_container_width=True,
        key=f"{key_prefix}_{topic_id}",
    ):
        _start_topic_practice(topic_id)
        st.rerun()


def _render_topic_card_grid(
    rows: List[Dict[str, Any]], *, key_prefix: str
) -> None:
    if not rows:
        _render_topic_v2_empty_state()
        return
    st.markdown(
        '<div class="tp-cards-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    for i in range(0, len(rows), 2):
        col_left, col_right = st.columns(2)
        pair = rows[i : i + 2]
        for col, row in zip((col_left, col_right), pair):
            with col:
                _render_topic_practice_card(row, key_prefix=key_prefix)


def _render_roleplay_practice_card(ent: Dict[str, Any], *, key_prefix: str) -> None:
    set_id = str(ent.get("set_id") or "").strip()
    if not set_id:
        return
    title_ko = str(ent.get("title_ko") or set_id).strip()
    topic_id = str(ent.get("topic_id") or "").strip()
    visual = _topic_visual_for_id(topic_id)
    title_en = str(visual.get("title_en") or "").strip()
    _render_tp_card_html(
        title_ko=title_ko,
        title_en=title_en,
        icon=str(visual.get("icon") or "circle"),
        accent=str(visual.get("accent") or "teal"),
    )
    if st.button(
        f"{title_ko} 연습 시작",
        use_container_width=True,
        key=f"{key_prefix}_{set_id}",
    ):
        _start_roleplay_practice(set_id)
        st.rerun()


def _render_roleplay_card_grid() -> None:
    sets = [dict(ent) for ent in ROLEPLAY_PRACTICE_SETS if isinstance(ent, dict)]
    if not sets:
        _render_topic_v2_empty_state()
        return
    st.markdown(
        '<div class="tp-cards-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    for i in range(0, len(sets), 2):
        col_left, col_right = st.columns(2)
        pair = sets[i : i + 2]
        for col, ent in zip((col_left, col_right), pair):
            with col:
                _render_roleplay_practice_card(ent, key_prefix="topic_v2_roleplay")


def _render_advanced_practice_card(ent: Dict[str, Any], *, key_prefix: str) -> None:
    set_id = str(ent.get("set_id") or "").strip()
    if not set_id:
        return
    title_ko = str(ent.get("title_ko") or set_id).strip()
    visual = _topic_visual_for_id(set_id)
    title_en = str(visual.get("title_en") or "Comparison · News/Issue").strip()
    _render_tp_card_html(
        title_ko=title_ko,
        title_en=title_en,
        icon=str(visual.get("icon") or "circle"),
        accent=str(visual.get("accent") or "purple"),
    )
    if st.button(
        f"{title_ko} AL 연습",
        use_container_width=True,
        key=f"{key_prefix}_{set_id}",
    ):
        _start_advanced_practice(set_id)
        st.rerun()


def _render_advanced_card_grid() -> None:
    sets = list_advanced_sets()
    if not sets:
        _render_topic_v2_empty_state()
        return
    st.markdown(
        '<div class="tp-cards-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    for i in range(0, len(sets), 2):
        col_left, col_right = st.columns(2)
        pair = sets[i : i + 2]
        for col, ent in zip((col_left, col_right), pair):
            with col:
                _render_advanced_practice_card(ent, key_prefix="topic_v2_advanced")


def _render_keyword_constraint_practice_card(ent: Dict[str, Any], *, key_prefix: str) -> None:
    set_id = str(ent.get("set_id") or "").strip()
    if not set_id:
        return
    title_ko = str(ent.get("title_ko") or set_id).strip()
    visual = _topic_visual_for_id(set_id)
    _render_tp_card_html(
        title_ko=title_ko,
        title_en="",
        icon=str(visual.get("icon") or "circle"),
        accent=str(visual.get("accent") or "amber"),
    )
    if st.button(
        f"{title_ko} 5콤보 시작",
        use_container_width=True,
        key=f"{key_prefix}_{set_id}",
    ):
        _start_keyword_constraint_practice(set_id)
        st.rerun()


def _render_select_keyword_set() -> None:
    if _is_portal_keyword_entry():
        render_top_bar(
            "키워드 표현 연습",
            on_back=_return_to_learning_portal,
            back_key="topic_v2_keyword_set_portal",
            eyebrow="주제 선택",
        )
    else:
        render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow="키워드 표현 연습")
    st.markdown("### 키워드 표현 연습")
    st.caption(
        "주제 하나를 고르면 묘사 → 루틴 → 경험 → 세부경험 → 롤플 5콤보를 순서대로 풀어요."
    )
    _render_keyword_constraint_card_grid()


def _render_keyword_constraint_card_grid() -> None:
    groups = list_keyword_constraint_sets_by_category()
    if not groups:
        st.caption("준비된 키워드 제약 세트가 없습니다.")
        return
    st.markdown(
        '<div class="tp-cards-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    for group in groups:
        category = str(group.get("category") or "").strip()
        sets = group.get("sets") if isinstance(group.get("sets"), list) else []
        if not category or not sets:
            continue
        st.markdown(f"#### {html.escape(category)}")
        for i in range(0, len(sets), 2):
            col_left, col_right = st.columns(2)
            pair = sets[i : i + 2]
            for col, ent in zip((col_left, col_right), pair):
                with col:
                    if isinstance(ent, dict):
                        _render_keyword_constraint_practice_card(
                            ent,
                            key_prefix="topic_v2_keyword_constraint",
                        )


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
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow="주제 선택")
    st.markdown("### 주제별 연습")

    if _KEY_TOPIC_CATEGORY not in st.session_state:
        st.session_state[_KEY_TOPIC_CATEGORY] = "일상"
    if st.session_state.get(_KEY_TOPIC_CATEGORY) not in _TOPIC_V2_CATEGORY_LABELS:
        st.session_state[_KEY_TOPIC_CATEGORY] = "일상"

    search_query = st.text_input(
        "주제 검색",
        placeholder="주제를 검색해 보세요. 예: 카페, 영화, 여행",
        key=_KEY_TOPIC_SEARCH,
        label_visibility="collapsed",
    )
    search_active = bool(str(search_query or "").strip())

    if search_active:
        results = _filter_topics_by_search(_all_topic_catalog_rows(), search_query)
        st.markdown("#### 검색 결과")
        _render_topic_card_grid(results, key_prefix="topic_v2_search")
    else:
        st.markdown("#### 추천 주제")
        recommended = _topic_rows_by_ids(_RECOMMENDED_TOPIC_IDS)
        _render_topic_card_grid(recommended, key_prefix="topic_v2_rec")

        st.markdown("#### 카테고리")
        category = st.radio(
            "카테고리",
            list(_TOPIC_V2_CATEGORY_LABELS),
            horizontal=True,
            key=_KEY_TOPIC_CATEGORY,
            label_visibility="collapsed",
        )
        st.markdown("#### 선택한 카테고리 주제")
        category_topics = _topics_for_category_label(str(category or "일상"))
        _render_topic_card_grid(category_topics, key_prefix="topic_v2_cat")

    st.divider()
    st.markdown("#### 키워드 표현 연습")
    st.caption("목표·금지·패턴 — 주제당 5콤보(묘사→루틴→경험→세부→롤플)")
    if not st.session_state.get(_KEY_KEYWORD_CONSTRAINT_EXPAND):
        if st.button(
            "키워드 제약 세트 보기",
            use_container_width=True,
            key="topic_v2_show_keyword_constraint",
        ):
            st.session_state[_KEY_KEYWORD_CONSTRAINT_EXPAND] = True
            st.rerun()
    else:
        if st.button(
            "키워드 제약 세트 접기",
            use_container_width=True,
            key="topic_v2_hide_keyword_constraint",
        ):
            st.session_state[_KEY_KEYWORD_CONSTRAINT_EXPAND] = False
            st.rerun()
        _render_keyword_constraint_card_grid()

    st.divider()
    st.markdown("#### AL 고난도")
    st.caption("최상위 도전 · 실전 14·15번 유형(Comparison · News/Issue) 2문항 세트")
    if not st.session_state.get(_KEY_ADVANCED_EXPAND):
        if st.button(
            "AL 고난도 세트 보기",
            use_container_width=True,
            key="topic_v2_show_advanced",
        ):
            st.session_state[_KEY_ADVANCED_EXPAND] = True
            st.rerun()
    else:
        if st.button(
            "AL 고난도 세트 접기",
            use_container_width=True,
            key="topic_v2_hide_advanced",
        ):
            st.session_state[_KEY_ADVANCED_EXPAND] = False
            st.rerun()
        _render_advanced_card_grid()

    st.divider()
    st.markdown("#### 롤플레이 연습")
    if not st.session_state.get(_KEY_ROLEPLAY_EXPAND):
        if st.button(
            "롤플레이 세트 보기",
            use_container_width=True,
            key="topic_v2_show_roleplay",
        ):
            st.session_state[_KEY_ROLEPLAY_EXPAND] = True
            st.rerun()
    else:
        if st.button(
            "롤플레이 세트 접기",
            use_container_width=True,
            key="topic_v2_hide_roleplay",
        ):
            st.session_state[_KEY_ROLEPLAY_EXPAND] = False
            st.rerun()
        _render_roleplay_card_grid()




def build_topic_practice_header_html(
    topic_id: str,
    q_idx: int,
    *,
    total_questions: int = 3,
    include_screen_marker: bool = False,
    chip_title: Optional[str] = None,
    badge_label: str = "",
) -> str:
    """Topic chip row + ``.mx-progress`` strip — question and saved screens."""
    from components.exam_question_screen import build_progress_segments_html

    visual = _topic_visual_for_id(topic_id)
    accent = html.escape(visual["accent"])
    icon_name = visual["icon"]
    svg = TOPIC_ICONS.get(icon_name, TOPIC_ICONS["circle"])
    title_ko = html.escape((chip_title or visual["title_ko"]).strip() or visual["title_ko"])
    total = max(int(total_questions), 1)
    current = min(int(q_idx) + 1, total)
    progress_html = build_progress_segments_html(
        current,
        total,
        badge_label=badge_label,
    )
    marker = (
        '<div class="tq-screen-marker" aria-hidden="true"></div>'
        if include_screen_marker
        else ""
    )
    return (
        marker
        + '<div class="tq-header">'
        + f'<div class="tq-topic-chip tq-topic-chip--{accent}">'
        + f'<span class="tq-topic-chip-ico">{svg}</span>'
        + f'<span class="tq-topic-chip-name">{title_ko}</span>'
        + "</div>"
        + "</div>"
        + progress_html
    )


def _keyword_constraint_constraints_html(bank_row: Dict[str, Any]) -> str:
    """Target / banned / pattern cards shown under the question (keyword_constraint mode)."""
    raw_targets = bank_row.get("target_expressions") or []
    targets: List[Dict[str, str]] = []
    for item in raw_targets:
        if isinstance(item, dict):
            expr = str(item.get("expr") or "").strip()
            if expr:
                targets.append(
                    {
                        "expr": expr,
                        "ko": str(item.get("ko") or "").strip(),
                    }
                )
        else:
            expr = str(item or "").strip()
            if expr:
                targets.append({"expr": expr, "ko": ""})
    banned = [
        str(x).strip()
        for x in (bank_row.get("banned_expressions") or [])
        if str(x).strip()
    ]
    patterns = [
        str(x).strip()
        for x in (bank_row.get("patterns") or [])
        if str(x).strip()
    ]
    if not targets and not banned and not patterns:
        return ""

    combo_ko = str(bank_row.get("combo_ko") or "").strip()
    combo_head = (
        f'<div class="tq-kc-combo-label">{html.escape(combo_ko)} · 표현 제약</div>'
        if combo_ko
        else ""
    )

    def _chip_list(items: List[str], *, strike: bool = False) -> str:
        if not items:
            return '<p class="tq-kc-empty">—</p>'
        style = ' style="text-decoration:line-through;"' if strike else ""
        chips = "".join(
            f'<span class="tq-kc-chip"{style}>{html.escape(item)}</span>'
            for item in items
        )
        return f'<div class="tq-kc-chips">{chips}</div>'

    def _target_chip_list(items: List[Dict[str, str]]) -> str:
        if not items:
            return '<p class="tq-kc-empty">—</p>'
        chips: List[str] = []
        for item in items:
            expr = html.escape(item.get("expr") or "")
            ko = html.escape(item.get("ko") or "")
            ko_part = (
                f'<span class="tq-kc-chip-ko">{ko}</span>' if ko else ""
            )
            chips.append(
                f'<span class="tq-kc-chip tq-kc-chip--target">'
                f"{expr}{ko_part}</span>"
            )
        return f'<div class="tq-kc-chips">{"".join(chips)}</div>'

    return (
        '<div class="tq-kc-panel" role="region" aria-label="표현 제약">'
        f"{combo_head}"
        '<div class="tq-kc-block tq-kc-block--target">'
        '<div class="tq-kc-label">목표 표현</div>'
        f"{_target_chip_list(targets)}"
        "</div>"
        '<div class="tq-kc-block tq-kc-block--banned">'
        '<div class="tq-kc-label">금지 표현</div>'
        f"{_chip_list(banned, strike=True)}"
        "</div>"
        '<div class="tq-kc-block tq-kc-block--pattern">'
        '<div class="tq-kc-label">확장 패턴</div>'
        f"{_chip_list(patterns)}"
        "</div>"
        "</div>"
        "<style>"
        ".tq-kc-panel{display:flex;flex-direction:column;gap:10px;margin:0 0 14px 0;}"
        ".tq-kc-combo-label{font-size:13px;font-weight:700;color:#0f766e;margin:0 0 2px 0;}"
        ".tq-kc-block{border-radius:12px;padding:12px 14px;border:0.5px solid transparent;}"
        ".tq-kc-block--target{background:#ecfdf5;border-color:#99f6e4;}"
        ".tq-kc-block--banned{background:#fff7ed;border-color:#fdba74;}"
        ".tq-kc-block--pattern{background:#f5f3ff;border-color:#c4b5fd;}"
        ".tq-kc-label{font-size:12px;font-weight:700;margin:0 0 8px 0;color:#334155;}"
        ".tq-kc-block--target .tq-kc-label{color:#0f766e;}"
        ".tq-kc-block--banned .tq-kc-label{color:#c2410c;}"
        ".tq-kc-block--pattern .tq-kc-label{color:#5b21b6;}"
        ".tq-kc-chips{display:flex;flex-wrap:wrap;gap:6px;}"
        ".tq-kc-chip{display:inline-block;padding:4px 10px;border-radius:999px;"
        "font-size:13px;font-weight:600;background:rgba(255,255,255,0.72);color:#0f172a;}"
        ".tq-kc-block--target .tq-kc-chip{color:#0f766e;}"
        ".tq-kc-chip-ko{margin-left:5px;font-size:11px;font-weight:500;color:#94a3b8;}"
        ".tq-kc-block--banned .tq-kc-chip{color:#c2410c;}"
        ".tq-kc-block--pattern .tq-kc-chip{color:#5b21b6;}"
        ".tq-kc-empty{margin:0;font-size:13px;color:#64748b;}"
        "</style>"
    )


def _render_topic_question_shell_html(
    *,
    topic_id: str,
    q: Dict[str, str],
    q_idx: int,
    total_questions: int,
) -> str:
    visual = _topic_visual_for_id(topic_id)
    badge = _opic_type_badge_label(str(q.get("opic_type") or ""))
    en = html.escape(str(q.get("en") or ""))
    ko_raw = str(q.get("ko") or "").strip()
    ko_block = (
        f'<p class="tq-question-ko">{html.escape(ko_raw)}</p>' if ko_raw else ""
    )
    header = build_topic_practice_header_html(
        topic_id,
        q_idx,
        total_questions=total_questions,
        include_screen_marker=True,
        chip_title=_practice_chip_title(topic_id),
        badge_label=badge,
    )
    return (
        header
        + f'<div class="mx-question-card tq-card">'
        + f'<p class="mx-question-topic tq-question">{en}</p>'
        f"{ko_block}"
        f"</div>"
    )


_TOPIC_WAVE_BAR_HEIGHTS_PX = (
    14, 18, 22, 28, 32, 36, 34, 36, 34, 32, 28, 22, 18, 16, 14
)


def _topic_wave_bars_html() -> str:
    """15 static bars — fixed heights for a resting waveform silhouette."""
    bars = "".join(
        f'<span class="tq-wave-bar" style="height:{h}px"></span>'
        for h in _TOPIC_WAVE_BAR_HEIGHTS_PX
    )
    return f'<div class="tq-wave-bars" aria-hidden="true">{bars}</div>'


def _render_topic_wave_mic_observer() -> None:
    """Read-only poll of mic iframe button label; toggles .tq-wave-slot--active on parent."""
    components.html(
        """
        <script>
        (function () {
          var POLL_MS = 280;
          var STOP_HINT = "녹음 완료";
          var timer = null;

          function parentDoc() {
            try {
              if (window.parent && window.parent.document) {
                return window.parent.document;
              }
            } catch (e) { /* cross-origin */ }
            return null;
          }

          function findMicIframe(doc) {
            try {
              var ifr = doc.querySelector('iframe[src*="streamlit_mic_recorder"]');
              if (ifr) return ifr;
              var hosts = doc.querySelectorAll(
                '[data-testid="stCustomComponentV1"], [data-testid="stCustomComponent"]'
              );
              for (var i = 0; i < hosts.length; i++) {
                var inner = hosts[i].querySelector("iframe");
                if (!inner) continue;
                var src = inner.getAttribute("src") || "";
                if (src.indexOf("streamlit_mic_recorder") >= 0) return inner;
              }
            } catch (e) { /* ignore */ }
            return null;
          }

          function micShowsRecording(doc) {
            try {
              var ifr = findMicIframe(doc);
              if (!ifr) return false;
              var idoc = ifr.contentDocument;
              if (!idoc) return false;
              var btn = idoc.querySelector("button");
              if (!btn) return false;
              var text = (btn.innerText || btn.textContent || "").trim();
              return text.indexOf(STOP_HINT) >= 0;
            } catch (e) {
              return false;
            }
          }

          function tick() {
            try {
              var doc = parentDoc();
              if (!doc || !doc.querySelector(".tq-screen-marker")) return;
              var slot = doc.querySelector(".tq-wave-slot");
              if (!slot) return;
              slot.classList.toggle("tq-wave-slot--active", micShowsRecording(doc));
            } catch (e) { /* ignore */ }
          }

          function start() {
            if (timer) clearInterval(timer);
            tick();
            timer = setInterval(tick, POLL_MS);
          }

          if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", start);
          } else {
            start();
          }
        })();
        </script>
        """,
        height=0,
    )


def _render_topic_answer_card_top_html(topic_id: str) -> str:
    visual = _topic_visual_for_id(topic_id)
    accent = html.escape(visual["accent"])
    mic_svg = TOPIC_ICONS.get("microphone-2", TOPIC_ICONS["circle"])
    desc = (
        "답변 시작을 누르고 영어로 말해 보세요. "
        "녹음이 끝나면 AI가 텍스트로 인식합니다."
    )
    return (
        f'<div class="mx-record-stage mx-record-stage--v2">'
        f'<p class="mx-record-eyebrow">답변 녹음</p>'
        f'<div class="tq-answer-card-top">'
        f'<div class="tq-answer-head">'
        f'<span class="tq-answer-ico tq-answer-ico--{accent}">{mic_svg}</span>'
        f'<span class="tq-answer-title">말로 답변하기</span>'
        f"</div>"
        f'<p class="tq-answer-desc">{html.escape(desc)}</p>'
        f'<div class="tq-wave-slot tq-wave-slot--{accent}">'
        f"{_topic_wave_bars_html()}"
        f"</div>"
        f"</div>"
        f"</div>"
    )


def _render_question() -> None:
    topic_id = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    _log_topic_v2_mode(step="question", q_idx=q_idx)
    if not _session_valid_for_practice():
        _goto_topic_select()
        st.rerun()
        return

    qs = _session_question_set()
    min_questions = _session_min_questions()
    if len(qs) < min_questions:
        st.session_state[_KEY_STEP] = "insufficient"
        st.rerun()
        return

    q = _sync_current_question(q_idx)
    if not isinstance(q, dict) or not (q.get("en") or "").strip():
        _goto_topic_select()
        st.rerun()
        return

    render_top_bar(
        "주제별 연습",
        on_back=_question_back_handler,
        back_key="topic_v2_question",
        eyebrow=_practice_eyebrow("질문"),
    )
    st.markdown(
        _render_topic_question_shell_html(
            topic_id=topic_id,
            q=q,
            q_idx=q_idx,
            total_questions=len(qs),
        ),
        unsafe_allow_html=True,
    )

    bank_row = _bank_question_at_index(q_idx)
    if _is_keyword_constraint_mode():
        kc_html = _keyword_constraint_constraints_html(bank_row)
        if kc_html:
            st.markdown(kc_html, unsafe_allow_html=True)

    if _is_advanced_mode() or _is_keyword_constraint_mode():
        question_id = str(
            bank_row.get("audio_id") or bank_row.get("id") or ""
        ).strip()
    else:
        question_id = str(bank_row.get("id") or "").strip()
    if question_id:
        mp3_path = _QUESTION_AUDIO_DIR / f"{question_id}.mp3"
        if mp3_path.is_file():
            try:
                audio_bytes = mp3_path.read_bytes()
            except OSError:
                audio_bytes = b""
            if len(audio_bytes) >= 64:
                topic_accent = _topic_visual_for_id(topic_id)["accent"]
                render_exam_question_audio_player(
                    audio_bytes,
                    "audio/mp3",
                    f"topic_{question_id}",
                    int(q_idx),
                    max_plays=2,
                    accent=topic_accent,
                )

    st.markdown(_render_topic_answer_card_top_html(topic_id), unsafe_allow_html=True)
    topic_accent = str(_topic_visual_for_id(topic_id).get("accent") or "teal")
    timer_id = build_answer_timer_id("topic_v2", topic_id, str(q_idx))
    render_answer_countdown_timer(
        timer_id=timer_id,
        accent=topic_accent,
        duration_sec=DEFAULT_DURATION_SEC,
    )
    _render_topic_wave_mic_observer()

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
        dismiss_answer_timer_signal(timer_id)
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
                    mic_result=mic_result,
                )
            st.rerun()

    q_en = str(q.get("en") or "")
    q_ko = str(q.get("ko") or "")

    def _commit_from_timer(audio_bytes: bytes, mime_type: str, mic_payload: Any) -> None:
        with st.spinner("답변을 저장하고 음성을 인식하고 있어요…"):
            _commit_topic_v2_recording(
                topic_id,
                q_idx,
                q_en,
                q_ko,
                audio_bytes,
                mime_type or "audio/webm",
                mic_result=mic_payload,
            )

    if handle_answer_timer_expiry(
        timer_id,
        mic_result=mic_result,
        extract_audio=lambda: _extract_topic_v2_audio_bytes(None, mic_key=""),
        commit_audio=_commit_from_timer,
        commit_empty=lambda: _commit_topic_v2_timer_expired(topic_id, q_idx, q_en, q_ko),
    ):
        st.rerun()

    # Text fallback expander is hidden: st.text_area + this flow surfaced internal keys as "key..." for
    # some students. Re-enable with st.text_area("영어 답변을 입력해 주세요", key=text_draft_key, ...) and
    # _commit_topic_v2_manual_text_draft(topic, q_idx, q, draft).


def _render_saved_normal(topic: str, q_idx: int) -> None:
    render_top_bar(
        "주제별 연습",
        back_href="?nav=MOCK",
        eyebrow=_practice_eyebrow("저장"),
    )
    st.markdown(
        build_topic_practice_header_html(
            topic,
            q_idx,
            total_questions=_topic_v2_progress_total(),
            include_screen_marker=False,
            chip_title=_practice_chip_title(topic),
        ),
        unsafe_allow_html=True,
    )

    accent = str(_topic_visual_for_id(topic).get("accent") or "teal")
    _render_topic_v2_accent_scope(accent)
    render_saved_status(accent=accent)

    last_row = _last_answer_row_for_q(q_idx)
    tr = _transcript_from_row(last_row) if last_row else ""
    ab, audio_mime = _get_topic_v2_audio_blob(topic, q_idx)
    has_audio = len(ab) > 0
    is_manual = bool(
        last_row
        and (
            str(last_row.get("stt_status") or "") == "manual_text"
            or str(last_row.get("source") or "") == "manual_text"
        )
    )

    if has_audio:
        render_saved_recording_header(accent=accent)
        render_recording_playback_player(
            ab,
            audio_mime or "audio/webm",
            f"topic_{topic}_{q_idx}",
            accent=accent,
            label="",
            show_progress=True,
        )
    elif is_manual:
        st.caption("텍스트 답변으로 저장되었습니다.")

    render_saved_transcript(transcript=tr, accent=accent)

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
    aid = _feedback_answer_id(last_row, topic=topic, q_idx=q_idx)
    fb_disabled, fb_label = _feedback_request_button_state(aid)
    _render_feedback_guard_notice()

    st.markdown('<div class="tq-saved-actions" aria-hidden="true"></div>', unsafe_allow_html=True)

    if _is_single_question_retry():
        if can_ai:
            if st.button(
                fb_label,
                type="primary",
                use_container_width=True,
                key="topic_v2_request_ai_feedback",
                disabled=fb_disabled,
            ):
                _run_topic_v2_feedback_request(topic, q_idx, last_row)
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "같은 질문 다시 말하기",
                type="secondary",
                use_container_width=True,
                key="topic_v2_retry_same",
            ):
                _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
                st.session_state[_KEY_FEEDBACK] = None
                st.session_state[_KEY_STEP] = "question"
                st.rerun()
        with c2:
            if st.button(
                _back_to_select_label(),
                type="secondary",
                use_container_width=True,
                key="topic_v2_back_select",
            ):
                if _is_keyword_constraint_mode():
                    _goto_keyword_back()
                else:
                    _goto_topic_select()
                st.rerun()
        return

    if can_ai:
        if st.button(
            fb_label,
            type="primary",
            use_container_width=True,
            key="topic_v2_request_ai_feedback",
            disabled=fb_disabled,
        ):
            _run_topic_v2_feedback_request(topic, q_idx, last_row)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            "다음 질문",
            type="secondary",
            use_container_width=True,
            key="topic_v2_next_q",
        ):
            _advance_after_question(topic, q_idx)
            st.rerun()
    with c2:
        if st.button(
            "같은 질문 다시 말하기",
            type="secondary",
            use_container_width=True,
            key="topic_v2_retry_same",
        ):
            _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
            st.session_state[_KEY_FEEDBACK] = None
            st.session_state[_KEY_STEP] = "question"
            st.rerun()
    with c3:
        if st.button(
            _back_to_select_label(),
            type="secondary",
            use_container_width=True,
            key="topic_v2_back_select",
        ):
            if _is_keyword_constraint_mode():
                _goto_keyword_back()
            else:
                _goto_topic_select()
            st.rerun()


def _run_topic_v2_feedback_request(
    topic: str, q_idx: int, last_row: Optional[Dict[str, Any]]
) -> None:
    row_in = last_row if isinstance(last_row, dict) else {}
    aid = _feedback_answer_id(row_in, topic=topic, q_idx=q_idx)
    allowed, block_msg = _can_request_topic_v2_feedback(aid)
    if not allowed:
        st.session_state[_KEY_FB_NOTICE] = block_msg
        try:
            logger.info(
                "[TOPIC_V2_FEEDBACK] blocked answer_id=%s reason=cooldown_or_limit",
                aid,
            )
        except Exception:
            pass
        st.rerun()
        return

    st.session_state[_KEY_FB_IN_FLIGHT] = True
    st.session_state.pop(_KEY_FB_NOTICE, None)
    result: Dict[str, Any]
    spinner_msg = (
        "키워드 표현 피드백을 만들고 있어요…"
        if _is_keyword_constraint_mode()
        else "AI 짧은 피드백을 만들고 있어요…"
    )
    try:
        with st.spinner(spinner_msg):
            if _is_keyword_constraint_mode():
                from services.keyword_constraint_analysis import (
                    analyze_keyword_constraint_answer,
                )

                set_meta = _keyword_constraint_set_meta(q_idx)
                result = analyze_keyword_constraint_answer(dict(row_in), set_meta)
            else:
                from services.topic_practice_v2_analysis import (
                    analyze_topic_practice_v2_answer,
                )

                result = analyze_topic_practice_v2_answer(dict(row_in))
    except Exception as exc:
        try:
            logger.exception("[TOPIC_V2_FEEDBACK] analyze_failed: %s", exc)
        except Exception:
            pass
        if _is_keyword_constraint_mode():
            result = {
                "ok": False,
                "summary": "",
                "coaching": "",
                "naturalness_note": "",
                "patterns_used": False,
                "pattern_quote": "",
                "targets": [],
                "banned": [],
                "target_used_count": 0,
                "target_total": 0,
                "banned_hit_count": 0,
                "error_category": "exception",
                "error_message": _TOPIC_V2_FEEDBACK_FAIL_USER_MESSAGE,
            }
        else:
            result = {
                "ok": False,
                "answer_level": "",
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
    finally:
        st.session_state[_KEY_FB_IN_FLIGHT] = False

    st.session_state[_KEY_FEEDBACK] = result
    if result.get("ok"):
        _clear_feedback_guard(aid)
        _stash_topic_v2_feedback_for_q(q_idx, result)
        _log_topic_v2_feedback_ready(topic=topic, q_idx=q_idx, answer_id=aid)
        st.session_state[_KEY_STEP] = "feedback"
    else:
        cat = str(result.get("error_category") or "api_error")
        _register_feedback_failure(cat, aid)
        st.session_state[_KEY_STEP] = "pending"
    st.rerun()


def _stash_topic_v2_feedback_for_q(q_idx: int, result: Dict[str, Any]) -> None:
    """Keep per-question short feedback for history sync (session-only)."""
    if not isinstance(result, dict) or not result.get("ok"):
        return
    log = st.session_state.get(_KEY_FEEDBACK_BY_Q)
    if not isinstance(log, dict):
        log = {}
    entry: Dict[str, Any] = {"ok": True}
    if _is_keyword_constraint_mode():
        entry.update(
            {
                "summary": result.get("summary"),
                "coaching": result.get("coaching"),
                "naturalness_note": result.get("naturalness_note"),
                "patterns_used": result.get("patterns_used"),
                "pattern_quote": result.get("pattern_quote"),
                "targets": result.get("targets"),
                "banned": result.get("banned"),
                "target_used_count": result.get("target_used_count"),
                "target_total": result.get("target_total"),
                "banned_hit_count": result.get("banned_hit_count"),
            }
        )
    else:
        entry.update(
            {
                "answer_level": result.get("answer_level"),
                "summary": result.get("summary"),
                "strength": result.get("strength"),
                "correction_focus": result.get("correction_focus"),
                "better_expression": result.get("better_expression"),
                "upgrade_sample": result.get("upgrade_sample"),
                "keyword_drill": result.get("keyword_drill"),
                "practice_mission": result.get("practice_mission"),
            }
        )
    log[int(q_idx)] = entry
    st.session_state[_KEY_FEEDBACK_BY_Q] = log


def _topic_v2_short_feedback_for_q(q_idx: int) -> Optional[Dict[str, Any]]:
    log = st.session_state.get(_KEY_FEEDBACK_BY_Q)
    if isinstance(log, dict):
        fb = log.get(int(q_idx))
        if isinstance(fb, dict) and fb.get("ok"):
            return fb
    return None


def build_topic_v2_history_payload(topic_id: str) -> Dict[str, Any]:
    """Assemble practice_history content from topic_v2_answers + per-q feedback."""
    from utils.local_profile import iso_now

    tid = str(topic_id or "").strip()
    title = _topic_display_title(tid)
    results: List[Dict[str, Any]] = []
    feedback_bits: List[str] = []

    for q_idx in range(3):
        row = _last_answer_row_for_q(q_idx) or {}
        student, transcript = _answer_text_fields_from_row(row) if row else ("", "")
        text = (transcript or student or "").strip()
        fb = _topic_v2_short_feedback_for_q(q_idx)
        fb_summary = str(fb.get("summary") or "").strip() if fb else ""
        if fb_summary:
            feedback_bits.append(fb_summary)
        results.append(
            {
                "question_index": q_idx,
                "question": str(row.get("en") or "").strip(),
                "topic": str(row.get("en") or "").strip()[:80],
                "transcript": text,
                "answer_text": text,
                "feedback": fb_summary,
                "short_feedback": fb,
                "opic_type": str(row.get("opic_type") or "").strip(),
                "status": str(row.get("status") or "").strip(),
                "answer_id": str(row.get("answer_id") or "").strip(),
            }
        )

    if feedback_bits:
        summary = feedback_bits[0] if len(feedback_bits) == 1 else " / ".join(feedback_bits[:2])
    else:
        summary = f"{title} 주제 3문항 연습을 완료했어요."

    saved_n = sum(1 for r in results if str(r.get("transcript") or "").strip())

    return {
        "ok": True,
        "report_source": "topic_practice_v2",
        "topic_id": tid,
        "topic_title": title,
        "completed_at": iso_now(),
        "summary": summary,
        "results": results,
        "answers_count": saved_n,
    }


def _maybe_persist_topic_v2_history(topic_id: str) -> None:
    """Logged-in users: append one practice_history row (idempotent per practice sig)."""
    if _is_roleplay_mode() or _is_advanced_mode() or _is_keyword_constraint_mode():
        return
    tid = str(topic_id or "").strip()
    if not tid or not _topic_id_valid(tid):
        return
    if _topic_v2_answers_count() < 3:
        return
    sig = str(st.session_state.get(_KEY_PRACTICE_SIG) or "").strip()
    if not sig:
        sig = f"{tid}_fallback"
    try:
        from utils.history_sync import save_topic_report

        payload = build_topic_v2_history_payload(tid)
        save_topic_report(
            payload,
            topic_title=_topic_display_title(tid),
            sig=sig,
        )
    except Exception:
        try:
            logger.exception("[TOPIC_V2_HISTORY] save failed topic=%s", tid)
        except Exception:
            pass


def _render_saved_complete(topic: str) -> None:
    _maybe_persist_topic_v2_history(topic)
    title = _topic_display_title(topic)
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=f"{title} · 완료")
    _render_topic_v2_accent_scope(
        str(_topic_visual_for_id(topic).get("accent") or "teal")
    )
    st.markdown("### 이 주제 연습을 완료했어요.")
    if st.button("같은 주제 다시 연습", type="primary", use_container_width=True, key="topic_v2_restart_same_topic"):
        _start_topic_practice(topic)
        st.rerun()
    if st.button(_other_practice_label(), use_container_width=True, key="topic_v2_pick_other_topic"):
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
    if _is_at_practice_complete(q_idx):
        if _is_roleplay_mode():
            _render_roleplay_complete()
        elif _is_advanced_mode():
            _render_advanced_complete()
        elif _is_keyword_constraint_mode():
            _render_keyword_constraint_complete()
        else:
            _render_saved_complete(topic)
    else:
        _render_saved_normal(topic, q_idx)


def _render_roleplay_complete() -> None:
    topic = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    title = _roleplay_set_title() or "롤플레이"
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=_practice_eyebrow("완료"))
    _render_topic_v2_accent_scope(
        str(_topic_visual_for_id(topic).get("accent") or "teal")
    )
    st.markdown("### 롤플레이 세트를 완료했어요.")
    st.caption("Q6–Q8 세트 3문항을 모두 마쳤어요.")
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


def _render_advanced_complete() -> None:
    render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=_practice_eyebrow("완료"))
    _render_topic_v2_accent_scope(
        str(_topic_visual_for_id(str(st.session_state.get(_KEY_TOPIC) or "")).get("accent") or "teal")
    )
    st.markdown("### AL 고난도 세트를 완료했어요.")
    st.caption("Comparison · News/Issue 2문항을 모두 마쳤어요.")
    set_id = str(st.session_state.get(_KEY_ADVANCED_SET_ID) or "").strip()
    if st.button(
        "같은 세트 다시 하기",
        type="primary",
        use_container_width=True,
        key="topic_v2_restart_same_advanced",
    ):
        if set_id:
            _start_advanced_practice(set_id)
        st.rerun()
    if st.button(
        "다른 AL 세트 선택",
        use_container_width=True,
        key="topic_v2_pick_other_advanced",
    ):
        _goto_topic_select()
        st.rerun()
    if st.button(
        "주제별 연습으로 돌아가기",
        use_container_width=True,
        key="topic_v2_back_to_topic_practice_advanced",
    ):
        _goto_topic_select()
        st.rerun()


def _render_keyword_constraint_complete() -> None:
    if _is_portal_keyword_entry():
        render_top_bar(
            "키워드 표현 연습",
            on_back=_return_to_learning_portal,
            back_key="topic_v2_keyword_portal_complete",
            eyebrow=_practice_eyebrow("완료"),
        )
    else:
        render_top_bar("주제별 연습", back_href="?nav=MOCK", eyebrow=_practice_eyebrow("완료"))
    _render_topic_v2_accent_scope("teal")
    st.markdown("### 키워드 표현 연습을 완료했어요.")
    total = _session_question_total()
    st.caption(f"묘사→루틴→경험→세부경험→롤플 {total}콤보를 모두 마쳤어요.")
    set_id = str(st.session_state.get(_KEY_KEYWORD_CONSTRAINT_SET_ID) or "").strip()
    if st.button(
        "같은 세트 다시 하기",
        type="primary",
        use_container_width=True,
        key="topic_v2_restart_same_keyword_constraint",
    ):
        if set_id:
            _start_keyword_constraint_practice(set_id)
        st.rerun()
    if _is_portal_keyword_entry():
        if st.button(
            "다른 주제 선택",
            use_container_width=True,
            key="topic_v2_pick_other_keyword_constraint",
        ):
            _goto_keyword_set_select()
            st.rerun()
        if st.button(
            "학습 포털로",
            use_container_width=True,
            key="topic_v2_back_to_portal_keyword_constraint",
        ):
            _return_to_learning_portal()
            st.rerun()
    else:
        if st.button(
            "다른 키워드 세트 선택",
            use_container_width=True,
            key="topic_v2_pick_other_keyword_constraint",
        ):
            _goto_topic_select()
            st.rerun()
        if st.button(
            "주제별 연습으로 돌아가기",
            use_container_width=True,
            key="topic_v2_back_to_topic_practice_keyword_constraint",
        ):
            _goto_topic_select()
            st.rerun()


def _render_keyword_constraint_feedback_ui(
    fb: Dict[str, Any], *, topic: str, q_idx: int
) -> None:
    total = _session_question_total()
    if _is_portal_keyword_entry():
        render_top_bar(
            "키워드 표현 연습",
            on_back=_return_to_learning_portal,
            back_key="topic_v2_keyword_fb_portal",
            eyebrow=_practice_eyebrow("피드백"),
        )
    else:
        render_top_bar(
            "주제별 연습",
            back_href="?nav=MOCK",
            eyebrow=_practice_eyebrow("피드백"),
        )
    _render_topic_v2_accent_scope("teal")
    st.markdown(
        build_topic_practice_header_html(
            topic,
            q_idx,
            total_questions=total,
            include_screen_marker=True,
            chip_title=_practice_chip_title(topic),
        ),
        unsafe_allow_html=True,
    )
    render_keyword_constraint_feedback(fb, accent="teal")

    st.divider()
    last_idx = _last_question_index()
    if q_idx < last_idx:
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button(
                "같은 질문 다시 말하기",
                use_container_width=True,
                key="topic_v2_kc_fb_retry_same",
            ):
                _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
                st.session_state[_KEY_FEEDBACK] = None
                st.session_state[_KEY_STEP] = "question"
                st.rerun()
        with c2:
            if st.button(
                "다음 콤보",
                use_container_width=True,
                type="primary",
                key="topic_v2_kc_fb_next",
            ):
                st.session_state[_KEY_FEEDBACK] = None
                _advance_after_question(topic, q_idx)
                st.rerun()
        with c3:
            if st.button(
                _back_to_select_label(),
                use_container_width=True,
                key="topic_v2_kc_fb_back",
            ):
                st.session_state[_KEY_FEEDBACK] = None
                _goto_keyword_back()
                st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "같은 질문 다시 말하기",
                use_container_width=True,
                type="primary",
                key="topic_v2_kc_fb_retry_same",
            ):
                _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
                st.session_state[_KEY_FEEDBACK] = None
                st.session_state[_KEY_STEP] = "question"
                st.rerun()
        with c2:
            if st.button(
                _back_to_select_label(),
                use_container_width=True,
                key="topic_v2_kc_fb_back",
            ):
                st.session_state[_KEY_FEEDBACK] = None
                _goto_keyword_back()
                st.rerun()


def _render_feedback_ui() -> None:
    topic = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    if not _session_valid_for_practice():
        _goto_topic_select()
        st.rerun()
        return
    fb = st.session_state.get(_KEY_FEEDBACK)
    if not isinstance(fb, dict) or not fb.get("ok"):
        st.session_state[_KEY_STEP] = "saved"
        st.rerun()
        return

    if _is_keyword_constraint_mode():
        _render_keyword_constraint_feedback_ui(fb, topic=topic, q_idx=q_idx)
        return

    render_top_bar(
        "주제별 연습",
        back_href="?nav=MOCK",
        eyebrow=_practice_eyebrow("피드백"),
    )
    accent = str(_topic_visual_for_id(topic).get("accent") or "teal")
    _render_topic_v2_accent_scope(accent)
    st.markdown(
        build_topic_practice_header_html(
            topic,
            q_idx,
            total_questions=3,
            include_screen_marker=True,
            chip_title=_practice_chip_title(topic),
        ),
        unsafe_allow_html=True,
    )
    render_feedback_label(accent=accent)

    summary = _topic_v2_fb_text(fb, "summary", _FB_FALLBACK_SUMMARY)
    strength = _topic_v2_fb_text(fb, "strength", _FB_FALLBACK_STRENGTH)
    correction = _topic_v2_fb_text(fb, "correction_focus", _FB_FALLBACK_CORRECTION_FOCUS)
    better = str(fb.get("better_expression") or "").strip()
    better_disp = better if better else _EMPTY_FIELD_PLACEHOLDER
    upgrade = str(fb.get("upgrade_sample") or "").strip()
    upgrade_disp = upgrade if upgrade else _EMPTY_FIELD_PLACEHOLDER
    mission = _topic_v2_fb_text(fb, "practice_mission", _FB_FALLBACK_PRACTICE_MISSION)
    kwords = _topic_v2_fb_keywords(fb)
    answer_level = str(fb.get("answer_level") or "").strip()

    render_feedback_summary(summary, accent=accent, answer_level=answer_level)

    fb_c1, fb_c2 = st.columns(2)
    with fb_c1:
        render_feedback_section_card(
            "잘한 점", strength, accent="teal", icon="circle-check"
        )
    with fb_c2:
        render_feedback_section_card(
            "바로 고칠 점", correction, accent="amber", icon="target"
        )

    render_feedback_section_card(
        "더 자연스러운 표현", better_disp, accent="blue", icon="edit"
    )
    render_feedback_section_card(
        "내 답변 업그레이드 예시", upgrade_disp, accent="purple", icon="message-up"
    )
    render_feedback_keyword_chips(kwords, accent="teal")
    render_feedback_section_card(
        "다음 연습 미션", mission, accent="amber", icon="flag", filled=True
    )

    st.divider()
    if _is_single_question_retry():
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "같은 질문 다시 말하기",
                use_container_width=True,
                type="primary",
                key="topic_v2_fb_retry_same",
            ):
                _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
                st.session_state[_KEY_FEEDBACK] = None
                st.session_state[_KEY_STEP] = "question"
                st.rerun()
        with c2:
            if st.button(
                _back_to_select_label(),
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
        if st.button(
            "다음 질문",
            use_container_width=True,
            type="primary",
            key="topic_v2_fb_next",
        ):
            st.session_state[_KEY_FEEDBACK] = None
            _advance_after_question(topic, q_idx)
            st.rerun()
    with c3:
        if st.button(
            _other_practice_label(),
            use_container_width=True,
            key="topic_v2_fb_other_topic",
        ):
            st.session_state[_KEY_FEEDBACK] = None
            _goto_topic_select()
            st.rerun()


def _render_pending_ui() -> None:
    topic = str(st.session_state.get(_KEY_TOPIC) or "").strip()
    q_idx = int(st.session_state.get(_KEY_Q_INDEX) or 0)
    if not _session_valid_for_practice():
        _goto_topic_select()
        st.rerun()
        return
    fb = st.session_state.get(_KEY_FEEDBACK)
    last_row = _last_answer_row_for_q(q_idx)
    aid = _feedback_answer_id(last_row, topic=topic, q_idx=q_idx)
    cat = ""
    em = ""
    if isinstance(fb, dict):
        cat = str(fb.get("error_category") or "")
        em = str(fb.get("error_message") or "").strip()

    render_top_bar(
        "주제별 연습",
        back_href="?nav=MOCK",
        eyebrow=_practice_eyebrow("피드백"),
    )
    accent = str(_topic_visual_for_id(topic).get("accent") or "teal")
    _render_topic_v2_accent_scope(accent)
    st.markdown(
        build_topic_practice_header_html(
            topic,
            q_idx,
            total_questions=3,
            include_screen_marker=True,
            chip_title=_practice_chip_title(topic),
        ),
        unsafe_allow_html=True,
    )
    render_feedback_label(accent=accent)
    if cat in ("api_key", "insufficient_text") and em:
        fail_body = html.escape(em).replace("\n\n", "<br/><br/>").replace("\n", "<br/>")
        st.markdown(
            render_recovery_card_html(
                eyebrow=ANALYSIS_RECOVERY_EYEBROW,
                title=ANALYSIS_RECOVERY_TITLE,
                body_html=fail_body,
                character_size=72,
                compact=True,
            ),
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            render_analysis_recovery_card(compact=True, character_size=72),
            unsafe_allow_html=True,
        )
    _render_feedback_guard_notice()
    retry_disabled, retry_label = _feedback_request_button_state(aid)
    if not retry_disabled:
        retry_label = "피드백 다시 받기"

    if isinstance(fb, dict) and st.session_state.get("show_dev_debug"):
        st.caption(f"(debug) error_category={fb.get('error_category')!r}")

    st.divider()
    if _is_single_question_retry():
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                retry_label,
                type="primary",
                use_container_width=True,
                key="topic_v2_pending_retry_feedback",
                disabled=retry_disabled,
            ):
                _run_topic_v2_feedback_request(topic, q_idx, last_row)
        with c2:
            if st.button(
                "같은 질문 다시 말하기",
                use_container_width=True,
                key="topic_v2_pending_retry_speak",
            ):
                _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
                st.session_state[_KEY_FEEDBACK] = None
                st.session_state.pop(_KEY_FB_COOLDOWN_UNTIL, None)
                st.session_state.pop(_KEY_FB_NOTICE, None)
                st.session_state[_KEY_STEP] = "question"
                st.rerun()
        if st.button(
            _back_to_select_label(),
            use_container_width=True,
            key="topic_v2_pending_back_select",
        ):
            st.session_state[_KEY_FEEDBACK] = None
            _goto_topic_select()
            st.rerun()
        st.markdown(render_recovery_retry_caption_html(), unsafe_allow_html=True)
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button(
            retry_label,
            type="primary",
            use_container_width=True,
            key="topic_v2_pending_retry_feedback",
            disabled=retry_disabled,
        ):
            _run_topic_v2_feedback_request(topic, q_idx, last_row)
    with c2:
        if st.button(
            "같은 질문 다시 말하기",
            use_container_width=True,
            key="topic_v2_pending_retry_speak",
        ):
            _log_topic_v2_retry_same_question(topic=topic, q_idx=q_idx)
            st.session_state[_KEY_FEEDBACK] = None
            st.session_state.pop(_KEY_FB_COOLDOWN_UNTIL, None)
            st.session_state.pop(_KEY_FB_NOTICE, None)
            st.session_state[_KEY_STEP] = "question"
            st.rerun()
    with c3:
        if st.button("다음 질문", use_container_width=True, key="topic_v2_pending_next_q"):
            st.session_state[_KEY_FEEDBACK] = None
            _advance_after_question(topic, q_idx)
            st.rerun()
    st.markdown(render_recovery_retry_caption_html(), unsafe_allow_html=True)


def render_topic_practice_v2() -> None:
    """Entry: learning portal → Topic Practice V2 (isolated session keys)."""
    _ensure_topic_v2_minimal_defaults()
    page = str(st.session_state.get(_KEY_PAGE) or "practice").strip()
    step = str(st.session_state.get(_KEY_STEP) or "select_topic").strip()
    if page == "history" or step == "history":
        try:
            logger.info(
                "[TOPIC_V2] stale history route — redirect to select_topic page=%s step=%s",
                page or "-",
                step or "-",
            )
        except Exception:
            pass
        st.session_state[_KEY_PAGE] = "practice"
        st.session_state[_KEY_STEP] = "select_topic"
        page = "practice"
        step = "select_topic"

    try:
        logger.info(
            "[TOPIC_V2_RENDER_ENTER] answers_count=%s audio_blobs_count=%s page=%s step=%s",
            _get_topic_v2_answers_count(),
            _audio_blobs_count(),
            page or "-",
            step or "-",
        )
    except Exception:
        pass

    ensure_mock(st.session_state)
    mock_session()
    _ensure_topic_v2_defaults()

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
    elif step == "select_keyword_set":
        _render_select_keyword_set()
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
