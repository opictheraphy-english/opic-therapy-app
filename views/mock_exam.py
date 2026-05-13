"""모의고사 SURVEY / TEST / REPORT."""
from __future__ import annotations

import logging
import re
import secrets

import streamlit as st
from streamlit_mic_recorder import mic_recorder

from components.audio_player import render_exam_question_audio_player
from components.navigation import render_bottom_navigation
from components.visualizer import render_realtime_visualizer
from services.mock_exam.mock_exam_test_set_generator import generate_test_set
from views.final_report import render_final_report
from services.evaluation_service import analyze_audio_with_ai
from services.final_report_demo import seed_demo_final_report
from services.report_service import cache_analysis_payload
from services.tts_service import (
    DEFAULT_TTS_PITCH,
    DEFAULT_TTS_SPEAKING_RATE,
    clear_mock_question_tts_keys,
    neural2_voice_for_session,
    tts_audio_cached,
)
from utils.secrets import get_gemini_api_key
from utils.session_state import mock_session, settings_session, sync_settings_to_legacy
from utils.text_utils import DISCOURSE_MARKERS, PRECISION_MAP, keywords

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
        seed_demo_final_report(mx)
        mx["_demo_preview_loaded"] = True
        try:
            del st.query_params["preview_final"]
        except Exception:
            pass
        st.rerun()

    if mx.get("exam_finished") or mx.get("mock_page") == "FINAL":
        render_final_report(mx)
        st.caption("© opictherapist")
        render_bottom_navigation()
        return

    # --- [PAGE 2: SURVEY] 백그라운드 서베이 ---
    if mx["mock_page"] == "SURVEY":
        st.title("📋 Background Survey")
        st.write("당신의 상황에 맞는 답변을 선택해주세요. 이 선택에 따라 문제가 출제됩니다.")
        d1, d2 = st.columns([1, 2])
        with d1:
            if st.button(
                "📋 종합 리포트 미리보기 (데모)",
                help="녹음·시험 없이 최종 진단 리포트 화면만 확인합니다.",
                key="btn_preview_final_demo",
            ):
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
            for k in (
                "final_report_generated",
                "overall_estimated_level",
                "analytics_cache",
                "downloadable_report_bytes",
                "_analytics_sig",
                "_show_exam_celebration",
            ):
                mx.pop(k, None)
            # 서베이 결과를 로직에 전달
            mx["survey_results"] = {
                "work": work,
                "housing": housing,
                "leisure": leisure,
                "interests": interests,
                "sports": sports,
                "travel": travel,
                "difficulty": int(settings_session()['difficulty']),
            }
            _exam = generate_test_set(
                mx["survey_results"],
                difficulty=int(settings_session()['difficulty']),
            )
            mx["current_exam"] = _exam
            mx["exam"] = _exam
            mx["current_idx"] = 0
            mx["results"] = []
            mx["last_result"] = None
            mx["question_play_counts"] = {}
            mx["exam_listen_nonce"] = secrets.token_hex(8)
            clear_mock_question_tts_keys()
            mx["mock_page"] = "TEST"
            st.rerun()

    # --- [PAGE 3: TEST] 모의고사 진행 ---
    elif mx["mock_page"] == "TEST":
        api_key = get_gemini_api_key()
        if not api_key:
            st.warning("Gemini API Key가 없습니다. `.streamlit/secrets.toml` 또는 환경변수 `GEMINI_API_KEY`를 설정해주세요.")

        if not mx.get("exam_listen_nonce"):
            mx["exam_listen_nonce"] = secrets.token_hex(8)

        _exam_run = mx.get("current_exam") or mx["exam"]
        if not _exam_run:
            st.warning("시험지가 없습니다. 설문에서 「시험지 생성 및 시험 시작」을 눌러 주세요.")
            mx["mock_page"] = "SURVEY"
            mx["current_idx"] = 0
            st.rerun()

        q = _exam_run[mx["current_idx"]]
        q_id = q["id"]
        st.progress((mx["current_idx"] + 1) / len(_exam_run))
        left, right = st.columns([4, 1.6])
        with left:
            st.markdown('<div class="glass-card">', unsafe_allow_html=True)
            st.write(f"### Q{q_id} / {len(_exam_run)}")
            st.markdown(f"**[{q['type']}] {q.get('topic', '')}**")
            st.caption("정밀 언어 진단 센터 모드: 질문 텍스트 숨김 / 오디오 중심")
            st.markdown("</div>", unsafe_allow_html=True)
        with right:
            last_wpm = 0
            if mx["last_result"]:
                last_wpm = mx["last_result"].get("wpm", 0) or 0
            density = round((len(mx["audio_bytes"] or b"") / 1024), 1)
            st.markdown(
                f'<div class="glass-card"><b>Live Analytics</b><br/>WPM: <b>{last_wpm}</b><br/>Density: <b>{density} KB</b></div>',
                unsafe_allow_html=True,
            )

        q_text = q["question"]
        voice_id = neural2_voice_for_session()

        mock_err_key = f"_mock_q_tts_err_{q_id}"
        pref_key = f"_mock_tts_pref_{q_id}_{voice_id}"
        fail_key = f"_mock_pref_fail_{q_id}"

        # Prefetch once per question+voice (cached)
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

        st.caption("질문 음성은 **재생(▶) 시작마다** 횟수가 줄며, **문항당 최대 2회**까지 재생됩니다.")

        err_msg = st.session_state.get(mock_err_key)
        if err_msg:
            st.error(f"질문 음성을 만들 수 없습니다.\n\n{err_msg}")
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
        saved_audio = st.session_state.get(f"audio_{q_id}")
        # 실시간 마이크 반응형 비주얼라이저(AnalyserNode + canvas)
        render_realtime_visualizer(f"q{q_id}", auto_start=not bool(saved_audio))

        # 마이크 녹음기 (중앙 배치)
        audio = None
        audio_key = f"q_{q_id}"
        audio = mic_recorder(start_prompt="🎤 답변 시작 (클릭)", stop_prompt="⏹️ 녹음 완료 (클릭)", key=f"rec_{q_id}")
        if audio and audio.get("bytes"):
            mx["recordings"][audio_key] = audio["bytes"]
            mx["audio_bytes"] = audio["bytes"]
        saved_audio = mx["audio_bytes"] or mx["recordings"].get(audio_key)

        if saved_audio:
            st.caption(f"녹음 데이터 감지됨: {len(saved_audio)} bytes")
            logger.info("[audio-buffer] q=%s bytes=%s", q_id, len(saved_audio))
        else:
            st.info("먼저 녹음을 완료해주세요. 녹음이 저장되면 진단 버튼이 활성화됩니다.")

        status_box = st.empty()
        if mx["analysis_status"]:
            status_box.info(mx["analysis_status"])
        if mx["analysis_error_msg"]:
            st.error(mx["analysis_error_msg"])
            mx["analysis_error_msg"] = ""
        if mx["analysis_done"]:
            mx["analysis_done"] = False

        # 진단 버튼 (직접 호출 + 강제 페이지 전환)
        if st.button("AI 테라피 진단받기", disabled=(not bool(api_key))):
            mx["analysis_result"] = None
            mx["analysis_error_msg"] = ""
            mx["analysis_done"] = False
            mx["analysis_status"] = ""

            audio_key = f"q_{q_id}"
            blob = mx["audio_bytes"] or mx["recordings"].get(audio_key)

            if not blob:
                st.error("오디오 데이터가 유실되었습니다. 다시 녹음해주세요.")
                missing_audio_result = {
                    "diagnosis_status": "api_error",
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
                mx["results"].append(
                    {
                        "q_id": q["id"],
                        "question": q["question"],
                        "type": q["type"],
                        "topic": q.get("topic", ""),
                        "result": missing_audio_result,
                    }
                )
                _nav_after_question_analysis(mx, q["id"])
                mx["analysis_done"] = True
            else:
                with st.status("에릭 노 AI가 발화를 정밀 진단 중입니다...", expanded=True) as status:
                    status.write("🎤 1. 오디오 데이터 확인 완료")
                    status.write(f"📦 오디오 버퍼 크기: {len(blob)} bytes")
                    status.write("🧠 2. 제미나이 엔진 분석 시작...")
                    try:
                        result = analyze_audio_with_ai(
                            blob,
                            q["question"],
                            api_key,
                            int(settings_session()['difficulty']),
                        )

                        if not result or "error" in result:
                            status.update(label="❌ 분석 엔진 오류", state="error")
                            safe_result = result or {"error": "결과값이 비어있습니다."}
                            err_msg = (safe_result.get("error") or "결과값이 비어있습니다.").strip()
                            err_upper = err_msg.upper()
                            if "404" in err_upper or "NOT_FOUND" in err_upper or "엔진 경로" in err_msg:
                                st.error("엔진 경로 재설정 중")
                            elif "429" in err_upper or "RESOURCE_EXHAUSTED" in err_upper or "할당량 초과" in err_msg:
                                st.error("잠시 대기")
                            else:
                                st.error(f"상세 에러: {err_msg}")
                            available_models = safe_result.get("available_models") or []
                            if available_models:
                                st.error(f"사용 가능한 모델 예시: {available_models[0]}")
                            tried_models = safe_result.get("tried_models") or []
                            if tried_models:
                                st.caption(f"시도한 엔진: {', '.join(tried_models[:4])}")
                            safe_result.setdefault("diagnosis_status", "api_error")
                            safe_result.setdefault("transcript", f"(분석 실패 원문) {err_msg}")
                            safe_result.setdefault("estimated_level", "측정 불가")
                            safe_result.setdefault("estimated_level_display", "측정 불가")
                            safe_result.setdefault("summary_speech_rehab", f"분석 엔진 오류: {err_msg}")
                            safe_result.setdefault("prescription", "네트워크 상태를 확인하고, 3~5초 길이로 다시 녹음해 주세요.")
                            safe_result.setdefault("wpm", 0)
                            safe_result.setdefault("sentence_count", 0)
                            safe_result.setdefault("word_count", 0)
                            safe_result.setdefault("fact_scores", {"text_type": 0, "accuracy": 0})
                            result_to_store = safe_result
                        else:
                            status.write("✅ 3. 진단 완료! 리포트를 생성합니다.")
                            status.update(label="🚀 진단 완료! 화면 이동 중...", state="complete")
                            result_to_store = cache_analysis_payload(result)

                        mx["analysis_result"] = result_to_store
                        mx["preview_transcript"] = (result_to_store.get("transcript") or "").strip()
                        raw_parse_failed = (result_to_store.get("raw_text_parse_failed") or "").strip()
                        if raw_parse_failed:
                            st.error(raw_parse_failed)
                        mx["last_result"] = result_to_store
                        mx["results"].append(
                            {
                                "q_id": q["id"],
                                "question": q["question"],
                                "type": q["type"],
                                "topic": q.get("topic", ""),
                                "result": result_to_store,
                            }
                        )
                        _nav_after_question_analysis(mx, q["id"])
                        mx["analysis_done"] = True
                    except Exception as e:
                        status.update(label="❌ 시스템 치명적 오류", state="error")
                        st.error(f"에러 발생: {str(e)}")

                if mx["analysis_done"]:
                    st.rerun()

    # --- [PAGE 4: REPORT] 결과 리포트 ---
    elif mx["mock_page"] == "REPORT":
        st.header("🎯 AI 진단 결과 리포트")
        st.caption("Eric No Coaching Mode")

        _exam_run = mx.get("current_exam") or mx["exam"]

        if mx["results"]:
            _lr = mx["results"][-1].get("result", {})
            _lq = mx["results"][-1].get("q_id")
            _heard = (_lr.get("transcript") or "").strip()
            st.write("AI가 들은 내용:", _heard or "(없음)")

            st.subheader("📝 복원 발화 텍스트")
            st.text_area(
                f"Q{_lq} 상세",
                value=_heard or "(없음)",
                height=160,
                key=f"restored_transcript_q_{_lq}",
            )
            _sum_rehab = (_lr.get("summary_speech_rehab") or "").strip()
            if _sum_rehab:
                st.subheader("💬 총평 · Speech rehabilitation (발화 재활)")
                st.info(_sum_rehab)
            _raw_parse_failed = (_lr.get("raw_text_parse_failed") or "").strip()
            if _raw_parse_failed:
                st.error(_raw_parse_failed)
            _wpm = _lr.get("wpm")
            if isinstance(_wpm, (int, float)):
                st.caption(f"WPM: {_wpm} | 문장수: {_lr.get('sentence_count', 0)} | 단어수: {_lr.get('word_count', 0)}")

        api_error_count = sum(
            1
            for item in mx["results"]
            if item.get("result", {}).get("diagnosis_status") == "api_error"
        )
        if api_error_count:
            st.info(f"API 오류로 실패한 문항: {api_error_count}개")

        st.subheader("🧾 문항별 코칭 카드")
        for item in mx["results"]:
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
                if "error" in result:
                    st.error(result["error"])
                    continue

                st.markdown(f"**문제:** {item.get('question', '')}")
                if qid == 1:
                    st.info("몸 풀기 단계입니다. 본인의 바이브를 잘 점검해 보세요.")
                else:
                    display_level = result.get("estimated_level_display") or result.get("estimated_level", "N/A")
                    st.markdown(f"**Q{qid} 예상 등급:** {display_level}")
                if result.get("estimated_range"):
                    st.info(result["estimated_range"])

                wpm = result.get("wpm")
                word_count = result.get("word_count", 0)
                if isinstance(wpm, (int, float)):
                    st.markdown(f"**유창성(Velocity):** WPM {wpm}")
                fact_scores = result.get("fact_scores") or {}
                if isinstance(fact_scores, dict):
                    st.markdown(
                        f"**구조(Text Type) / 정확도(Accuracy):** "
                        f"Text Type {fact_scores.get('text_type', 0)} / Accuracy {fact_scores.get('accuracy', 0)}"
                    )
                if result.get("final_grade_score") is not None:
                    st.markdown(f"**최종 종합 점수:** {result.get('final_grade_score')}")
                if result.get("question_type"):
                    st.markdown(f"**질문 유형 분류:** {result.get('question_type')}")
                rubric_scores = result.get("rubric_scores") or {}
                if isinstance(rubric_scores, dict):
                    st.markdown(
                        f"**세부 점수:** "
                        f"Fluency {rubric_scores.get('fluency', 0)} / "
                        f"Lexical {rubric_scores.get('lexical', 0)} / "
                        f"Logic {rubric_scores.get('logic', 0)} / "
                        f"Grammar {rubric_scores.get('grammar', 0)}"
                    )

                st.subheader("🚨 시제 적절성 피드백")
                st.write(result.get("tense_appropriateness_feedback") or result.get("breakdown", "없음"))

                acting = (result.get("acting_feedback") or "").strip()
                if isinstance(wpm, (int, float)) and wpm >= 200:
                    if word_count < 120:
                        acting = "속도는 매우 빠르지만 암기 발화(Drone) 가능성이 있습니다. 감정선과 호흡, 강조 포인트를 분명히 분배하세요."
                    else:
                        acting = "초고속 발화 구간에서도 연기력과 감정 전달이 유지되는지 냉정하게 점검했습니다."
                st.subheader("🔥 연기력 피드백")
                st.write(acting or "연기력 피드백 데이터가 없습니다.")

                _sr = (result.get("summary_speech_rehab") or "").strip()
                if _sr:
                    st.subheader("💬 총평")
                    st.info(_sr)
                st.subheader("💊 에릭의 처방전")
                st.write(result.get("prescription", "처방전을 생성할 수 없습니다."))
                raw_parse_failed = (result.get("raw_text_parse_failed") or "").strip()
                if raw_parse_failed:
                    st.error(raw_parse_failed)

                transcript = (result.get("transcript") or "").strip()
                st.text_area(
                    f"Q{qid} 복원 텍스트",
                    value=transcript or "(비어 있음)",
                    height=120,
                    key=f"transcript_{qid}",
                )

        if st.button("처음으로 돌아가기"):
            st.session_state.page = "HOME"
            mx["mock_page"] = "SURVEY"
            mx["current_idx"] = 0
            mx["results"] = []
            mx["last_result"] = None
            mx["recordings"] = {}
            mx["audio_bytes"] = None
            mx["preview_transcript"] = None
            mx["question_play_counts"] = {}
            mx["exam"] = []
            mx["current_exam"] = []
            for k in (
                "exam_finished",
                "final_report_generated",
                "overall_estimated_level",
                "analytics_cache",
                "downloadable_report_bytes",
                "_analytics_sig",
                "_show_exam_celebration",
                "_final_report_demo",
                "_demo_preview_loaded",
            ):
                mx.pop(k, None)
            clear_mock_question_tts_keys()
            st.rerun()

        if mx["current_idx"] < len(_exam_run) - 1:
            if st.button("다음 문제 계속하기"):
                mx["current_idx"] += 1
                mx["audio_bytes"] = None
                mx["preview_transcript"] = None
                mx["mock_page"] = "TEST"
                st.rerun()

        # --- 에릭의 발화 정밀 처방전 ---
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

                # 1) Precision 어휘 교정
                for weak, better in PRECISION_MAP.items():
                    if re.search(rf"\b{re.escape(weak)}\b", lower):
                        lines.append({
                            "axis": "어휘 (Precision)",
                            "current": f"'{weak}'와 같은 평이한 단어 반복",
                            "recommend": f"{better} 같은 정밀 어휘로 교체해 표현 밀도를 높이세요.",
                        })

                # 2) 논리 구조 개선 (Text Type)
                text_type_score = (result.get("fact_scores") or {}).get("text_type", 0)
                marker_hit = any(m.lower() in lower for m in [m.lower() for m in DISCOURSE_MARKERS])
                if text_type_score < 60 or not marker_hit:
                    lines.append({
                        "axis": "논리 (Text Type)",
                        "current": "문장 연결이 단조롭거나 구조 전개가 약함",
                        "recommend": f"{', '.join(DISCOURSE_MARKERS[:4])} 등을 활용해 문장 간 전개를 분명히 하세요.",
                    })

                # 3) 앞선 문항과 내용 중복 감지
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
                        lines.append({
                            "axis": "내용 중복 (Repetition)",
                            "current": f"Q{prev.get('q_id')}와 소재/표현이 상당히 겹침",
                            "recommend": "동일한 소재의 반복은 평가에서 불리할 수 있습니다. 새로운 관점(인물·장소·갈등·결과)을 추가하세요.",
                        })
                        overlap_warned = True
                        break
                if not overlap_warned and len(cur_keys) < 8:
                    lines.append({
                        "axis": "내용 중복 (Repetition)",
                        "current": "핵심 소재 풀이 좁아 반복 위험이 높음",
                        "recommend": "소재 축을 넓혀 주세요: 감정 변화, 예외 상황, 교훈, 비교 관점을 하나씩 추가하세요.",
                    })

                # 4) 문법(Accuracy) 치명 오류 교정 우선
                breakdown = (result.get("breakdown") or "").strip()
                if breakdown and breakdown != "없음":
                    lines.append({
                        "axis": "문법 (Accuracy)",
                        "current": breakdown[:120] + ("..." if len(breakdown) > 120 else ""),
                        "recommend": "시제 붕괴/수 일치를 먼저 고정하세요. 핵심 동사 시제를 문단 끝까지 유지하는 훈련이 필요합니다.",
                    })

                # 고속인데 빈약한 내용의 냉철 코멘트
                wpm = result.get("wpm", 0)
                if isinstance(wpm, (int, float)) and wpm >= 200 and len(cur_keys) < 10:
                    lines.append({
                        "axis": "냉철 코멘트",
                        "current": "속도는 높지만 어휘·내용 밀도가 낮음",
                        "recommend": "단어 사용이 똑같고 논리 구조 미흡합니다. 속도보다 정보 밀도(근거/장면/결과)를 우선 보강하세요.",
                    })

                if not lines:
                    lines.append({
                        "axis": "종합",
                        "current": "큰 결함 없이 안정적",
                        "recommend": "현재 구조를 유지하되, 표현 다양성만 소폭 확장하면 상위 등급 안정화에 유리합니다.",
                    })

                for row in lines:
                    st.markdown(f"- **{row['axis']}** | 현재 발화: {row['current']} | 에릭의 추천: {row['recommend']}")

    st.caption("© opictherapist")
    render_bottom_navigation()
