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

import streamlit as st

from components.audio_player import render_exam_question_audio_player
from components.coaching_experience import (
    render_coaching_cta_preamble,
    render_coaching_retry_banner,
    render_flow_coaching_section,
    render_grammar_and_expression_coaching,
    render_history_expander_coaching,
    render_native_upgrade_section,
    render_overall_coaching_hero,
    render_strong_points_cards,
)
from components.navigation import render_bottom_navigation
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
    NO_SPEECH_ERROR_SENTINEL,
    build_analysis_pending_result,
    classify_analysis_error,
    clear_pending_recovery,
    count_completed_exam_prefix,
    has_pending_recovery_for,
    has_resumable_exam,
    mark_pending_recovery,
    reconcile_mock_exam_pointer,
    reset_exam_state,
    upsert_mock_exam_result,
)
from utils.local_profile import force_restore_mock_from_disk, iso_now
from utils.secrets import get_gemini_api_key
from utils.session_state import mock_session, settings_session, sync_settings_to_legacy
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
    """Q15 완료 시 종합 리포트로, 그 외에는 문항 리포트."""
    if int(qid) >= 15:
        mx["exam_finished"] = True
        mx["mock_page"] = "FINAL"
        mx["_show_exam_celebration"] = True
    else:
        mx["mock_page"] = "REPORT"


def render_mock_exam_shell() -> None:
    mx = mock_session()
    if mx["mock_page"] not in {"SURVEY", "TEST", "REPORT", "FINAL"}:
        mx["mock_page"] = "SURVEY"
        st.rerun()

    # If the user lands on the MOCK tab with the default ``mock_page="SURVEY"``
    # (e.g. tapping 모의고사 in the bottom nav without an explicit ``?mock=``
    # param) **and** they have a resumable exam, jump straight into the
    # test instead of forcing them through the survey again. This honors
    # the spec's "DO NOT reopen survey flow if resumable exam exists" rule
    # for every entry path, not just the home "이어하기" card.
    if mx["mock_page"] == "SURVEY" and has_resumable_exam(mx):
        mx["mock_page"] = "TEST"

    # Every MOCK entry reconciles ``current_idx`` vs ``results`` so stale
    # disk snapshots (idx stuck on a completed question) cannot replay Q1.
    if mx.get("current_exam"):
        reconcile_mock_exam_pointer(mx)

    if "mock_data" not in st.session_state:
        st.session_state.mock_data = {"recording_active": False}
    st.session_state.mock_data["recording_active"] = bool(mx["audio_bytes"])


def render_mock_flow() -> None:
    mx = mock_session()
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

    if mx.get("exam_finished") or mx.get("mock_page") == "FINAL":
        render_top_bar("종합 리포트", back_href="?nav=HOME", eyebrow="모의고사")
        from views.final_report import render_final_report

        render_final_report(mx)
        st.caption("© opictherapist")
        render_bottom_navigation()
        return

    if mx["mock_page"] == "SURVEY":
        _render_survey(mx)
    elif mx["mock_page"] == "TEST":
        _render_test(mx)
    elif mx["mock_page"] == "REPORT":
        _render_report(mx)

    st.caption("© opictherapist")
    render_bottom_navigation()


