"""Script Coaching — UPGRADE rubric (Gemini prompt builder, no API calls).

# Stage 2 of Script Coaching: rewrite a diagnosed script up to a target level.
# This is a SEPARATE engine from the diagnose rubric.
#
# Calibration (level anchors, question-type guidance) comes from the SHARED
# source: mini_mock_v2_level_rules.format_level_rules_for_prompt().
#
# Core principle — HONEST EXPANSION:
#   - Expand ONLY within what the student actually said. Never invent new
#     facts, experiences, or details the student did not mention.
#   - If the original is too short to reach the target level honestly,
#     do NOT pad with fabricated content. Instead emit fill_in_guides:
#     concrete prompts telling the student what THEY should add.
#
# Two modes:
#   - "upgrade": rewrite toward a higher target level (1 or 2 steps up).
#   - "polish": for AL scripts — no level change, light refinement only.
#
# Output is an upgraded script PLUS change explanations (what was expanded
# and how), so the student learns rather than just copies.
"""

from __future__ import annotations

RUBRIC_VERSION = "script_coaching_upgrade_v1"

_LEVEL_ORDER = ("NH", "IL", "IM1", "IM2", "IM3", "IH", "AL")


def target_levels_for(current_level: str) -> dict:
    """Resolve the 1-step and 2-step targets above current_level.

    Returns a dict: {"mode": "upgrade"|"polish", "one_step": str|None,
    "two_step": str|None}. AL -> polish mode (no targets).
    """
    lv = str(current_level or "").strip().upper()
    if lv not in _LEVEL_ORDER:
        lv = "IL"
    idx = _LEVEL_ORDER.index(lv)
    if lv == "AL":
        return {"mode": "polish", "one_step": None, "two_step": None}
    one = _LEVEL_ORDER[idx + 1] if idx + 1 < len(_LEVEL_ORDER) else None
    two = _LEVEL_ORDER[idx + 2] if idx + 2 < len(_LEVEL_ORDER) else None
    return {"mode": "upgrade", "one_step": one, "two_step": two}


