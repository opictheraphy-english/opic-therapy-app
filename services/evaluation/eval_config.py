"""OPIc-style hybrid evaluation — constants and thresholds (single source)."""

from __future__ import annotations

import os
from typing import Dict, FrozenSet, List, Tuple

# Gemini models — STT vs report (optional legacy GEMINI_MODEL applies to both if set).
_DEFAULT_STT_MODEL = "gemini-3.5-flash"
_DEFAULT_REPORT_MODEL = "gemini-2.5-flash"
_LEGACY_GEMINI_MODEL = (os.getenv("GEMINI_MODEL") or "").strip()

STT_MODEL_NAME = (os.getenv("GEMINI_STT_MODEL") or _LEGACY_GEMINI_MODEL or "").strip() or _DEFAULT_STT_MODEL
REPORT_MODEL_NAME = (
    (os.getenv("GEMINI_REPORT_MODEL") or _LEGACY_GEMINI_MODEL or "").strip()
    or _DEFAULT_REPORT_MODEL
)

# Backward compatibility for existing imports.
MODEL_NAME = REPORT_MODEL_NAME
_DEFAULT_MODEL = _DEFAULT_REPORT_MODEL


def _dedupe_models(candidates: List[str]) -> List[str]:
    out: List[str] = []
    for raw in candidates:
        name = (raw or "").strip()
        if not name:
            continue
        for prefix in ("models/", "publishers/google/models/"):
            if name.startswith(prefix):
                name = name[len(prefix) :]
        if name and name not in out:
            out.append(name)
    return out


def build_stt_model_candidates() -> List[str]:
    """STT model fallback chain — stable audio-capable models; 2.5 Flash-Lite removed (stopped responding to audio STT)."""
    return _dedupe_models(
        [
            STT_MODEL_NAME,
            "gemini-3.5-flash",
            "gemini-2.5-flash",
        ]
    )


def build_report_model_candidates() -> List[str]:
    """Legacy mock exam report stack."""
    return _dedupe_models(
        [
            REPORT_MODEL_NAME,
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-1.5-flash",
        ]
    )


# Mini Mock V2 report — fast diagnosis (Flash-Lite default).
# Resolution: GEMINI_MINI_REPORT_MODEL → GEMINI_REPORT_MODEL → GEMINI_MODEL → default.
_DEFAULT_MINI_REPORT_MODEL = "gemini-2.5-flash-lite"
MINI_REPORT_MODEL_NAME = (
    (os.getenv("GEMINI_MINI_REPORT_MODEL") or "").strip()
    or (os.getenv("GEMINI_REPORT_MODEL") or _LEGACY_GEMINI_MODEL or "").strip()
    or _DEFAULT_MINI_REPORT_MODEL
)
MINI_V2_REPORT_MODEL_NAME = MINI_REPORT_MODEL_NAME  # backward-compatible alias

# Future Real Mock V2 report — precision exam (not wired to flows yet).
# Resolution: GEMINI_REAL_REPORT_MODEL → GEMINI_REPORT_MODEL → GEMINI_MODEL → default.
_DEFAULT_REAL_REPORT_MODEL = "gemini-2.5-flash"
REAL_REPORT_MODEL_NAME = (
    (os.getenv("GEMINI_REAL_REPORT_MODEL") or "").strip()
    or (os.getenv("GEMINI_REPORT_MODEL") or _LEGACY_GEMINI_MODEL or "").strip()
    or _DEFAULT_REAL_REPORT_MODEL
)


def build_mini_mock_v2_report_model_candidates() -> List[str]:
    """Mini Mock V2 final report only — no Pro models, no discontinued 2.0 Flash."""
    return _dedupe_models(
        [
            MINI_REPORT_MODEL_NAME,
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
        ]
    )


# Topic Practice V2 — short feedback (text-only), 2.5 Flash family only.
_DEFAULT_TOPIC_FEEDBACK_MODEL = "gemini-2.5-flash-lite"
TOPIC_FEEDBACK_MODEL_NAME = (
    (os.getenv("GEMINI_TOPIC_FEEDBACK_MODEL") or "").strip()
    or _DEFAULT_TOPIC_FEEDBACK_MODEL
)


def build_topic_feedback_model_candidates() -> List[str]:
    """Topic Practice V2 AI feedback — env override, then 2.5 Flash-Lite / Flash only."""
    return _dedupe_models(
        [
            TOPIC_FEEDBACK_MODEL_NAME,
            "gemini-2.5-flash-lite",
            "gemini-2.5-flash",
        ]
    )


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
