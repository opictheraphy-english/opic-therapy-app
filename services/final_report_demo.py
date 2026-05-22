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

_MOCK_V2_STASH_KEYS = (
    "mock_v2_step",
    "mock_v2_survey_results",
    "mock_v2_questions",
    "mock_v2_index",
    "mock_v2_answers",
    "mock_v2_audio_blobs",
    "mock_v2_report",
    "mock_v2_started_at",
    "mock_v2_finished_at",
    "mock_v2_new_final_bundle",
    "mock_v2_new_final_sig",
    "mock_v2_new_final_pdf_bytes",
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


def build_demo_mock_v2_report() -> Dict[str, Any]:
    """Gemini-shaped report dict for new_final_report (no API calls)."""
    rows = build_demo_results()
    q_feedback: List[Dict[str, Any]] = []
    for row in rows:
        qid = int(row.get("q_id") or 0)
        res = row.get("result") or {}
        q_feedback.append(
            {
                "question_index": qid - 1,
                "question_number": qid,
                "opic_type": str(row.get("type") or ""),
                "status": "saved",
                "feedback": str(res.get("semantic_feedback") or "").strip(),
                "better_direction": str(res.get("prescription") or "").strip(),
            }
        )
    return {
        "ok": True,
        "overall_level": "IH",
        "summary": (
            "데모 리포트입니다. 15문항 전반에서 주제에 맞는 답을 이어가며, "
            "구체적 예시와 연결어를 보강하면 IH~AL 구간 신호가 더 또렷해집니다."
        ),
        "score_breakdown": {
            "response_amount": 74,
            "relevance": 76,
            "structure": 73,
            "grammar": 71,
            "vocabulary": 75,
            "naturalness": 77,
        },
        "question_feedback": q_feedback,
        "strengths": [
            "주제별로 답을 끊기지 않고 이어가는 흐름이 안정적입니다.",
            "경험·묘사 문항에서 구체적 장면을 붙이려는 시도가 보입니다.",
        ],
        "weaknesses": [
            "비교·이슈 문항에서 찬반/대조 구조를 더 분명히 할 필요가 있습니다.",
            "답변 마무리에서 한 줄 요약(Overall, I'd say…)을 넣으면 전달력이 좋아집니다.",
        ],
        "practice_mission": (
            "다음 연습에서는 Q14 비교 문항에서 'On one hand / On the other hand' "
            "구조로 30초 안에 두 관점을 대비해 보세요."
        ),
        "error_category": "",
        "error_message": "",
    }


def build_demo_mock_v2_answers() -> List[Dict[str, Any]]:
    answers: List[Dict[str, Any]] = []
    for row in build_demo_results():
        qid = int(row.get("q_id") or 0)
        res = row.get("result") or {}
        tx = str(res.get("transcript") or "").strip()
        answers.append(
            {
                "answer_id": f"demo_a{qid}",
                "question_index": qid - 1,
                "question_number": qid,
                "question_id": f"demo_q{qid}",
                "opic_type": str(row.get("type") or ""),
                "combo": "",
                "topic": str(row.get("topic") or ""),
                "question_text": str(row.get("question") or ""),
                "student_answer": tx,
                "transcript": tx,
                "word_count": int((res.get("metrics") or {}).get("word_count") or 120),
                "duration_seconds": 45.0,
                "wpm": float(res.get("wpm") or 110.0),
                "stt_status": "transcript_ready",
                "status": "saved",
                "audio_saved": True,
            }
        )
    return answers


def build_demo_mock_v2_questions() -> List[Dict[str, Any]]:
    return [
        {
            "id": f"demo_q{row['q_id']}",
            "question_index": int(row["q_id"]) - 1,
            "question_number": int(row["q_id"]),
            "question_text": row["question"],
            "topic": row["topic"],
            "opic_type": row["type"],
            "combo": "",
        }
        for row in build_demo_results()
    ]


def seed_demo_mock_v2_session() -> None:
    """Seed Mock V2 session keys and open the new final report screen (demo only)."""
    import streamlit as st

    from views.mock_v2 import clear_mock_v2_session

    clear_mock_v2_session()
    st.session_state["_final_report_demo"] = True
    st.session_state["mock_v2_step"] = "report"
    st.session_state["mock_v2_report"] = build_demo_mock_v2_report()
    st.session_state["mock_v2_answers"] = build_demo_mock_v2_answers()
    st.session_state["mock_v2_questions"] = build_demo_mock_v2_questions()
    st.session_state["mock_v2_index"] = 0
    st.session_state["mock_v2_finished_at"] = "demo"
    st.session_state["mock_v2_started_at"] = "demo"


def _maybe_stash_before_demo(mx: Dict[str, Any]) -> None:
    """Preserve in-progress Mock V2 or legacy mock session before opening sample report."""
    import streamlit as st

    from utils.exam_state import has_resumable_exam

    if mx.get("_final_report_demo") or st.session_state.get("_final_report_demo"):
        return
    has_mx = has_resumable_exam(mx) or bool(mx.get("results"))
    has_v2 = str(st.session_state.get("mock_v2_step") or "") not in ("", "survey")
    if not has_mx and not has_v2:
        return
    st.session_state[_DEMO_RESTORE_KEY] = {
        "mx": copy.deepcopy({k: mx.get(k) for k in _DEMO_STASH_KEYS}),
        "mock_v2": copy.deepcopy(
            {k: st.session_state.get(k) for k in _MOCK_V2_STASH_KEYS}
        ),
        "mock_mode": st.session_state.get("mock_mode"),
        "practice_portal_selected": st.session_state.get("practice_portal_selected"),
    }


def open_demo_final_report(mx: Dict[str, Any]) -> None:
    """Seed demo Mock V2 data and route to new_final_report (no Gemini, no legacy UI)."""
    import streamlit as st

    _maybe_stash_before_demo(mx)
    seed_demo_mock_v2_session()
    st.session_state["practice_portal_selected"] = True
    st.session_state["mock_mode"] = "mock_v2"
    mx["mock_mode"] = "mock_v2"
    mx.pop("_view_completed_report", None)
    st.session_state.pop("_view_completed_report", None)
    try:
        st.query_params.clear()
        st.query_params["nav"] = "MOCK"
    except Exception:
        pass


def exit_demo_final_report(mx: Dict[str, Any]) -> None:
    """Leave sample report and restore a stashed session when present."""
    import streamlit as st

    from views.mock_v2 import clear_mock_v2_session

    snap = st.session_state.pop(_DEMO_RESTORE_KEY, None)
    clear_mock_v2_session()
    for key in ("_final_report_demo", "_demo_preview_loaded", "_view_completed_report"):
        mx.pop(key, None)
        st.session_state.pop(key, None)
    if isinstance(snap, dict):
        mx_part = snap.get("mx")
        if isinstance(mx_part, dict):
            mx.update(mx_part)
        v2_part = snap.get("mock_v2")
        if isinstance(v2_part, dict):
            for k, v in v2_part.items():
                if v is not None:
                    st.session_state[k] = v
        if snap.get("mock_mode") is not None:
            st.session_state["mock_mode"] = snap["mock_mode"]
            mx["mock_mode"] = snap["mock_mode"]
        if snap.get("practice_portal_selected") is not None:
            st.session_state["practice_portal_selected"] = snap["practice_portal_selected"]
    else:
        mx["results"] = []
        mx["exam_finished"] = False
        mx.pop("analytics_cache", None)
        mx.pop("_analytics_sig", None)
        mx.pop("downloadable_report_bytes", None)
        st.session_state.pop("mock_mode", None)
        st.session_state["practice_portal_selected"] = False
        mx["mock_page"] = "PICK"
    if not st.session_state.get("mock_mode"):
        st.session_state["mock_page"] = "PICK"
        mx.setdefault("mock_page", "PICK")
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
