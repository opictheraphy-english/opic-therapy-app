"""Session state for Topic Practice — separate from full mock exam ``mx[\"results\"]``."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from utils.exam_state import build_analysis_pending_result, classify_analysis_error

_RESULTS_KEY = "topic_practice_results"
_RECORDINGS_KEY = "topic_practice_recordings"


def _ss():
    import streamlit as st

    return st.session_state


def topic_audio_key(topic_id: str, question_id: str) -> str:
    return f"tp_{topic_id}_{question_id}"


def get_topic_results() -> List[Dict[str, Any]]:
    ss = _ss()
    rows = ss.get(_RESULTS_KEY)
    if not isinstance(rows, list):
        rows = []
        ss[_RESULTS_KEY] = rows
    return rows


def get_topic_recordings() -> Dict[str, bytes]:
    ss = _ss()
    rec = ss.get(_RECORDINGS_KEY)
    if not isinstance(rec, dict):
        rec = {}
        ss[_RECORDINGS_KEY] = rec
    return rec


def clear_topic_recordings() -> None:
    _ss().pop(_RECORDINGS_KEY, None)


def find_topic_result(topic_id: str, question_id: str) -> Optional[Dict[str, Any]]:
    tid = str(topic_id or "").strip()
    qid = str(question_id or "").strip()
    if not tid or not qid:
        return None
    for row in get_topic_results():
        if not isinstance(row, dict):
            continue
        if str(row.get("topic_id") or "") == tid and str(row.get("question_id") or "") == qid:
            return row
    return None


def upsert_topic_result(row: Dict[str, Any]) -> None:
    """Replace row with same ``topic_id`` + ``question_id``; never duplicate."""
    tid = str(row.get("topic_id") or "").strip()
    qid = str(row.get("question_id") or "").strip()
    results = get_topic_results()
    for i, existing in enumerate(results):
        if not isinstance(existing, dict):
            continue
        if str(existing.get("topic_id") or "") == tid and str(existing.get("question_id") or "") == qid:
            results[i] = row
            return
    results.append(row)


def _analysis_status_from_result(result: Dict[str, Any]) -> str:
    ast = str(result.get("analysis_status") or "").lower()
    if ast:
        return ast
    if result.get("diagnosis_status") == "no_speech":
        return "no_speech"
    if result.get("diagnosis_status") == "analysis_pending" or result.get("analysis_pending"):
        return "pending"
    if result.get("diagnosis_status") == "ok":
        return "completed"
    return "failed"


def build_topic_row(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "mode": "topic_practice",
        "topic_id": topic_id,
        "topic_title": topic_title,
        "question_index": int(question_index),
        "question_id": str(question.get("question_id") or ""),
        "question_text": str(question.get("question_en") or ""),
        "question_ko": str(question.get("question_ko") or ""),
        "audio_key": audio_key,
        "transcript": (result.get("transcript") or "").strip(),
        "analysis_status": _analysis_status_from_result(result),
        "analysis_result": result,
    }


def question_as_mock_q(question: Dict[str, Any], topic_title: str) -> Dict[str, Any]:
    """Shape compatible with ``build_analysis_pending_result`` / exam helpers."""
    return {
        "id": question.get("question_id"),
        "question": question.get("question_en") or "",
        "type": question.get("type_label") or question.get("type") or "",
        "topic": topic_title,
    }


def save_topic_placeholder_before_ai(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    audio_bytes: bytes,
) -> None:
    rec = get_topic_recordings()
    rec[audio_key] = audio_bytes
    q_mock = question_as_mock_q(question, topic_title)
    pending = build_analysis_pending_result(q_mock, "unknown", 0)
    pending["analysis_status"] = "pending"
    pending["saved_before_ai"] = True
    upsert_topic_result(
        build_topic_row(
            topic_id=topic_id,
            topic_title=topic_title,
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=pending,
        )
    )


def apply_topic_completed_result(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    stored = dict(result)
    stored["analysis_status"] = "completed"
    if stored.get("diagnosis_status") not in ("no_speech", "no_audio"):
        stored["diagnosis_status"] = stored.get("diagnosis_status") or "ok"
    stored.pop("analysis_pending", None)
    upsert_topic_result(
        build_topic_row(
            topic_id=topic_id,
            topic_title=topic_title,
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=stored,
        )
    )
    return stored


def apply_topic_pending_result(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    error_message: str,
    attempts: int,
    transcript: str = "",
) -> Dict[str, Any]:
    q_mock = question_as_mock_q(question, topic_title)
    err_kind = classify_analysis_error(error_message)
    pending = build_analysis_pending_result(q_mock, err_kind, attempts)
    pending["analysis_status"] = "pending"
    if transcript:
        pending["transcript"] = transcript.strip()
    upsert_topic_result(
        build_topic_row(
            topic_id=topic_id,
            topic_title=topic_title,
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=pending,
        )
    )
    return pending


def apply_topic_no_speech_result(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
) -> Dict[str, Any]:
    res = {
        "analysis_status": "no_speech",
        "diagnosis_status": "no_speech",
        "no_speech_detected": True,
        "transcript": "",
        "estimated_level": "측정 불가",
        "estimated_level_display": "측정 불가",
        "summary_speech_rehab": "음성이 감지되지 않았어요. 다시 녹음해 주세요.",
        "prescription": "마이크와 주변 소음을 확인한 뒤 또렷하게 다시 답변해 주세요.",
        "wpm": 0,
        "sentence_count": 0,
        "word_count": 0,
        "fact_scores": {"text_type": 0.0, "accuracy": 0.0},
        "rubric_scores": {"fluency": 0, "lexical": 0, "logic": 0, "grammar": 0},
    }
    upsert_topic_result(
        build_topic_row(
            topic_id=topic_id,
            topic_title=topic_title,
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=res,
        )
    )
    return res


def summarize_topic_session(topic_id: str) -> Dict[str, int]:
    rows = [
        r
        for r in get_topic_results()
        if isinstance(r, dict) and str(r.get("topic_id") or "") == str(topic_id)
    ]
    done = len(rows)
    completed = sum(1 for r in rows if str(r.get("analysis_status") or "") == "completed")
    pending = sum(1 for r in rows if str(r.get("analysis_status") or "") == "pending")
    return {"answered": done, "completed": completed, "pending": pending}
