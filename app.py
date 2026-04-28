import streamlit as st
import os
from streamlit_mic_recorder import mic_recorder
from logic import generate_test_set
import plotly.graph_objects as go
from evaluator import analyze_audio_with_ai

# --- 설정 및 디자인 ---
st.set_page_config(page_title="OPIc Therapy Clinic", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stButton>button { width: 100%; border-radius: 12px; height: 3em; font-weight: bold; }
    .clinic-card { background: white; padding: 30px; border-radius: 20px; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); border-top: 5px solid #2563eb; }
    .survey-label { font-size: 1.2rem; font-weight: 600; color: #1e293b; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)


def get_api_key():
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        secret_key = None
    return secret_key or os.getenv("GEMINI_API_KEY")


# --- 세션 상태 관리 (페이지 이동 로직) ---
if 'page' not in st.session_state:
    st.session_state.page = "HOME"  # HOME, SURVEY, TEST, REPORT
if 'survey_results' not in st.session_state:
    st.session_state.survey_results = {}
if 'exam' not in st.session_state:
    st.session_state.exam = []
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0
if 'results' not in st.session_state:
    st.session_state.results = []
if 'last_result' not in st.session_state:
    st.session_state.last_result = None
if 'recordings' not in st.session_state:
    st.session_state.recordings = {}
if 'analysis_status' not in st.session_state:
    st.session_state.analysis_status = ""
if 'difficulty' not in st.session_state:
    st.session_state.difficulty = 5

# --- [PAGE 1: HOME] 대기 화면 ---
if st.session_state.page == "HOME":
    st.image("https://images.unsplash.com/photo-1505751172876-fa1923c5c528?auto=format&fit=crop&q=80&w=1280", use_column_width=True)
    st.title("🏥 OPIc Therapy AI Clinic")
    st.write("### 당신의 오픽 등급을 치료해 드립니다.")
    st.write("실제 시험과 동일한 환경에서 서베이를 진행하고 AI 진단을 받아보세요.")

    with st.container(border=True):
        st.subheader("🎚️ Self-Assessment (난이도 설정)")
        difficulty = st.radio(
            "난이도",
            [5, 6],
            format_func=lambda v: (
                "레벨 5 (IH 목표): 유창한 발화와 시제 관리를 집중적으로 훈련합니다."
                if v == 5
                else "레벨 6 (AL 목표): 완벽한 시제 일관성과 고난도 시사 이슈 대응력을 평가합니다."
            ),
            horizontal=True,
        )
        st.session_state.difficulty = int(difficulty)

    if st.button("모의고사 시작하기 (서베이 이동)"):
        st.session_state.page = "SURVEY"
        st.rerun()

# --- [PAGE 2: SURVEY] 백그라운드 서베이 ---
elif st.session_state.page == "SURVEY":
    st.title("📋 Background Survey")
    st.write("당신의 상황에 맞는 답변을 선택해주세요. 이 선택에 따라 문제가 출제됩니다.")

    with st.container(border=True):
        st.subheader("🎚️ Self-Assessment (난이도 설정)")
        difficulty = st.radio(
            "난이도",
            [5, 6],
            index=0 if int(st.session_state.difficulty) == 5 else 1,
            format_func=lambda v: (
                "레벨 5 (IH 목표): 유창한 발화와 시제 관리를 집중적으로 훈련합니다."
                if v == 5
                else "레벨 6 (AL 목표): 완벽한 시제 일관성과 고난도 시사 이슈 대응력을 평가합니다."
            ),
            horizontal=True,
            key="difficulty_survey",
        )
        st.session_state.difficulty = int(difficulty)

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
        # 서베이 결과를 로직에 전달
        st.session_state.survey_results = {
            "work": work,
            "housing": housing,
            "leisure": leisure,
            "interests": interests,
            "sports": sports,
            "travel": travel,
            "difficulty": int(st.session_state.difficulty),
        }
        st.session_state.exam = generate_test_set(
            st.session_state.survey_results,
            difficulty=int(st.session_state.difficulty),
        )
        st.session_state.current_idx = 0
        st.session_state.results = []
        st.session_state.last_result = None
        st.session_state.page = "TEST"
        st.rerun()

# --- [PAGE 3: TEST] 모의고사 진행 ---
elif st.session_state.page == "TEST":
    api_key = get_api_key()
    if not api_key:
        st.warning("Gemini API Key가 없습니다. `.streamlit/secrets.toml` 또는 환경변수 `GEMINI_API_KEY`를 설정해주세요.")

    q = st.session_state.exam[st.session_state.current_idx]
    st.progress((st.session_state.current_idx + 1) / len(st.session_state.exam))
    st.write(f"### Q{q['id']} / {len(st.session_state.exam)}")
    st.markdown(f"**[{q['type']}] {q.get('topic', '')}**")
    st.write(q['question'])

    # 마이크 녹음기 (중앙 배치)
    audio = mic_recorder(start_prompt="🎤 답변 시작 (클릭)", stop_prompt="⏹️ 녹음 완료 (클릭)", key=f"rec_{q['id']}")
    audio_key = f"q_{q['id']}"
    if audio and audio.get("bytes"):
        st.session_state.recordings[audio_key] = audio["bytes"]
    saved_audio = st.session_state.recordings.get(audio_key)

    if saved_audio:
        st.audio(saved_audio)  # 내가 녹음한 것 들어보기
        st.caption(f"녹음 데이터 감지됨: {len(saved_audio)} bytes")
    else:
        st.info("먼저 녹음을 완료해주세요. 녹음이 저장되면 진단 버튼이 활성화됩니다.")

    status_box = st.empty()
    if st.session_state.analysis_status:
        status_box.info(st.session_state.analysis_status)

    # 진단 버튼
    if st.button("AI 테라피 진단받기", disabled=(not bool(api_key) or not bool(saved_audio))):
        if not saved_audio:
            st.error("녹음 데이터가 없습니다. 다시 녹음 후 시도해주세요.")
        else:
            try:
                st.session_state.analysis_status = "AI 분석 시작됨..."
                status_box.info(st.session_state.analysis_status)
                with st.spinner("에릭의 AI가 당신의 목소리를 분석 중입니다..."):
                    result = analyze_audio_with_ai(
                        saved_audio,
                        q['question'],
                        api_key,
                        difficulty=int(st.session_state.difficulty),
                    )

                st.session_state.analysis_status = "API 응답 완료됨..."
                status_box.success(st.session_state.analysis_status)

                if "error" not in result:
                    # 결과를 세션에 저장
                    st.session_state.last_result = result
                    st.session_state.results.append(
                        {
                            "q_id": q["id"],
                            "question": q["question"],
                            "type": q["type"],
                            "topic": q.get("topic", ""),
                            "result": result,
                        }
                    )
                    st.session_state.page = "REPORT"
                    st.rerun()
                else:
                    st.error(f"API 오류 발생: {result['error']}")
                    st.session_state.analysis_status = ""
            except Exception as e:
                st.error(f"API 오류 발생: {e}")
                st.session_state.analysis_status = ""

# --- [PAGE 4: REPORT] 결과 리포트 ---
elif st.session_state.page == "REPORT":
    st.header("🎯 AI 진단 결과 리포트")
    st.caption("Eric No Coaching Mode: FACT + Breakdown + AL 3-Step")
    valid_results = [
        item["result"] for item in st.session_state.results
        if item.get("result", {}).get("diagnosis_status") == "ok"
        and "error" not in item.get("result", {})
    ]
    insufficient_count = sum(
        1
        for item in st.session_state.results
        if item.get("result", {}).get("diagnosis_status") == "insufficient_speech"
    )

    if not valid_results:
        st.warning("발화량 부족으로 진단 불가")
    else:
        # 난이도/목표 달성률
        target_level = "AL" if int(st.session_state.difficulty) == 6 else "IH"
        st.info(f"선택 난이도: Level {int(st.session_state.difficulty)} | 목표: {target_level}")

        level_order = ["IM1", "IM2", "IM3", "IH", "AL"]
        level_rank = {lvl: i for i, lvl in enumerate(level_order)}
        level_counts = {level: 0 for level in level_order}
        breakdowns = []
        acting_feedbacks = []
        prescriptions = []

        for result in valid_results:
            level = result.get("estimated_level")
            if level in level_counts:
                level_counts[level] += 1
            if result.get("breakdown"):
                breakdowns.append(result["breakdown"])
            if result.get("acting_feedback"):
                acting_feedbacks.append(result["acting_feedback"])
            if result.get("prescription"):
                prescriptions.append(result["prescription"])

        final_level = max(level_counts, key=level_counts.get) if any(level_counts.values()) else "평가 보류"
        level_sequence = [r.get("estimated_level") for r in valid_results if r.get("estimated_level") in level_order]
        latest_level = level_sequence[-1] if level_sequence else "평가 보류"
        start_level = level_sequence[0] if level_sequence else "평가 보류"

        col_a, col_b, col_c = st.columns(3)
        col_a.metric("최종 예상 등급", final_level)
        col_b.metric("첫 유효 등급", start_level)
        col_c.metric("마지막 유효 등급", latest_level)

        target_rank = level_rank.get(target_level, 0)
        achieved = [
            r for r in valid_results
            if level_rank.get(r.get("estimated_level"), -1) >= target_rank
        ]
        achievement_rate = round((len(achieved) / len(valid_results)) * 100, 1) if valid_results else 0
        st.progress(min(achievement_rate, 100.0) / 100.0)
        st.write(f"목표 달성률: **{achievement_rate}%** (목표 이상 문항 {len(achieved)}/{len(valid_results)})")

        if insufficient_count:
            st.info(f"발화량 부족으로 제외된 문항: {insufficient_count}개")

        fig = go.Figure(
            data=[
                go.Bar(x=list(level_counts.keys()), y=list(level_counts.values()))
            ]
        )
        fig.update_layout(title="등급 분포", xaxis_title="등급", yaxis_title="문항 수")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("📚 강의형 총평")
        if final_level in ["IM1", "IM2", "IM3"]:
            st.markdown("- **Function**: 질문 의도에는 답하지만 스토리 전개가 짧습니다.")
            st.markdown("- **Text Type**: 문장 나열 비중이 높아 단락화가 약합니다.")
            st.markdown("- **처방**: `Initially → Specifically → Eventually` 3단계 구조로 한 답변 40초 이상 확장하세요.")
        elif final_level == "IH":
            st.markdown("- **강점**: 스토리 전개 의지가 있고 확장 시도가 좋습니다.")
            st.markdown("- **위험**: 과거 설명 중 현재 시제로 복귀하는 Breakdown 가능성이 남아 있습니다.")
            st.markdown("- **처방**: 과거 답변 시작 시 동사 시제를 끝까지 과거로 고정하세요.")
        elif final_level == "AL":
            st.markdown("- **강점**: 응답 구조와 논리 흐름이 안정적입니다.")
            st.markdown("- **개선**: 정밀 어휘와 연기형 감탄사를 더 자연스럽게 섞으면 완성도가 올라갑니다.")
            st.markdown("- **처방**: 비교/시사 문항에서 근거 2개 + 반례 1개 패턴을 고정 훈련하세요.")
        else:
            st.markdown("- 유효한 등급 데이터가 부족합니다. 발화량을 늘려 다시 진단해보세요.")

        st.subheader("🚨 시제 붕괴 피드백")
        if breakdowns:
            for text in breakdowns[:5]:
                st.error(text)
        else:
            st.success("명확한 시제 붕괴 포인트가 감지되지 않았습니다.")

        st.subheader("🔥 연기력 피드백")
        if acting_feedbacks:
            st.write(acting_feedbacks[-1])
        else:
            st.write("연기력 피드백 데이터가 없습니다.")

        st.subheader("💊 에릭의 처방전")
        if int(st.session_state.difficulty) == 6:
            st.write("AL로 가기 위한 마지막 한 걸음")
        else:
            st.write("IH 안착을 위한 시제 고정")
        st.write(prescriptions[-1] if prescriptions else "처방전을 생성할 수 없습니다.")

        st.subheader("🧾 문항별 코칭 카드")
        for item in st.session_state.results:
            result = item.get("result", {})
            label = f"Q{item.get('q_id')} | {item.get('type', '')} {item.get('topic', '')}".strip()
            with st.expander(label, expanded=False):
                if result.get("diagnosis_status") == "insufficient_speech":
                    st.warning("발화량 부족으로 진단 불가")
                    continue
                if result.get("diagnosis_status") == "api_fallback":
                    st.warning("API 호출 실패로 자동 데모 모드가 적용되었습니다. 이 결과는 실제 채점이 아닙니다.")
                    continue
                if "error" in result:
                    st.error(result["error"])
                    continue

                st.markdown(f"**문제:** {item.get('question', '')}")
                st.markdown(f"**예상 등급:** {result.get('estimated_level', 'N/A')}")
                st.markdown(f"**Breakdown:** {result.get('breakdown', '없음')}")
                st.markdown(f"**Acting Feedback:** {result.get('acting_feedback', '없음')}")
                st.markdown(f"**Prescription:** {result.get('prescription', '없음')}")
                fact_scores = result.get("fact_scores")
                if isinstance(fact_scores, dict):
                    st.markdown(
                        f"**FACT 점수** - F:{fact_scores.get('function', 0)} / "
                        f"A:{fact_scores.get('accuracy', 0)} / "
                        f"C:{fact_scores.get('context', 0)} / "
                        f"T:{fact_scores.get('text_type', 0)}"
                    )
                transcript = result.get("transcript", "")
                if transcript:
                    st.text_area(
                        f"Q{item.get('q_id')} STT",
                        transcript,
                        height=120,
                        key=f"transcript_{item.get('q_id')}",
                    )

    if st.button("처음으로 돌아가기"):
        st.session_state.page = "HOME"
        st.session_state.current_idx = 0
        st.session_state.results = []
        st.session_state.last_result = None
        st.session_state.recordings = {}
        st.rerun()

    if st.session_state.current_idx < len(st.session_state.exam) - 1:
        if st.button("다음 문제 계속하기"):
            st.session_state.current_idx += 1
            st.session_state.page = "TEST"
            st.rerun()
