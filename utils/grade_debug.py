"""Developer grade diagnostics — never shown in Streamlit UI."""

from __future__ import annotations

import json
from typing import Any, Dict

from utils.safe_debug_log import safe_debug_log


def grade_debug(msg: str) -> None:
    safe_debug_log("GRADE_DEBUG", msg)


def _preview_text(text: Any, limit: int = 120) -> str:
    s = str(text or "").replace("\n", " ").strip()
    if len(s) > limit:
        return s[:limit] + "…"
    return s


def log_saved_result(q_label: str, result: Dict[str, Any]) -> None:
    if not isinstance(result, dict):
        grade_debug(f"q={q_label} saved_result=invalid")
        return
    tx = str(result.get("transcript") or "")
    sem = result.get("semantic_dimensions") if isinstance(result.get("semantic_dimensions"), dict) else {}
    rub = result.get("rubric_scores") if isinstance(result.get("rubric_scores"), dict) else {}
    pri = result.get("priority_scores") if isinstance(result.get("priority_scores"), dict) else {}
    flags = result.get("grading_rule_flags") if isinstance(result.get("grading_rule_flags"), dict) else {}
    grade_debug(
        f"q={q_label} saved_result "
        f"diagnosis_status={result.get('diagnosis_status')!r} "
        f"analysis_status={result.get('analysis_status')!r} "
        f"transcript_len={len(tx)} "
        f"transcript_preview={_preview_text(tx)!r} "
        f"estimated_level={result.get('estimated_level')!r} "
        f"estimated_level_display={result.get('estimated_level_display')!r} "
        f"final_grade_score={result.get('final_grade_score')!r} "
        f"metrics={json.dumps(result.get('metrics') or {}, ensure_ascii=False)[:200]} "
        f"semantic_dimensions_keys={list(sem.keys())} "
        f"rubric_scores={rub} "
        f"priority_scores={pri} "
        f"grading_rule_flags={flags} "
        f"no_speech_detected={result.get('no_speech_detected')!r} "
        f"language_status={result.get('language_mismatch_kind') or result.get('analysis_status')!r}"
    )


def log_parsed_model_response(q_label: str, parsed: Dict[str, Any], *, parse_error: bool = False) -> None:
    if not isinstance(parsed, dict):
        grade_debug(f"q={q_label} parsed_model_response=not_a_dict")
        return
    grade_debug(
        f"q={q_label} parsed_model_response "
        f"has_transcript={bool(str(parsed.get('transcription') or parsed.get('transcript') or '').strip())} "
        f"has_semantic={bool(parsed.get('semantic_dimensions') or parsed.get('fluency_score'))} "
        f"has_estimated_level={bool(parsed.get('estimated_level'))} "
        f"has_final_grade_score={parsed.get('final_grade_score') is not None} "
        f"has_metrics={bool(parsed.get('metrics'))} "
        f"has_error={bool(parsed.get('error'))} "
        f"fallback_used={bool(parsed.get('raw_parse_fragment'))} "
        f"parse_error={parse_error}"
    )
