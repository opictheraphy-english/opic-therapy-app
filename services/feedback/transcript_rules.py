"""
Rule-based grammar corrections and expression upgrades from transcript text only.

Feedback post-processing — does not affect scores or call Gemini.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Tuple

_MAX_GRAMMAR = 4
_MAX_EXPRESSION = 4


def _snippet(body: str, m: re.Match[str]) -> str:
    return body[m.start() : m.end()]


def _grammar_row(before: str, after: str, reason: str) -> Dict[str, str]:
    before = (before or "").strip()
    after = (after or "").strip()
    reason = (reason or "").strip()
    return {
        "before": before,
        "after": after,
        "reason": reason,
        "wrong": before,
        "right": after,
        "note": reason,
    }


def _expression_row(before: str, better: List[str], reason: str) -> Dict[str, Any]:
    before = (before or "").strip()
    alts = [str(b).strip() for b in better if str(b).strip()]
    reason = (reason or "").strip()
    return {
        "before": before,
        "better": alts,
        "reason": reason,
        "phrase": before,
        "alternatives": alts,
        "note": reason,
    }


def _apply_grammar_rules(
    body: str,
    lower: str,
    rules: Tuple[Callable[[str, str, List[Dict[str, str]], set[str]], None], ...],
) -> List[Dict[str, str]]:
    found: List[Dict[str, str]] = []
    used_ids: set[str] = set()

    def add(rule_id: str, row: Dict[str, str]) -> None:
        if len(found) >= _MAX_GRAMMAR or rule_id in used_ids:
            return
        key = (row.get("before") or "").lower()
        if any((x.get("before") or "").lower() == key for x in found):
            return
        used_ids.add(rule_id)
        found.append(row)

    for rule_fn in rules:
        if len(found) >= _MAX_GRAMMAR:
            break
        rule_fn(body, lower, found, used_ids, add)

    return found


def _rule_living_here_in(body: str, lower: str, _f, _u, add) -> None:
    m = re.search(
        r"\bi(?:'m)\s+living\s+here\s+in\s+([A-Za-z][\w\s.-]{0,40}?)(?=[.,;!?]|\s+and\b|\s+uh\b|\s+um\b|$)",
        lower,
        re.IGNORECASE,
    )
    if not m:
        return
    place = body[m.start(1) : m.end(1)].strip()
    add(
        "living_here_in",
        _grammar_row(
            _snippet(body, m),
            f"I live in {place}",
            "현재 사는 곳을 일반적으로 말할 때는 현재형 live가 더 자연스럽습니다.",
        ),
    )


def _rule_pet_named(body: str, lower: str, _f, _u, add) -> None:
    for pet in ("puppy", "dog", "pet", "cat"):
        m = re.search(
            rf"\b(?:a\s+)?(?:cute\s+)?{pet}\s+name\s+([A-Za-z][A-Za-z'-]*)",
            lower,
            re.IGNORECASE,
        )
        if not m:
            continue
        name = body[m.start(1) : m.end(1)]
        before = _snippet(body, m)
        article = "a " if re.search(r"\ba\s+", before, re.IGNORECASE) else ""
        cute = "cute " if "cute" in before.lower() else ""
        after = f"{article}{cute}{pet} named {name}".replace("  ", " ").strip()
        add(
            f"named_{pet}",
            _grammar_row(
                before,
                after,
                "name을 뒤에서 수식할 때는 named를 쓰는 것이 자연스럽습니다.",
            ),
        )
        return


def _rule_breed_jindo(body: str, lower: str, _f, _u, add) -> None:
    m = re.search(
        r"\b(?:uh\s+)?(?:the\s+)?breed\s+is\s+(?:a\s+)?jindo\s+mix\b",
        lower,
        re.IGNORECASE,
    )
    if m:
        add(
            "breed_is_jindo",
            _grammar_row(
                _snippet(body, m),
                "She is a Jindo mix",
                "품종을 소개할 때는 She is a … mix처럼 주어를 넣는 편이 자연스럽습니다.",
            ),
        )


def _rule_love_to_stay(body: str, lower: str, _f, _u, add) -> None:
    m = re.search(r"\bi\s+love\s+to\s+stay\s+here\b", lower, re.IGNORECASE)
    if m:
        add(
            "love_to_stay",
            _grammar_row(
                _snippet(body, m),
                "I love living here",
                "거주지에 대해 말할 때 stay보다 live가 자연스럽습니다.",
            ),
        )


def _rule_living_here_with(body: str, lower: str, _f, used_ids: set, add) -> None:
    if "living_here_in" in used_ids:
        return
    m = re.search(r"\bi(?:'m)\s+living\s+here\s+with\b", lower, re.IGNORECASE)
    if m:
        add(
            "living_here_with",
            _grammar_row(
                _snippet(body, m),
                "I live here with",
                "현재 거주 상황을 말할 때는 I'm living보다 I live here가 자연스럽습니다.",
            ),
        )


def _rule_rooms_bedroom_plural(body: str, lower: str, _f, _u, add) -> None:
    m = re.search(
        r"\b(\w+\s+rooms?\s+and\s+)(two|three|four)\s+bedroom\b(?!\s*-)",
        lower,
        re.IGNORECASE,
    )
    if m:
        count = body[m.start(2) : m.end(2)]
        before = _snippet(body, m)
        after = f"{body[m.start(1):m.end(1)]}{count} bedrooms"
        add(
            "rooms_and_bedroom_plural",
            _grammar_row(
                before,
                after,
                "숫자 뒤 bedroom은 복수형 bedrooms를 씁니다.",
            ),
        )


def _rule_two_bedroom(body: str, lower: str, _f, _u, add) -> None:
    m = re.search(r"\btwo\s+bedroom\b(?!\s*s)(?!\s*-)", lower, re.IGNORECASE)
    if m:
        add(
            "two_bedroom",
            _grammar_row(
                _snippet(body, m),
                "two bedrooms / a two-bedroom apartment",
                "숫자 뒤 명사는 복수형. 형용사처럼 쓰면 two-bedroom이 됩니다.",
            ),
        )


def _rule_quite_good_house(body: str, lower: str, _f, _u, add) -> None:
    m = re.search(r"\ba\s+quite\s+good\s+house\b", lower, re.IGNORECASE)
    if m:
        add(
            "quite_good_house",
            _grammar_row(
                _snippet(body, m),
                "quite a good house / a pretty nice place",
                "quite의 위치가 더 자연스럽습니다.",
            ),
        )


_GRAMMAR_RULE_FUNCS = (
    _rule_living_here_in,
    _rule_pet_named,
    _rule_breed_jindo,
    _rule_love_to_stay,
    _rule_living_here_with,
    _rule_rooms_bedroom_plural,
    _rule_two_bedroom,
    _rule_quite_good_house,
)


def extract_grammar_corrections(transcript: str) -> List[Dict[str, str]]:
    """Detect common learner grammar patterns; return up to 4 items."""
    body = (transcript or "").strip()
    if len(body) < 8:
        return []
    return _apply_grammar_rules(body, body.lower(), _GRAMMAR_RULE_FUNCS)


def extract_expression_upgrades(transcript: str) -> List[Dict[str, Any]]:
    """Detect basic or awkward expressions; return up to 4 items."""
    body = (transcript or "").strip()
    if len(body) < 8:
        return []

    lower = body.lower()
    found: List[Dict[str, Any]] = []
    used_ids: set[str] = set()

    def add(rule_id: str, row: Dict[str, Any]) -> None:
        if len(found) >= _MAX_EXPRESSION or rule_id in used_ids:
            return
        key = (row.get("before") or "").lower()
        if any((x.get("before") or "").lower() == key for x in found):
            return
        used_ids.add(rule_id)
        found.append(row)

    priority: Tuple[Tuple[str, str, Tuple[str, ...], str], ...] = (
        (
            "quiet_place",
            r"\bquiet\s+place\b",
            ("a calm and peaceful area", "a quiet residential area"),
            "quiet place보다 area나 residential처럼 맥락을 넓혀 주면 더 자연스럽습니다.",
        ),
        (
            "can_you_imagine",
            r"\bcan\s+you\s+imagine\s+that\b",
            (
                "I know, it sounds almost unbelievable",
                "It's hard to believe, honestly",
            ),
            "대화체로는 좋지만 너무 자주 쓰면 과장되게 들릴 수 있어요.",
        ),
    )

    for rule_id, pattern, alts, reason in priority:
        m = re.search(pattern, lower, re.IGNORECASE)
        if m:
            add(rule_id, _expression_row(_snippet(body, m), list(alts), reason))

    m = re.search(
        r"\bsuper\s+cheap\b[^.]{0,40}?\bvery\s+affordable\b",
        lower,
        re.IGNORECASE,
    )
    if m:
        add(
            "super_cheap_affordable",
            _expression_row(
                _snippet(body, m),
                ["surprisingly affordable", "the rent is very reasonable"],
                "cheap은 의미는 통하지만 다소 직접적이라 affordable/reasonable이 더 자연스럽습니다.",
            ),
        )

    rules: Tuple[Tuple[str, str, Tuple[str, ...], str], ...] = (
        (
            "really_great",
            r"\breally\s+great\b",
            (
                "cozy and practical",
                "comfortable and convenient",
                "a nice place to live",
            ),
            "great만 쓰기보다 집·거주지 묘사에서는 cozy, comfortable처럼 구체적인 형용사가 좋아요.",
        ),
        (
            "super_cheap",
            r"\bsuper\s+cheap\b",
            ("surprisingly affordable", "the rent is very reasonable"),
            "cheap은 의미는 통하지만 다소 직접적이라 affordable/reasonable이 더 자연스럽습니다.",
        ),
        (
            "very_affordable",
            r"\bvery\s+affordable\b",
            (
                "surprisingly affordable",
                "much more affordable than I expected",
            ),
            "very affordable보다 surprisingly affordable이 더 자연스럽게 들려요.",
        ),
        (
            "crazy_neighbor",
            r"\bcrazy\s+neighbor\b",
            ("a noisy neighbor", "a neighbor who can be a bit loud"),
            "crazy는 강하고 비격식적이라 시험 답변에서는 noisy, loud가 더 안전해요.",
        ),
        (
            "just_wanna_say",
            r"\bi\s+just\s+wanna\s+say\b",
            ("overall, I'd say", "to be honest, I'd say"),
            "구어체 wanna 대신 overall I'd say처럼 마무리하면 자연스럽습니다.",
        ),
        (
            "quite_good_house",
            r"\bquite\s+good\s+house\b",
            (
                "a comfortable place to live",
                "a practical apartment",
                "a pretty nice place",
            ),
            "good house보다 comfortable place처럼 구체적으로 묘사하면 좋아요.",
        ),
        (
            "good_house",
            r"\bgood\s+house\b",
            ("a comfortable place to live", "a practical apartment"),
            "good house보다 comfortable place처럼 구체적으로 묘사하면 좋아요.",
        ),
    )

    for rule_id, pattern, alts, reason in rules:
        if len(found) >= _MAX_EXPRESSION:
            break
        if rule_id == "super_cheap" and "super_cheap_affordable" in used_ids:
            continue
        if rule_id == "very_affordable" and "super_cheap_affordable" in used_ids:
            continue
        m = re.search(pattern, lower, re.IGNORECASE)
        if m:
            add(rule_id, _expression_row(_snippet(body, m), list(alts), reason))

    weak_rules: Tuple[Tuple[str, str, Tuple[str, ...], str], ...] = (
        (
            "really_adj",
            r"\breally\s+(good|nice|great|bad)\b",
            ("quite", "fairly", "genuinely"),
            "really + 형용사는 반복되면 단조롭게 들릴 수 있어요.",
        ),
        (
            "very_adj",
            r"\bvery\s+(good|nice|bad|happy)\b",
            ("quite", "fairly", "genuinely"),
            "very + 형용사 대신 한 단어 형용사를 써 보세요.",
        ),
        (
            "stuff",
            r"\bstuff\b",
            ("things", "belongings", "details"),
            "stuff는 비격식 — 맥락에 맞는 명사로 바꿔 보세요.",
        ),
    )
    for rule_id, pattern, alts, reason in weak_rules:
        if len(found) >= _MAX_EXPRESSION:
            break
        m = re.search(pattern, lower, re.IGNORECASE)
        if m:
            add(rule_id, _expression_row(_snippet(body, m), list(alts), reason))

    return found[:_MAX_EXPRESSION]
