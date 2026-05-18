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
from typing import Any

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
    close_record_stage,
    open_record_stage,
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
    mark_pending_recovery,
    reconcile_mock_exam_pointer,
    reset_exam_state,
    save_answer_placeholder_before_ai,
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
    classify_post_analysis_issue,
    classify_pre_analysis_blob,
    has_substantial_recording,
    recording_byte_length,
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

# Re-entry guard. Streamlit reruns are normally synchronous so a second
# call is unlikely, but this defends against any odd path where the same
# rerun reaches _run_analysis twice (e.g. recovery panel + button race).
_ANALYSIS_IN_FLIGHT_KEY = "_analysis_in_flight"

logger = logging.getLogger(__name__)


def _nav_after_question_analysis(mx: dict, qid: int) -> None:
    """Last question → completion screen; otherwise per-question report."""
    if is_last_mock_question(mx, qid):
        mark_mock_exam_completed(mx, st.session_state)
    else:
        mx["mock_page"] = "REPORT"


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
    if mode in ("mini_mock", "mini"):
        return "mini_mock"
    return None


def _mock_mode_label(mode: str | None) -> str:
    if mode == "real_mock":
        return "실전 모의고사"
    if mode == "coaching":
        return "AI 코칭 연습"
    if mode == "topic_practice":
        return "주제별 답변 연습"
    if mode == "mini_mock":
        return "5분 진단 미니 모의고사"
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


def _clear_topic_practice_state() -> None:
    from utils.topic_practice_state import clear_topic_recordings

    for key in (
        "topic_practice_step",
        "selected_topic_id",
        "topic_practice_question_index",
        "topic_practice_results",
        "topic_mini_report",
        "topic_mini_report_pending",
        "topic_report_status",
        "topic_report_last_error",
    ):
        st.session_state.pop(key, None)
    clear_topic_recordings()


_MINI_MOCK_QUESTION_COUNT = 3


def _mini_mock_question_index() -> int:
    try:
        idx = int(st.session_state.get("mini_mock_question_index") or 0)
    except (TypeError, ValueError):
        idx = 0
    return max(0, min(_MINI_MOCK_QUESTION_COUNT - 1, idx))


def _mini_mock_page() -> str:
    return str(st.session_state.get("mini_mock_page") or "QUESTION").strip()


def _clear_mini_mock_state() -> None:
    from utils.mini_mock_state import clear_mini_mock_session

    for key in (
        "mini_mock_question_index",
        "mini_mock_results",
        "mini_mock_completed",
        "mini_mock_page",
    ):
        st.session_state.pop(key, None)
    clear_mini_mock_session()


def _mini_mock_saved_confirm_key(question_id: str) -> str:
    return f"mm_saved_confirm_{question_id}"


def _normalize_topic_practice_step(step: str) -> str:
    s = (step or "").strip()
    if s in ("practice",):
        return "question"
    if s in ("complete", "feedback"):
        return s
    return s or "select_topic"


def _topic_saved_confirm_key(topic_id: str, question_id: str) -> str:
    return f"tp_saved_confirm_{topic_id}_{question_id}"


def _exit_topic_practice_to_mode_picker(mx: dict) -> None:
    _clear_topic_practice_state()
    reset_to_learning_portal()


def _has_mock_mode(mx: dict) -> bool:
    return _mock_mode(mx) is not None


def _set_mock_mode(mx: dict, mode: str) -> None:
    if mode not in ("real_mock", "coaching", "topic_practice", "mini_mock"):
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
    st.session_state["practice_portal_selected"] = False
    st.session_state["mock_mode"] = None
    st.session_state["mock_page"] = "PICK"
    st.session_state["topic_practice_step"] = None
    st.session_state["selected_topic_id"] = None
    _clear_mini_mock_state()
    mx["mock_page"] = "PICK"
    mx.pop("mock_mode", None)
    mx.pop("mock_mode_label", None)
    mx.pop("_resume_confirmed", None)
    st.session_state.pop("mock_mode", None)


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
    if mode in ("mini_mock", "mini"):
        return "mini_mock"
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
        if result_display_status(res) != "AI 분석 대기 중":
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

    total = get_mock_total_questions(mx)
    preview = build_final_report_preview(mx.get("results") or [], total_count=total)
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
        "최종 리포트 전체 보기",
        type="primary",
        use_container_width=True,
        key="mx_mock_final_report",
    ):
        mx["_view_completed_report"] = True
        mx["mock_page"] = "FINAL"
        st.session_state["mock_page"] = "FINAL"
        try:
            st.query_params.clear()
            st.query_params["nav"] = "MOCK"
            st.query_params["mock"] = "FINAL"
        except Exception:
            pass
        st.rerun()

    pending = int(preview.get("pending_count") or 0)
    if pending > 0:
        c_retry, c_back = st.columns(2)
        with c_retry:
            if st.button(
                "분석 대기 문항 다시 시도",
                use_container_width=True,
                key="mx_mock_retry_pending",
            ):
                _retry_first_pending_analysis(mx)
        with c_back:
            if st.button(
                "학습하기로 돌아가기",
                use_container_width=True,
                key="mx_mock_back_portal",
            ):
                st.session_state["practice_portal_selected"] = False
                st.session_state["mock_page"] = "PICK"
                mx["mock_page"] = "PICK"
                try:
                    st.query_params.clear()
                    st.query_params["nav"] = "MOCK"
                except Exception:
                    pass
                st.rerun()
    elif st.button("학습하기로 돌아가기", use_container_width=True, key="mx_mock_back_portal"):
        st.session_state["practice_portal_selected"] = False
        st.session_state["mock_page"] = "PICK"
        mx["mock_page"] = "PICK"
        try:
            st.query_params.clear()
            st.query_params["nav"] = "MOCK"
        except Exception:
            pass
        st.rerun()


