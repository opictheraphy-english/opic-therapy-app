"""Lightweight rule-based grammar & expression coach.

Two complementary detectors operate over the LLM transcript:

* :func:`detect_grammar_corrections` — flags well-known ESL slips and returns
  ``{wrong, right, note}`` dicts.
* :func:`detect_alternative_expressions` — surfaces low-flair phrases and
  returns ``{phrase, alternatives, note}`` dicts.

These run **after** the AI evaluation so they never block the analysis
pipeline, and they have no external dependencies — pure regex over the
transcript. They were added to replace the generic "speak more naturally"
boilerplate with concrete, actionable corrections.

Design rules:
* Each rule fires **at most once per response** so we never show the same
  correction twice.
* The lists are intentionally small and high-precision; widening them is
  one-line work.
* Cards are capped (``_MAX_*_HITS``) so a verbose answer doesn't drown the
  user in suggestions.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

# (rule_id, regex, canonical_fix, korean_note)
_GRAMMAR_RULES: Tuple[Tuple[str, str, str, str], ...] = (
    ("very_like", r"\bvery\s+like\b", "really like / really enjoy",
     "‘very’는 동사 ‘like’를 직접 수식하지 못합니다."),
    ("very_much_like", r"\bvery\s+much\s+like\b", "really enjoy",
     "OPIc 답변에서는 ‘really enjoy’가 더 자연스럽습니다."),
    ("am_agree", r"\b(?:i\s+am|i'm)\s+agree\b", "I agree",
     "‘agree’는 동사라 be 동사와 결합하지 않습니다."),
    ("discuss_about", r"\bdiscuss\s+about\b", "discuss",
     "‘discuss’는 타동사 — about이 필요 없습니다."),
    ("explain_about", r"\bexplain\s+about\b", "explain",
     "‘explain X’ 또는 ‘explain that …’ 패턴을 쓰세요."),
    ("people_likes", r"\bpeople\s+likes\b", "people like",
     "people은 복수 — 동사도 복수형."),
    ("advices", r"\badvices\b", "advice",
     "advice는 셀 수 없는 명사입니다."),
    ("informations", r"\binformations\b", "information",
     "information은 셀 수 없는 명사입니다."),
    ("go_to_home", r"\bgo\s+to\s+home\b", "go home",
     "home은 부사로 쓰여 to가 붙지 않습니다."),
    ("more_better", r"\bmore\s+better\b", "better",
     "이중 비교급은 사용하지 않습니다."),
    ("most_best", r"\bmost\s+best\b", "the best",
     "이중 최상급은 사용하지 않습니다."),
    ("have_ever_been", r"\bhave\s+ever\s+been\s+to\b", "have been to",
     "현재완료 긍정문에는 ‘ever’를 거의 쓰지 않습니다."),
    ("almost_people", r"\balmost\s+people\b", "almost everyone / most people",
     "almost는 부사 — 명사 직접 수식 불가."),
    ("a_lots_of", r"\ba\s+lots\s+of\b", "a lot of / plenty of",
     "‘a lots of’는 잘못된 형태입니다."),
    ("there_is_plural", r"\bthere\s+is\s+(?:many|several|a\s+few|two|three|four)\b",
     "there are …",
     "복수 명사 앞에는 ‘there are’."),
    ("very_unique", r"\bvery\s+(?:unique|perfect|essential)\b",
     "truly unique / pretty much essential",
     "절대형용사는 강조어를 잘 받지 않습니다."),
    ("could_to", r"\bcould\s+to\s+\w+", "could …",
     "조동사 뒤에는 to-부정사가 오지 않습니다."),
    ("would_to", r"\bwould\s+to\s+\w+", "would …",
     "조동사 뒤에는 to-부정사가 오지 않습니다."),
    ("listen_music", r"\blisten\s+music\b", "listen to music",
     "‘listen’은 to와 함께 씁니다."),
    ("married_with", r"\bmarried\s+with\b", "married to",
     "married는 ‘to’와 결합합니다."),
    ("how_to_say", r"\bhow\s+to\s+say\b", "how I can say it / how to put it",
     "‘how to say’는 미완성 — 보완 표현이 필요합니다."),
)

# (rule_id, phrase_regex, upgrades, korean_note)
_ALT_RULES: Tuple[Tuple[str, str, Tuple[str, ...], str], ...] = (
    ("a_lot_of", r"\ba\s+lot\s+of\b",
     ("plenty of", "a wide range of", "numerous"),
     "수량 강조 표현을 다양화하세요."),
    ("very_good", r"\bvery\s+good\b",
     ("impressive", "remarkable", "outstanding"),
     "‘very + good’보다 단일 형용사가 더 고급스럽게 들립니다."),
    ("very_nice", r"\bvery\s+nice\b",
     ("pleasant", "polished", "well put-together"),
     "감상 표현은 한 단어 형용사로 압축하면 자연스럽습니다."),
    ("very_happy", r"\bvery\s+happy\b",
     ("delighted", "thrilled", "content"),
     "감정 강조어를 다양화해 보세요."),
    ("very_bad", r"\bvery\s+bad\b",
     ("awful", "terrible", "disappointing"),
     "구체적인 부정 형용사를 사용해 보세요."),
    ("i_think", r"\bi\s+think\b",
     ("I'd say", "From my perspective", "In my view"),
     "‘I think’를 반복해 쓰면 단조롭게 들립니다."),
    ("big", r"\bbig\b",
     ("substantial", "sizeable", "considerable"),
     "‘big’은 IH/AL에서 한 단계 격상된 형용사로 교체해 보세요."),
    ("small", r"\bsmall\b",
     ("compact", "modest", "limited"),
     "맥락에 따라 더 정확한 형용사를 선택해 보세요."),
    ("many_things", r"\bmany\s+things\b",
     ("a wide range of options", "multiple aspects", "various factors"),
     "‘things’는 정보 밀도를 낮춥니다."),
    ("a_lot", r"\b(?:a\s+lot|lots)\b",
     ("a great deal", "considerably", "to a significant extent"),
     "수량 부사도 다양화하면 점수에 유리합니다."),
    ("kind_of", r"\bkind\s+of\b",
     ("somewhat", "rather", "to some extent"),
     "구어체 hedger는 시험 환경에서 다른 표현으로 교체해 보세요."),
    ("you_know", r"\byou\s+know\b",
     ("as you can imagine", "as one would expect"),
     "필러 ‘you know’는 횟수를 줄이거나 다른 표현으로 바꿔 보세요."),
    ("stuff", r"\bstuff\b",
     ("items", "belongings", "details"),
     "‘stuff’는 비격식 — 맥락에 맞는 명사로 교체하세요."),
    ("really_like", r"\breally\s+like\b",
     ("genuinely enjoy", "have a soft spot for", "find … rewarding"),
     "‘really like’가 반복되면 단조롭게 들립니다."),
    ("good_at", r"\bgood\s+at\b",
     ("skilled at", "proficient in", "well-versed in"),
     "역량 표현을 한 단계 올려 보세요."),
)

_MAX_GRAMMAR_HITS = 4
_MAX_ALT_HITS = 4


def _norm(text: str) -> str:
    return (text or "").strip()


def detect_grammar_corrections(transcript: str) -> List[Dict[str, str]]:
    """Return ``[{wrong, right, note}, ...]`` for surfaced grammar slips."""
    body = _norm(transcript)
    if not body:
        return []
    lower = body.lower()
    found: List[Dict[str, str]] = []
    for rule_id, pattern, fix, note in _GRAMMAR_RULES:
        m = re.search(pattern, lower, flags=re.IGNORECASE)
        if not m:
            continue
        snippet = body[m.start(): m.end()]
        found.append({"wrong": snippet, "right": fix, "note": note})
        if len(found) >= _MAX_GRAMMAR_HITS:
            break
    return found


def detect_alternative_expressions(transcript: str) -> List[Dict[str, Any]]:
    """Return ``[{phrase, alternatives, note}, ...]`` for upgradeable phrases."""
    body = _norm(transcript)
    if not body:
        return []
    lower = body.lower()
    found: List[Dict[str, Any]] = []
    for rule_id, pattern, alternatives, note in _ALT_RULES:
        m = re.search(pattern, lower, flags=re.IGNORECASE)
        if not m:
            continue
        snippet = body[m.start(): m.end()]
        found.append(
            {
                "phrase": snippet,
                "alternatives": list(alternatives),
                "note": note,
            }
        )
        if len(found) >= _MAX_ALT_HITS:
            break
    return found


def build_smart_feedback(transcript: str) -> Dict[str, List[Dict[str, Any]]]:
    """Convenience facade — bundles both detectors for the view layer."""
    return {
        "grammar_corrections": detect_grammar_corrections(transcript),
        "alternative_expressions": detect_alternative_expressions(transcript),
    }
