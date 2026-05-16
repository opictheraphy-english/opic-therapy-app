"""Static question sets for Topic Practice mode (3-question OPIc combos per topic)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

TOPIC_PRACTICE_SETS: List[Dict[str, Any]] = [
    {
        "topic_id": "park",
        "topic_title": "공원",
        "topic_subtitle": "자주 가는 장소, 루틴, 기억에 남는 경험",
        "level": "IM~IH",
        "questions": [
            {
                "question_id": "park_q1",
                "type": "description",
                "type_label": "묘사",
                "question_en": "Tell me about a park you often visit. What does it look like?",
                "question_ko": "자주 가는 공원에 대해 말해 주세요. 그 공원은 어떻게 생겼나요?",
                "focus": "장소 묘사",
                "starter_keywords": [
                    "near my place",
                    "peaceful",
                    "walking path",
                    "trees",
                    "clear my head",
                ],
            },
            {
                "question_id": "park_q2",
                "type": "routine",
                "type_label": "루틴",
                "question_en": "What do you usually do at the park?",
                "question_ko": "공원에서 보통 무엇을 하시나요?",
                "focus": "공원 루틴",
                "starter_keywords": [
                    "take a walk",
                    "jog",
                    "stretch",
                    "sit on a bench",
                    "listen to music",
                ],
            },
            {
                "question_id": "park_q3",
                "type": "experience",
                "type_label": "경험",
                "question_en": "Tell me about a memorable experience you had at a park.",
                "question_ko": "공원에서 기억에 남는 경험에 대해 말해 주세요.",
                "focus": "기억에 남는 경험",
                "starter_keywords": [
                    "one weekend",
                    "with friends",
                    "picnic",
                    "unexpected",
                    "still remember",
                ],
            },
        ],
    },
    {
        "topic_id": "cafe",
        "topic_title": "카페",
        "topic_subtitle": "분위기 묘사, 자주 하는 일, 특별한 경험",
        "level": "IM~IH",
        "questions": [
            {
                "question_id": "cafe_q1",
                "type": "description",
                "type_label": "묘사",
                "question_en": "Describe a cafe you often go to.",
                "question_ko": "자주 가는 카페를 묘사해 주세요.",
                "focus": "카페 분위기",
                "starter_keywords": [
                    "cozy",
                    "quiet",
                    "near my office",
                    "warm lighting",
                    "comfortable seats",
                ],
            },
            {
                "question_id": "cafe_q2",
                "type": "routine",
                "type_label": "루틴",
                "question_en": "What do you usually do at that cafe?",
                "question_ko": "그 카페에서 보통 무엇을 하시나요?",
                "focus": "카페에서 하는 일",
                "starter_keywords": [
                    "order coffee",
                    "read",
                    "work on my laptop",
                    "meet a friend",
                    "take a break",
                ],
            },
            {
                "question_id": "cafe_q3",
                "type": "experience",
                "type_label": "경험",
                "question_en": "Tell me about a memorable time you had at a cafe.",
                "question_ko": "카페에서 있었던 기억에 남는 시간에 대해 말해 주세요.",
                "focus": "특별한 경험",
                "starter_keywords": [
                    "first time",
                    "surprised",
                    "great conversation",
                    "special drink",
                    "won't forget",
                ],
            },
        ],
    },
    {
        "topic_id": "home",
        "topic_title": "집",
        "topic_subtitle": "집 묘사, 방 소개, 집에서 하는 활동",
        "level": "IM~IH",
        "questions": [
            {
                "question_id": "home_q1",
                "type": "description",
                "type_label": "묘사",
                "question_en": "Please describe your home. What is it like?",
                "question_ko": "집을 묘사해 주세요. 어떤 곳인가요?",
                "focus": "집 묘사",
                "starter_keywords": [
                    "apartment",
                    "spacious",
                    "bright",
                    "living room",
                    "feel relaxed",
                ],
            },
            {
                "question_id": "home_q2",
                "type": "routine",
                "type_label": "루틴",
                "question_en": "What do you usually do at home?",
                "question_ko": "집에서 보통 무엇을 하시나요?",
                "focus": "집에서 하는 활동",
                "starter_keywords": [
                    "cook",
                    "watch TV",
                    "rest",
                    "clean up",
                    "spend time with family",
                ],
            },
            {
                "question_id": "home_q3",
                "type": "experience",
                "type_label": "경험",
                "question_en": "Tell me about a memorable experience you had at home.",
                "question_ko": "집에서 있었던 기억에 남는 경험에 대해 말해 주세요.",
                "focus": "기억에 남는 경험",
                "starter_keywords": [
                    "family gathering",
                    "holiday",
                    "unexpected guest",
                    "special moment",
                    "meaningful",
                ],
            },
        ],
    },
    {
        "topic_id": "exercise",
        "topic_title": "운동",
        "topic_subtitle": "운동 장소, 운동 루틴, 시작 계기",
        "level": "IM~IH",
        "questions": [
            {
                "question_id": "exercise_q1",
                "type": "description",
                "type_label": "묘사",
                "question_en": "Tell me about a place where you usually exercise.",
                "question_ko": "보통 운동하는 장소에 대해 말해 주세요.",
                "focus": "운동 장소",
                "starter_keywords": [
                    "gym",
                    "near my home",
                    "well equipped",
                    "not too crowded",
                    "easy to get to",
                ],
            },
            {
                "question_id": "exercise_q2",
                "type": "routine",
                "type_label": "루틴",
                "question_en": "What do you usually do when you exercise?",
                "question_ko": "운동할 때 보통 무엇을 하시나요?",
                "focus": "운동 루틴",
                "starter_keywords": [
                    "warm up",
                    "cardio",
                    "strength training",
                    "stretch",
                    "three times a week",
                ],
            },
            {
                "question_id": "exercise_q3",
                "type": "change",
                "type_label": "변화",
                "question_en": "Tell me how your exercise habits have changed over time.",
                "question_ko": "시간이 지나면서 운동 습관이 어떻게 바뀌었는지 말해 주세요.",
                "focus": "습관 변화",
                "starter_keywords": [
                    "used to",
                    "these days",
                    "more consistent",
                    "health goal",
                    "gradually",
                ],
            },
        ],
    },
    {
        "topic_id": "movie",
        "topic_title": "영화",
        "topic_subtitle": "좋아하는 영화, 영화관, 기억에 남는 장면",
        "level": "IM~IH",
        "questions": [
            {
                "question_id": "movie_q1",
                "type": "preference",
                "type_label": "취향",
                "question_en": "What kinds of movies do you like?",
                "question_ko": "어떤 종류의 영화를 좋아하시나요?",
                "focus": "영화 취향",
                "starter_keywords": [
                    "action",
                    "drama",
                    "feel-good",
                    "not too scary",
                    "good story",
                ],
            },
            {
                "question_id": "movie_q2",
                "type": "routine",
                "type_label": "루틴",
                "question_en": "How do you usually watch movies?",
                "question_ko": "보통 영화는 어떻게 보시나요?",
                "focus": "영화 보는 방식",
                "starter_keywords": [
                    "at the theater",
                    "streaming",
                    "with friends",
                    "on weekends",
                    "popcorn",
                ],
            },
            {
                "question_id": "movie_q3",
                "type": "experience",
                "type_label": "경험",
                "question_en": "Tell me about a movie that left a strong impression on you.",
                "question_ko": "강한 인상을 남긴 영화에 대해 말해 주세요.",
                "focus": "인상 깊은 영화",
                "starter_keywords": [
                    "the ending",
                    "moved me",
                    "watched twice",
                    "recommend",
                    "still think about",
                ],
            },
        ],
    },
    {
        "topic_id": "music",
        "topic_title": "음악",
        "topic_subtitle": "좋아하는 음악, 가수, 음악을 듣는 상황",
        "level": "IM~IH",
        "questions": [
            {
                "question_id": "music_q1",
                "type": "preference",
                "type_label": "취향",
                "question_en": "What kind of music do you like?",
                "question_ko": "어떤 음악을 좋아하시나요?",
                "focus": "음악 취향",
                "starter_keywords": [
                    "pop",
                    "K-pop",
                    "relaxing",
                    "upbeat",
                    "favorite artist",
                ],
            },
            {
                "question_id": "music_q2",
                "type": "routine",
                "type_label": "루틴",
                "question_en": "When and where do you usually listen to music?",
                "question_ko": "보통 언제, 어디서 음악을 듣나요?",
                "focus": "음악 듣는 상황",
                "starter_keywords": [
                    "on my commute",
                    "while studying",
                    "at home",
                    "before bed",
                    "headphones",
                ],
            },
            {
                "question_id": "music_q3",
                "type": "experience",
                "type_label": "경험",
                "question_en": "Tell me about a memorable experience related to music.",
                "question_ko": "음악과 관련된 기억에 남는 경험에 대해 말해 주세요.",
                "focus": "음악 관련 경험",
                "starter_keywords": [
                    "concert",
                    "live performance",
                    "with friends",
                    "surprised",
                    "unforgettable",
                ],
            },
        ],
    },
    {
        "topic_id": "travel",
        "topic_title": "여행",
        "topic_subtitle": "여행지 묘사, 여행 루틴, 기억에 남는 여행",
        "level": "IM~IH",
        "questions": [
            {
                "question_id": "travel_q1",
                "type": "description",
                "type_label": "묘사",
                "question_en": "Describe a place you visited on a trip.",
                "question_ko": "여행에서 방문했던 장소를 묘사해 주세요.",
                "focus": "여행지 묘사",
                "starter_keywords": [
                    "beautiful scenery",
                    "coastal city",
                    "historic",
                    "first time",
                    "impressed me",
                ],
            },
            {
                "question_id": "travel_q2",
                "type": "routine",
                "type_label": "루틴",
                "question_en": "What do you usually do when you travel?",
                "question_ko": "여행할 때 보통 무엇을 하시나요?",
                "focus": "여행 루틴",
                "starter_keywords": [
                    "plan ahead",
                    "try local food",
                    "take photos",
                    "walk around",
                    "visit landmarks",
                ],
            },
            {
                "question_id": "travel_q3",
                "type": "experience",
                "type_label": "경험",
                "question_en": "Tell me about a memorable trip you took.",
                "question_ko": "기억에 남는 여행에 대해 말해 주세요.",
                "focus": "기억에 남는 여행",
                "starter_keywords": [
                    "with family",
                    "unexpected",
                    "learned a lot",
                    "best part",
                    "want to go again",
                ],
            },
        ],
    },
    {
        "topic_id": "roleplay",
        "topic_title": "롤플레이",
        "topic_subtitle": "문의, 예약, 문제 해결, 대안 제시",
        "level": "IM~IH",
        "questions": [
            {
                "question_id": "roleplay_q1",
                "type": "inquiry",
                "type_label": "문의",
                "question_en": "Call a hotel and ask three questions about making a reservation.",
                "question_ko": "호텔에 전화해서 예약에 대해 세 가지 질문을 해 보세요.",
                "focus": "예약 문의",
                "starter_keywords": [
                    "I'd like to make a reservation",
                    "check-in time",
                    "room rate",
                    "availability",
                    "breakfast included",
                ],
            },
            {
                "question_id": "roleplay_q2",
                "type": "problem_solving",
                "type_label": "문제 해결",
                "question_en": "You have a problem with your reservation. Call the hotel and explain the situation.",
                "question_ko": "예약에 문제가 생겼습니다. 호텔에 전화해서 상황을 설명해 보세요.",
                "focus": "문제 설명",
                "starter_keywords": [
                    "there seems to be a mistake",
                    "double booking",
                    "wrong date",
                    "could you help me",
                    "I reserved under",
                ],
            },
            {
                "question_id": "roleplay_q3",
                "type": "alternatives",
                "type_label": "대안 제시",
                "question_en": "Your original plan is not possible. Suggest two or three alternatives.",
                "question_ko": "원래 계획이 불가능합니다. 대안 두세 가지를 제안해 보세요.",
                "focus": "대안 제시",
                "starter_keywords": [
                    "instead of",
                    "would it be possible",
                    "another option",
                    "how about",
                    "flexible",
                ],
            },
        ],
    },
]

_TOPIC_BY_ID: Dict[str, Dict[str, Any]] = {
    item["topic_id"]: item for item in TOPIC_PRACTICE_SETS
}


def get_topic_sets() -> List[Dict[str, Any]]:
    """Return all topic practice sets (shallow copy of the list)."""
    return list(TOPIC_PRACTICE_SETS)


def get_topic_by_id(topic_id: str) -> Optional[Dict[str, Any]]:
    """Look up one topic set by ``topic_id``; returns ``None`` if missing."""
    if not topic_id:
        return None
    return _TOPIC_BY_ID.get(str(topic_id).strip())


def get_topic_question(topic_id: str, question_index: int) -> Optional[Dict[str, Any]]:
    """Return one question dict (0-based index) or ``None`` if out of range."""
    topic = get_topic_by_id(topic_id)
    if not topic:
        return None
    questions = topic.get("questions")
    if not isinstance(questions, list):
        return None
    idx = int(question_index)
    if idx < 0 or idx >= len(questions):
        return None
    q = questions[idx]
    return q if isinstance(q, dict) else None
