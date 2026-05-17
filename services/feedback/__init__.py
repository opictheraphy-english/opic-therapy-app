"""Student-facing feedback post-processing (no scoring)."""

from .coach_copy import build_coach_summary, collect_transcript_strengths
from .feedback_builder import (
    build_improved_answer,
    build_student_feedback,
    expression_empty_message,
    grammar_empty_message,
    merge_expression_upgrades_for_display,
    merge_grammar_corrections_for_display,
    safe_get_existing_feedback,
    safe_get_metrics,
    safe_get_pronunciation_scores,
    safe_get_transcript,
)
from .missions import build_next_missions
from .structure_feedback import build_structure_feedback
from .transcript_rules import extract_expression_upgrades, extract_grammar_corrections

__all__ = [
    "build_coach_summary",
    "build_improved_answer",
    "build_next_missions",
    "build_student_feedback",
    "collect_transcript_strengths",
    "build_structure_feedback",
    "expression_empty_message",
    "extract_expression_upgrades",
    "extract_grammar_corrections",
    "grammar_empty_message",
    "merge_expression_upgrades_for_display",
    "merge_grammar_corrections_for_display",
    "safe_get_existing_feedback",
    "safe_get_metrics",
    "safe_get_pronunciation_scores",
    "safe_get_transcript",
]
