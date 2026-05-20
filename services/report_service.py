"""Report helpers — cache snapshots to avoid rerun recomputation in UI."""

from __future__ import annotations

from typing import Any, Dict


def normalize_result_score_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    """Mirror priority_scores ↔ rubric_scores so final report tables stay consistent."""
    if not isinstance(result, dict):
        return result
    ps = result.get("priority_scores")
    rs = result.get("rubric_scores")
    if isinstance(ps, dict) and ps:
        if not isinstance(rs, dict) or not rs:
            result["rubric_scores"] = dict(ps)
    elif isinstance(rs, dict) and rs:
        if not isinstance(ps, dict) or not ps:
            result["priority_scores"] = dict(rs)
    return result


def cache_analysis_payload(result: Dict[str, Any]) -> Dict[str, Any]:
    """Attach stable analysis_cache for REPORT expanders."""
    if not result:
        return result
    out = normalize_result_score_fields(dict(result))
    out["analysis_cache"] = {
        "estimated_level": out.get("estimated_level"),
        "estimated_level_display": out.get("estimated_level_display"),
        "final_grade_score": out.get("final_grade_score"),
        "semantic_dimensions": out.get("semantic_dimensions"),
        "rubric_scores": out.get("rubric_scores"),
        "fact_scores": out.get("fact_scores"),
    }
    return out
