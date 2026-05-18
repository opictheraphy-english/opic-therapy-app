"""Session state for 5-minute mini mock — separate from full mock ``mx[\"results\"]``."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from utils.exam_state import build_analysis_pending_result, classify_analysis_error
from utils.local_profile import iso_now
from utils.speech_recording import recording_byte_length

_MODE = "mini_mock"
_RESULTS_KEY = "mini_mock_results"
_RECORDINGS_KEY = "mini_mock_recordings"


def _ss():
    import streamlit as st

    return st.session_state


def mini_mock_audio_key(question_id: str) -> str:
    return f"mm_{question_id}"


def get_mini_mock_results() -> List[Dict[str, Any]]:
    ss = _ss()
    rows = ss.get(_RESULTS_KEY)
    if not isinstance(rows, list):
        rows = []
        ss[_RESULTS_KEY] = rows
    return rows


def get_mini_mock_recordings() -> Dict[str, bytes]:
    ss = _ss()
    rec = ss.get(_RECORDINGS_KEY)
    if not isinstance(rec, dict):
        rec = {}
        ss[_RECORDINGS_KEY] = rec
    return rec


def clear_mini_mock_recordings() -> None:
    _ss().pop(_RECORDINGS_KEY, None)


def clear_mini_mock_session() -> None:
    ss = _ss()
    for key in (
        "mini_mock_question_index",
        "mini_mock_results",
        "mini_mock_completed",
        "mini_mock_page",
    ):
        ss.pop(key, None)
    clear_mini_mock_recordings()
    for k in list(ss.keys()):
        if isinstance(k, str) and k.startswith("mm_saved_confirm_"):
            ss.pop(k, None)


def mini_mock_rows_sorted() -> List[Dict[str, Any]]:
    rows = [r for r in get_mini_mock_results() if isinstance(r, dict)]
    return sorted(rows, key=lambda x: int(x.get("question_index") or 0))


def count_mini_mock_saved_answers(*, expected: int = 3) -> int:
    return sum(1 for r in mini_mock_rows_sorted() if get_mini_mock_answer_blob(r))


def row_result(row: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    res = row.get("analysis_result")
    if isinstance(res, dict):
        return res
    res = row.get("result")
    return res if isinstance(res, dict) else {}


def get_mini_mock_answer_blob(row: Dict[str, Any]) -> bytes | None:
    if not isinstance(row, dict):
        return None
    audio_key = str(row.get("audio_key") or "").strip()
    if audio_key:
        blob = get_mini_mock_recordings().get(audio_key)
        if blob:
            return blob
    return None


def find_mini_mock_result(question_id: str) -> Optional[Dict[str, Any]]:
    qid = str(question_id or "").strip()
    if not qid:
        return None
    for row in get_mini_mock_results():
        if not isinstance(row, dict):
            continue
        if str(row.get("question_id") or "") == qid:
            return row
    return None


def upsert_mini_mock_result(row: Dict[str, Any]) -> None:
    results = get_mini_mock_results()
    qid = str(row.get("question_id") or "").strip()
    for i, existing in enumerate(results):
        if not isinstance(existing, dict):
            continue
        if str(existing.get("question_id") or "") == qid:
            results[i] = row
            return
    results.append(row)


def _analysis_status_from_result(result: Dict[str, Any]) -> str:
    ast = str(result.get("analysis_status") or "").lower()
    if ast:
        return ast
    if result.get("diagnosis_status") in (
        "no_speech",
        "unclear_speech",
        "needs_review",
        "non_english",
        "language_mismatch",
    ):
        return str(result.get("diagnosis_status"))
    if result.get("diagnosis_status") == "no_audio":
        return "no_audio"
    if result.get("diagnosis_status") == "analysis_pending" or result.get("analysis_pending"):
        return "pending"
    if result.get("diagnosis_status") == "ok":
        return "completed"
    return "failed"


def build_mini_mock_row(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    result: Dict[str, Any],
    mime_type: str = "",
) -> Dict[str, Any]:
    nbytes = int(result.get("source_audio_size_bytes") or 0)
    recorded_at = str(result.get("recorded_at") or iso_now())
    return {
        "mode": _MODE,
        "question_id": str(question.get("question_id") or ""),
        "question_index": int(question_index),
        "question_type": str(question.get("type") or ""),
        "question_label": str(question.get("type_label") or ""),
        "question_text": str(question.get("question_en") or ""),
        "question_ko": str(question.get("question_ko") or ""),
        "audio_key": audio_key,
        "mime_type": mime_type,
        "audio_len": nbytes,
        "recorded_at": recorded_at,
        "transcript": (result.get("transcript") or "").strip(),
        "analysis_status": _analysis_status_from_result(result),
        "result": result,
        "analysis_result": result,
    }


def question_as_mock_q(question: Dict[str, Any]) -> Dict[str, Any]:
    """Shape compatible with ``build_analysis_pending_result`` / exam helpers."""
    label = str(question.get("type_label") or question.get("type") or "")
    return {
        "id": question.get("question_id"),
        "question": question.get("question_en") or "",
        "type": label,
        "topic": label,
    }


def mini_mock_needs_analysis(row: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(row, dict):
        return False
    res = row_result(row)
    ast = str(row.get("analysis_status") or res.get("analysis_status") or "").lower()
    if ast in ("saved_unanalyzed", "unknown"):
        return True
    from services.exam_analytics import result_display_status

    return result_display_status(res) == "AI 분석 대기 중"


def save_mini_mock_unanalyzed_answer(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    audio_bytes: bytes,
    mime_type: str = "",
) -> Dict[str, Any]:
    rec = get_mini_mock_recordings()
    rec[audio_key] = audio_bytes
    nbytes = recording_byte_length(audio_bytes)
    placeholder: Dict[str, Any] = {
        "analysis_status": "saved_unanalyzed",
        "diagnosis_status": "saved_unanalyzed",
        "transcript": "",
        "saved_before_ai": True,
        "source_audio_size_bytes": nbytes,
        "recorded_at": iso_now(),
    }
    if mime_type:
        placeholder["audio_mime_guess"] = mime_type
    row = build_mini_mock_row(
        question_index=question_index,
        question=question,
        audio_key=audio_key,
        result=placeholder,
        mime_type=mime_type,
    )
    row["audio_len"] = nbytes
    row["recorded_at"] = placeholder["recorded_at"]
    upsert_mini_mock_result(row)
    return row


def save_mini_mock_placeholder_before_ai(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    audio_bytes: bytes,
) -> None:
    rec = get_mini_mock_recordings()
    rec[audio_key] = audio_bytes
    q_mock = question_as_mock_q(question)
    pending = build_analysis_pending_result(q_mock, "unknown", 0)
    pending["analysis_status"] = "pending"
    pending["saved_before_ai"] = True
    upsert_mini_mock_result(
        build_mini_mock_row(
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=pending,
        )
    )


def apply_mini_mock_completed_result(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    stored = dict(result)
    stored["analysis_status"] = "completed"
    if stored.get("diagnosis_status") not in ("no_speech", "no_audio", "unclear_speech"):
        stored["diagnosis_status"] = stored.get("diagnosis_status") or "ok"
    stored.pop("analysis_pending", None)
    upsert_mini_mock_result(
        build_mini_mock_row(
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=stored,
        )
    )
    return stored


def apply_mini_mock_pending_result(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    error_message: str,
    attempts: int,
    transcript: str = "",
    mime_type: str = "",
    model: str = "",
    audio_bytes_len: int = 0,
    elapsed_ms: Optional[float] = None,
    empty_response: bool = False,
) -> Dict[str, Any]:
    from utils.ai_pending_diag import (
        build_pending_error_metadata,
        category_to_legacy_error_kind,
    )

    meta = build_pending_error_metadata(
        error_message or "",
        empty_response=empty_response,
        question_index=question_index,
        mode=_MODE,
        audio_bytes_len=audio_bytes_len,
        mime_type=mime_type,
        model=model,
        retry_count=attempts,
        elapsed_ms=elapsed_ms,
    )
    q_mock = question_as_mock_q(question)
    err_kind = classify_analysis_error(error_message)
    if err_kind not in (
        "no_speech",
        "no_audio",
        "unclear_speech",
        "needs_review",
        "non_english",
    ):
        err_kind = category_to_legacy_error_kind(meta.get("analysis_error_category", ""))
    pending = build_analysis_pending_result(q_mock, err_kind, attempts)
    pending.update(meta)
    pending["analysis_status"] = "pending"
    if mime_type:
        pending["audio_mime_guess"] = mime_type
    if model:
        pending["model_used"] = model
    if transcript:
        pending["transcript"] = transcript.strip()
    upsert_mini_mock_result(
        build_mini_mock_row(
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=pending,
        )
    )
    return pending


def _speech_issue_result(
    *,
    analysis_status: str,
    diagnosis_status: str,
    summary: str,
    prescription: str,
    source_audio_size_bytes: int = 0,
    audio_mime_guess: str = "",
) -> Dict[str, Any]:
    res: Dict[str, Any] = {
        "analysis_status": analysis_status,
        "diagnosis_status": diagnosis_status,
        "no_speech_detected": diagnosis_status in ("no_speech", "unclear_speech"),
        "transcript": "",
        "estimated_level": "측정 불가",
        "estimated_level_display": "측정 불가",
        "summary_speech_rehab": summary,
        "prescription": prescription,
        "wpm": 0,
        "sentence_count": 0,
        "word_count": 0,
        "fact_scores": {"text_type": 0.0, "accuracy": 0.0},
        "rubric_scores": {"fluency": 0, "lexical": 0, "logic": 0, "grammar": 0},
    }
    if source_audio_size_bytes > 0:
        res["source_audio_size_bytes"] = int(source_audio_size_bytes)
    if audio_mime_guess:
        res["audio_mime_guess"] = audio_mime_guess
    return res


def apply_mini_mock_no_audio_result(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    source_audio_size_bytes: int = 0,
) -> Dict[str, Any]:
    res = _speech_issue_result(
        analysis_status="no_audio",
        diagnosis_status="no_audio",
        summary="녹음이 제대로 저장되지 않았어요. 마이크 권한을 확인하고 다시 녹음해 주세요.",
        prescription="브라우저 마이크 권한 허용 후 3초 이상 다시 녹음해 주세요.",
        source_audio_size_bytes=source_audio_size_bytes,
    )
    upsert_mini_mock_result(
        build_mini_mock_row(
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=res,
        )
    )
    return res


def apply_mini_mock_unclear_speech_result(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    source_audio_size_bytes: int,
    audio_mime_guess: str = "",
) -> Dict[str, Any]:
    res = _speech_issue_result(
        analysis_status="unclear_speech",
        diagnosis_status="unclear_speech",
        summary=(
            "녹음은 저장되었지만, AI가 답변을 충분히 읽지 못했어요. "
            "조금 더 또렷하게 다시 말해 주세요."
        ),
        prescription="마이크와 주변 소음을 확인한 뒤 또렷하게 다시 답변해 주세요.",
        source_audio_size_bytes=source_audio_size_bytes,
        audio_mime_guess=audio_mime_guess,
    )
    upsert_mini_mock_result(
        build_mini_mock_row(
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=res,
        )
    )
    return res


def apply_mini_mock_non_english_result(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    source_audio_size_bytes: int,
    audio_mime_guess: str = "",
    non_english_preview: str = "",
    language_mismatch_kind: str = "korean",
) -> Dict[str, Any]:
    from utils.language_detection import language_mismatch_body, language_mismatch_title

    kind = (language_mismatch_kind or "korean").strip()
    res = _speech_issue_result(
        analysis_status="non_english",
        diagnosis_status="non_english",
        summary=language_mismatch_title(kind),
        prescription=language_mismatch_body(kind),
        source_audio_size_bytes=source_audio_size_bytes,
        audio_mime_guess=audio_mime_guess,
    )
    res["no_speech_detected"] = False
    preview = (non_english_preview or "").strip()
    if preview:
        res["non_english_preview"] = preview[:120]
        res["language_mismatch_kind"] = kind
    upsert_mini_mock_result(
        build_mini_mock_row(
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=res,
        )
    )
    return res


def apply_mini_mock_needs_review_result(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    source_audio_size_bytes: int,
    audio_mime_guess: str = "",
) -> Dict[str, Any]:
    res = _speech_issue_result(
        analysis_status="needs_review",
        diagnosis_status="needs_review",
        summary="답변 일부가 불명확하게 인식되었어요.",
        prescription="조금 더 또렷하게 다시 말해 주세요.",
        source_audio_size_bytes=source_audio_size_bytes,
        audio_mime_guess=audio_mime_guess,
    )
    upsert_mini_mock_result(
        build_mini_mock_row(
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=res,
        )
    )
    return res


def apply_mini_mock_no_speech_result(
    *,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    source_audio_size_bytes: int = 0,
) -> Dict[str, Any]:
    res = _speech_issue_result(
        analysis_status="no_speech",
        diagnosis_status="no_speech",
        summary="음성이 감지되지 않았어요. 다시 녹음해 주세요.",
        prescription="마이크와 주변 소음을 확인한 뒤 또렷하게 다시 답변해 주세요.",
        source_audio_size_bytes=source_audio_size_bytes,
    )
    upsert_mini_mock_result(
        build_mini_mock_row(
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=res,
        )
    )
    return res


def clear_mini_mock_answer_for_question(question_id: str) -> None:
    row = find_mini_mock_result(question_id)
    if not isinstance(row, dict):
        return
    audio_key = str(row.get("audio_key") or "").strip()
    if audio_key:
        get_mini_mock_recordings().pop(audio_key, None)
    results = get_mini_mock_results()
    qid = str(question_id or "").strip()
    _ss()[_RESULTS_KEY] = [
        r for r in results if isinstance(r, dict) and str(r.get("question_id") or "") != qid
    ]
