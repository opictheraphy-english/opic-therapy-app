import google.generativeai as genai
import json
from bible import BIBLE_CONTENT


def _demo_diagnosis(question_text, difficulty=5):
    return {
        "diagnosis_status": "api_fallback",
        "transcript": "",
        "estimated_level": None,
        "fact_scores": {"function": 0, "accuracy": 0, "context": 0, "text_type": 0},
        "fact_feedback": {
            "function": "API 호출 실패로 채점 불가",
            "accuracy": "API 호출 실패로 채점 불가",
            "context": "API 호출 실패로 채점 불가",
            "text_type": "API 호출 실패로 채점 불가",
        },
        "breakdown": "API 호출 실패로 시제 붕괴 진단 불가",
        "acting_feedback": "API 호출 실패로 연기력 진단 불가",
        "prescription": (
            "AL로 가기 위한 마지막 한 걸음: 다시 녹음 후 재진단하세요."
            if int(difficulty) == 6
            else "IH 안착을 위한 시제 고정: 다시 녹음 후 재진단하세요."
        ),
        "model_used": "demo-mode",
    }


def list_available_gemini_models(api_key):
    genai.configure(api_key=api_key)
    models = []
    for m in genai.list_models():
        name = getattr(m, "name", "")
        methods = getattr(m, "supported_generation_methods", []) or []
        if "generateContent" in methods:
            models.append(name)
    return models


def analyze_audio_with_ai(audio_bytes, question_text, api_key, difficulty=5):
    if not audio_bytes or len(audio_bytes) < 4000:
        return {
            "diagnosis_status": "insufficient_speech",
            "transcript": "",
            "estimated_level": None,
            "breakdown": "발화량 부족으로 진단 불가",
            "acting_feedback": "발화량 부족으로 진단 불가",
            "prescription": "발화량 부족으로 진단 불가",
        }

    # 1. AI 설정 (명시적 v1beta 설정 없이 기본 안정 API 사용)
    genai.configure(api_key=api_key)
    primary_model = "gemini-1.5-flash"
    fallback_model = "gemini-1.5-flash-latest"

    # 2. 오디오 데이터를 제미나이가 읽을 수 있는 형식으로 준비
    audio_part = {
        "mime_type": "audio/wav",
        "data": audio_bytes
    }

    # 3. 에릭 노의 철학이 담긴 프롬프트 (STT 포함)
    target = "Level 6 (AL 목표)" if int(difficulty) == 6 else "Level 5 (IH 목표)"
    strictness = (
        "- Level 6: 시제 붕괴(Breakdown)와 정밀 어휘(Precise vocab)에 매우 엄격하게.\n"
        "- AL을 받기 위한 미세한 감점 포인트까지 집요하게 지적.\n"
        "- Initially-Specifically-Eventually 3단계 구조가 보이는지 체크.\n"
    ) if int(difficulty) == 6 else (
        "- Level 5: 발화량(유창성)과 문장 연결성에 집중.\n"
        "- 질문 의도에 맞는 Functions(Describe/Narrate) 수행 여부를 우선.\n"
        "- IH에서 흔한 시제 붕괴를 잡되, 과도한 고급어휘 강요는 금지.\n"
    )
    prompt = f"""
    당신은 오픽 전문가 '에릭 노'의 AI 조서입니다.
    제공된 오디오를 듣고 다음 지침에 따라 분석하세요.

    [목표 난이도]
    {target}

    [채점 엄격도]
    {strictness}

    [분석 지침]
    1. STT: 음성을 텍스트로 완벽하게 받아쓰세요.
    2. FACT 진단: {BIBLE_CONTENT}에 기반하여 Function, Accuracy, Context, Text Type을 평가하세요.
    3. 시제 붕괴(Breakdown): 과거 질문인데 현재 시제를 쓴 구간을 찾아 '원본 -> 교정' 형태로 적어주세요.
    4. 연기력(Acting): 'Eww', 'Oh man' 등 감탄사의 톤이 자연스러운지, 고민하는 흔적(Filler)이 있는지 평가하세요.

    [질문 정보]
    {question_text}

    [출력 형식]
    반드시 아래의 JSON 형식으로만 답변하세요. 다른 말은 하지 마세요.
    {{
        "transcript": "받아쓴 전체 텍스트",
        "estimated_level": "예상 등급",
        "fact_scores": {{
            "function": 0-100,
            "accuracy": 0-100,
            "context": 0-100,
            "text_type": 0-100
        }},
        "fact_feedback": {{
            "function": "Functions 코칭",
            "accuracy": "Accuracy 코칭",
            "context": "Context/Content 코칭",
            "text_type": "Text Type 코칭"
        }},
        "breakdown": "시제 오류 지점 및 설명",
        "acting_feedback": "연기력 및 인토네이션 피드백",
        "prescription": "에릭의 최종 처방전"
    }}
    """

    try:
        last_error = None
        for model_name in (primary_model, fallback_model):
            try:
                # 요청한 형식으로 표준화
                model = genai.GenerativeModel(model_name=model_name)
                # AI에게 음성과 프롬프트 전달
                # 무료 Quota 절약을 위해 출력 길이를 제한합니다.
                response = model.generate_content(
                    [prompt, audio_part],
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=300,
                        temperature=0.2,
                    ),
                )
                raw = (response.text or "").strip()
                cleaned = raw.replace("```json", "").replace("```", "").strip()
                # JSON 결과만 추출
                result = json.loads(cleaned)
                result.setdefault("diagnosis_status", "ok")
                result.setdefault("model_used", model_name)
                return result
            except Exception as inner_e:
                last_error = inner_e
                continue
        # API 호출이 모두 실패하면 즉시 데모 모드로 전환
        demo = _demo_diagnosis(question_text, difficulty=difficulty)
        demo["api_error"] = str(last_error) if last_error else "unknown_error"
        return demo
    except Exception as e:
        # 앱이 멈추지 않도록 데모 모드로 처리
        demo = _demo_diagnosis(question_text, difficulty=difficulty)
        demo["api_error"] = str(e)
        return demo


def analyze_answer(audio_data, question_text, api_key):
    return analyze_audio_with_ai(audio_data, question_text, api_key)