def _render_survey(mx: dict) -> None:
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
            )

            st.markdown("<p class='survey-label'>2. 현재 귀하는 어디에 살고 계십니까?</p>", unsafe_allow_html=True)
            housing = st.radio(
                "주거",
                ["홀로 거주", "가족과 함께 거주", "친구/룸메이트와 거주"],
                label_visibility="collapsed",
            )

            with st.expander("3) 여가 활동", expanded=True):
                leisure = st.multiselect(
                    "여가 활동",
                    [
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
                    ],
                    default=["영화 보기", "공원 가기"],
                    key="survey_leisure",
                )

        with col_right:
            with st.expander("4) 취미/관심사", expanded=True):
                interests = st.multiselect(
                    "취미/관심사",
                    ["음악 감상하기", "악기 연주하기", "요리하기", "혼자 노래 부르기", "글쓰기", "그림 그리기"],
                    default=["음악 감상하기", "요리하기"],
                    key="survey_interests",
                )

            with st.expander("5) 운동", expanded=True):
                sports = st.multiselect(
                    "운동",
                    ["조깅", "걷기", "자전거", "수영", "테니스", "축구", "농구", "야구", "골프", "헬스(Gym)", "요가", "운동을 전혀 하지 않음"],
                    default=["조깅", "걷기"],
                    key="survey_sports",
                )

            with st.expander("6) 여행", expanded=True):
                travel = st.multiselect(
                    "여행",
                    ["국내 여행", "해외 여행", "집에서 보내는 휴가(스테이케이션)"],
                    default=["국내 여행"],
                    key="survey_travel",
                )

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
    render_top_bar(
        f"Q{q_id} · {q.get('topic', '')}".strip(" ·"),
        back_href="?nav=MOCK&mock=SURVEY",
        eyebrow=f"모의고사 · {q_id}/{total}",
    )

    # Marker — activates the ``section.main:has(.mx-marker)`` Streamlit-widget
    # overrides in ``ui/styles.py`` (progress bar hidden, primary button
    # styled, expander cards). Stays invisible (``display:none`` via empty
    # element) so it only acts as a CSS sentinel.
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

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

    q_text = q["question"]
    voice_id = neural2_voice_for_session()

    mock_err_key = f"_mock_q_tts_err_{q_id}"
    pref_key = f"_mock_tts_pref_{q_id}_{voice_id}"
    fail_key = f"_mock_pref_fail_{q_id}"

    if pref_key not in st.session_state and not st.session_state.get(fail_key):
        try:
            st.session_state[pref_key] = tts_audio_cached(
                q_text,
                voice_id,
                DEFAULT_TTS_SPEAKING_RATE,
                DEFAULT_TTS_PITCH,
            )
            st.session_state.pop(mock_err_key, None)
        except Exception as e:
            st.session_state[fail_key] = True
            st.session_state[mock_err_key] = str(e)
            logger.warning("Mock exam TTS prefetch failed: %s: %s", type(e).__name__, e)

    # 3) Listen stage — branded label above the audio player.
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
            st.rerun()

    payload = st.session_state.get(pref_key)
    if isinstance(payload, dict) and payload.get("audio_bytes"):
        render_exam_question_audio_player(
            payload["audio_bytes"],
            payload.get("audio_format", "audio/mp3"),
            str(mx["exam_listen_nonce"]),
            int(q_id),
            max_plays=2,
        )

    st.markdown("</div>", unsafe_allow_html=True)

    # 4) Record stage — the dark-teal "studio" panel. The mic_recorder
    # component renders an iframe so we can only style the wrapper, but
    # the wrapper alone shifts the screen's emotional focus to recording.
    st.markdown(
        '<div class="mx-record-stage">'
        '<p class="mx-record-eyebrow">답변 녹음</p>'
        '<div class="mx-record-title">마이크 버튼을 눌러 답변을 시작하세요</div>'
        '<p class="mx-record-hint">'
        '준비가 되면 <b>답변 시작</b>을 누르고, 마치면 <b>녹음 완료</b>를 눌러 저장합니다.'
        '</p>',
        unsafe_allow_html=True,
    )

    from streamlit_mic_recorder import mic_recorder

    audio = mic_recorder(
        start_prompt="🎤 답변 시작 (클릭)",
        stop_prompt="⏹️ 녹음 완료 (클릭)",
        key=f"rec_{q_id}",
    )
    if audio and audio.get("bytes"):
        mx["recordings"][audio_key] = audio["bytes"]
        mx["audio_bytes"] = audio["bytes"]
    saved_audio = mx["audio_bytes"] or mx["recordings"].get(audio_key)

    if saved_audio:
        st.markdown(
            f'<div class="mx-record-saved">'
            f'녹음 저장됨 · {len(saved_audio):,} bytes'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="mx-record-empty">'
            '먼저 녹음을 완료해 주세요. 녹음이 저장되면 진단 버튼이 활성화됩니다.'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

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

    # 6) Primary CTA — restyled to mint pill via :has() scope (see ui/styles.py).
    in_flight = bool(st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY))
    if not st.button(
        "AI 테라피 진단받기",
        type="primary",
        use_container_width=True,
        disabled=(not bool(api_key)) or (not bool(saved_audio)) or in_flight,
        help=(
            "AI 분석이 진행 중이에요. 잠시만 기다려 주세요."
            if in_flight
            else None
        ),
    ):
        return

    _run_analysis(mx, q, q_id, audio_key, api_key)


