"""
Next-practice missions from transcript + feedback rows (max 2).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

_GENERIC_MISSIONS = (
    "문장 끝마다 한 번씩 쉬고 다음 문장으로 넘어가기",
    "다음엔 연결어만 살짝 얹어 보세요",
)


def build_next_missions(
    transcript: str,
    grammar_corrections: Optional[List[Dict[str, Any]]] = None,
    expression_upgrades: Optional[List[Dict[str, Any]]] = None,
    structure_feedback: Optional[Dict[str, Any]] = None,
    *,
    wpm: Optional[float] = None,
) -> List[str]:
    """1–2 concrete missions; transcript-specific when possible."""
    lower = (transcript or "").lower()
    missions: List[str] = []
    grammar = grammar_corrections or []
    expression = expression_upgrades or []
    struct = structure_feedback if isinstance(structure_feedback, dict) else {}

    def add(mission: str) -> None:
        m = (mission or "").strip()
        if not m or m in missions:
            return
        if any(g in m for g in _GENERIC_MISSIONS) and len(missions) >= 1:
            return
        if len(missions) < 2:
            missions.append(m)

    for row in grammar:
        before = (row.get("before") or row.get("wrong") or "").strip()
        after = (row.get("after") or row.get("right") or "").strip()
        if not before or not after:
            continue
        bl = before.lower()
        if "living here" in bl or "i'm living" in bl:
            add(f"「{before}」 대신 「{after}」... 으로 시작해 보기")
            break
        if "puppy name" in bl or "dog name" in bl:
            add(f"「{before}」 → 「{after}」 로 고쳐 말하기")
            break
        if "breed is" in bl or "jindo mix" in bl:
            add("Jindo mix 설명은 한 번만 말하고 다음 내용으로 넘어가기")
            break
        if "love to stay" in bl or "love to live" in bl:
            add(f"「{before}」 대신 「{after}」 로 마무리해 보기")
            break
        add(f"「{before}」 → 「{after}」 로 바꿔 말하기")
        break

    expr_pick: Optional[tuple[str, List[str]]] = None
    for row in expression:
        before = (row.get("before") or row.get("phrase") or "").strip()
        alts = row.get("better") or row.get("alternatives") or []
        if isinstance(alts, str):
            alts = [alts]
        if not before or not alts:
            continue
        bl = before.lower()
        if "super cheap" in bl or "very affordable" in bl:
            expr_pick = (before, alts)
            break
        if expr_pick is None and "quiet place" in bl:
            expr_pick = (before, alts)
        if expr_pick is None and "can you imagine" in bl:
            expr_pick = (before, alts)
        if expr_pick is None:
            expr_pick = (before, alts)
    if expr_pick:
        before, alts = expr_pick
        bl = before.lower()
        if "super cheap" in bl or "very affordable" in bl:
            add(f"「{before}」 대신 {alts[0]} 사용해 보기")
        elif "quiet place" in bl:
            add(f"「{before}」 대신 {alts[0]} 로 묘사해 보기")
        elif "can you imagine" in bl:
            add("Can you imagine that? 대신 짧은 이유 문장으로 이어가기")
        else:
            add(f"「{before}」 대신 {alts[0]} 같은 표현을 한 번 써 보기")

    tip = (struct.get("transition_tip") or "").strip()
    if tip and len(missions) < 2:
        add(f"주제 전환 시: {tip}")
    elif len(missions) < 2:
        for miss in struct.get("missing") or []:
            ms = str(miss)
            if "연결" in ms or "넘어" in ms or "반려견" in ms:
                add(
                    "강아지 이야기에서 월세 이야기로 넘어갈 때 "
                    "Another thing I like is... 붙여 보기"
                )
                break
        if (
            len(missions) < 2
            and re.search(r"\b(?:puppy|dog|jindo)\b", lower)
            and re.search(r"\b(?:cheap|affordable|rent|bucks)\b", lower)
        ):
            add(
                "강아지 이야기에서 월세 이야기로 넘어갈 때 "
                "Another thing I like is... 붙여 보기"
            )

    try:
        w = float(wpm) if wpm is not None else 0.0
    except (TypeError, ValueError):
        w = 0.0
    if w >= 260 and len(missions) < 2:
        add("문장 끝마다 0.5초 쉬기")

    if len(missions) < 2 and re.search(r"\bjindo\s+mix\b", lower):
        add("Jindo mix 설명은 한 번만 말하고 다음 내용으로 넘어가기")

    if not missions:
        add("문장 끝마다 0.5초 쉬기")

    return missions[:2]
