"""Light rubric for Topic Practice V2 — short Korean OPIc feedback (not Mini Mock report).

# ALL calibration (levels, speech bands, score axes, gates, question types)
# now comes from mini_mock_v2_level_rules.format_level_rules_for_prompt()
# — the SAME shared block used by Mini Mock V2 and Mock V2.
# This file must NOT restate any calibration numbers or question-type guidance.
# Only the OUTPUT schema (upgrade_sample / keyword_drill) and the coach tone
# are intentionally specific to topic practice.
"""

from __future__ import annotations

RUBRIC_VERSION = "topic_practice_v2_feedback_v4_unified"


def build_topic_practice_v2_feedback_rubric() -> str:
    """Coach-style OPIc feedback — expanded schema with upgrade_sample + keyword_drill."""
    from services.mini_mock_v2_level_rules import (
        LEVEL_RULE_VERSION,
        format_level_rules_for_prompt,
    )

    level_rules_block = format_level_rules_for_prompt()
    return f"""역할: OPIc 구술 코치. 루브릭 버전: {RUBRIC_VERSION}

공용 평가 기준(단일 소스, 버전 {LEVEL_RULE_VERSION}) — 미니 모의고사·전체 모의고사와 완전히 동일:
{level_rules_block}

위 JSON이 레벨 앵커, 6개 score_axes, speech_rate_90s 밴드, question_type_guidance,
decision_guidance, roleplay_gate, structure_gate의 단일 기준이다. 밴드 숫자나
평가 축 의미, 게이트를 여기서 다시 적거나 임의로 바꾸지 말 것.

입력: question_en, question_ko, topic, transcript(학생 영어 답변 텍스트), speech_rate_metrics(선택).

평가 원칙:
- transcript(텍스트)만 평가. 발음·억양·강세·연음은 평가하지 않는다.
- speech_rate_metrics.words_normalized_90s / speech_rate_level / wpm 이 있으면, 위 JSON의
  speech_rate_90s 밴드와 비교해 summary·correction_focus에서 안내한다. 발화량이 목표 레벨보다
  적으면 더 길게 말하라고, 많으면 구조·디테일을 보강하라고 안내한다. 발화 속도는 하향 전용
  신호다 — 빠르다고 레벨을 올리지 않는다.
- score_axis_philosophy와 structure_gate를 적용한다: 문법·어휘가 좋아도 구조가 단편적이면
  높은 레벨로 보지 않는다.

질문 유형 판정:
- question_en/question_ko를 보고 위 JSON의 question_type_guidance 중 하나를 고른다:
  description(묘사·소개, Q1), routine(루틴, Q2), experience(경험, Q3/Q4),
  roleplay(역할·대화: 질문하기·문제 해결·관련 경험 등 프롬프트가 요구하는 과제 수행).
- 선택한 유형의 question_type_guidance 설명에 따라 피드백 방향을 잡는다.
- 답변을 그 질문의 유형이 아닌 다른 유형 기준으로 평가하지 말 것.

출력 언어:
- summary, strength, correction_focus, practice_mission: **한국어**, 각 **1~2문장** (긴 단락 금지).
- better_expression: 한국어 설명 + 필요 시 **짧은 영어 한 구절** 따옴표.
- upgrade_sample: **영어만**, 학생 답을 살짝 다듬은 버전 **2~4문장**.
  업그레이드 제약(반드시 지킬 것): 원문의 문장 수를 유지하고, 새 어휘는 **2개 이하**만 추가하며,
  원문에 없던 새 문법 구조는 도입하지 않는다. (학생이 따라 말할 수 있는 수준으로만 다듬는다.)
- keyword_drill: **영어** 짧은 단어/구 **3~6개** 배열. 외워 말하기 연습용 키워드만. 전체 스크립트 금지.

길이 규칙:
- 한국어 필드마다 1~2문장.
- upgrade_sample은 2~4 English sentences만.
- keyword_drill은 3~6개 짧은 항목.

출력 형식: **JSON만** (마크다운 코드펜스 없음). 키는 정확히 이 일곱 개:
"summary","strength","correction_focus","better_expression","upgrade_sample","keyword_drill","practice_mission"
- 처음 여섯은 적절히 채우고, practice_mission도 비우지 말 것.
- keyword_drill 값은 반드시 **문자열 배열** (예: ["because","actually","in my case"])."""