def _run_analysis(mx: dict, q: dict, q_id: int, audio_key: str, api_key: str) -> None:
    """Drive Gemini analysis with smart retry + cross-session serialization.

    All the heavy lifting (process-wide lock, exponential backoff, transient
    vs. non-transient classification) lives in
    ``services.evaluation_service.analyze_audio_with_retry`` so this view
    only owns the state-machine transitions:

      * Missing audio        →  upsert ``no_audio`` row, navigate, reconcile
                                 pointer (next question index persisted).
      * Success              →  upsert result, navigate, reconcile pointer,
                                 clear recovery.
      * All retries exhausted  →  upsert ``analysis_pending`` row, advance
                                 exam pointer (recording kept in ``recordings``).

    A small re-entry guard (``_ANALYSIS_IN_FLIGHT_KEY``) makes the function
    idempotent within a single rerun — Streamlit is synchronous in practice
    but this defends against any unexpected re-entry from the recovery
    panel or rapid widget interactions.
    """
    if st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY):
        # An analysis is already running in this rerun's call chain; refuse
        # to start a second one. The user's audio is safe regardless.
        return

    st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = True
    try:
        mx["analysis_result"] = None
        mx["analysis_error_msg"] = ""
        mx["analysis_done"] = False
        mx["analysis_status"] = ""
        # CRITICAL: wipe any leftover transcript from a PREVIOUS question
        # before this attempt. If analysis fails or returns no speech, the
        # recovery panel must never surface the previous question's text
        # as if it belonged to this question.
        mx["preview_transcript"] = None

        blob = mx["audio_bytes"] or mx["recordings"].get(audio_key)
        if not blob:
            st.error("오디오 데이터가 유실되었습니다. 다시 녹음해주세요.")
            missing_audio_result = {
                "diagnosis_status": "no_audio",
                "error": "오디오 데이터 유실",
                "transcript": "",
                "estimated_level": "측정 불가",
                "estimated_level_display": "측정 불가",
                "summary_speech_rehab": "녹음 데이터가 전달되지 않아 분석을 진행할 수 없었습니다.",
                "prescription": "브라우저 마이크 권한 허용 후 3초 이상 다시 녹음해 주세요.",
                "wpm": 0,
                "sentence_count": 0,
                "word_count": 0,
                "fact_scores": {"text_type": 0, "accuracy": 0},
            }
            mx["analysis_result"] = missing_audio_result
            mx["last_result"] = missing_audio_result
            upsert_mock_exam_result(
                mx,
                {
                    "q_id": q["id"],
                    "question": q["question"],
                    "type": q["type"],
                    "topic": q.get("topic", ""),
                    "result": missing_audio_result,
                },
            )
            _nav_after_question_analysis(mx, q["id"])
            reconcile_mock_exam_pointer(mx)
            mx["analysis_done"] = True
            return

        difficulty = int(settings_session()["difficulty"])

        # ``st.status`` (vs ``st.spinner``) lets us push friendlier interim
        # messages while the retry loop is running. The label updates are
        # opacity-only so they never feel like a hard rerun.
        with st.status("AI가 발화를 진단 중입니다…", expanded=False) as status:

            def _on_status(stage: str, label: str) -> None:
                try:
                    status.update(label=label)
                except Exception:  # pragma: no cover — status UI is best-effort
                    logger.debug("status.update raised; ignoring (stage=%s)", stage)

            result, last_error, attempts = analyze_audio_with_retry(
                blob,
                q["question"],
                api_key,
                difficulty,
                on_status=_on_status,
            )

            try:
                if result is None:
                    status.update(
                        label="잠시 후 다시 시도해 주세요. 답변은 안전하게 저장되었습니다.",
                        state="error",
                    )
                else:
                    status.update(label="진단 완료", state="complete")
            except Exception:
                pass

        if result is None:
            err_kind = classify_analysis_error(last_error)
            logger.warning(
                "Gemini analysis exhausted retries q_id=%s attempts=%s kind=%s",
                q.get("id"),
                attempts,
                err_kind,
            )
            logger.warning("Gemini last_error detail (server log): %s", last_error)
            pending = build_analysis_pending_result(q, err_kind, attempts)
            mx["analysis_result"] = pending
            mx["last_result"] = pending
            upsert_mock_exam_result(
                mx,
                {
                    "q_id": q["id"],
                    "question": q["question"],
                    "type": q["type"],
                    "topic": q.get("topic", ""),
                    "result": pending,
                },
            )
            clear_pending_recovery(mx)
            _nav_after_question_analysis(mx, q["id"])
            reconcile_mock_exam_pointer(mx)
            mx["analysis_done"] = True
            mx["preview_transcript"] = None
            st.rerun()
            return

        # Unified trust gate: treat the answer as "no speech" if EITHER
        # the pipeline already flagged it OR the transcript fails the
        # view-boundary sanitizer (placeholder phrases, question-echo,
        # leaked JSON fragments, …). Either way we route through the
        # recovery flow with a calm "음성이 감지되지 않았어요" panel +
        # an explicit re-record affordance — never silently committing
        # an empty / fabricated transcript and advancing the exam.
        _pipeline_no_speech = bool(result.get("no_speech_detected")) or (
            result.get("diagnosis_status") == "no_speech"
        )
        _transcript_raw = (result.get("transcript") or "").strip()
        _transcript_is_real = bool(_transcript_raw) and is_real_speech_transcript(
            _transcript_raw
        )
        if _pipeline_no_speech or not _transcript_is_real:
            mark_pending_recovery(
                mx,
                q_id=int(q["id"]),
                audio_key=audio_key,
                error_message=NO_SPEECH_ERROR_SENTINEL,
                attempts=attempts,
                transcript_preview=None,
            )
            st.rerun()
            return

        result_to_store = cache_analysis_payload(result)
        mx["preview_transcript"] = _transcript_raw
        mx["analysis_result"] = result_to_store
        raw_parse_failed = (result_to_store.get("raw_text_parse_failed") or "").strip()
        if raw_parse_failed:
            st.error(raw_parse_failed)
        mx["last_result"] = result_to_store
        upsert_mock_exam_result(
            mx,
            {
                "q_id": q["id"],
                "question": q["question"],
                "type": q["type"],
                "topic": q.get("topic", ""),
                "result": result_to_store,
            },
        )
        _nav_after_question_analysis(mx, q["id"])
        reconcile_mock_exam_pointer(mx)
        mx["analysis_done"] = True
        clear_pending_recovery(mx)

        st.rerun()
    finally:
        # Always clear the flag so a future rerun starts fresh — even if
        # ``st.rerun()`` raised or the user navigated away mid-call.
        st.session_state[_ANALYSIS_IN_FLIGHT_KEY] = False


