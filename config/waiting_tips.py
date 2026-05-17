"""OPIc pattern tips shown while AI analysis runs (local only, no API)."""

from __future__ import annotations

from typing import Any, Dict, List, TypedDict


class WaitingTip(TypedDict):
    pattern: str
    meaning: str
    example: str


WAITING_TIPS: List[WaitingTip] = [
    {
        "pattern": "Let me tell you about...",
        "meaning": "답변을 자연스럽게 시작할 때 좋아요.",
        "example": "Let me tell you about my home.",
    },
    {
        "pattern": "What I like about it is that...",
        "meaning": "좋아하는 이유를 설명할 때 좋아요.",
        "example": "What I like about my room is that it feels cozy.",
    },
    {
        "pattern": "To be more specific, ...",
        "meaning": "답변을 더 구체적으로 늘릴 때 좋아요.",
        "example": "To be more specific, I usually go there on weekends.",
    },
    {
        "pattern": "The main reason is that...",
        "meaning": "이유를 말할 때 좋아요.",
        "example": "The main reason is that it helps me relax.",
    },
    {
        "pattern": "I remember one time when...",
        "meaning": "경험형 답변으로 넘어갈 때 좋아요.",
        "example": "I remember one time when I went there with my friend.",
    },
    {
        "pattern": "Overall, I'd say...",
        "meaning": "답변을 자연스럽게 마무리할 때 좋아요.",
        "example": "Overall, I'd say it is a great place to relax.",
    },
    {
        "pattern": "It used to be..., but now...",
        "meaning": "과거와 현재를 비교할 때 좋아요.",
        "example": "It used to be quiet, but now it is more crowded.",
    },
    {
        "pattern": "One thing I noticed is that...",
        "meaning": "관찰한 점을 말할 때 좋아요.",
        "example": "One thing I noticed is that people spend more time outside these days.",
    },
    {
        "pattern": "Compared to the past, ...",
        "meaning": "변화 비교 답변에 좋아요.",
        "example": "Compared to the past, people recycle more carefully now.",
    },
    {
        "pattern": "If I had to choose, I'd say...",
        "meaning": "선택·선호 답변에 좋아요.",
        "example": "If I had to choose, I'd say I prefer cafes to restaurants.",
    },
    {
        "pattern": "First of all, ...",
        "meaning": "여러 포인트를 순서대로 말할 때 좋아요.",
        "example": "First of all, the location is very convenient.",
    },
    {
        "pattern": "What happened next was...",
        "meaning": "경험 이야기를 이어 갈 때 좋아요.",
        "example": "What happened next was that we found a better table.",
    },
    {
        "pattern": "Looking back, ...",
        "meaning": "경험을 정리하며 마무리할 때 좋아요.",
        "example": "Looking back, it was one of my best trips.",
    },
    {
        "pattern": "On weekends, I usually...",
        "meaning": "루틴·습관 답변을 시작할 때 좋아요.",
        "example": "On weekends, I usually cook at home.",
    },
    {
        "pattern": "The best part is that...",
        "meaning": "장점을 강조할 때 좋아요.",
        "example": "The best part is that I can walk to work.",
    },
]
