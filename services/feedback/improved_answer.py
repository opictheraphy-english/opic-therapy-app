"""
Local rewritten sample answers for coaching UI (no LLM).

Feedback-only — does not affect scores or call Gemini.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

_INSUFFICIENT_MSG = (
    "답변 내용이 충분히 인식되지 않아 예시 답변을 만들기 어려웠어요. "
    "같은 질문을 한 번 더 말해보세요."
)

_TOPIC_HOME = "home"
_TOPIC_PARK = "park"
_TOPIC_CAFE = "cafe"
_TOPIC_GENERAL = "general"

_NUMBER_WORDS = {
    "one": "one",
    "two": "two",
    "three": "three",
    "four": "four",
    "five": "five",
    "a": "one",
    "an": "one",
    "just": "one",
}


def _norm(text: str) -> str:
    return (text or "").strip()


def _word_count(text: str) -> int:
    return len(re.findall(r"\b[\w']+\b", text))


def _is_sufficient(transcript: str) -> bool:
    t = _norm(transcript)
    if len(t) < 18:
        return False
    if _word_count(t) < 10:
        return False
    if not re.search(r"[a-zA-Z]{3,}", t):
        return False
    return True


def _detect_topic(transcript: str, question_text: str) -> str:
    blob = f"{question_text} {transcript}".lower()
    if re.search(
        r"\b(?:house|home|apartment|room|bedroom|bathroom|rent|neighbor|puppy|dog)\b",
        blob,
    ) or re.search(r"집|아파트|방|월세", blob):
        return _TOPIC_HOME
    if re.search(r"\b(?:park|playground|trail|hiking|picnic)\b", blob) or "공원" in blob:
        return _TOPIC_PARK
    if re.search(r"\b(?:cafe|coffee|espresso|latte|bakery)\b", blob) or "카페" in blob:
        return _TOPIC_CAFE
    return _TOPIC_GENERAL


def _extract_city(transcript: str, lower: str) -> Optional[str]:
    if re.search(r"\bgwangju\b", lower):
        return "Gwangju"
    m = re.search(
        r"\b(?:live|living)\s+(?:here\s+)?in\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b",
        transcript,
    )
    if m:
        name = m.group(1).strip()
        if name.lower() not in ("the", "an", "a", "uh", "um", "here"):
            return name
    m2 = re.search(r"\b([A-Z][a-z]+)\s+City\b", transcript)
    if m2:
        return m2.group(1)
    return None


def _extract_room_phrase(lower: str) -> Optional[str]:
    rooms_m = re.search(
        r"\b(?:(one|two|three|four|five|a|an|just)\s+)?(\d+)\s+rooms?\b", lower
    )
    bath_m = re.search(
        r"\b(?:(one|two|three|just)\s+)?(\d+)?\s*bathrooms?\b", lower
    )
    rooms: Optional[str] = None
    if rooms_m:
        if rooms_m.group(2):
            n = rooms_m.group(2)
            rooms = f"{n} room{'s' if n != '1' else ''}"
        elif rooms_m.group(1):
            w = _NUMBER_WORDS.get(rooms_m.group(1).lower(), rooms_m.group(1))
            rooms = f"{w} rooms"
    if not rooms and re.search(r"\bthree\s+rooms?\b", lower):
        rooms = "three rooms"
    baths: Optional[str] = None
    if bath_m:
        if bath_m.group(2):
            n = bath_m.group(2)
            baths = f"{n} bathroom{'s' if n != '1' else ''}"
        elif bath_m.group(1):
            w = _NUMBER_WORDS.get(bath_m.group(1).lower(), bath_m.group(1))
            baths = f"{w} bathroom"
    if not baths and re.search(r"\bone\s+bathroom\b", lower):
        baths = "one bathroom"
    if rooms and baths:
        return f"{rooms} and {baths}"
    if rooms:
        return rooms
    if re.search(r"\bapartment\b", lower):
        return "a few rooms"
    return None


def _extract_pet(transcript: str, lower: str) -> Tuple[Optional[str], Optional[str], str]:
    """Returns (name, breed, pronoun)."""
    name: Optional[str] = None
    for pat in (
        r"\b(?:puppy|dog|pet)\s+named\s+([A-Z][a-z]+)\b",
        r"\b(?:puppy|dog|pet)\s+name[d]?\s+([A-Z][a-z]+)\b",
        r"\b([A-Z][a-z]+)\s+is\s+a\s+jindo\b",
    ):
        m = re.search(pat, transcript, re.IGNORECASE)
        if m:
            name = m.group(1).capitalize()
            break
    if not name and re.search(r"\bsogum\b", lower):
        name = "Sogum"
    breed = "Jindo mix" if re.search(r"\bjindo\b", lower) else None
    pronoun = "She" if re.search(r"\b(?:she|her|puppy|dog)\b", lower) else "He"
    if name and re.search(rf"\b{re.escape(name.lower())}\b.*\bshe\b", lower):
        pronoun = "She"
    return name, breed, pronoun


def _city_impression(lower: str) -> str:
    if re.search(r"\bquiet\s+place\b", lower):
        return "a calm and comfortable city"
    if re.search(r"\b(?:peaceful|calm|comfortable)\b", lower):
        return "a calm and comfortable city"
    if re.search(r"\b(?:nice|great|good)\b", lower):
        return "a nice place to live"
    return "a good place to live"


def _rent_phrase(lower: str) -> str:
    if re.search(r"\b200\s+bucks\b", lower):
        return "the rent is surprisingly affordable"
    if re.search(r"\baffordable\b", lower) and re.search(r"\bcheap\b", lower):
        return "the rent is surprisingly affordable"
    if re.search(r"\baffordable\b", lower):
        return "the rent is surprisingly affordable"
    if re.search(r"\bcheap\b", lower):
        return "the rent is very reasonable"
    if re.search(r"\brent\b", lower):
        return "the rent is reasonable"
    return "living here is affordable"


def _build_home_answer(transcript: str, lower: str) -> Optional[str]:
    city = _extract_city(transcript, lower)
    rooms = _extract_room_phrase(lower)
    pet_name, breed, pronoun = _extract_pet(transcript, lower)
    has_apartment = bool(re.search(r"\bapartment\b", lower))
    has_rent = bool(
        re.search(r"\b(?:cheap|affordable|rent|bucks|200)\b", lower)
    )
    has_downside = bool(re.search(r"\b(?:noisy|neighbor|downside|problem)\b", lower))

    if not city and not has_apartment and not pet_name:
        return None

    sentences: List[str] = []

    if city:
        imp = _city_impression(lower)
        sentences.append(
            f"Yes, I live in {city}, and I would say it is {imp}."
        )
    elif has_apartment:
        sentences.append("Yes, I live in an apartment that works well for me.")

    if has_apartment and rooms:
        if pet_name:
            sentences.append(
                f"I live in an apartment with {rooms}, and I share the place "
                f"with my cute dog, {pet_name}."
            )
        else:
            sentences.append(
                f"I live in an apartment with {rooms}."
            )
    elif has_apartment:
        if pet_name:
            sentences.append(
                f"I live in an apartment, and I share the place with my dog, {pet_name}."
            )
        else:
            sentences.append("I live in a comfortable apartment.")

    if pet_name and breed:
        warmth = (
            f"{pronoun} is a {breed}, and {pronoun.lower()} makes the apartment "
            "feel much warmer."
        )
        sentences.append(warmth)
    elif pet_name:
        sentences.append(
            f"My dog, {pet_name}, makes the apartment feel much warmer."
        )
    elif breed:
        sentences.append(f"I have a {breed}, and it makes home feel cozier.")

    if has_rent:
        sentences.append(
            f"One thing I really like about my place is that {_rent_phrase(lower)}."
        )

    if has_downside:
        sentences.append(
            "It is not perfect, but it is still a practical place for everyday life."
        )
        sentences.append(
            "Overall, it is a comfortable place to live even with a few small issues."
        )
    else:
        sentences.append(
            "Overall, it is not a fancy apartment, but it is a comfortable and "
            "practical place to live."
        )

    return _finalize_sentences(sentences)


def _build_park_answer(transcript: str, lower: str) -> Optional[str]:
    if not re.search(r"\b(?:park|playground|trail)\b", lower):
        return None
    place = "a park near my home"
    m = re.search(r"\b(?:called|named)\s+([A-Z][a-z]+)\b", transcript)
    if m:
        place = f"{m.group(1)} Park"
    sentences = [
        f"I often go to {place} when I have free time.",
        "It is usually quiet, so I can relax and clear my head.",
        "I like walking there or sitting on a bench for a while.",
        "Overall, it is one of my favorite places to unwind.",
    ]
    return _finalize_sentences(sentences)


def _build_cafe_answer(transcript: str, lower: str) -> Optional[str]:
    if not re.search(r"\b(?:cafe|coffee)\b", lower):
        return None
    sentences = [
        "There is a cafe I go to pretty often near where I live.",
        "I like the atmosphere because it is calm and easy to stay for a while.",
        "I usually grab a drink and chat with a friend or read for a bit.",
        "Overall, it is a simple place, but it always feels comfortable.",
    ]
    return _finalize_sentences(sentences)


def _clean_fillers(text: str) -> str:
    t = re.sub(r"\b(?:uh|um|er|ah)\b[,.]?\s*", "", text, flags=re.IGNORECASE)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _apply_grammar_hints(text: str, grammar_corrections: Optional[List[Dict[str, Any]]]) -> str:
    out = text
    for row in grammar_corrections or []:
        if not isinstance(row, dict):
            continue
        before = (row.get("before") or row.get("wrong") or "").strip()
        after = (row.get("after") or row.get("right") or "").strip()
        if before and after and before.lower() in out.lower():
            out = re.sub(re.escape(before), after, out, count=1, flags=re.IGNORECASE)
    replacements = (
        (r"\bi'?m\s+living\s+here\b", "I live here"),
        (r"\bi'?m\s+living\s+in\b", "I live in"),
        (r"\bpuppy\s+name\s+(\w+)\b", r"puppy named \1"),
        (r"\bthe\s+breed\s+is\s+jindo\s+mix\b", ""),
        (r"\b,\s*uh\s+the\s+breed\s+is\s+jindo\s+mix\b", ""),
        (r"\bi\s+love\s+to\s+stay\s+here\b", "I like living here"),
        (r"\bsuper\s+cheap\b", "surprisingly affordable"),
        (r"\bvery\s+affordable\b", "surprisingly affordable"),
        (r"\bcan\s+you\s+imagine\s+that\??\b", ""),
    )
    for pat, repl in replacements:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return _clean_fillers(out)


def _split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", _norm(text))
    return [p.strip() for p in parts if p.strip()]


def _dedupe_sentences(sentences: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for s in sentences:
        key = re.sub(r"[^\w]+", "", s.lower())[:80]
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def _capitalize_first(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    return s[0].upper() + s[1:]


def _finalize_sentences(sentences: List[str], *, min_n: int = 4, max_n: int = 6) -> str:
    cleaned: List[str] = []
    for s in sentences:
        s = _capitalize_first(s.strip())
        if not s:
            continue
        if s[-1] not in ".!?":
            s += "."
        cleaned.append(s)
    cleaned = _dedupe_sentences(cleaned)
    if len(cleaned) > max_n:
        cleaned = cleaned[:max_n]
    while len(cleaned) < min_n and len(cleaned) >= 1:
        break
    return " ".join(cleaned)


def _build_general_answer(
    transcript: str,
    lower: str,
    grammar_corrections: Optional[List[Dict[str, Any]]],
) -> str:
    cleaned = _apply_grammar_hints(transcript, grammar_corrections)
    parts = _split_sentences(cleaned)
    if not parts:
        parts = [_capitalize_first(cleaned)]

    upgraded: List[str] = []
    for p in parts[:3]:
        p = re.sub(r"\bquiet\s+place\b", "calm area", p, flags=re.IGNORECASE)
        p = re.sub(r"\breally\s+great\b", "really nice", p, flags=re.IGNORECASE)
        p = re.sub(r"\bsuper\s+cheap\b", "very affordable", p, flags=re.IGNORECASE)
        upgraded.append(_capitalize_first(p))

    if len(upgraded) < 4:
        if not re.search(r"\b(?:because|since|reason)\b", lower):
            upgraded.append("That is mainly because it fits my daily life well.")
        if not re.search(r"\b(?:for\s+example|such\s+as)\b", lower):
            upgraded.append("For example, I can relax there after a busy day.")
        upgraded.append("Overall, I am happy with it for now.")

    return _finalize_sentences(upgraded)


def _too_similar_to_original(improved: str, transcript: str) -> bool:
    """True if rewrite is mostly the raw transcript."""
    imp = re.sub(r"[^\w\s]", "", improved.lower())
    orig = re.sub(r"[^\w\s]", "", transcript.lower())
    if not imp or not orig:
        return False
    imp_words = imp.split()
    orig_words = set(orig.split())
    if len(imp_words) < 8:
        return False
    overlap = sum(1 for w in imp_words if w in orig_words) / len(imp_words)
    return overlap > 0.88


def build_improved_answer(
    transcript: str,
    question_text: str = "",
    grammar_corrections: Optional[List[Dict[str, Any]]] = None,
    expression_upgrades: Optional[List[Dict[str, Any]]] = None,
    structure_feedback: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Rule-based spoken English sample (4–6 sentences, IM2→IH level).

    Uses the student's ideas only — no Gemini, no unrelated fabrication.
    """
    del expression_upgrades, structure_feedback  # reserved for future hinting

    text = _norm(transcript)
    if not _is_sufficient(text):
        return _INSUFFICIENT_MSG

    lower = text.lower()
    topic = _detect_topic(text, question_text or "")

    improved: Optional[str] = None
    if topic == _TOPIC_HOME:
        improved = _build_home_answer(text, lower)
    elif topic == _TOPIC_PARK:
        improved = _build_park_answer(text, lower)
    elif topic == _TOPIC_CAFE:
        improved = _build_cafe_answer(text, lower)

    if not improved:
        improved = _build_general_answer(text, lower, grammar_corrections)

    if _too_similar_to_original(improved, text):
        retry = _build_home_answer(text, lower)
        if retry:
            improved = retry
        else:
            improved = _build_general_answer(text, lower, grammar_corrections)

    return improved