# ---------------------------------------------------------------------------
# Recovery panel — surfaced only while ``pending_recovery`` is set for the
# current question. Three actions; never destructive.
# ---------------------------------------------------------------------------

_RECOVERY_COPY: dict[str, tuple[str, str]] = {
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
        "AI 분석이 잠시 지연되고 있어요 🙏",
        "녹음과 진행 상황은 모두 안전하게 보관됐어요. "
        "‘다시 분석하기’를 눌러도 같은 문항에 그대로 머무릅니다.",
    ),
}


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
    audio_size = len(saved_audio) if saved_audio else 0
    is_no_speech = err_kind == "no_speech"

    # Different eyebrow / meta for the no-speech case — this isn't an AI
    # failure, it's an empty-state, so we don't show "AI 분석 일시 지연".
    eyebrow_text = "음성 미감지" if is_no_speech else "AI 분석 일시 지연"
    audio_meta = (
        "녹음 음성 미감지"
        if is_no_speech
        else f"녹음 {audio_size:,} bytes 보존됨"
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

    in_flight = bool(st.session_state.get(_ANALYSIS_IN_FLIGHT_KEY))
    c1, c2, c3 = st.columns(3)

    if is_no_speech:
        # No-speech branch: re-analysing the same silent audio would just
        # produce no_speech again, so the primary action is "re-record".
        # We deliberately drop the saved audio for this question so the
        # mic recorder comes back fresh — no stale or "leaked" audio.
        with c1:
            if st.button(
                "🎤 다시 녹음하기",
                key=f"recover_rerecord_{q_id}",
                type="primary",
                use_container_width=True,
            ):
                mx["audio_bytes"] = None
                mx["recordings"].pop(audio_key, None)
                mx["preview_transcript"] = None
                clear_pending_recovery(mx)
                st.rerun()
        with c2:
            if st.button(
                "⏸️ 잠시 후 시도",
                key=f"recover_pause_{q_id}",
                use_container_width=True,
            ):
                clear_pending_recovery(mx)
                st.rerun()
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
                _run_analysis(mx, q, q_id, audio_key, api_key)
    with c2:
        if st.button(
            "⏸️ 잠시 후 시도",
            key=f"recover_pause_{q_id}",
            use_container_width=True,
        ):
            # Hide the panel — audio and question state stay intact, the
            # regular test UI returns with the "AI 테라피 진단받기" button
            # ready for whenever the user is ready.
            clear_pending_recovery(mx)
            st.rerun()
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
        with st.expander("복원된 발화 미리보기", expanded=False):
            st.write(preview)

    # Last-resort technical detail, collapsed by default so it doesn't
    # crowd the friendly copy.
    err_msg = (pr.get("error_message") or "").strip()
    if err_msg:
        with st.expander("기술 상세", expanded=False):
            st.code(err_msg, language="text")


def _render_report(mx: dict) -> None:
    render_top_bar(
        "말하기 코칭",
        back_href="?nav=MOCK&mock=TEST",
        eyebrow="모의고사 · 코칭",
    )

    # Marker for the scoped Streamlit-widget overrides (button + expander).
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    _exam_run = mx.get("current_exam") or mx["exam"]
    if _exam_run:
        reconcile_mock_exam_pointer(mx)

    _latest_ok_coaching = False
    _last_i = -1
    if mx["results"]:
        _last_i = len(mx["results"]) - 1
        _lr = mx["results"][-1].get("result", {})
        _lq = mx["results"][-1].get("q_id")
        _heard_raw = (_lr.get("transcript") or "").strip()
        # Trust gate: AI-emitted no_speech OR sanitizer rejection both lead
        # to the friendly empty-state hero. We never render unknown text
        # as if it were the user's recorded speech.
        _no_speech = bool(_lr.get("no_speech_detected")) or (
            _lr.get("diagnosis_status") == "no_speech"
        )
        _has_real_speech = (
            bool(_heard_raw)
            and not _no_speech
            and is_real_speech_transcript(_heard_raw)
        )
        _latest_ok_coaching = _has_real_speech and _lr.get("diagnosis_status") == "ok"

        if _latest_ok_coaching:
            render_overall_coaching_hero(_lr, int(_lq))
            render_strong_points_cards(_lr)

        if _has_real_speech:
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
        elif _lr.get("diagnosis_status") == "analysis_pending":
            summ = html.escape((_lr.get("summary_speech_rehab") or "").strip())
            prev = html.escape((_lr.get("prescription") or "").strip())
            st.markdown(
                f"""
                <section class="mx-report-hero">
                  <p class="mx-rh-eyebrow">Q{_lq} · AI 분석 대기</p>
                  <div class="mx-rh-title">이번 답변은 아직 AI 피드백이 연결되지 않았어요</div>
                  <div class="mx-rh-transcript">{summ}</div>
                  <p class="mx-rh-transcript" style="margin-top:10px;font-size:0.95rem;">{prev}</p>
                </section>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <section class="mx-report-hero">
                  <p class="mx-rh-eyebrow">Q{_lq} · 음성 미감지</p>
                  <div class="mx-rh-title">음성이 감지되지 않았어요 🙏</div>
                  <div class="mx-rh-transcript">
                    이번 답변에서는 인식된 발화가 없습니다. 마이크가 켜져 있는지 확인하고
                    다시 한 번 또렷한 목소리로 답변해 보세요.
                  </div>
                </section>
                """,
                unsafe_allow_html=True,
            )

        if _latest_ok_coaching:
            render_grammar_and_expression_coaching(_heard_raw)
            render_native_upgrade_section(_lr)
            render_flow_coaching_section(_lr)
            _sum_rehab = (_lr.get("summary_speech_rehab") or "").strip()
            if _sum_rehab and len(_sum_rehab) > 160:
                with st.expander("AI 총평 전문", expanded=False):
                    st.write(_sum_rehab)
        elif _has_real_speech:
            render_grammar_and_expression_coaching(_heard_raw)
            _sum_rehab = (_lr.get("summary_speech_rehab") or "").strip()
            if _sum_rehab:
                st.caption(_sum_rehab[:280] + ("…" if len(_sum_rehab) > 280 else ""))
        elif _lr.get("diagnosis_status") == "analysis_pending":
            pass
        else:
            _sum_rehab = (_lr.get("summary_speech_rehab") or "").strip()
            if _sum_rehab:
                st.caption(_sum_rehab[:280] + ("…" if len(_sum_rehab) > 280 else ""))

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

    st.markdown('<div class="mx-section-h">이번 세션 문항 기록</div>', unsafe_allow_html=True)
    for i, item in enumerate(mx["results"]):
        if i == _last_i and _latest_ok_coaching:
            continue
        result = item.get("result", {})
        qid = item.get("q_id")
        label = f"Q{qid} | {item.get('type', '')} {item.get('topic', '')}".strip()
        with st.expander(label, expanded=False):
            if result.get("diagnosis_status") == "no_audio":
                st.error(result.get("error", "녹음 데이터 없음"))
                continue
            if result.get("diagnosis_status") == "api_error":
                st.error(result.get("error", "API 오류"))
                continue
            if result.get("diagnosis_status") == "analysis_pending":
                st.info(
                    (result.get("summary_speech_rehab") or "").strip()
                    + " "
                    + (result.get("prescription") or "").strip()
                )
                continue
            if "error" in result:
                st.error(result["error"])
                continue

            st.caption(item.get("question", "") or "")
            if qid == 1:
                st.info("몸 풀기 단계입니다. 본인의 바이브를 잘 점검해 보세요.")
            render_history_expander_coaching(item)

    _answered_report = count_completed_exam_prefix(mx)
    has_next = (_answered_report < len(_exam_run)) and not mx.get("exam_finished")

    render_coaching_retry_banner(has_next=has_next)
    render_coaching_cta_preamble(has_next=has_next)

    if has_next:
        col_secondary, col_primary = st.columns([1, 1])
        with col_primary:
            if st.button(
                "다음 단계로 계속하기",
                type="primary",
                use_container_width=True,
                key="report_next_q",
            ):
                # ``current_idx`` already advanced right after analysis; do not
                # increment again (double-advance used to skip a question).
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

    with st.expander("더 깊은 분석 (선택)", expanded=False):
        _render_precision_section(mx)
    st.subheader("🧪 에릭의 발화 정밀 처방전")
    st.caption("FACT 기반 냉철 분석 모드: 어휘 · 논리 · 내용 중복 · 문법")
    for idx, item in enumerate(mx["results"]):
        result = item.get("result", {})
        if result.get("diagnosis_status") != "ok":
            continue

        qid = item.get("q_id")
        transcript = (result.get("transcript") or "").strip()
        if not transcript:
            continue

        with st.expander(f"Q{qid} 정밀 처방", expanded=False):
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
                continue

            for row in lines:
                st.markdown(
                    f"- **{row['axis']}** | 현재 발화: {row['current']} | 에릭의 추천: {row['recommend']}"
                )