def _render_real_mock_flow(mx: dict) -> None:
    if (
        has_resumable_exam(mx)
        and not mx.get("_resume_confirmed")
        and _mock_mode(mx) == "real_mock"
    ):
        render_resumable_landing(mx)
        return
    if is_completed_mock(mx):
        if _should_show_completed_final_report(mx):
            render_top_bar(
                "종합 리포트",
                back_href="?nav=MOCK",
                eyebrow=format_mock_attempt_label(mx),
            )
            from views.final_report import render_final_report

            render_final_report(mx)
            return
        if _get_mock_page(mx) == "FINAL" or mx.get("exam_completed"):
            render_mock_exam_completion_screen(mx)
            return
        render_completed_exam_landing(mx)
        return
    mock_page = _get_mock_page(mx)
    if mock_page == "SURVEY":
        _render_survey(mx)
    elif mock_page == "TEST":
        _render_test(mx)
    elif mock_page == "REPORT":
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

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            """
            <section class="continue-card continue-card--start mx-mode-card" role="region"
                     aria-label="실전 모의고사">
              <div class="cc-title">실전 모의고사</div>
              <div class="cc-meta">실제 오픽처럼 연속으로 답변하고 마지막에 전체 리포트를 확인해요.</div>
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
            st.session_state["mock_mode"] = "real_mock"
            st.session_state["practice_portal_selected"] = True
            st.session_state["mock_page"] = "SURVEY"
            _sync_portal_mode_to_mx(mx, "real_mock")
            _set_mock_page(mx, "SURVEY")
            _clear_reset_practice_query_param()
            st.rerun()
    with c2:
        st.markdown(
            """
            <section class="continue-card continue-card--start mx-mode-card" role="region"
                     aria-label="5분 진단 미니 모의고사">
              <div class="cc-title">5분 진단 미니 모의고사</div>
              <div class="cc-meta">묘사, 경험, 롤플레이 3문항으로 빠르게 현재 답변 습관을 진단해요.</div>
              <p class="mx-mode-badge">추천 · 약 5분</p>
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
            _clear_mini_mock_state()
            st.session_state["mock_mode"] = "mini_mock"
            st.session_state["practice_portal_selected"] = True
            st.session_state["mini_mock_question_index"] = 0
            st.session_state["mini_mock_results"] = []
            st.session_state["mini_mock_completed"] = False
            st.session_state["mini_mock_page"] = "QUESTION"
            _sync_portal_mode_to_mx(mx, "mini_mock")
            _set_mock_page(mx, "MINI_MOCK")
            _clear_reset_practice_query_param()
            st.rerun()

    c3, _ = st.columns(2)
    with c3:
        st.markdown(
            """
            <section class="continue-card continue-card--start mx-mode-card" role="region"
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
            st.session_state["mock_mode"] = "topic_practice"
            st.session_state["practice_portal_selected"] = True
            st.session_state["topic_practice_step"] = "select_topic"
            st.session_state["selected_topic_id"] = None
            st.session_state["topic_practice_question_index"] = 0
            st.session_state["mock_page"] = "TOPIC"
            _sync_portal_mode_to_mx(mx, "topic_practice")
            _set_mock_page(mx, "TOPIC")
            _clear_reset_practice_query_param()
            st.rerun()

    _render_dev_portal_debug(mx)


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
        st.session_state["selected_topic_id"] = topic_id
        st.session_state["topic_practice_question_index"] = 0
        st.session_state["topic_practice_results"] = []
        st.session_state["topic_practice_step"] = "question"
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
    reset_recording_timer()
    st.session_state["topic_practice_question_index"] = 0
    st.session_state["topic_practice_results"] = []
    st.session_state["topic_practice_step"] = "select_topic"


def _topic_advance_after_saved_answer(
    mx: dict, topic_id: str, question_id: str, *, mic_key: str = ""
) -> None:
    from components.answer_recording import clear_mic_recording_cache, reset_recording_ui_for_question

    reset_recording_timer()
    timer_key = f"tp_{topic_id}_{question_id}"
    reset_recording_ui_for_question(timer_key)
    if mic_key:
        clear_mic_recording_cache(mic_key)
    mx["audio_bytes"] = None
    mx.pop("preview_transcript", None)
    st.session_state.pop(_topic_saved_confirm_key(topic_id, question_id), None)
    idx = _topic_practice_question_index()
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

    recordings = get_topic_recordings()
    blob = mx.get("audio_bytes") or recordings.get(audio_key)
    if not blob:
        st.error("녹음이 제대로 저장되지 않았어요. 같은 질문을 다시 말해 주세요.")
        return False
    if classify_pre_analysis_blob(blob) == "no_audio":
        st.error("녹음이 제대로 저장되지 않았어요. 같은 질문을 다시 말해 주세요.")
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
    question_id = str(question.get("question_id") or "")
    st.session_state[_topic_saved_confirm_key(topic_id, question_id)] = True
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
    in_flight = bool(st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY))
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

    if st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY):
        return

    topic_title = str(topic.get("topic_title") or "")
    question_id = str(question.get("question_id") or "")
    if not audio_key:
        audio_key = topic_audio_key(topic_id, question_id)

    st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = True
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
        st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = False


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

    if manage_in_flight and st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY):
        return

    question_id = str(question.get("question_id") or "")
    if not audio_key:
        audio_key = mini_mock_audio_key(question_id)

    row = find_mini_mock_result(question_id)
    if row and not from_retry and not mini_mock_needs_analysis(row):
        return

    if manage_in_flight:
        st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = True
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
        except Exception as exc:
            logger.exception("Mini mock Gemini failure q=%s", question_id)
            last_error = f"{type(exc).__name__}: {exc}"
            result = None
            attempts = max(attempts, 1)
        finally:
            if external_wait_slot is None:
                finish_analysis_waiting_ui(wait_slot, submission_id)

        if _is_analysis_failed(result, last_error):
            _empty_resp = bool(last_error and "비어" in last_error)
            apply_mini_mock_pending_result(
                question_index=q_idx,
                question=question,
                audio_key=audio_key,
                error_message=last_error or "AI 분석 실패",
                attempts=attempts,
                mode="mini_mock",
                mime_type=mime_for_gemini,
                model=str((result or {}).get("model_used") or ""),
                audio_bytes_len=mm_nbytes,
                empty_response=_empty_resp,
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
        if not defer_rerun:
            st.rerun()
    finally:
        if manage_in_flight:
            st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = False


def run_mini_mock_report_analysis(mx: dict) -> None:
    """Analyze all 3 saved mini-mock answers — only after user requests the report."""
    from data.mini_mock_questions import get_mini_mock_question
    from services.exam_analytics import result_display_status
    from utils.mini_mock_state import (
        count_mini_mock_saved_answers,
        get_mini_mock_answer_blob,
        mini_mock_audio_key,
        mini_mock_needs_analysis,
        mini_mock_rows_sorted,
        row_result,
    )

    if st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY):
        return

    saved_n = count_mini_mock_saved_answers()
    if saved_n < _MINI_MOCK_QUESTION_COUNT:
        st.warning("아직 3개 문항이 모두 저장되지 않았어요.")
        st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
        st.rerun()
        return

    api_key = get_gemini_api_key()
    if not api_key:
        st.warning("API Key를 설정하면 AI 진단 리포트를 받을 수 있어요.")
        st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
        st.rerun()
        return

    st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = True
    submission_id = secrets.token_hex(4)
    wait_slot = st.empty()

    def _show_batch_wait(stage_label: str = "") -> None:
        with wait_slot.container():
            render_ai_analysis_waiting(
                submission_id,
                title="AI가 3개 답변을 분석하고 있어요",
                subtitle=(
                    "묘사, 경험, 롤플레이 답변을 바탕으로 현재 말하기 습관을 진단하는 중입니다.<br/>"
                    "조금 시간이 걸릴 수 있어요."
                ),
                stage_label=stage_label or None,
            )

    try:
        _show_batch_wait()
        for q_idx in range(_MINI_MOCK_QUESTION_COUNT):
            question = get_mini_mock_question(q_idx)
            if not question:
                continue
            question_id = str(question.get("question_id") or "")
            row = None
            for r in mini_mock_rows_sorted():
                if str(r.get("question_id") or "") == question_id:
                    row = r
                    break
            if not row or not mini_mock_needs_analysis(row):
                continue
            audio_key = str(row.get("audio_key") or "") or mini_mock_audio_key(question_id)
            blob = get_mini_mock_answer_blob(row)
            if blob:
                mx["audio_bytes"] = blob
            _show_batch_wait(f"Q{q_idx + 1}/3 분석 중…")
            _run_mini_mock_analysis(
                mx,
                question,
                q_idx,
                audio_key,
                api_key,
                from_retry=True,
                defer_rerun=True,
                manage_in_flight=False,
                external_wait_slot=wait_slot,
                external_submission_id=submission_id,
            )

        rows = mini_mock_rows_sorted()
        completed = 0
        pending = 0
        for row in rows:
            status = result_display_status(row_result(row))
            if status == "분석 완료":
                completed += 1
            elif status == "AI 분석 대기 중":
                pending += 1

        st.session_state["mini_mock_completed"] = True
        if completed == 0 and pending > 0:
            st.session_state["mini_mock_page"] = "REPORT_PENDING"
        else:
            st.session_state["mini_mock_page"] = "REPORT"
    finally:
        finish_analysis_waiting_ui(wait_slot, submission_id)
        st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = False
    st.rerun()


def _run_topic_mini_report_analysis(
    mx: dict,
    topic_id: str,
    topic: dict,
    api_key: str,
    *,
    from_retry: bool = False,
) -> None:
    """One Gemini call for all 3 saved answers → real AI report or pending retry."""
    from services.feedback.topic_mini_report_analysis import (
        TOPIC_REPORT_COMPLETED,
        TOPIC_REPORT_FAILED,
        TOPIC_REPORT_PENDING_RETRY,
        is_real_topic_ai_report,
        run_topic_mini_report_analysis,
    )
    from utils.topic_practice_state import topic_rows_for_session

    if st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY):
        return
    if not api_key:
        st.error("API Key가 설정되지 않아 분석을 시작할 수 없습니다.")
        return

    topic_title = str(topic.get("topic_title") or "")
    rows = topic_rows_for_session(topic_id)
    if len(rows) < _TOPIC_PRACTICE_QUESTION_COUNT:
        st.warning("저장된 답변이 3개가 아닙니다. 각 문항을 녹음해 주세요.")
        return

    st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = True
    st.session_state["topic_practice_step"] = "analyzing_report"
    st.session_state["topic_report_status"] = "analyzing"
    st.session_state.pop("topic_mini_report", None)
    st.session_state.pop("topic_mini_report_pending", None)
    st.session_state.pop("topic_report_last_error", None)

    submission_id = secrets.token_hex(4)
    wait_slot = st.empty()
    difficulty = int(settings_session()["difficulty"])

    def _show_wait(label: str) -> None:
        with wait_slot.container():
            render_topic_mini_report_waiting(submission_id, stage_label=label)

    try:
        _show_wait("복원 발화·문법·표현·답변 흐름을 정리하는 중…")
        topic_category = str(topic.get("category") or topic.get("topic_category") or "")
        outcome = run_topic_mini_report_analysis(
            rows,
            {
                "topic_id": topic_id,
                "topic_title": topic_title,
                "topic_category": topic_category,
            },
            api_key,
            difficulty=difficulty,
            mx=mx,
            consume_daily_slot=not from_retry,
            from_retry=from_retry,
        )
        finish_analysis_waiting_ui(wait_slot, submission_id)
        status = str(outcome.get("topic_report_status") or "")
        st.session_state["topic_report_status"] = status

        if status == TOPIC_REPORT_COMPLETED:
            report = outcome.get("report")
            if isinstance(report, dict) and is_real_topic_ai_report(report):
                st.session_state["topic_mini_report"] = report
                st.session_state.pop("topic_mini_report_pending", None)
                st.session_state["topic_practice_step"] = "mini_report"
            else:
                st.session_state.pop("topic_mini_report", None)
                st.session_state["topic_report_status"] = TOPIC_REPORT_PENDING_RETRY
                st.session_state["topic_mini_report_pending"] = True
                st.session_state["topic_practice_step"] = "answers_saved"
        elif status == TOPIC_REPORT_PENDING_RETRY:
            st.session_state.pop("topic_mini_report", None)
            st.session_state["topic_mini_report_pending"] = True
            st.session_state["topic_practice_step"] = "answers_saved"
        else:
            st.session_state.pop("topic_mini_report", None)
            st.session_state.pop("topic_mini_report_pending", None)
            st.session_state["topic_practice_step"] = "answers_saved"
            msg = str(outcome.get("user_message") or "").strip()
            if msg:
                st.session_state["topic_report_last_error"] = msg
    finally:
        st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = False
    st.rerun()


def render_topic_practice_question_page(mx: dict) -> None:
    """Topic question + recorder — save only; mini report after all 3 answers."""
    from components.answer_recording import (
        STATE_SAVED,
        clear_mic_recording_cache,
        get_recording_ui_state,
        reset_recording_ui_for_question,
    )
    from utils.topic_practice_state import (
        clear_topic_answer_for_question,
        get_topic_recordings,
        topic_audio_key,
    )
    from utils.speech_recording import recording_byte_length

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
    audio_key = topic_audio_key(topic_id, question_id)
    confirm_key = _topic_saved_confirm_key(topic_id, question_id)
    is_last = q_idx >= _TOPIC_PRACTICE_QUESTION_COUNT - 1

    render_top_bar(
        "주제별 연습",
        back_href="?nav=MOCK",
        eyebrow=f"{title} 콤보 연습 · Q{q_idx + 1}/3",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_topic_question_body(topic, question, q_idx)

    recordings = get_topic_recordings()
    timer_key = f"tp_{topic_id}_{question_id}"
    mic_key = f"tp_rec_{topic_id}_{question_id}"
    saved_blob = mx.get("audio_bytes") or recordings.get(audio_key)
    ui_state = get_recording_ui_state(timer_key, has_saved=bool(saved_blob))
    show_saved = ui_state == STATE_SAVED or (
        bool(st.session_state.get(confirm_key)) and bool(saved_blob)
    )

    if not show_saved:
        open_record_stage("🎤 답변 시작 → 말한 뒤 녹음 완료")

        def _topic_on_recording_complete(_blob: bytes) -> bool:
            return _topic_commit_saved_answer(
                mx,
                topic_id=topic_id,
                topic_title=title,
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
            on_recording_complete=_topic_on_recording_complete,
        )
        close_record_stage()
        if st.button("주제 다시 선택", use_container_width=True, key=f"tp_reselect_{topic_id}_{q_idx}"):
            _topic_back_to_select_topic()
            st.rerun()
        return

    audio_len = recording_byte_length(saved_blob)
    render_topic_answer_saved_card(q_idx=q_idx, audio_len=audio_len, is_last=is_last)

    c1, c2 = st.columns(2)
    with c1:
        next_label = "완료하고 리포트 받기" if is_last else "다음 질문으로"
        if st.button(
            next_label,
            type="primary",
            use_container_width=True,
            key=f"tp_next_{topic_id}_{q_idx}",
        ):
            if not st.session_state.get(confirm_key):
                if not _topic_commit_saved_answer(
                    mx,
                    topic_id=topic_id,
                    topic_title=title,
                    q_idx=q_idx,
                    question=question,
                    audio_key=audio_key,
                ):
                    return
            _topic_advance_after_saved_answer(mx, topic_id, question_id, mic_key=mic_key)
    with c2:
        if st.button(
            "같은 질문 다시 말하기",
            use_container_width=True,
            key=f"tp_rerecord_{topic_id}_{q_idx}",
        ):
            clear_topic_answer_for_question(topic_id, question_id)
            reset_recording_ui_for_question(timer_key)
            clear_mic_recording_cache(mic_key)
            reset_recording_timer()
            mx["audio_bytes"] = None
            mx.pop("preview_transcript", None)
            st.session_state.pop(confirm_key, None)
            st.rerun()

    if st.button("주제 다시 선택", use_container_width=True, key=f"tp_reselect_saved_{topic_id}_{q_idx}"):
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
        st.markdown(f"- Q{ql} · 녹음 저장됨 · {nbytes:,} bytes")

    from services.feedback.topic_mini_report_analysis import TOPIC_REPORT_PENDING_RETRY

    api_key = get_gemini_api_key()
    in_flight = bool(st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY))
    pending_retry = (
        st.session_state.get("topic_report_status") == TOPIC_REPORT_PENDING_RETRY
        or st.session_state.get("topic_mini_report_pending")
    )
    last_err = str(st.session_state.get("topic_report_last_error") or "").strip()
    if last_err:
        st.warning(last_err)

    if pending_retry:
        render_topic_report_pending_retry_screen(saved_count=len(rows))

    if st.button(
        "AI 풀 리포트 받기",
        type="primary",
        use_container_width=True,
        key=f"tp_mini_report_{topic_id}",
        disabled=in_flight or not api_key,
    ):
        _run_topic_mini_report_analysis(mx, topic_id, topic, api_key)

    if pending_retry:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "AI 분석 다시 시도",
                type="primary",
                use_container_width=True,
                key=f"tp_mini_retry_{topic_id}",
                disabled=in_flight or not api_key,
            ):
                _run_topic_mini_report_analysis(
                    mx, topic_id, topic, api_key, from_retry=True
                )
        with c2:
            if st.button(
                "주제 선택으로 돌아가기",
                use_container_width=True,
                key=f"tp_mini_back_topics_{topic_id}",
            ):
                _topic_back_to_select_topic()
                st.rerun()
    else:
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


def render_topic_mini_report_page(mx: dict) -> None:
    from services.feedback.topic_mini_report_analysis import (
        TOPIC_REPORT_COMPLETED,
        is_real_topic_ai_report,
    )

    report = st.session_state.get("topic_mini_report")
    status = str(st.session_state.get("topic_report_status") or "")
    if (
        not isinstance(report, dict)
        or not is_real_topic_ai_report(report)
        or status != TOPIC_REPORT_COMPLETED
    ):
        st.session_state.pop("topic_mini_report", None)
        if status != TOPIC_REPORT_COMPLETED:
            st.session_state["topic_report_status"] = "pending_retry"
            st.session_state["topic_mini_report_pending"] = True
        st.session_state["topic_practice_step"] = "answers_saved"
        st.rerun()
        return

    title = str(report.get("topic_title") or "주제")
    render_top_bar("주제별 풀 리포트", back_href="?nav=MOCK", eyebrow=title)
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    render_topic_mini_report(report)

    if st.button("같은 주제 다시 연습", type="primary", use_container_width=True, key="mx_tp_restart_same"):
        st.session_state["topic_practice_question_index"] = 0
        st.session_state["topic_practice_results"] = []
        st.session_state.pop("topic_mini_report", None)
        st.session_state.pop("topic_mini_report_pending", None)
        st.session_state.pop("topic_report_status", None)
        st.session_state["topic_practice_step"] = "question"
        st.rerun()

    if st.button("다른 주제 선택", use_container_width=True, key="mx_tp_other_topic"):
        st.session_state["selected_topic_id"] = None
        _topic_back_to_select_topic()
        st.rerun()

    if st.button("학습 방식 다시 선택", use_container_width=True, key="mx_tp_mini_portal"):
        _exit_topic_practice_to_mode_picker(mx)
        st.rerun()


def render_topic_practice_feedback(mx: dict) -> None:
    """Legacy per-question feedback — redirect to report flow."""
    from services.feedback.topic_mini_report_analysis import (
        TOPIC_REPORT_COMPLETED,
        is_real_topic_ai_report,
    )

    report = st.session_state.get("topic_mini_report")
    if (
        isinstance(report, dict)
        and is_real_topic_ai_report(report)
        and st.session_state.get("topic_report_status") == TOPIC_REPORT_COMPLETED
    ):
        st.session_state["topic_practice_step"] = "mini_report"
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


def _mini_mock_advance_after_saved_answer(mx: dict, question_id: str, *, mic_key: str = "") -> None:
    from components.answer_recording import clear_mic_recording_cache, reset_recording_ui_for_question

    reset_recording_timer()
    timer_key = f"mm_{question_id}"
    reset_recording_ui_for_question(timer_key)
    if mic_key:
        clear_mic_recording_cache(mic_key)
    mx["audio_bytes"] = None
    mx.pop("preview_transcript", None)
    st.session_state.pop(_mini_mock_saved_confirm_key(question_id), None)
    idx = _mini_mock_question_index()
    if idx >= _MINI_MOCK_QUESTION_COUNT - 1:
        st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
    else:
        st.session_state["mini_mock_question_index"] = idx + 1
        st.session_state["mini_mock_page"] = "QUESTION"
    st.rerun()


def _mini_mock_commit_saved_answer(
    mx: dict,
    *,
    q_idx: int,
    question: dict,
    audio_key: str,
) -> bool:
    from utils.mini_mock_state import get_mini_mock_recordings, save_mini_mock_unanalyzed_answer
    from utils.speech_recording import classify_pre_analysis_blob, resolve_mime_for_analysis

    recordings = get_mini_mock_recordings()
    blob = mx.get("audio_bytes") or recordings.get(audio_key)
    if not blob:
        st.error("녹음이 제대로 저장되지 않았어요. 같은 질문을 다시 말해 주세요.")
        return False
    if classify_pre_analysis_blob(blob) == "no_audio":
        st.error("녹음이 제대로 저장되지 않았어요. 같은 질문을 다시 말해 주세요.")
        return False
    mime = resolve_mime_for_analysis(blob, mx=mx, audio_key=audio_key)
    save_mini_mock_unanalyzed_answer(
        question_index=q_idx,
        question=question,
        audio_key=audio_key,
        audio_bytes=blob,
        mime_type=mime,
    )
    question_id = str(question.get("question_id") or "")
    st.session_state[_mini_mock_saved_confirm_key(question_id)] = True
    if q_idx >= _MINI_MOCK_QUESTION_COUNT - 1:
        st.session_state["mini_mock_page"] = "READY_FOR_REPORT"
    else:
        st.session_state["mini_mock_page"] = "SAVED"
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


def render_mini_mock_question_page(mx: dict) -> None:
    from components.answer_recording import (
        STATE_SAVED,
        clear_mic_recording_cache,
        get_recording_ui_state,
        reset_recording_ui_for_question,
    )
    from data.mini_mock_questions import get_mini_mock_question
    from utils.mini_mock_state import (
        clear_mini_mock_answer_for_question,
        get_mini_mock_recordings,
        mini_mock_audio_key,
    )

    page = _mini_mock_page()
    if page == "READY_FOR_REPORT":
        render_top_bar("5분 진단", back_href="?nav=MOCK", eyebrow="미니 모의고사 · 저장 완료")
        st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
        _render_mini_mock_answer_saved_card(ready_for_report=True)
        if st.button(
            "AI 진단 리포트 받기",
            type="primary",
            use_container_width=True,
            key="mini_mock_get_report",
        ):
            st.session_state["mini_mock_page"] = "ANALYZING_REPORT"
            st.rerun()
        if st.button("학습 방식 다시 선택", use_container_width=True, key="mm_ready_back_portal"):
            reset_to_learning_portal()
            st.rerun()
        return

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
    confirm_key = _mini_mock_saved_confirm_key(question_id)

    render_top_bar(
        "5분 진단",
        back_href="?nav=MOCK",
        eyebrow=f"미니 모의고사 · Q{q_idx + 1}/3",
    )
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_mini_mock_question_body(question, q_idx)

    recordings = get_mini_mock_recordings()
    timer_key = f"mm_{question_id}"
    mic_key = f"mm_rec_{question_id}"
    saved_blob = mx.get("audio_bytes") or recordings.get(audio_key)
    ui_state = get_recording_ui_state(timer_key, has_saved=bool(saved_blob))
    show_saved = ui_state == STATE_SAVED or (
        bool(st.session_state.get(confirm_key)) and bool(saved_blob)
    )

    if not show_saved:
        open_record_stage("🎤 답변 시작 → 말한 뒤 녹음 완료")

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
        )
        close_record_stage()
        if st.button("학습 방식 다시 선택", use_container_width=True, key=f"mm_back_portal_{q_idx}"):
            reset_to_learning_portal()
            st.rerun()
        return

    if page == "SAVED" or show_saved:
        _render_mini_mock_answer_saved_card(ready_for_report=False)
        if st.button(
            "다음 문항으로",
            type="primary",
            use_container_width=True,
            key=f"mini_mock_next_{q_idx}",
        ):
            if not st.session_state.get(confirm_key):
                if not _mini_mock_commit_saved_answer(
                    mx,
                    q_idx=q_idx,
                    question=question,
                    audio_key=audio_key,
                ):
                    return
            _mini_mock_advance_after_saved_answer(mx, question_id, mic_key=mic_key)

    if st.button(
        "같은 질문 다시 말하기",
        use_container_width=True,
        key=f"mm_rerecord_{question_id}_{q_idx}",
    ):
        clear_mini_mock_answer_for_question(question_id)
        reset_recording_ui_for_question(timer_key)
        clear_mic_recording_cache(mic_key)
        reset_recording_timer()
        mx["audio_bytes"] = None
        mx.pop("preview_transcript", None)
        st.session_state.pop(confirm_key, None)
        st.session_state["mini_mock_page"] = "QUESTION"
        st.rerun()

    if st.button("학습 방식 다시 선택", use_container_width=True, key=f"mm_back_saved_{q_idx}"):
        reset_to_learning_portal()
        st.rerun()


def render_mini_mock_report_page(mx: dict) -> None:
    from components.mini_mock_report_ui import (
        render_mini_mock_report,
        render_mini_mock_report_actions,
        render_mini_mock_report_download,
    )
    from services.feedback.mini_mock_report import build_mini_mock_report_data
    from utils.mini_mock_state import mini_mock_rows_sorted

    if st.session_state.pop("_mm_retry_pending", None):
        st.session_state["mini_mock_page"] = "ANALYZING_REPORT"
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
    from utils.mini_mock_state import count_mini_mock_saved_answers

    render_top_bar("5분 진단", back_href="?nav=MOCK", eyebrow="미니 진단 리포트")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    saved_n = count_mini_mock_saved_answers()
    st.markdown(
        f"""
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">AI 분석</div>
          <div class="rv-title">AI 분석을 다시 시도해야 해요</div>
          <div class="rv-body">3개 답변은 모두 안전하게 저장되어 있습니다.<br/>
            현재 AI 분석 요청이 정상적으로 완료되지 않았어요.<br/>
            잠시 후 다시 분석을 눌러 미니 진단 리포트를 받아보세요.</div>
          <div class="rv-meta"><span>저장된 답변 {saved_n}개</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if st.button(
        "AI 분석 다시 시도",
        type="primary",
        use_container_width=True,
        key="mm_report_retry_analysis",
    ):
        st.session_state["mini_mock_page"] = "ANALYZING_REPORT"
        st.rerun()
    if st.button("학습 방식 다시 선택", use_container_width=True, key="mm_pending_back_portal"):
        reset_to_learning_portal()
        st.rerun()


def render_mini_mock_flow(mx: dict) -> None:
    page = _mini_mock_page()
    if page == "ANALYZING_REPORT":
        run_mini_mock_report_analysis(mx)
        return
    if page == "REPORT":
        render_mini_mock_report_page(mx)
        return
    if page == "REPORT_PENDING":
        render_mini_mock_report_pending_page(mx)
        return
    render_mini_mock_question_page(mx)


def render_topic_practice_flow(mx: dict) -> None:
    step = _normalize_topic_practice_step(_topic_practice_step() or "select_topic")
    if step == "mini_report":
        render_topic_mini_report_page(mx)
    elif step == "analyzing_report":
        render_topic_answers_saved_page(mx)
    elif step == "answers_saved" or step == "complete":
        render_topic_answers_saved_page(mx)
    elif step == "feedback":
        render_topic_practice_feedback(mx)
    elif step == "question" or step == "practice":
        render_topic_practice_question_page(mx)
    else:
        render_topic_selection(mx)


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
    if issue in ("unclear_speech", "needs_review", "non_english") and nbytes > 0:
        meta_html = (
            f'<div class="mx-rh-meta">'
            f'<span class="mx-rh-chip">녹음 저장됨 · {html.escape(f"{nbytes:,}")} bytes</span>'
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
    if not is_completed_mock(mx):
        return False
    return bool(mx.get("_view_completed_report"))


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
        mx["mock_page"] = "FINAL"
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
    if page not in {"PICK", "TOPIC", "MINI_MOCK", "SURVEY", "TEST", "REPORT", "FINAL"}:
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
    if is_completed_mock(mx):
        if mock_q is None and mx.get("mock_page") != "FINAL":
            mx.pop("_view_completed_report", None)

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
        reconcile_mock_exam_pointer(mx)

    if "mock_data" not in st.session_state:
        st.session_state.mock_data = {"recording_active": False}
    st.session_state.mock_data["recording_active"] = bool(mx.get("audio_bytes"))


def render_mock_flow() -> None:
    mx = mock_session()
    _sync_mock_routing_state(mx)
    sync_settings_to_legacy(st.session_state)

    _pv = st.query_params.get("preview_final")
    if isinstance(_pv, list):
        _pv = _pv[0] if _pv else None
    if _pv == "1" and not mx.get("_demo_preview_loaded"):
        from services.final_report_demo import seed_demo_final_report

        seed_demo_final_report(mx)
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

    if mode == "topic_practice":
        render_topic_practice_flow(mx)
        return

    if mode == "mini_mock":
        render_mini_mock_flow(mx)
        return

    if mode == "real_mock":
        if is_completed_mock(mx) and not _should_show_completed_final_report(mx):
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
                from services.final_report_demo import seed_demo_final_report

                seed_demo_final_report(mx)
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
) -> None:
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


def _render_mock_question_listen_stage(mx: dict, q: dict, q_id: int) -> None:
    """Listen UI — never blocks the record stage; TTS loads lazily."""
    q_text = q["question"]
    voice_id = neural2_voice_for_session()
    mock_err_key, pref_key, fail_key = _mock_tts_session_keys(q_id, voice_id)

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
            _render_mock_question_audio_when_ready(mx, q_id, payload)
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
            _render_mock_question_audio_when_ready(mx, q_id, loaded)

    try:
        frag = st.fragment(run_every=run_every)(_auto_prefetch_listen_audio)
    except TypeError:
        return
    frag()


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
            <span class="mx-progress-eyebrow">진행</span>
            <span class="mx-progress-count">Q{q_id} <span class="mx-progress-of">/ {total}</span></span>
          </div>
          {('<div class="mx-progress-chip">' + topic_safe + '</div>') if topic_safe else ''}
        </div>
        <div class="mx-progress-bar" aria-hidden="true">
          <span class="mx-progress-fill" style="width:{progress_pct}%"></span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 2) Question card — type chip + topic + listening guidance. The
    # question text itself stays hidden ("질문 텍스트는 비공개") because the
    # OPIc format requires the test-taker to comprehend from audio only.
    st.markdown(
        f"""
        <div class="mx-question-card">
          {('<span class="mx-question-type">' + type_safe + '</span>') if type_safe else ''}
          <div class="mx-question-topic">{topic_safe or '주제 안내'}</div>
          <p class="mx-question-hint">
            <strong>질문 음성</strong>을 듣고 답변을 녹음해 주세요. 질문 텍스트는 공개되지 않습니다.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 3) Listen stage — TTS loads lazily (never blocks recorder below).
    _render_mock_question_listen_stage(mx, q, q_id)

    open_record_stage("🎤 답변 시작 → 말한 뒤 녹음 완료")
    timer_key = f"mock_{audio_key}"
    in_flight = bool(st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY))
    _render_answer_recording_stage(
        mx,
        question_key=timer_key,
        mic_key=f"rec_{q_id}",
        audio_key=audio_key,
        analyzing=in_flight,
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
        mic_key=f"rec_{q_id}",
        on_analyze=_mock_analyze,
        analyze_key=f"mock_analyze_{q_id}",
        rerecord_key=f"mock_rerecord_{q_id}",
        analyze_disabled=(not bool(api_key)) or in_flight,
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
) -> None:
    """Save answer first, then analyze — API failure never blocks progress."""
    if st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY):
        return

    st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = True
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
            st.rerun()
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
            st.rerun()
            return

        if not from_retry:
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
                diag={
                    "submission_id": submission_id,
                    "question_index": q_index,
                    "question_id": q_id,
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
            _nav_after_question_analysis(mx, q["id"])
            mx["analysis_done"] = True
            mx["preview_transcript"] = None
            st.rerun()
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
            st.rerun()
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
        mx["preview_transcript"] = _transcript_raw
        mx["analysis_result"] = result_to_store
        raw_parse_failed = (result_to_store.get("raw_text_parse_failed") or "").strip()
        if raw_parse_failed:
            st.error(raw_parse_failed)
        mx["last_result"] = result_to_store
        _nav_after_question_analysis(mx, q["id"])
        reconcile_mock_exam_pointer(mx)
        mx["analysis_done"] = True
        clear_pending_recovery(mx)
        st.rerun()
    finally:
        st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = False


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
    in_flight = bool(st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY))
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
        audio_meta = f"녹음 저장됨 · {audio_size:,} bytes"
    elif is_no_audio:
        audio_meta = (
            f"녹음 {audio_size:,} bytes" if audio_size else "녹음 데이터 없음"
        )
    elif is_legacy_no_speech:
        audio_meta = "녹음 음성 미감지"
    else:
        audio_meta = f"녹음 {audio_size:,} bytes 보존됨"

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

    in_flight = bool(st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY))
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
        if status in ["pending", "analysis_pending", "api_error", "failed"]:
            st.info("AI 분석 대기 중입니다. 나중에 다시 시도할 수 있어요.")
        elif transcript:
            st.caption(transcript[:300])
        else:
            st.caption("표시할 답변 내용이 없습니다.")


def _render_report(mx: dict) -> None:
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
