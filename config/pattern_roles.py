"""Pattern Role System — 말하기 조립(speech-building) 단계 라벨."""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Literal, Optional

ALLOWED_PATTERN_ROLES = frozenset(
    {
        "starter",
        "detail",
        "atmosphere",
        "emotion",
        "comparison",
        "transition",
        "closing",
        "opinion",
    }
)

ROLE_ORDER_FOR_INTERLEAVE: List[str] = [
    "starter",
    "detail",
    "atmosphere",
    "emotion",
    "comparison",
    "transition",
    "closing",
    "opinion",
]

# DB subcategory(slug) → pattern_role (묘사·공통 확장 시 여기만 보강)
SUBCATEGORY_TO_ROLE: Dict[str, str] = {
    "opening_intro": "starter",
    "exterior": "detail",
    "appearance": "detail",
    "visuals": "detail",
    "interior_space": "detail",
    "interior": "detail",
    "space": "detail",
    "favorite_space": "detail",
    "location": "detail",
    "size": "detail",
    "layout": "detail",
    "environment": "detail",
    "details": "detail",
    "weather": "detail",
    "condition": "detail",
    "daily_routine": "detail",
    "strengths": "detail",
    "benefits": "detail",
    "features": "detail",
    "atmosphere": "atmosphere",
    "lighting": "atmosphere",
    "comfort": "atmosphere",
    "sound": "atmosphere",
    "crowd": "atmosphere",
    "features_love": "emotion",
    "emphasis": "emotion",
    "comparison_phrase": "comparison",
    "preference_type": "comparison",
    "companions": "transition",
    "responsibilities": "transition",
    "conclusion": "closing",
    "overall_impression": "closing",
    "recommendation": "closing",
    "personal_view": "opinion",
    "preference_reason": "opinion",
}


def normalize_role(value: Optional[str]) -> Optional[str]:
    if not value or not isinstance(value, str):
        return None
    r = value.strip().lower()
    return r if r in ALLOWED_PATTERN_ROLES else None


def infer_pattern_role(rec: Dict[str, Any]) -> str:
    """Infer role from explicit field, then subcategory, then light heuristics on English."""
    explicit = normalize_role(rec.get("pattern_role"))
    if explicit:
        return explicit

    sub = (rec.get("subcategory") or "general").strip().lower().replace(" ", "_")
    if sub in SUBCATEGORY_TO_ROLE:
        return SUBCATEGORY_TO_ROLE[sub]

    pe = (rec.get("pattern_en") or rec.get("example_en") or "").strip().lower()
    if pe.startswith("let me tell you"):
        return "starter"
    if "compared to" in pe or " rather than " in pe:
        return "comparison"
    if pe.startswith(("overall", "in conclusion", "to sum up", "in summary")):
        return "closing"
    if pe.startswith(("i feel", "i love", "i enjoy", "i'm grateful")):
        return "emotion"

    return "detail"


RoleFilterMode = Literal["all", "starter", "emotion", "advanced"]


def apply_role_filter(
    rows: List[Dict[str, Any]], mode: RoleFilterMode
) -> List[Dict[str, Any]]:
    if mode == "all":
        return list(rows)
    out: List[Dict[str, Any]] = []
    for r in rows:
        role = r.get("pattern_role") or infer_pattern_role(r)
        if mode == "starter" and role == "starter":
            out.append(r)
        elif mode == "emotion" and role == "emotion":
            out.append(r)
        elif mode == "advanced" and role != "starter":
            out.append(r)
    return out


def interleave_patterns_by_role(patterns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    같은 role이 길게 연속되지 않도록 라운드로빈 병합 (조립 훈련용 노출 순서).
    """
    if len(patterns) <= 1:
        return list(patterns)

    buckets: Dict[str, deque] = {r: deque() for r in ROLE_ORDER_FOR_INTERLEAVE}
    overflow: deque = deque()

    for p in patterns:
        role = normalize_role(p.get("pattern_role")) or infer_pattern_role(p)
        if role in buckets:
            buckets[role].append(p)
        else:
            overflow.append(p)

    merged: List[Dict[str, Any]] = []
    while True:
        progressed = False
        for r in ROLE_ORDER_FOR_INTERLEAVE:
            if buckets[r]:
                merged.append(buckets[r].popleft())
                progressed = True
        if overflow and not progressed:
            merged.append(overflow.popleft())
            progressed = True
        if not progressed:
            break
    return merged
