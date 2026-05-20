"""Session state for Topic Practice — separate from full mock exam ``mx[\"results\"]``."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from utils.exam_state import build_analysis_pending_result, classify_analysis_error
from utils.local_profile import iso_now
from utils.speech_recording import recording_byte_length

_RESULTS_KEY = "topic_practice_results"
_RECORDINGS_KEY = "topic_practice_recordings"


def _ss():
    import streamlit as st

    return st.session_state


def topic_audio_key(
    topic_id: str,
    question_id: str,
    question_index: int | None = None,
) -> str:
    """Stable scoped key — includes q_idx and retry nonce (not global mx audio)."""
    tid = str(topic_id or "").strip()
    qid = str(question_id or "").strip()
    if question_index is None:
        return f"topic_practice_{tid}_{qid}_0_0"
    idx = int(question_index)
    from components.answer_recording import get_recording_retry_nonce

    nonce = get_recording_retry_nonce(f"topic_{tid}", qid, idx)
    return f"topic_practice_{tid}_{qid}_{idx}_{nonce}"


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


def topic_rows_for_session(topic_id: str) -> List[Dict[str, Any]]:
    tid = str(topic_id or "").strip()
    rows = [
        r
        for r in get_topic_results()
        if isinstance(r, dict) and str(r.get("topic_id") or "") == tid
    ]
    return sorted(rows, key=lambda x: int(x.get("question_index") or 0))


def get_topic_answer_blob(row: Dict[str, Any]) -> bytes | None:
    if not isinstance(row, dict):
        return None
    audio_key = str(row.get("audio_key") or "").strip()
    if audio_key:
        blob = get_topic_recordings().get(audio_key)
        if blob:
            return blob
    res = row.get("analysis_result")
    if isinstance(res, dict):
        nbytes = int(res.get("source_audio_size_bytes") or 0)
        if nbytes > 0 and audio_key:
            return get_topic_recordings().get(audio_key)
    return None


def count_topic_saved_answers(topic_id: str) -> int:
    return sum(1 for r in topic_rows_for_session(topic_id) if get_topic_answer_blob(r))


def all_topic_answers_saved(topic_id: str, *, expected: int = 3) -> bool:
    return count_topic_saved_answers(topic_id) >= int(expected)


def save_topic_unanalyzed_answer(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    audio_bytes: bytes,
    mime_type: str = "",
) -> Dict[str, Any]:
    """Persist recording only — no Gemini until mini report."""
    rec = get_topic_recordings()
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
    upsert_topic_result(
        build_topic_row(
            topic_id=topic_id,
            topic_title=topic_title,
            question_index=question_index,
            question=question,
            audio_key=audio_key,
            result=placeholder,
        )
    )
    row = find_topic_result(topic_id, str(question.get("question_id") or ""))
    if isinstance(row, dict):
        row["mime_type"] = mime_type
        row["audio_len"] = nbytes
        row["recorded_at"] = placeholder["recorded_at"]
    return placeholder


def apply_stt_to_topic_saved_row(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    audio_bytes: bytes,
    mime_type: str = "",
) -> Dict[str, Any] | None:
    """Run STT after audio save and persist transcript fields on the topic row."""
    import logging

    from services.stt_service import merge_stt_into_answer_result, transcribe_answer_audio

    question_id = str(question.get("question_id") or "")
    row = find_topic_result(topic_id, question_id)
    if not isinstance(row, dict):
        return None
    res = row.get("analysis_result")
    base = dict(res) if isinstance(res, dict) else {}
    nbytes = recording_byte_length(audio_bytes)
    question_text = str(question.get("question_en") or question.get("question") or "")
    stt = transcribe_answer_audio(
        audio_bytes,
        mime_type=mime_type or "audio/webm",
        language_hint="en",
        question_text=question_text,
        mode="topic_practice",
        question_id=question_id,
    )
    merged = merge_stt_into_answer_result(
        base,
        stt,
        question_text=question_text,
        question_index=question_index,
        question_id=question_id,
        audio_key=audio_key,
        audio_len=nbytes,
    )
    updated = build_topic_row(
        topic_id=topic_id,
        topic_title=topic_title,
        question_index=question_index,
        question=question,
        audio_key=audio_key,
        result=merged,
    )
    updated["mime_type"] = mime_type
    updated["audio_len"] = nbytes
    upsert_topic_result(updated)
    try:
        logging.getLogger(__name__).debug(
            "[TOPIC_STT] topic_id=%s q_idx=%s stt_status=%s word_count=%s ok=%s",
            topic_id,
            question_index,
            merged.get("stt_status"),
            merged.get("stt_word_count"),
            stt.get("ok"),
        )
    except Exception:
        pass
    return merged


def clear_topic_answer_for_question(topic_id: str, question_id: str) -> None:
    row = find_topic_result(topic_id, question_id)
    if not isinstance(row, dict):
        return
    audio_key = str(row.get("audio_key") or "").strip()
    if audio_key:
        get_topic_recordings().pop(audio_key, None)
    results = get_topic_results()
    qid = str(question_id or "").strip()
    tid = str(topic_id or "").strip()
    keep = [
        r
        for r in results
        if not (
            isinstance(r, dict)
            and str(r.get("topic_id") or "") == tid
            and str(r.get("question_id") or "") == qid
        )
    ]
    _ss()[_RESULTS_KEY] = keep


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
        "stt_status": str(result.get("stt_status") or ""),
        "stt_word_count": int(result.get("stt_word_count") or 0),
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
    if stored.get("diagnosis_status") not in ("no_speech", "no_audio", "unclear_speech"):
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
    mode: str = "topic_practice",
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
        mode=mode,
        audio_bytes_len=audio_bytes_len,
        mime_type=mime_type,
        model=model,
        retry_count=attempts,
        elapsed_ms=elapsed_ms,
    )
    q_mock = question_as_mock_q(question, topic_title)
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


def _topic_speech_issue_result(
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


def apply_topic_no_audio_result(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    source_audio_size_bytes: int = 0,
) -> Dict[str, Any]:
    res = _topic_speech_issue_result(
        analysis_status="no_audio",
        diagnosis_status="no_audio",
        summary="녹음이 제대로 저장되지 않았어요. 마이크 권한을 확인하고 다시 녹음해 주세요.",
        prescription="브라우저 마이크 권한 허용 후 3초 이상 다시 녹음해 주세요.",
        source_audio_size_bytes=source_audio_size_bytes,
    )
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


def apply_topic_unclear_speech_result(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    source_audio_size_bytes: int,
    audio_mime_guess: str = "",
) -> Dict[str, Any]:
    res = _topic_speech_issue_result(
        analysis_status="unclear_speech",
        diagnosis_status="unclear_speech",
        summary=(
            "녹음은 저장되었지만, AI가 답변을 충분히 읽지 못했어요. "
            "조금 더 또렷하게 다시 말하거나, 저장하고 다음 문항으로 넘어갈 수 있어요."
        ),
        prescription="마이크와 주변 소음을 확인한 뒤 또렷하게 다시 답변해 주세요.",
        source_audio_size_bytes=source_audio_size_bytes,
        audio_mime_guess=audio_mime_guess,
    )
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


def apply_topic_non_english_result(
    *,
    topic_id: str,
    topic_title: str,
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
    res = _topic_speech_issue_result(
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


def apply_topic_needs_review_result(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    source_audio_size_bytes: int,
    audio_mime_guess: str = "",
) -> Dict[str, Any]:
    res = _topic_speech_issue_result(
        analysis_status="needs_review",
        diagnosis_status="needs_review",
        summary="답변 일부가 불명확하게 인식되었어요.",
        prescription=(
            "녹음은 저장되어 있습니다. 조금 더 또렷하게 다시 말하거나, "
            "같은 녹음으로 다시 분석해 보세요."
        ),
        source_audio_size_bytes=source_audio_size_bytes,
        audio_mime_guess=audio_mime_guess,
    )
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


def apply_topic_no_speech_result(
    *,
    topic_id: str,
    topic_title: str,
    question_index: int,
    question: Dict[str, Any],
    audio_key: str,
    source_audio_size_bytes: int = 0,
) -> Dict[str, Any]:
    res = _topic_speech_issue_result(
        analysis_status="no_speech",
        diagnosis_status="no_speech",
        summary="음성이 감지되지 않았어요. 다시 녹음해 주세요.",
        prescription="마이크와 주변 소음을 확인한 뒤 또렷하게 다시 답변해 주세요.",
        source_audio_size_bytes=source_audio_size_bytes,
    )
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


def clear_topic_practice_session() -> None:
    """Clear topic-practice session keys only — never touches mock exam ``mx['results']``."""
    import logging

    ss = _ss()
    cleared: list[str] = []
    for key in (
        "topic_practice_step",
        "topic_practice_question_index",
        "topic_practice_results",
        "topic_report_status",
        "topic_report_result",
        "topic_mini_report",
        "topic_mini_report_pending",
        "topic_report_last_error",
        "topic_pending_reason",
        "topic_practice_last_saved_q_idx",
        "topic_report_analysis_batch_finished",
        "topic_report_analysis_attempt_id",
        "selected_topic_id",
    ):
        if key in ss:
            cleared.append(key)
        ss.pop(key, None)
    clear_topic_recordings()
    for k in list(ss.keys()):
        if isinstance(k, str) and k.startswith("tp_saved_confirm_"):
            ss.pop(k, None)
    try:
        logging.getLogger(__name__).debug(
            "[STATE_RESET] mode=topic_practice cleared_keys=%s", cleared
        )
    except Exception:
        pass


def summarize_topic_session(topic_id: str) -> Dict[str, int]:
    rows = topic_rows_for_session(topic_id)
    done = len(rows)
    completed = sum(1 for r in rows if str(r.get("analysis_status") or "") == "completed")
    pending = sum(1 for r in rows if str(r.get("analysis_status") or "") == "pending")
    saved = sum(
        1 for r in rows if str(r.get("analysis_status") or "") == "saved_unanalyzed"
    )
    return {
        "answered": done,
        "completed": completed,
        "pending": pending,
        "saved_unanalyzed": saved,
    }
