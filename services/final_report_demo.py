"""Synthetic 15-question results for final-report UI preview — no Gemini calls."""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

_DEMO_RESTORE_KEY = "_demo_mx_restore_snapshot"

_DEMO_STASH_KEYS = (
    "results",
    "exam_finished",
    "mock_page",
    "current_exam",
    "exam",
    "current_idx",
    "recordings",
    "audio_bytes",
    "mock_mode",
    "analytics_cache",
    "_analytics_sig",
    "_view_completed_report",
    "final_report_generated",
    "overall_estimated_level",
    "downloadable_report_bytes",
    "last_result",
    "preview_transcript",
    "analysis_status",
    "analysis_done",
)

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
    mx["_view_completed_report"] = True
    mx.setdefault("attempt_no", 1)
    mx["survey_completed"] = True
    # Minimal valid survey so "새 모의고사 시작하기" can regenerate a set in demo mode.
    mx.setdefault(
        "survey_results",
        {
            "work": "사업·회사원",
            "housing": "홀로 거주",
            "leisure": [
                "영화 보기",
                "공원 가기",
                "캠핑 하기",
                "게임 하기",
                "박물관 가기",
                "공연 보기",
                "콘서트 보기",
            ],
            "interests": ["음악 감상하기", "요리하기"],
            "sports": ["조깅", "걷기"],
            "travel": ["국내 여행"],
            "difficulty": 5,
        },
    )
    for k in (
        "final_report_generated",
        "overall_estimated_level",
        "analytics_cache",
        "downloadable_report_bytes",
        "_analytics_sig",
    ):
        mx.pop(k, None)


def _maybe_stash_mx_before_demo(mx: Dict[str, Any]) -> None:
    """Preserve in-progress or completed real attempt before opening sample report."""
    import streamlit as st

    from utils.exam_state import has_resumable_exam

    if mx.get("_final_report_demo"):
        return
    has_progress = has_resumable_exam(mx) or bool(mx.get("results"))
    if not has_progress:
        return
    st.session_state[_DEMO_RESTORE_KEY] = copy.deepcopy(
        {k: mx.get(k) for k in _DEMO_STASH_KEYS}
    )


def open_demo_final_report(mx: Dict[str, Any]) -> None:
    """Seed synthetic 15-question results and route to the full final report UI."""
    import streamlit as st

    _maybe_stash_mx_before_demo(mx)
    seed_demo_final_report(mx)
    st.session_state["_final_report_demo"] = True
    st.session_state["practice_portal_selected"] = True
    st.session_state["mock_mode"] = "real_mock"
    st.session_state["mock_page"] = "FINAL"
    mx["mock_mode"] = "real_mock"
    mx["mock_mode_label"] = "실전 모의고사"
    try:
        st.query_params.clear()
        st.query_params["nav"] = "MOCK"
        st.query_params["mock"] = "FINAL"
    except Exception:
        pass


def exit_demo_final_report(mx: Dict[str, Any]) -> None:
    """Leave sample report and restore a stashed real session when present."""
    import streamlit as st

    snap = st.session_state.pop(_DEMO_RESTORE_KEY, None)
    for key in ("_final_report_demo", "_demo_preview_loaded", "_view_completed_report"):
        mx.pop(key, None)
        st.session_state.pop(key, None)
    if isinstance(snap, dict):
        mx.update(snap)
    else:
        mx["results"] = []
        mx["exam_finished"] = False
        mx.pop("analytics_cache", None)
        mx.pop("_analytics_sig", None)
        mx.pop("downloadable_report_bytes", None)
    st.session_state["practice_portal_selected"] = False
    st.session_state["mock_page"] = "PICK"
    mx["mock_page"] = "PICK"
    try:
        st.query_params.clear()
        st.query_params["nav"] = "MOCK"
    except Exception:
        pass


def build_demo_sample_pdf_bytes() -> Optional[bytes]:
    """PDF bytes from demo results only — no Gemini."""
    from services.exam_analytics import compute_exam_aggregates, summary_rows_for_table
    from services.pdf_report import build_exam_pdf, pdf_export_available

    if not pdf_export_available():
        return None
    results = build_demo_results()
    try:
        agg = compute_exam_aggregates(results)
        return build_exam_pdf(
            agg,
            summary_rows_for_table(results),
            results,
            patient_label="OPIc Sample Report",
        )
    except Exception:
        return None
