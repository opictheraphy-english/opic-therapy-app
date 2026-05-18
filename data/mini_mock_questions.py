"""Fixed 3-question set for 5-minute diagnostic mini mock."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

MINI_MOCK_QUESTION_COUNT = 3

MINI_MOCK_QUESTIONS: List[Dict[str, Any]] = [
    {
        "question_id": "mini_mock_q1",
        "question_index": 0,
        "type": "description",
        "type_label": "묘사",
        "question_en": (
            "Tell me about the place where you live. What is it like, "
            "and what do you like about it?"
        ),
        "question_ko": (
            "현재 살고 있는 곳에 대해 설명해 주세요. 어떤 곳이고, "
            "어떤 점이 마음에 드나요?"
        ),
    },
    {
        "question_id": "mini_mock_q2",
        "question_index": 1,
        "type": "memorable_experience",
        "type_label": "기억에 남는 경험",
        "question_en": (
            "Tell me about a memorable experience you had at home or in your neighborhood. "
            "What happened, and why do you remember it?"
        ),
        "question_ko": (
            "집이나 동네에서 있었던 기억에 남는 경험을 말해 주세요. "
            "무슨 일이 있었고, 왜 기억에 남나요?"
        ),
    },
    {
        "question_id": "mini_mock_q3",
        "question_index": 2,
        "type": "roleplay",
        "type_label": "롤플레이",
        "question_en": (
            "You want to invite a friend to your place, but your schedule suddenly changed. "
            "Call your friend, explain the situation, and suggest another time."
        ),
        "question_ko": (
            "친구를 집으로 초대하려고 했는데 갑자기 일정이 바뀌었습니다. "
            "친구에게 전화해서 상황을 설명하고 다른 시간을 제안해 주세요."
        ),
    },
]


def get_mini_mock_questions() -> List[Dict[str, Any]]:
    return list(MINI_MOCK_QUESTIONS)


def get_mini_mock_question(index: int) -> Optional[Dict[str, Any]]:
    try:
        idx = int(index)
    except (TypeError, ValueError):
        return None
    if idx < 0 or idx >= MINI_MOCK_QUESTION_COUNT:
        return None
    return dict(MINI_MOCK_QUESTIONS[idx])
