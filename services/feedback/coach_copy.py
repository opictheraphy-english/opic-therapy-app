"""
Transcript-specific coach summary and strength bullets (no LLM, no scoring).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_BANNED_PHRASES = (
    "오늘 답변, 전체적으로 좋은 흐름",
    "천천히 말하려는 태도",
    "다음엔 연결어만 살짝",
    "전체적으로 좋은 흐름",
    "연결어만 살짝 얹어",
)


def _norm(text: str) -> str:
    return (text or "").strip()


def _pet_name(transcript: str, lower: str) -> Optional[str]:
    for pat in (
        r"\b(?:puppy|dog|pet)\s+named\s+([A-Z][a-z]+)\b",
        r"\b(?:puppy|dog|pet)\s+name[d]?\s+([A-Z][a-z]+)\b",
        r"\b([A-Z][a-z]+)\s+is\s+a\s+jindo\b",
    ):
        m = re.search(pat, transcript, re.IGNORECASE)
        if m:
            return m.group(1).capitalize()
    if re.search(r"\bsogum\b", lower):
        return "Sogum"
    return None


def collect_transcript_strengths(transcript: str) -> List[str]:
    """Short encouraging bullets grounded in what the student said."""
    t = _norm(transcript)
    if not t:
        return []
    lower = t.lower()
    out: List[str] = []

    detail_flags = [
        bool(re.search(r"\b(?:city|town|gwangju|seoul|busan)\b", lower)),
        bool(re.search(r"\b(?:apartment|house|room|bathroom)\b", lower)),
        bool(re.search(r"\b(?:puppy|dog|pet|family|with\s+my)\b", lower)),
        bool(re.search(r"\b(?:cheap|affordable|rent|bucks|reason)\b", lower)),
        bool(re.search(r"\b(?:quiet|peaceful|nice|comfortable)\b", lower)),
    ]
    if sum(detail_flags) >= 3:
        out.append("구체적인 정보가 많아서 답변이 생생했어요.")

    pet = _pet_name(t, lower)
    if pet:
        out.append(
            f"강아지 {pet}처럼 개인적인 소재가 들어가서 답변이 더 자연스럽게 들렸어요."
        )
    elif re.search(r"\b(?:puppy|dog|pet|cat)\b", lower):
        out.append("개인적인 소재가 들어가서 답변이 더 자연스럽게 들렸어요.")

    if re.search(r"\b(?:cheap|affordable|bucks|rent)\b", lower) and re.search(
        r"\b(?:love|like|reason|stay)\b", lower
    ):
        out.append(
            "집을 좋아하는 이유가 월세·가격이라는 구체적인 장점으로 연결된 점이 좋았어요."
        )
    elif re.search(r"\b(?:because|reason|so\s+that)\b", lower):
        out.append("이유를 말하려는 흐름이 분명했어요.")

    if re.search(r"\b(?:three\s+rooms?|\d+\s+rooms?|bathroom)\b", lower):
        if not any("구체적" in x for x in out):
            out.append("집 구조를 짧게 설명해 답의 뼈대가 잡혔어요.")

    if re.search(r"\b(?:park|cafe|hobby|work|job)\b", lower) and len(out) < 2:
        out.append("질문 주제에 맞는 내용으로 답을 이어 갔어요.")

    seen: set[str] = set()
    deduped: List[str] = []
    for line in out:
        if line not in seen:
            seen.add(line)
            deduped.append(line)
    return deduped[:4]


def build_coach_summary(
    transcript: str,
    grammar_corrections: Optional[List[Dict[str, Any]]] = None,
    expression_upgrades: Optional[List[Dict[str, Any]]] = None,
    structure_feedback: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str]:
    """2–3 sentence coach body + short title (transcript-first)."""
    t = _norm(transcript)
    lower = t.lower()
    parts: List[str] = []

    strengths = collect_transcript_strengths(t)
    for s in strengths[:2]:
        parts.append(s)

    struct = structure_feedback if isinstance(structure_feedback, dict) else {}
    for g in struct.get("good") or []:
        g = str(g).strip()
        if g and g not in parts and len(g) <= 90:
            parts.append(g.rstrip("."))
        if len(parts) >= 2:
            break

    grammar = grammar_corrections or []
    expression = expression_upgrades or []

    if grammar and len(parts) < 3:
        w = (grammar[0].get("before") or grammar[0].get("wrong") or "").strip()
        r = (grammar[0].get("after") or grammar[0].get("right") or "").strip()
        if w and r:
            parts.append(f"「{w}」는 「{r}」처럼 다듬으면 더 자연스러워요.")

    if expression and len(parts) < 3:
        p = (expression[0].get("before") or expression[0].get("phrase") or "").strip()
        alts = expression[0].get("better") or expression[0].get("alternatives") or []
        if isinstance(alts, str):
            alts = [alts]
        if p and alts:
            parts.append(f"「{p}」는 {alts[0]}처럼 바꿔 말해 보세요.")

    if re.search(r"\bwhat do you like\b", lower) and len(parts) < 3:
        parts.append("중간에 스스로 질문을 던지면 흐름이 잠깐 끊겨요.")

    parts = [p for p in parts if not any(b in p for b in _BANNED_PHRASES)]

    title = "답변의 방향은 좋았어요"
    if grammar and expression:
        title = "핵심은 잡았어요 — 표현만 조금 다듬으면 돼요"
    elif grammar:
        title = "내용은 전달됐어요 — 문법만 살짝 고치면 좋아요"
    elif expression:
        title = "답변 흐름은 괜찮아요 — 표현을 구체적으로 바꿔 보세요"

    if not parts:
        parts.append(
            "질문 주제에 맞게 답을 이어 갔어요. 아래에서 문법·표현·구조를 짧게 정리했어요."
        )

    body = " ".join(parts[:3]).strip()
    if len(body) > 360:
        body = body[:357].rstrip() + "…"
    return title, body
