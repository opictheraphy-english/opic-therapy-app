"""OPIc-style hybrid evaluation — constants and thresholds (single source)."""

from __future__ import annotations

import os
from typing import Dict, FrozenSet, List, Tuple

# Multimodal semantic call (mock exam feedback). Optional override: GEMINI_MODEL.
_DEFAULT_MODEL = "gemini-2.5-flash"
MODEL_NAME = (os.getenv("GEMINI_MODEL") or "").strip() or _DEFAULT_MODEL

# --- Levels (ordinal scale for calibration; NH band subdivided via novice_band) ---
LEVEL_ORDER: List[str] = ["NH", "IL", "IM1", "IM2", "IM3", "IH", "AL"]
LEVEL_COMPRESS: Dict[str, str] = {"IM1": "IM", "IM2": "IM", "IM3": "IM"}

# Quantity gates: duration + spoken units + words — WPM is diagnostic only (not a gate driver).
GRADING_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "IL": {"min_seconds": 35.0, "min_units": 4.0, "min_words": 45.0},
    "IM1": {"min_seconds": 48.0, "min_units": 6.0, "min_words": 65.0},
    "IM2": {"min_seconds": 58.0, "min_units": 9.0, "min_words": 92.0},
    "IM3": {"min_seconds": 72.0, "min_units": 11.0, "min_words": 118.0},
    "IH": {"min_seconds": 92.0, "min_units": 13.0, "min_words": 155.0},
    "AL": {"min_seconds": 98.0, "min_units": 15.0, "min_words": 215.0},
}

# Composite score → provisional quality tier (before quantity merge & caps)
QUALITY_SCORE_BANDS: List[Tuple[float, str]] = [
    (82.0, "AL"),
    (73.0, "IH"),
    (65.0, "IM3"),
    (56.0, "IM2"),
    (47.0, "IM1"),
    (38.0, "IL"),
    (0.0, "NH"),
]

# Discourse markers for segmentation & connector-variation heuristic
SPOKEN_SEGMENT_MARKERS: Tuple[str, ...] = (
    r"\band then\b",
    r"\bafter that\b",
    r"\bso\b",
    r"\bbecause\b",
    r"\bbut\b",
    r"\bmeanwhile\b",
    r"\banyway\b",
    r"\bsuddenly\b",
    r"\bthen\b",
    r"\blater\b",
    r"\beventually\b",
)

ADVANCED_MARKERS: FrozenSet[str] = frozenset(
    {
        "initially",
        "specifically",
        "eventually",
        "furthermore",
        "on the other hand",
        "consequently",
        "first of all",
        "to begin with",
        "as it turned out",
        "in the end",
        "looking back",
        "nevertheless",
        "whereas",
        "in contrast",
    }
)

FILLERS: FrozenSet[str] = frozenset(
    {"well", "you know", "i mean", "actually", "to be honest", "like", "kind of", "sort of"}
)

BASIC_WORDS: FrozenSet[str] = frozenset({"very", "good", "happy", "nice", "really", "just"})

SIMPLE_PATTERNS: FrozenSet[str] = frozenset({"i like", "it was", "there is", "i think"})

MOVIE_SYNONYMS: FrozenSet[str] = frozenset({"film", "cinema", "feature", "clip", "flick"})

IDIOM_SMALL_BONUS_PHRASES: FrozenSet[str] = frozenset(
    {
        "butterflies in my stomach",
        "piece of cake",
        "once in a blue moon",
        "hit the nail on the head",
        "under the weather",
    }
)

# Fake fluency: high velocity without substance
FAKE_FLUENCY_WPM_MIN = 148
FAKE_FLUENCY_SEMANTIC_MAX = 46
FAKE_FLUENCY_DISCOURSE_MAX = 46
FAKE_FLUENCY_CAP_LEVEL = "IH"

# IM3 requires ≥2 of these semantic gates (when quantity suggests IM3+)
IM3_GATE_SEMANTIC_THRESHOLDS = {
    "narrative_depth": 54.0,
    "discourse_continuity": 54.0,
    "elaboration_quality": 54.0,
}

# Modifier / synonym diversity — weak noun-repeat penalty
MODIFIER_HINTS: FrozenSet[str] = frozenset(
    {"quite", "rather", "pretty", "fairly", "especially", "particularly", "actually", "honestly"}
)

API_TIMEOUT_SECONDS = 18
