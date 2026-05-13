"""Report helpers — cache snapshots to avoid rerun recomputation in UI."""

from __future__ import annotations

from typing import Any, Dict


def cache_analysis_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Attach stable analysis_cache for REPORT expanders."""
    if not result:
        return result
    out = dict(result)
    out["analysis_cache"] = {
        "estimated_level": result.get("estimated_level"),
        "estimated_level_display": result.get("estimated_level_display"),
        "final_grade_score": result.get("final_grade_score"),
        "semantic_dimensions": result.get("semantic_dimensions"),
        "rubric_scores": result.get("rubric_scores"),
        "fact_scores": result.get("fact_scores"),
    }
    return out
