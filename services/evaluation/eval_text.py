"""Spoken-text metrics: segmentation, repetition, shallow-template signals."""

from __future__ import annotations

import re
from typing import Dict, List, Set

from .eval_config import (
    ADVANCED_MARKERS,
    FILLERS,
    MODIFIER_HINTS,
    MOVIE_SYNONYMS,
    SIMPLE_PATTERNS,
    SPOKEN_SEGMENT_MARKERS,
)

_WORD_RE = re.compile(r"\b[\w']+\b", re.I)
_MARKER_SPLIT_RE = re.compile(
    "(" + "|".join(SPOKEN_SEGMENT_MARKERS) + r")",
    re.IGNORECASE,
)
_MARKER_ONLY_RE = re.compile(
    "^(" + "|".join(SPOKEN_SEGMENT_MARKERS) + r")$",
    re.IGNORECASE,
)


def count_words(text: str) -> int:
    if not text:
        return 0
    return len(_WORD_RE.findall(text.lower()))


def segment_spoken_units(text: str) -> List[str]:
    """
    Spoken clause / idea units: punctuation splits first, then marker-based splits
    inside long fragments so STT without periods still yields plausible counts.
    """
    if not (text or "").strip():
        return []

    rough = [p.strip() for p in re.split(r"[.!?]+", text) if p.strip()]
    units: List[str] = []
    for chunk in rough:
        if len(chunk) < 120:
            units.append(chunk)
            continue
        sub = _MARKER_SPLIT_RE.split(chunk)
        for piece in sub:
            p = piece.strip()
            if not p or _MARKER_ONLY_RE.match(p):
                continue
            units.append(p)
    return units if units else [text.strip()]


def count_spoken_units(text: str) -> int:
    return len(segment_spoken_units(text))


def count_sentences_punctuation_only(text: str) -> int:
    if not text:
        return 0
    parts = [p.strip() for p in re.split(r"[.!?]+", text) if p.strip()]
    return len(parts)


def filler_hits(lower_text: str) -> int:
    return sum(1 for f in FILLERS if f in lower_text)


def filler_tier_adjustment(hits: int) -> float:
    """1–3 slight bonus, 4–6 neutral, 7+ penalty."""
    if 1 <= hits <= 3:
        return 4.0
    if 4 <= hits <= 6:
        return 0.0
    if hits >= 7:
        return -min(22.0, float(hits - 6) * 3.5)
    return 0.0


def lexical_modifier_metrics(lower: str) -> Dict[str, float]:
    modifier_hits = sum(1 for m in MODIFIER_HINTS if m in lower.split())
    movie_repeats = lower.split().count("movie")
    has_synonym = any(s in lower for s in MOVIE_SYNONYMS)
    simple_hits = sum(1 for p in SIMPLE_PATTERNS if p in lower)
    return {
        "modifier_hits": float(modifier_hits),
        "movie_repeats": float(movie_repeats),
        "has_movie_synonym": 1.0 if has_synonym else 0.0,
        "simple_pattern_hits": float(simple_hits),
    }


def connector_variation_score(lower: str) -> float:
    hits = sum(1 for m in ADVANCED_MARKERS if m in lower)
    oral = sum(
        1
        for k in (
            "because",
            "so ",
            "but ",
            "although",
            "even though",
            "while ",
            "since ",
            "therefore",
            "meanwhile",
        )
        if k in lower
    )
    return float(min(100, hits * 12 + oral * 6))


def repetition_ratio_percent(lower: str, words: List[str]) -> float:
    """0–100 scale: higher = more repeated lemmas (content words only, rough)."""
    if len(words) < 8:
        return 0.0
    content = [w for w in words if len(w) > 3 and w not in {"that", "this", "with", "from", "have", "been"}]
    if len(content) < 6:
        return 0.0
    freq: Dict[str, int] = {}
    for w in content:
        freq[w] = freq.get(w, 0) + 1
    unique = len(freq)
    ratio = 1.0 - (unique / max(1, len(content)))
    return round(min(100.0, ratio * 130.0), 1)


def abandoned_fragments(lower: str) -> float:
    """Heuristic: orphan starters without closure."""
    starters = ("but ", "and ", "because ", "so ", "when ")
    hits = sum(lower.count(s) for s in starters)
    words_n = len(lower.split())
    if words_n == 0:
        return 0.0
    return round(min(100.0, (hits / max(8.0, words_n)) * 140.0), 1)


def extract_keywords(text: str, limit: int = 40) -> Set[str]:
    words = _WORD_RE.findall((text or "").lower())
    stop = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "to",
        "of",
        "in",
        "on",
        "for",
        "with",
        "and",
        "or",
        "but",
        "so",
        "it",
        "i",
        "my",
        "me",
        "we",
        "they",
        "that",
        "this",
    }
    out: Set[str] = set()
    for w in words:
        if len(w) > 2 and w not in stop:
            out.add(w)
        if len(out) >= limit:
            break
    return out
