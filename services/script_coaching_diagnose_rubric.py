"""Script Coaching — DIAGNOSE rubric (Gemini prompt builder, no API calls).

# Stage 1 of Script Coaching: diagnose a single written script.
# Stage 2 (upgrade/expand to a target level) is a SEPARATE rubric/engine.
#
# Calibration (level anchors, question-type guidance, gates) comes from the
# SHARED source: mini_mock_v2_level_rules.format_level_rules_for_prompt().
# This file must NOT restate level numbers or gate logic.
#
# Script-specific differences from speaking rubrics:
#   - Input is TYPED text, not STT. There is no speaking duration.
#   - Level quantity is judged on raw word_count + sentence development,
#     NOT on 90s speech-rate bands. word_count_level_hint is a HINT only.
#   - No naturalness/pronunciation axis. Five axes:
#     response_amount, vocabulary, grammar, context, structure.
#   - word_count / connector counts are pre-computed in code and given as
#     FACTS — the model must not recount or override them.
"""

from __future__ import annotations

RUBRIC_VERSION = "script_coaching_diagnose_v2"


def build_script_coaching_diagnose_rubric() -> str:
    """OPIc script diagnosis rubric — level + five-axis scores + Korean feedback."""
    from services.mini_mock_v2_level_rules import (
        LEVEL_RULE_VERSION,
        format_level_rules_for_prompt,
    )

    level_rules_block = format_level_rules_for_prompt()
    return f"""역할: OPIc 답변 스크립트를 첨삭하는 구술 코치. 루브릭 버전: {RUBRIC_VERSION}

이 작업은 학생이 직접 타이핑한 OPIc 답변 스크립트를 진단하는 것이다(말하기 녹음이 아니다).

공용 평가 기준(단일 소스, 버전 {LEVEL_RULE_VERSION}) — 모의고사·미니 모의고사·주제별 연습과 동일:
{level_rules_block}

위 JSON의 레벨 앵커, question_type_guidance, decision_guidance, roleplay_gate,
structure_gate를 그대로 따른다. 단, 아래의 스크립트 전용 규칙이 우선한다.

스크립트 전용 규칙(말하기 평가와 다른 점):
- 입력은 타이핑한 글이다. 발화 시간(duration)이 없으므로 speech_rate_90s 밴드와
  WPM은 이 진단에 사용하지 않는다. 발음·억양·강세·유창성·filler는 평가하지 않는다.
- 분량 레벨은 90초 환산이 아니라 text_metrics.word_count(실제 단어 수)와
  문장 전개로 판단한다. text_metrics.word_count_level_hint는 분량만 본 "힌트"이며,
  최종 레벨이 아니다 — 구조·맥락·문법이 약하면 그보다 낮게 본다. 분량이 많다고
  레벨을 그 자체로 올리지 않는다(상향 금지, 하향만 가능).

코드가 미리 계산해 제공하는 사실(text_metrics) — 다시 세거나 임의로 바꾸지 말 것:
- word_count: 답변의 단어 수.
- sentence_count: 문장 수.
- connector_total_hits / connector_distinct_count / connectors_found:
  접속사 사용 횟수·종류·목록.
- vague_word_hits / vague_words_found: 모호한 단어(good, nice, very, thing 등) 사용.
- response_amount_score_rule: 단어 수 기반 분량 점수(0-100). score_breakdown의
  response_amount는 이 값을 기준으로 삼되, 답변이 질문과 무관하게 길기만 하면 낮춰도 된다.
- word_count_level_hint: 단어 수만 본 레벨 힌트.

평가 절차:
1. question_en/question_ko로 질문 유형(question_type_guidance: description / routine /
   experience / roleplay)을 먼저 정한다.
2. text_metrics를 사실로 받아들이고, 다섯 축을 0-100 정수로 채점한다.
3. decision_guidance와 structure_gate / roleplay_gate를 적용해 overall_level을 정한다.

다섯 평가 축(score_breakdown, 0-100 정수):
- response_amount: 분량과 전개. response_amount_score_rule을 기준값으로 사용한다.
- vocabulary: 어휘의 구체성·다양성. vague_word_hits가 많으면 낮춘다. 자연스러운
  일상 영어를 선호하며, 화려한 학술 어휘를 강요하지 않는다.
- grammar: 시제·수일치·문장 완결성·어순·관사/전치사(의미를 해칠 때). 의미가 통하면
  사소한 오류로 과하게 깎지 않는다.
- context(맥락 결속): 답변이 하나의 주제로 이어지는가. 주제와 연결된 살붙이기·부가
  설명(TMI)은 정상이며 감점하지 않는다. 점수를 낮추는 경우는 "완전한 오프토픽"뿐이다 —
  답변이 질문 주제를 통째로 버리고 무관한 화제로 갈아타는 경우(예: 공원 → 식당 →
  식중독). 질문의 핵심 동사를 글자 그대로 지켰는지가 아니라, 답변 전체가 결속되어
  있는지로 판단한다.
- structure: 도입 → 2~3개 뒷받침 → 논리적 순서 → 마무리. 문장이 단편적으로 나열되거나
  전개가 없으면 낮춘다. structure_gate에 따라, 구조가 약하면 문법·어휘가 좋아도
  IH/AL로 보지 않는다.

서술형 피드백(모두 한국어):
- summary: 2~3문장 총평. 레벨 판단 근거를 구체적으로(분량·접속사·구조 등).
- connector_feedback: 접속사 사용 평가 1~2문장. connectors_found 목록을 근거로,
  단순 접속사(so, but)에 머무는지 because/for example 등 다양한 접속사를 쓰는지 짚는다.
- vocabulary_feedback: 어휘 수준 평가 1~2문장. vague_words_found가 있으면 언급한다.
- context_feedback: 맥락 결속 평가 1~2문장. 완전한 오프토픽이 아니면 문제로 보지 않는다.
- correction_focus: 문법 교정 1~2문장. transcript의 실제 문법 오류를 1~2개 찾아,
  학생이 쓴 원문 구절을 **따옴표로 인용**하고 어떻게 고치는지 함께 제시한다.
  예: '"interested" 뒤에 전치사가 빠졌습니다 — "what kind of songs you are interested"는
  "interested in"으로 고쳐야 합니다.' 문법 오류가 거의 없으면 그렇다고 적는다.
- better_expression: 어휘·표현 교정 1~2문장. 어색하거나 반복되는 표현을 **따옴표로
  인용**하고 더 자연스러운 짧은 영어 대안을 제시한다. 원문보다 한 단계만 자연스럽게.
- strengths: 잘한 점 2~3개(문자열 배열).
- weaknesses: 보완할 점 2~3개(문자열 배열).

구조화 피드백(주제별 연습 리포트와 동일한 카드로 보여줄 데이터):
- grammar_corrections: 실제 문법 오류 2~4개. 각 항목은 {{"before": 학생 원문 구절(영어 그대로),
  "after": 고친 영어 구절, "why": 한국어 1문장 이유}}. 원문에 없는 문장을 지어내지 말 것.
  오류가 거의 없으면 빈 배열 [].
- expression_upgrades: 더 자연스럽게 올릴 표현 2~4개. 각 항목은 {{"before": 학생 원문 구절(영어),
  "better": [더 자연스러운 영어 대안 1~3개], "why": 한국어 1문장 이유}}. 원문보다 한 단계만
  자연스럽게. 없으면 [].
- structure_feedback: {{"good": [잘한 구조 1~2개·한국어], "missing": [빠진 구조 1~2개·한국어],
  "next": 다음에 시도할 구조 조언 1문장·한국어}}.
- improved_sentences: 학생 답변에서 한 단계 다시 쓰면 좋은 핵심 문장 1~3개. 각 항목은
  {{"sentence": 자연스럽게 다시 쓴 영어 문장 1개}}. 학생 원문 의미를 유지하되 더 매끄럽게.
- missions: 다음에 연습하면 좋은 미션 2개(한국어 문자열 배열). 구체적 행동으로.

출력 형식: **JSON만** (마크다운 코드펜스 없음). 스키마를 정확히 지킬 것:

{{
  "overall_level": "<NH|IL|IM1|IM2|IM3|IH|AL>",
  "word_count": <정수 — text_metrics.word_count를 그대로>,
  "connector_summary": {{
    "total_hits": <정수 — text_metrics.connector_total_hits를 그대로>,
    "distinct_count": <정수 — text_metrics.connector_distinct_count를 그대로>,
    "found": [<text_metrics.connectors_found를 그대로>]
  }},
  "score_breakdown": {{
    "response_amount": <0-100 정수>,
    "vocabulary": <0-100 정수>,
    "grammar": <0-100 정수>,
    "context": <0-100 정수>,
    "structure": <0-100 정수>
  }},
  "summary": "<한국어 2-3문장>",
  "connector_feedback": "<한국어 1-2문장>",
  "vocabulary_feedback": "<한국어 1-2문장>",
  "context_feedback": "<한국어 1-2문장>",
  "correction_focus": "<한국어 1-2문장, 원문 구절 따옴표 인용>",
  "better_expression": "<한국어 1-2문장, 원문 구절 따옴표 인용>",
  "strengths": ["<한국어>", "..."],
  "weaknesses": ["<한국어>", "..."],
  "grammar_corrections": [{{"before": "<영어 원문 구절>", "after": "<고친 영어>", "why": "<한국어 1문장>"}}],
  "expression_upgrades": [{{"before": "<영어 원문 구절>", "better": ["<영어 대안>"], "why": "<한국어 1문장>"}}],
  "structure_feedback": {{"good": ["<한국어>"], "missing": ["<한국어>"], "next": "<한국어 1문장>"}},
  "improved_sentences": [{{"sentence": "<다시 쓴 영어 문장>"}}],
  "missions": ["<한국어>", "<한국어>"]
}}

word_count와 connector_summary는 text_metrics 값을 그대로 옮긴다 — 새로 세지 말 것.
grammar_corrections/expression_upgrades의 before는 반드시 학생이 쓴 원문에서 인용한다.
스키마에 없는 키를 추가하지 말 것. naturalness/pronunciation 축을 만들지 말 것."""
