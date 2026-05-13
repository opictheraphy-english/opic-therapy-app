"""Synthetic 15-question results for final-report UI preview — no Gemini calls."""

from __future__ import annotations

from typing import Any, Dict, List

_TOPICS = (
    ("Movies", "Past Experience"),
    ("Travel", "Description"),
    ("Work", "Comparison"),
    ("Leisure", "Hypothetical"),
    ("Sports", "Past Experience"),
    ("Food", "Description"),
    ("Music", "Opinion"),
    ("Reading", "Summary"),
    ("Technology", "Issue"),
    ("Family", "Past Experience"),
    ("Education", "Comparison"),
    ("Health", "Hypothetical"),
    ("Environment", "Issue"),
    ("Culture", "Role-play"),
    ("Current Events", "Issue"),
)


def _one_item(qid: int) -> Dict[str, Any]:
    topic, qtype = _TOPICS[qid - 1]
    base_score = 58 + (qid % 5) * 4
    sem = {
        "semantic_density": float(min(88, base_score + 6)),
        "discourse_continuity": float(min(90, base_score + 4)),
        "narrative_depth": float(min(85, base_score + 2)),
        "elaboration_quality": float(min(86, base_score + 3)),
        "spontaneity_score": float(min(84, base_score)),
        "naturalness": float(min(87, base_score + 5)),
        "tense_stability": float(min(82, base_score - 2)),
        "repetition_ratio": 38.0 if qid != 11 else 74.0,
    }
    fh = 2 + (qid % 4)
    if qid == 5:
        fh = 8
    wpm = 108.0 + qid * 2.5
    rs = {
        "fluency": min(95, base_score + 8),
        "lexical": min(92, base_score + 5),
        "logic": min(93, base_score + 6),
        "grammar": min(91, base_score + 4),
    }
    transcript = (
        f"[Demo transcript Q{qid}] I would say that {topic.lower()} has shaped how I express myself in English. "
        f"I try to give concrete examples and keep the flow natural when I speak about {topic.lower()}."
    )
    result: Dict[str, Any] = {
        "diagnosis_status": "ok",
        "transcript": transcript,
        "semantic_feedback": (
            "Ava (demo): Narration is coherent; discourse markers appear at helpful junctions. "
            "Elaboration could deepen on the ‘why’ layer for stronger IH signals."
        ),
        "summary_speech_rehab": "Demo summary: maintain rhythm; avoid stacking fillers before key claims.",
        "prescription": (
            f"Eric No (demo Q{qid}): Anchor each paragraph with one clear claim, then add one concrete detail. "
            "Swap repeated hedges for precise stance language."
        ),
        "estimated_level": "IH",
        "estimated_level_display": "IH",
        "final_grade_score": float(min(92, base_score + 10)),
        "rubric_scores": rs,
        "semantic_dimensions": sem,
        "metrics": {
            "wpm": wpm,
            "sentence_count": float(6 + (qid % 4)),
            "filler_hits": float(fh),
            "word_count": 120.0,
        },
        "wpm": wpm,
        "grading_rule_flags": {},
    }
    if qid == 14:
        result["grading_rule_flags"] = {"im3_gate_trim": True}
    return {
        "q_id": qid,
        "question": f"(Demo) Tell me about {topic} in the context of an OPIc-style {qtype.lower()} prompt.",
        "type": qtype,
        "topic": topic,
        "result": result,
    }


def build_demo_results() -> List[Dict[str, Any]]:
    return [_one_item(i) for i in range(1, 16)]


def seed_demo_final_report(mx: Dict[str, Any]) -> None:
    """Replace mock session with demo data and jump to FINAL report (preview only)."""
    mx["results"] = build_demo_results()
    mx["exam_finished"] = True
    mx["mock_page"] = "FINAL"
    mx["_show_exam_celebration"] = False
    mx["_final_report_demo"] = True
    for k in (
        "final_report_generated",
        "overall_estimated_level",
        "analytics_cache",
        "downloadable_report_bytes",
        "_analytics_sig",
    ):
        mx.pop(k, None)
