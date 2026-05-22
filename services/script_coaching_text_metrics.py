"""Script Coaching — deterministic text metrics (no API calls).

# Used by the Script Coaching DIAGNOSE engine.
# Word count and connector count are computed HERE in code (deterministic,
# reproducible) — never delegated to the LLM. Only judgement axes
# (vocabulary, grammar, context, structure) go to Gemini.
#
# Connector markers reuse MINI_MOCK_V2_CONNECTOR_MARKERS from the shared
# level-rules file and extend it with a few sequencing connectors that are
# common in written OPIc scripts.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from services.mini_mock_v2_level_rules import MINI_MOCK_V2_CONNECTOR_MARKERS

# Extra connectors common in written scripts but absent from the mini-mock list.
# Kept separate so the shared mini-mock metric is not affected.
_SCRIPT_EXTRA_CONNECTORS: Tuple[str, ...] = (
    "then ",
    "first ",
    "finally",
    "in addition",
    "for instance",
    "as a result",
    "on the other hand",
    "such as",
    "although",
    "since ",
    "therefore",
)

# Full marker set for script coaching: shared markers + script extras, deduped.
SCRIPT_CONNECTOR_MARKERS: Tuple[str, ...] = tuple(
    dict.fromkeys(
        tuple(m.lower() for m in MINI_MOCK_V2_CONNECTOR_MARKERS)
        + _SCRIPT_EXTRA_CONNECTORS
    )
)

# Vague filler words flagged for the vocabulary axis (counted, not scored, here).
_VAGUE_WORDS: Tuple[str, ...] = (
    "good", "nice", "many", "very", "thing", "things",
    "stuff", "really", "a lot",
)


def count_words(text: str) -> int:
    """Plain word count for written scripts.

    Independent of stt_service.count_english_words so script coaching does not
    depend on STT plumbing. Counts whitespace-separated tokens with a letter.
    """
    if not text:
        return 0
    tokens = re.findall(r"[A-Za-z][A-Za-z'\-]*", text)
    return len(tokens)


def count_sentences(text: str) -> int:
    """Rough sentence count by terminal punctuation; minimum 1 if any text."""
    if not text or not text.strip():
        return 0
    parts = [p for p in re.split(r"[.!?]+", text) if p.strip()]
    return max(1, len(parts))


def count_connectors(text: str) -> Dict[str, Any]:
    """Count connector marker hits in the script (case-insensitive, substring).

    Returns total hits plus the distinct markers found, so the rubric can tell
    'used because 5 times' apart from 'used 5 different connectors'.
    """
    if not text:
        return {"total_hits": 0, "distinct_count": 0, "found": []}
    low = " " + text.lower() + " "
    found: List[str] = []
    total = 0
    for marker in SCRIPT_CONNECTOR_MARKERS:
        n = low.count(marker)
        if n > 0:
            found.append(marker.strip())
            total += n
    return {
        "total_hits": total,
        "distinct_count": len(found),
        "found": found,
    }


def count_vague_words(text: str) -> Dict[str, Any]:
    """Count vague/filler words — supporting signal for the vocabulary axis."""
    if not text:
        return {"total_hits": 0, "found": []}
    low = " " + text.lower() + " "
    found: List[str] = []
    total = 0
    for w in _VAGUE_WORDS:
        n = low.count(" " + w + " ")
        if n > 0:
            found.append(w)
            total += n
    return {"total_hits": total, "found": found}


# Word-count anchors for a SINGLE written script answer (not a 3-question total).
# Written scripts have no speaking duration, so level quantity is judged on raw
# word count + sentence development, NOT on 90s speech-rate bands.
SCRIPT_WORD_ANCHORS: Tuple[Tuple[int, str, int], ...] = (
    # (min_words, level_label, response_amount_score at this floor)
    (0, "NH", 10),
    (20, "IL", 35),
    (45, "IM1", 50),
    (70, "IM2", 65),
    (100, "IM3", 78),
    (130, "IH", 88),
    (180, "AL", 96),
)


def response_amount_score_from_word_count(word_count: int) -> int:
    """0-100 quantity score from raw word count (linear between anchors)."""
    wc = max(0, int(word_count or 0))
    anchors = SCRIPT_WORD_ANCHORS
    if wc <= anchors[0][0]:
        return anchors[0][2]
    for i in range(1, len(anchors)):
        w0, _, s0 = anchors[i - 1]
        w1, _, s1 = anchors[i]
        if wc <= w1:
            if w1 <= w0:
                return s1
            t = (wc - w0) / (w1 - w0)
            return int(max(0, min(100, round(s0 + t * (s1 - s0)))))
    return 100


def word_count_level_hint(word_count: int) -> str:
    """The level whose word-count floor the script reaches (quantity only).

    This is a HINT for the rubric, not a final level — quality (structure,
    relevance, grammar) can lower it. Quantity never raises the final level
    on its own.
    """
    wc = max(0, int(word_count or 0))
    hint = "NH"
    for min_w, label, _ in SCRIPT_WORD_ANCHORS:
        if wc >= min_w:
            hint = label
    return hint


def build_script_text_metrics(text: str) -> Dict[str, Any]:
    """All deterministic metrics for one written script, for rubric injection."""
    wc = count_words(text)
    sentences = count_sentences(text)
    connectors = count_connectors(text)
    vague = count_vague_words(text)
    return {
        "word_count": wc,
        "sentence_count": sentences,
        "connector_total_hits": connectors["total_hits"],
        "connector_distinct_count": connectors["distinct_count"],
        "connectors_found": connectors["found"],
        "vague_word_hits": vague["total_hits"],
        "vague_words_found": vague["found"],
        "response_amount_score_rule": response_amount_score_from_word_count(wc),
        "word_count_level_hint": word_count_level_hint(wc),
    }
