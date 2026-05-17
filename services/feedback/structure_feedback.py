"""
Transcript-based answer structure feedback (OPIc descriptive answers).

Feedback-only — does not affect scores or call Gemini.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_TOPIC_HOME = "home"
_TOPIC_PARK = "park"
_TOPIC_CAFE = "cafe"
_TOPIC_GENERAL = "general"

_FLOWS: Dict[str, Tuple[str, ...]] = {
    _TOPIC_HOME: (
        "위치",
        "집 구조",
        "함께 사는 대상",
        "좋은 점",
        "아쉬운 점",
        "전체 평가",
    ),
    _TOPIC_PARK: (
        "위치",
        "분위기",
        "자주 하는 일",
        "기억에 남는 경험",
        "전체 평가",
    ),
    _TOPIC_CAFE: (
        "위치/분위기",
        "자주 가는 이유",
        "보통 하는 일",
        "특별한 경험",
        "전체 평가",
    ),
    _TOPIC_GENERAL: (
        "주제 소개",
        "구체적 설명",
        "개인적 이유",
        "짧은 예시",
        "마무리",
    ),
}

_NEXT_SENTENCE_HOME = (
    "위치 → 집 구조 → 강아지 이야기 → 월세 장점 → 전체 평가 순서로 정리하면 더 자연스러워요."
)
_NEXT_SENTENCE_PARK = (
    "위치 → 분위기 → 자주 하는 일 → 기억에 남는 경험 → 전체 평가 순서로 말하면 좋아요."
)
_NEXT_SENTENCE_CAFE = (
    "위치/분위기 → 자주 가는 이유 → 보통 하는 일 → 특별한 경험 → 마무리 순서로 정리해 보세요."
)
_NEXT_SENTENCE_GENERAL = (
    "주제 소개 → 구체적 설명 → 개인적 이유 → 짧은 예시 → 마무리 순서로 연결해 보세요."
)


def _norm(text: str) -> str:
    return (text or "").strip()


def _detect_topic(transcript: str, question_text: str) -> str:
    blob = f"{question_text} {transcript}".lower()
    if re.search(
        r"\b(?:house|home|apartment|room|bedroom|bathroom|living\s+room|rent|neighbor)\b",
        blob,
    ) or re.search(r"집|아파트|방|거실|화장실|월세|이웃", blob):
        return _TOPIC_HOME
    if re.search(r"\b(?:park|playground|trail|hiking|picnic)\b", blob) or "공원" in blob:
        return _TOPIC_PARK
    if re.search(r"\b(?:cafe|coffee|espresso|latte|bakery)\b", blob) or "카페" in blob:
        return _TOPIC_CAFE
    return _TOPIC_GENERAL


def _count_pattern(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, flags=re.IGNORECASE))


def _has_any(lower: str, patterns: Tuple[str, ...]) -> bool:
    return any(re.search(p, lower, re.IGNORECASE) for p in patterns)


def _extract_proper_nouns(transcript: str) -> List[str]:
    """City / pet names worth mentioning in feedback."""
    found: List[str] = []
    for m in re.finditer(
        r"\b(?:in|at|here in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        transcript,
    ):
        name = m.group(1).strip()
        if name.lower() not in ("the", "an", "a", "uh", "um") and name not in found:
            found.append(name)
    for m in re.finditer(
        r"\b(?:puppy|dog|pet|cat)\s+(?:named|name)\s+([A-Z][a-z]+)\b",
        transcript,
        re.IGNORECASE,
    ):
        found.append(m.group(1))
    if re.search(r"\bsogum\b", transcript, re.IGNORECASE) and "Sogum" not in found:
        found.append("Sogum")
    return found[:4]


def _detect_content_flags(lower: str, transcript: str) -> Dict[str, bool]:
    return {
        "location": _has_any(
            lower,
            (
                r"\b(?:live|living)\s+(?:here\s+)?in\b",
                r"\b(?:city|town|area|neighborhood|gwangju)\b",
                r"\bquiet\s+place\b",
            ),
        ),
        "impression": _has_any(
            lower,
            (
                r"\bquiet\s+place\b",
                r"\b(?:nice|great|good|comfortable|peaceful)\b",
            ),
        ),
        "structure": _has_any(
            lower,
            (
                r"\b(?:apartment|house|home|room|bedroom|bathroom|kitchen|living\s+room)\b",
                r"\b\d+\s+rooms?\b",
                r"\bthree\s+rooms\b",
            ),
        ),
        "people_pets": _has_any(
            lower,
            (
                r"\b(?:puppy|dog|pet|cat|with\s+my)\b",
                r"\bnamed\s+\w+",
                r"\bjindo\b",
                r"\bbreed\b",
            ),
        ),
        "advantage": _has_any(
            lower,
            (
                r"\b(?:cheap|affordable|rent|bucks|dollars|price|reason\s+i\s+love)\b",
                r"\b200\b",
                r"\bcan\s+you\s+imagine\b",
            ),
        ),
        "downside": _has_any(
            lower,
            (
                r"\b(?:noisy|neighbor|downside|problem|disadvantage|but\s+it)\b",
            ),
        ),
        "ending": _has_any(
            lower,
            (
                r"\b(?:overall|in\s+conclusion|that\s+is\s+(?:why|one\s+reason)|love\s+(?:to\s+)?(?:stay|living)\s+here)\b",
                r"\bso\s+that\s+is\b",
            ),
        ),
        "sensory": _has_any(
            lower,
            (
                r"\b(?:cozy|bright|spacious|dark|warm|smell|sound|view|furniture)\b",
            ),
        ),
        "example": _has_any(
            lower,
            (r"\b(?:for\s+example|such\s+as|like\s+when|one\s+time)\b",),
        ),
    }


def _detect_repetition(lower: str, transcript: str) -> List[str]:
    notes: List[str] = []
    if (
        _count_pattern(lower, r"\bjindo\s+mix\b") >= 2
        or (
            _count_pattern(lower, r"\bthe\s+breed\s+is\b") >= 1
            and _count_pattern(lower, r"\bjindo\b") >= 1
            and _count_pattern(lower, r"\bis\s+a\s+jindo\b") >= 1
        )
    ):
        notes.append("Jindo mix 설명")
    if _count_pattern(lower, r"\bi(?:'m| am)\s+living\b") >= 2:
        notes.append("I'm living 표현")
    if _count_pattern(lower, r"\bgwangju\b") >= 2:
        notes.append("Gwangju 언급")
    if _count_pattern(lower, r"\b(?:really|very)\b") >= 3:
        notes.append("really/very 강조")
    if notes:
        joined = "·".join(notes[:2])
        return [
            f"같은 표현({joined})이 반복되는 부분은 한 번으로 줄이고, "
            "다음 정보로 넘어가면 더 자연스러워요."
        ]
    return []


def _needs_transition_tip(lower: str) -> bool:
    """Pet/personal block then rent/advantage without linker phrases."""
    has_pet = _has_any(lower, (r"\b(?:puppy|dog|named|breed|jindo)\b",))
    has_rent = _has_any(lower, (r"\b(?:cheap|affordable|rent|bucks|200)\b",))
    has_linker = _has_any(
        lower,
        (
            r"\banother\s+thing\b",
            r"\bon\s+top\s+of\s+that\b",
            r"\bone\s+(?:more\s+)?reason\b",
            r"\b(?:what|one\s+thing)\s+that\s+i\s+love\s+about\b",
            r"\bi\s+love\s+about\b",
            r"\balso\b",
        ),
    )
    if has_pet and has_rent and not has_linker:
        pet_pos = re.search(r"\b(?:puppy|dog|breed|jindo)\b", lower)
        rent_pos = re.search(r"\b(?:cheap|affordable|rent)\b", lower)
        if pet_pos and rent_pos and pet_pos.start() < rent_pos.start():
            return True
    return False


def _build_good_bullets(
    flags: Dict[str, bool],
    topic: str,
    transcript: str,
    names: List[str],
) -> List[str]:
    good: List[str] = []
    lower = transcript.lower()

    if flags["location"]:
        loc_bits: List[str] = []
        if re.search(r"\bgwangju\b", lower):
            loc_bits.append("광주")
        for n in names:
            if n.lower() in ("sogum", "jindo"):
                continue
            if re.search(rf"\b{re.escape(n.lower())}\b", lower) and n not in loc_bits:
                if n.lower() != "city":
                    loc_bits.append(n)
        loc_label = "·".join(dict.fromkeys(loc_bits)) if loc_bits else "위치"
        if topic == _TOPIC_HOME:
            good.append(
                f"{loc_label}와 아파트 구조를 말해 답변의 기본 정보가 분명했어요."
                if flags["structure"]
                else f"{loc_label}를 말해 답변의 시작이 분명했어요."
            )
        else:
            good.append("어디인지·어떤 장소인지 말해 주제가 잡혔어요.")

    if flags["structure"] and topic == _TOPIC_HOME and not (
        good and "구조" in good[0]
    ):
        room_note = ""
        m = re.search(r"\b(\d+|three|two)\s+rooms?\b", lower)
        if m:
            room_note = f" ({m.group(0)} 등)"
        bath = "·화장실" if re.search(r"\bbathroom\b", lower) else ""
        good.append(f"방/공간 구성{room_note}{bath}을 넣어 집 묘사가 구체적이었어요.")

    if flags["people_pets"]:
        pet_name = ""
        m_pet = re.search(
            r"\b(?:puppy|dog|pet)\s+(?:named|name)\s+([A-Z][a-z]+)\b",
            transcript,
            re.IGNORECASE,
        )
        if m_pet:
            pet_name = m_pet.group(1)
        elif re.search(r"\bsogum\b", lower):
            pet_name = "Sogum"
        if re.search(r"\bpuppy\b|\bdog\b", lower):
            label = f"강아지 {pet_name}" if pet_name else "반려견"
            good.append(f"{label} 이야기를 넣어 개인적인 느낌이 살아났어요.")
        elif flags["people_pets"]:
            good.append("함께 사는 대상을 언급해 답변이 개인적으로 느껴졌어요.")

    if flags["advantage"] and not any("월세" in g or "가격" in g or "저렴" in g for g in good):
        if re.search(r"\b200\s+bucks\b|\baffordable\b|\bcheap\b", lower):
            good.append("월세·가격 이야기를 넣어 좋은 점의 이유가 분명했어요.")

    if flags["downside"] and len(good) < 3:
        good.append("아쉬운 점도 함께 말해 균형 있는 구성이었어요.")

    if flags["ending"] and len(good) < 3:
        good.append("마지막에 이곳을 좋아하는 이유로 답을 마무리했어요.")

    if not good:
        good.append("질문 주제에 맞게 답을 시작했어요.")
        if flags["structure"] or flags["impression"]:
            good.append("핵심 정보를 중심으로 이야기하려는 흐름이 보였어요.")

    return good[:3]


def _build_missing_bullets(
    flags: Dict[str, bool],
    topic: str,
    lower: str,
    repetition_notes: List[str],
) -> List[str]:
    missing: List[str] = []

    if repetition_notes:
        missing.extend(repetition_notes[:1])

    if not flags["sensory"] and topic == _TOPIC_HOME:
        missing.append(
            "방이나 거실이 어떤 분위기인지(밝은지, 아늑한지) 묘사가 조금 더 있으면 좋아요."
        )

    if not flags["example"] and len(missing) < 3:
        missing.append("짧은 구체적 예시 한 가지를 붙이면 설득력이 더 좋아져요.")

    if not flags["downside"] and topic == _TOPIC_HOME and flags["advantage"]:
        if len(missing) < 3:
            missing.append(
                "좋은 점만큼 아쉬운 점 한 가지를 말하면 균형 있는 마무리가 됩니다."
            )

    if not flags["ending"] and len(missing) < 3:
        missing.append("전체 평가 한 문장으로 끝을 정리하면 더 완성도 있게 들려요.")

    if _count_pattern(lower, r"\bwhat\s+do\s+you\b") >= 1:
        missing.append("중간에 질문형 문장이 들어가 흐름이 끊겨요 — 평서문으로 이어가 보세요.")

    if not missing:
        missing.append("정보는 있으니, 문장 사이 연결만 조금 더 매끄럽게 다듬어 보세요.")

    return missing[:3]


def build_structure_feedback(
    transcript: str,
    question_text: str = "",
) -> Dict[str, Any]:
    """
  Return structure coaching derived from the transcript.

    Keys: good, missing, next (str), suggested_flow (list), transition_tip (optional).
    """
    body = _norm(transcript)
    if len(body) < 12:
        flow = list(_FLOWS[_TOPIC_GENERAL])
        return {
            "good": ["질문에 맞게 답을 시작했어요."],
            "missing": ["조금 더 길게 말하면 구조 피드백이 더 정확해져요."],
            "next": _NEXT_SENTENCE_GENERAL,
            "suggested_flow": flow,
            "transition_tip": None,
        }

    lower = body.lower()
    topic = _detect_topic(body, question_text)
    flow_steps = list(_FLOWS.get(topic, _FLOWS[_TOPIC_GENERAL]))
    flags = _detect_content_flags(lower, body)
    names = _extract_proper_nouns(body)
    repetition = _detect_repetition(lower, body)

    good = _build_good_bullets(flags, topic, body, names)
    missing = _build_missing_bullets(flags, topic, lower, repetition)

    if topic == _TOPIC_HOME:
        next_sentence = _NEXT_SENTENCE_HOME
    elif topic == _TOPIC_PARK:
        next_sentence = _NEXT_SENTENCE_PARK
    elif topic == _TOPIC_CAFE:
        next_sentence = _NEXT_SENTENCE_CAFE
    else:
        next_sentence = _NEXT_SENTENCE_GENERAL

    transition_tip: Optional[str] = None
    if _needs_transition_tip(lower):
        transition_tip = (
            "강아지 이야기에서 월세 장점으로 넘어갈 때 "
            '"Another thing I like about this apartment is…" 또는 '
            '"One more reason I love living here is…" 같은 연결 표현을 쓰면 더 자연스러워요.'
        )
    elif flags["people_pets"] and flags["advantage"] and not _has_any(
        lower,
        (r"\banother\s+thing\b", r"\bone\s+more\s+reason\b"),
    ):
        if len(missing) < 3:
            missing.append(
                "반려견 이야기 다음에 월세 장점으로 넘어갈 때 연결 문장을 넣으면 흐름이 더 매끄러워요."
            )

    return {
        "good": good,
        "missing": missing,
        "next": next_sentence,
        "suggested_flow": flow_steps,
        "transition_tip": transition_tip,
    }
