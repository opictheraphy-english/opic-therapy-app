"""Rule-based corrections: fake fluency, IM3 gate, novice bands, shallow templates."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from .eval_config import (
    FAKE_FLUENCY_CAP_LEVEL,
    FAKE_FLUENCY_DISCOURSE_MAX,
    FAKE_FLUENCY_SEMANTIC_MAX,
    FAKE_FLUENCY_WPM_MIN,
    IM3_GATE_SEMANTIC_THRESHOLDS,
    LEVEL_ORDER,
)


def _idx(level: str) -> int:
    return LEVEL_ORDER.index(level) if level in LEVEL_ORDER else 0


def merge_quantity_quality_soft(quantity_level: str, score_level: str) -> str:
    """
    Quality may lower output by at most one step below quantity when quality collapses.
    If score is more than one tier below quantity, snap to quantity-1.
    """
    qi = _idx(quantity_level)
    si = _idx(score_level)
    if qi <= 0:
        return score_level
    if si < qi - 1:
        return LEVEL_ORDER[qi - 1]
    return score_level


def apply_fake_fluency_cap(
    level: str,
    wpm: float,
    semantic_density: float,
    discourse_continuity: float,
) -> Tuple[str, bool]:
    """High WPM + low substance → cap at IH (not AL)."""
    if (
        wpm >= FAKE_FLUENCY_WPM_MIN
        and semantic_density <= FAKE_FLUENCY_SEMANTIC_MAX
        and discourse_continuity <= FAKE_FLUENCY_DISCOURSE_MAX
    ):
        cap_i = _idx(FAKE_FLUENCY_CAP_LEVEL)
        if _idx(level) > cap_i:
            return FAKE_FLUENCY_CAP_LEVEL, True
    return level, False


def im3_quality_gate(
    level: str,
    semantic: Dict[str, Any],
    connector_score: float,
) -> Tuple[str, bool]:
    """
    IM3+ requires ≥2 of: narrative depth, discourse continuity, elaboration (semantic),
    or spoken connector variation (transcript heuristic).
    """
    if _idx(level) < _idx("IM3"):
        return level, False

    nd = float(semantic.get("narrative_depth") or 0)
    dc = float(semantic.get("discourse_continuity") or 0)
    elab = float(semantic.get("elaboration_quality") or 0)

    signals = [
        nd >= IM3_GATE_SEMANTIC_THRESHOLDS["narrative_depth"],
        dc >= IM3_GATE_SEMANTIC_THRESHOLDS["discourse_continuity"],
        elab >= IM3_GATE_SEMANTIC_THRESHOLDS["elaboration_quality"],
        connector_score >= 42.0,
    ]
    if sum(1 for s in signals if s) >= 2:
        return level, False
    if level == "IM3":
        return "IM2", True
    if _idx(level) > _idx("IM3"):
        return "IM3", True
    return level, False


def novice_sub_band(
    words: int,
    spoken_units: int,
    semantic_density: float,
    abandoned_ratio: float,
    grammar_score: float,
) -> Optional[str]:
    """NL / NM / NH — optional fine band below IL."""
    if words >= 38 and spoken_units >= 4:
        return None
    if words < 12 or semantic_density < 18:
        return "NL"
    if words < 28 or abandoned_ratio > 62 or grammar_score < 28:
        return "NM"
    return "NH"


def shallow_template_penalty(
    simple_pattern_hits: float,
    movie_repeats: float,
    has_movie_synonym: float,
) -> float:
    """Reduced noun-loop penalty vs legacy; still penalize empty templates."""
    pen = 0.0
    if simple_pattern_hits >= 3:
        pen += 10.0
    elif simple_pattern_hits >= 2:
        pen += 6.0
    if movie_repeats >= 4 and has_movie_synonym < 0.5:
        pen += 9.0
    elif movie_repeats >= 3 and has_movie_synonym < 0.5:
        pen += 5.0
    return pen