def build_script_coaching_upgrade_rubric(mode: str = "upgrade") -> str:
    """OPIc script upgrade rubric — honest expansion to a target level.

    Args:
        mode: "upgrade" (rewrite up to target level) or "polish" (AL light
              refinement, no level change).
    """
    from services.mini_mock_v2_level_rules import (
        LEVEL_RULE_VERSION,
        format_level_rules_for_prompt,
    )

    level_rules_block = format_level_rules_for_prompt()
    is_polish = str(mode or "upgrade").strip().lower() == "polish"

    if is_polish:
        mode_block = """이 작업은 POLISH(보완) 모드다.
- 학생의 답변은 이미 AL 수준이다. 레벨을 올리는 것이 목적이 아니다.
- 분량을 크게 늘리지 말 것. 문장 수를 원문과 비슷하게 유지한다.
- 어색한 표현·반복·사소한 문법만 자연스럽게 다듬는다.
- 새로운 내용·사실·경험을 추가하지 말 것. 빈칸 안내(fill_in_guides)도 만들지 않는다.
- target_level은 "AL"로 고정한다."""
    else:
        mode_block = """이 작업은 UPGRADE(업그레이드) 모드다.
- 학생의 답변을 target_level 수준에 맞게 다시 쓴다.
- target_level은 입력으로 주어진다(현재 레벨보다 1~2단계 위).
- 위 공용 기준 JSON의 levels 앵커를 참고해, target_level에 맞는 분량·문장
  수·연결어·담화 구조가 되도록 확장한다."""

    return f"""역할: OPIc 답변 스크립트를 더 높은 등급 수준으로 다시 써 주는 구술 코치.
루브릭 버전: {RUBRIC_VERSION}

{mode_block}

공용 평가 기준(단일 소스, 버전 {LEVEL_RULE_VERSION}):
{level_rules_block}

입력: question_en, question_ko, original_script(학생 원문), current_level(진단 등급),
target_level(목표 등급), text_metrics(원문 단어 수 등).

가장 중요한 원칙 — 정직한 확장(HONEST EXPANSION):
- 학생이 실제로 말한 내용 안에서만 확장한다. 학생이 언급하지 않은 새로운 사실·경험·
  사람·장소·사건을 절대 지어내지 말 것.
- 예: 학생이 "블랙핑크 노래를 좋아한다"고만 했으면, 그 노래의 어떤 점이 좋은지·언제
  듣는지·들을 때 기분이 어떤지처럼 학생 원문에서 자연스럽게 이어지는 내용으로 펼친다.
  하지만 "친구들과 매주 노래방에 간다" 같이 학생이 말한 적 없는 사실은 추가하지 않는다.
- 표현을 더 자연스럽게, 문장을 더 잘 연결하고, 연결어를 더하고, 디테일을 풀어내는 것은
  허용된다. 없던 사실을 만드는 것은 금지된다.

원문이 목표 등급에 비해 너무 짧을 때:
- 정직한 확장만으로 target_level 분량을 채울 수 없으면, 억지로 지어내 채우지 말 것.
- 대신 fill_in_guides를 만든다. 이는 "학생이 직접 채워야 할 빈칸 안내"다.
  각 항목은 학생이 무엇을 추가하면 좋을지 구체적으로 알려주는 한국어 한 문장이다.
  예: "이 노래를 주로 언제, 어떤 상황에서 듣는지 1~2문장 추가해 보세요."
  예: "그 경험을 했을 때 기분이 어땠는지 한 문장으로 덧붙여 보세요."
- upgraded_script에는 정직하게 확장 가능한 부분까지만 쓰고, 나머지는 fill_in_guides로
  넘긴다. 원문이 매우 짧으면 fill_in_guides가 여러 개일 수 있다.

upgraded_script(업그레이드된 스크립트):
- 영어로 작성한다.
- 학생 원문의 뼈대와 실제 내용을 유지하면서, target_level 수준의 표현·구조로 다시 쓴다.
- 학생이 외워서 자기 답변으로 말할 수 있어야 한다 — 화려하거나 지나치게 학술적인 표현은
  피하고, target_level에 맞는 자연스러운 구어체 영어로 쓴다.
- 지어낸 내용은 넣지 않는다. 확장이 부족한 부분은 fill_in_guides로 넘긴다.

change_notes(변환 설명):
- 원문을 어떻게 바꿨는지 학생이 학습할 수 있도록 설명하는 배열이다.
- 각 항목은 한국어로, "원문의 어느 부분"을 "어떻게" 바꿨는지 짚는다.
  원문 구절을 따옴표로 인용하면 좋다.
  예: '"i like music"을 "I really enjoy listening to upbeat music"으로 바꿔,
  구체적인 형용사와 자연스러운 동사 형태를 더했습니다.'
  예: '문장들을 because, so 같은 연결어로 이어 문단처럼 읽히게 했습니다.'
- 3~6개 정도. 학생이 "왜 이렇게 바뀌었는지" 이해할 수 있게 쓴다.

출력 형식: **JSON만** (마크다운 코드펜스 없음). 스키마를 정확히 지킬 것:

{{
  "ok": true,
  "mode": "{'polish' if is_polish else 'upgrade'}",
  "current_level": "<진단 등급 그대로>",
  "target_level": "<목표 등급 — polish 모드면 AL>",
  "upgraded_script": "<영어 업그레이드/보완 스크립트>",
  "change_notes": ["<한국어 변환 설명>", "..."],
  "fill_in_guides": ["<한국어 빈칸 안내>", "..."]
}}

- polish 모드에서는 fill_in_guides를 빈 배열 []로 둔다.
- upgrade 모드에서 원문이 충분히 길어 빈칸 안내가 필요 없으면 fill_in_guides는 []로 둔다.
- 스키마에 없는 키를 추가하지 말 것. 점수(score)나 등급 재평가를 출력하지 말 것 —
  이 작업은 진단이 아니라 다시 쓰기다."""
