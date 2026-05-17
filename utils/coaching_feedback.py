"""Local post-processing for coaching UI — no LLM calls."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_HEADLINE_PAIRS: Tuple[Tuple[str, str], ...] = (
    (
        "답변의 방향은 좋았어요",
        "핵심 내용은 전달됐지만, 표현과 문장 연결을 조금만 다듬으면 더 자연스러워요.",
    ),
    (
        "좋은 시작이었어요",
        "이제 이유와 구체적인 묘사를 붙이면 한 단계 올라갈 수 있어요.",
    ),
    (
        "오늘 답변, 잘 들었어요",
        "내용은 잡혔지만, 중간에 흐름이 끊기거나 평이한 표현이 보였어요.",
    ),
    (
        "핵심은 잡았어요",
        "다음 단계는 문법 슬립을 고치고, 더 구체적인 형용사로 바꿔 보는 거예요.",
    ),
    (
        "구조는 괜찮았어요",
        "공간·이유·마무리를 조금만 보완하면 IH 구간에서도 안정적으로 들릴 거예요.",
    ),
)

_GENERIC_STRONG_FALLBACKS: Tuple[str, ...] = (
    "질문에 맞는 주제로 답을 시작했어요.",
    "단점까지 언급해 균형 있게 말하려는 시도가 보였어요.",
    "문장 길이는 짧아도 핵심 정보는 전달됐어요.",
)


def _norm(text: str) -> str:
    return (text or "").strip()


def _sentences(text: str, *, max_n: int = 3) -> List[str]:
    t = _norm(text)
    if not t:
        return []
    parts = re.split(r"(?<=[.!?。])\s+", t)
    out = [p.strip() for p in parts if p.strip()]
    return out[:max_n]


def merge_grammar_hits(
    transcript: str,
    result: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    from utils.grammar_corrections import detect_grammar_corrections

    hits = detect_grammar_corrections(transcript)
    if not isinstance(result, dict):
        return hits
    extra = result.get("grammar_corrections") or result.get("grammar_fixes")
    if not isinstance(extra, list):
        return hits
    seen = {h.get("wrong", "").lower() for h in hits}
    for row in extra:
        if not isinstance(row, dict):
            continue
        wrong = _norm(str(row.get("wrong") or row.get("original") or ""))
        if not wrong or wrong.lower() in seen:
            continue
        hits.append(
            {
                "wrong": wrong,
                "right": _norm(str(row.get("right") or row.get("correction") or "")),
                "note": _norm(str(row.get("note") or row.get("reason") or "")),
            }
        )
        seen.add(wrong.lower())
    return hits[:4]


def merge_alt_hits(
    transcript: str,
    result: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    from utils.grammar_corrections import detect_alternative_expressions

    hits = detect_alternative_expressions(transcript)
    if not isinstance(result, dict):
        return hits
    extra = result.get("better_expressions") or result.get("alternative_expressions")
    if not isinstance(extra, list):
        return hits
    seen = {str(h.get("phrase", "")).lower() for h in hits}
    for row in extra:
        if not isinstance(row, dict):
            continue
        phrase = _norm(str(row.get("phrase") or row.get("before") or ""))
        if not phrase or phrase.lower() in seen:
            continue
        alts = row.get("alternatives") or row.get("better") or []
        if isinstance(alts, str):
            alts = [alts]
        hits.append(
            {
                "phrase": phrase,
                "alternatives": list(alts) if isinstance(alts, list) else [],
                "note": _norm(str(row.get("note") or row.get("why") or "")),
            }
        )
        seen.add(phrase.lower())
    return hits[:4]


def build_coach_headline(
    result: Dict[str, Any],
    transcript: str,
    grammar_hits: List[Dict[str, str]],
    alt_hits: List[Dict[str, Any]],
) -> Tuple[str, str]:
    """Varied 2–3 sentence coach summary (title + body)."""
    body_parts: List[str] = []

    sem = _norm(result.get("semantic_feedback") or "")
    summary = _norm(result.get("summary_speech_rehab") or "")
    rx = _norm(result.get("prescription") or "")

    for block in (summary, sem, rx):
        for sent in _sentences(block, max_n=2):
            if sent and sent not in body_parts:
                if not any(
                    g in sent
                    for g in (
                        "오늘 답변, 전체적으로 좋은 흐름",
                        "천천히 말하려는 태도",
                        "전체적으로 좋은 흐름",
                    )
                ):
                    body_parts.append(sent)

    lower = transcript.lower()
    if grammar_hits:
        g0 = grammar_hits[0]
        w = g0.get("wrong", "")
        if w:
            body_parts.append(f"특히 「{w}」 같은 표현은 바로 고치면 좋아요.")
    if alt_hits and len(body_parts) < 3:
        p = alt_hits[0].get("phrase", "")
        if p:
            body_parts.append(f"「{p}」처럼 평이한 표현은 더 구체적인 말로 바꿔 보세요.")

    if re.search(r"\bwhat do you like\b", lower):
        body_parts.append("중간에 스스로 질문을 던지는 문장이 들어가면서 흐름이 잠깐 끊겼어요.")

    if re.search(r"\b(?:room|bedroom|house)\b", lower) and re.search(
        r"\b(?:noisy|neighbor)\b", lower
    ):
        if not any("구조" in p or "단점" in p for p in body_parts):
            body_parts.append(
                "집의 구조와 장단점을 모두 말해서 답변 방향은 좋았어요."
            )

    idx = (len(transcript) + len(grammar_hits) * 11 + len(alt_hits) * 7) % len(
        _HEADLINE_PAIRS
    )
    title, default_sub = _HEADLINE_PAIRS[idx]

    if grammar_hits and alt_hits:
        title = "핵심은 잡았어요 — 표현만 조금 다듬으면 돼요"
    elif grammar_hits:
        title = "내용은 전달됐어요 — 문법만 살짝 고치면 좋아요"
    elif alt_hits:
        title = "답변 흐름은 괜찮아요 — 표현을 구체적으로 바꿔 보세요"

    body = " ".join(body_parts[:3]).strip() or default_sub
    if len(body) > 320:
        body = body[:317].rstrip() + "…"
    return title, body


def build_structure_feedback(transcript: str) -> Dict[str, List[str]]:
    """Good / missing / next structure bullets from transcript."""
    lower = transcript.lower()
    good: List[str] = []
    missing: List[str] = []
    nxt: List[str] = []

    if re.search(r"\b(?:house|home|apartment|room|bedroom)\b", lower):
        good.append("집·방 구조를 언급함")
    if re.search(r"\b(?:noisy|neighbor|downside|but)\b", lower):
        good.append("단점(소음 등)도 말함")
    if re.search(r"\b(?:like|enjoy|great|good|nice)\b", lower):
        good.append("좋은 점을 표현하려는 시도가 보임")

    if not re.search(r"\b(?:living room|kitchen|bathroom|dining)\b", lower):
        missing.append("거실·부엌 같은 공간별 묘사가 부족함")
    if not re.search(r"\b(?:because|since|so that|reason)\b", lower):
        missing.append("왜 편한지/좋은지 이유 설명이 부족함")
    if re.search(r"\bwhat do you\b", lower):
        missing.append("본인이 질문을 던져 흐름이 끊김")

    nxt.append('"위치 → 구조 → 좋은 점 → 아쉬운 점 → 전체 평가" 순서로 말하기')
    if missing:
        nxt.append("각 방/공간을 한 문장씩만 덧붙이기")

    if not good:
        good.extend(_GENERIC_STRONG_FALLBACKS[:2])

    return {"good": good[:4], "missing": missing[:3], "next": nxt[:2]}


def build_improved_answer_example(
    transcript: str,
    grammar_hits: List[Dict[str, str]],
    alt_hits: List[Dict[str, Any]],
) -> str:
    """Short IM→IH sample answer (rule-based, no LLM)."""
    lower = transcript.lower()
    lines: List[str] = []

    opener = "Let me tell you about my house."
    if re.search(r"\bhouse\b", lower):
        desc = "It is not huge, but it is comfortable and practical."
        if re.search(r"\breally\s+great\b", lower):
            desc = "It is not huge, but it is comfortable and practical."
        lines.append(f"{opener} {desc}")

    if re.search(r"\b(?:three\s+rooms?|room)\b", lower):
        room_line = (
            "There are three rooms, including one bedroom, "
            "and I usually spend most of my time in the living room."
        )
        if re.search(r"\btwo\s+bedroom\b", lower):
            room_line = (
                "There are three rooms, including two bedrooms, "
                "and I usually spend most of my time in the living room."
            )
        lines.append(room_line)

    if re.search(r"\b(?:noisy|neighbor)\b", lower):
        lines.append(
            "One downside is that it can get a little noisy because "
            "one of my neighbors is quite loud."
        )

    closer = "Still, overall, I'd say it is a pretty nice place to live."
    if re.search(r"\bjust\s+wanna\s+say\b", lower):
        closer = "Still, overall, I'd say it is a pretty nice place to live."
    lines.append(closer)

    if len(lines) < 3:
        t = _norm(transcript)
        if t:
            lines = _sentences(t, max_n=4)
            if lines:
                return " ".join(lines)

    return " ".join(lines[:5])


def build_next_missions(
    transcript: str,
    grammar_hits: List[Dict[str, str]],
    alt_hits: List[Dict[str, Any]],
) -> List[str]:
    missions: List[str] = []
    lower = transcript.lower()

    if alt_hits:
        phrase = str(alt_hits[0].get("phrase") or "")
        alts = alt_hits[0].get("alternatives") or []
        if alts:
            missions.append(
                f'「{phrase}」 대신 {alts[0]} 같은 표현을 한 번 써 보기'
            )
    elif re.search(r"\breally\s+great\b", lower):
        missions.append('"great" 대신 cozy / comfortable / convenient 중 하나 써 보기')

    if grammar_hits:
        missions.append(
            f'「{grammar_hits[0].get("wrong", "")}」 → {grammar_hits[0].get("right", "")} 로 바꿔 말하기'
        )

    try:
        from utils.coaching_feedback import pronunciation_wpm_note  # avoid circular
    except ImportError:
        pass

    if len(missions) < 2:
        missions.append("문장 끝마다 한 번씩 쉬고 다음 문장으로 넘어가기")

    return missions[:2]


def grammar_empty_message(alt_hits: List[Dict[str, Any]]) -> str:
    if alt_hits:
        return (
            "큰 문법 오류는 많지 않았어요. "
            "다만 더 자연스럽게 만들 수 있는 표현은 아래에서 정리했어요."
        )
    return (
        "큰 문법 오류는 많지 않았어요. "
        "다음 답변에서는 문장 끝 호흡과 구체적인 형용사를 의식해 보세요."
    )


def pronunciation_comment(result: Dict[str, Any]) -> str:
    """Score-aware pronunciation note with WPM caveat."""
    from services.evaluation.eval_grading import _pronunciation_feedback

    pron = result.get("pronunciation_scores")
    sem = result.get("semantic_dimensions") or {}
    if not isinstance(pron, dict) or not pron:
        pron = {
            k: sem.get(k)
            for k in (
                "pronunciation_clarity",
                "intonation_control",
                "stress_rhythm",
                "linking_naturalness",
            )
        }
        pron = {k: v for k, v in pron.items() if v is not None}

    base = (result.get("pronunciation_feedback") or "").strip()
    if not base and isinstance(pron, dict) and pron:
        try:
            base = _pronunciation_feedback({k: float(v) for k, v in pron.items()})
        except (TypeError, ValueError):
            base = ""

    wpm = result.get("wpm")
    try:
        w = float(wpm) if wpm is not None else 0.0
    except (TypeError, ValueError):
        w = 0.0

    if w >= 260:
        return (
            "속도가 빠르게 측정됐어요. 실제 말하기 속도뿐 아니라 "
            "녹음 길이 계산이나 문장 인식 방식의 영향도 있을 수 있어요. "
            "다음 답변에서는 문장 끝마다 0.5초 정도 쉬어 주세요."
        )
    if w >= 220:
        return (
            "속도가 상당히 빠르게 측정됐어요. 실제 말하기 속도라기보다 "
            "짧은 시간에 문장이 몰려 인식되었을 가능성도 있어요. "
            "다음 답변에서는 문장 끝마다 0.5초 쉬어 주세요."
        )
    if w >= 185:
        return (
            "속도가 빠른 편으로 측정됐어요. 숨을 한 번 넣고 강조할 단어만 "
            "살짝 늘리면 더 안정적으로 들려요."
        )
    if w > 0 and w < 70:
        return (
            "속도가 다소 느린 편이에요. 자연스러운 리듬을 위해 "
            "문장 사이에 짧은 쉼을 넣어 보세요."
        )

    if base and "속도는 빠른 편" not in base:
        return base
    if base:
        return base
    return (
        "발음은 전반적으로 이해 가능한 수준이에요. "
        "문장 끝을 너무 올리지 않고 살짝 내려 말하면 차분하게 들려요."
    )
