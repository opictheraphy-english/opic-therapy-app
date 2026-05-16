"""Centralized mock-exam state helpers.

Single source of truth for two operations that previously got reinvented in
multiple views and were the cause of two long-standing bugs:

* "처음부터 다시" did not fully reset the exam. The router only cleared
  ``audio_bytes`` and ``exam_finished``; the on-disk ``mock_snapshot`` then
  rehydrated the previous in-progress exam on the very next rerun, so the
  user ended up back inside an exam they explicitly chose to leave.

* When Gemini analysis failed (503 / 429 / timeout) the code appended a
  half-broken result row to ``mx["results"]`` and force-navigated to the
  per-question report — destroying the ability to retry the SAME question
  with the audio they had already recorded.

Both are now handled here so ``views/mock_exam.py``, ``views/home.py``,
``views/final_report.py``, and ``app.py`` share identical semantics.

State ownership (single source of truth)
----------------------------------------
* **ACTIVE EXAM**       — fields in ``mx`` defined by ``_RESET_DEFAULTS``.
* **PENDING_RECOVERY**  — ``mx["pending_recovery"]`` dict. Transient; never
  written to disk, never auto-restored.
* **RESUMABLE EXAM**    — ``mock_snapshot`` written to disk by
  ``utils.local_profile.sync_user_progress``. Restored at most once per
  session via ``maybe_restore_mock_from_disk`` unless suppressed.
* **COMPLETED EXAM**    — ``mx["exam_finished"] is True`` and the FINAL view
  is the only allowed render path.

These four states are mutually exclusive in practice:
  reset_exam_state()  →  wipes ACTIVE + PENDING_RECOVERY + COMPLETED, marks
                         disk restore suppressed for this session.
  start a new exam    →  ACTIVE only.
  recover from error  →  ACTIVE + PENDING_RECOVERY (audio preserved).
"""

from __future__ import annotations

import secrets
from copy import deepcopy
from typing import Any, Dict, List, MutableMapping, Optional

from utils.local_profile import iso_now


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------

# Every key in the mock namespace that meaningfully describes an exam in
# flight or a finished session. ``reset_exam_state`` wipes this entire set,
# nothing else should be touched (e.g. ``st.session_state.mock_data
# ["recording_active"]`` is transient and is reset elsewhere).
_RESET_DEFAULTS: Dict[str, Any] = {
    "mock_page": "SURVEY",
    "exam": [],
    "current_exam": [],
    "survey_results": {},
    "survey_completed": False,
    "attempt_no": 1,
    "completed_attempts": [],
    "current_idx": 0,
    "results": [],
    "last_result": None,
    "recordings": {},
    "exam_listen_nonce": None,
    "question_play_counts": {},
    "analysis_status": "",
    "analysis_done": False,
    "analysis_error_msg": "",
    "analysis_result": None,
    "audio_bytes": None,
    "preview_transcript": None,
    "exam_finished": False,
    "final_report_generated": False,
    "overall_estimated_level": None,
    "analytics_cache": None,
    "downloadable_report_bytes": None,
    "exam_started_at": None,
    "exam_last_seen_at": None,
    "pending_recovery": None,
}

# Keys that should be removed (not just defaulted) since they only exist
# when the corresponding feature is active.
_POP_KEYS = (
    "_analytics_sig",
    "_show_exam_celebration",
    "_final_report_demo",
    "_demo_preview_loaded",
)


def reset_exam_state(
    mx: Dict[str, Any],
    ss: MutableMapping[str, Any],
) -> None:
    """Wipe all exam state in-place and prevent the on-disk snapshot from
    silently rehydrating it on the very next rerun.

    Use cases:
      * ``?nav=MOCK&mock=SURVEY&reset=1`` URL (home "처음부터 다시" anchor)
      * "처음으로 돌아가기" button on the per-question report
      * "🏠 홈으로 돌아가기" button on the final report
    """
    for key, default in _RESET_DEFAULTS.items():
        mx[key] = default if not isinstance(default, (list, dict)) else type(default)()

    for key in _POP_KEYS:
        mx.pop(key, None)

    mx.pop("mock_mode", None)
    mx.pop("mock_mode_label", None)
    mx.pop("_resume_confirmed", None)
    ss.pop("mock_mode", None)

    # One-shot guard: ``maybe_restore_mock_from_disk`` checks this and skips
    # rehydration for this session. The very next ``sync_user_progress`` call
    # writes the cleared snapshot, so subsequent sessions also see an empty
    # disk and there is nothing left to restore.
    ss["_suppress_disk_restore"] = True
    ss["_mock_restored_from_disk"] = True
    # Force the progress signature to refresh so the very next sync writes.
    ss.pop("_progress_sig", None)


# ---------------------------------------------------------------------------
# Pending recovery (AI failure retry state)
# ---------------------------------------------------------------------------

# Sentinel used by the view to flag "AI accepted the audio but heard no
# speech" through the same ``mark_pending_recovery`` channel as real
# transport errors. We never want the auto-advance success path to
# commit an empty transcript silently — the user needs an explicit
# "음성이 감지되지 않았어요" prompt + a re-record affordance.
NO_SPEECH_ERROR_SENTINEL = "NO_SPEECH"


def build_analysis_pending_result(
    q: Dict[str, Any],
    error_kind: str,
    attempts: int,
) -> Dict[str, Any]:
    """Safe placeholder row when Gemini did not return after all retries.

    Lets the exam advance without duplicating ``q_id`` rows or blocking on
    ``pending_recovery``. ``error_kind`` matches :func:`classify_analysis_error`.
    """
    tips = {
        "overload": "서버가 잠시 바빴을 수 있어요. 다음 문항으로 진행한 뒤, 나중에 홈에서 이어하기로 다시 시도해 보세요.",
        "rate_limit": "요청이 잠깐 많았어요. 1~2분 뒤 같은 녹음으로 다시 분석할 수 있어요.",
        "timeout": "응답이 지연되었어요. 네트워크가 안정된 곳에서 다시 시도해 보세요.",
        "engine_path": "모델 연결을 확인 중이에요. 잠시 후 다시 시도해 주세요.",
        "unknown": "분석이 완료되지 않았어요. 녹음은 저장되어 있으니 이후에 다시 시도할 수 있어요.",
    }
    body = tips.get(error_kind, tips["unknown"])
    summary = (
        "이 문항은 AI 분석이 아직 완료되지 않았습니다. "
        "시험 흐름은 그대로 이어가며, 이후 다시 분석을 시도할 수 있어요."
    )
    return {
        "analysis_status": "pending",
        "diagnosis_status": "analysis_pending",
        "analysis_pending": True,
        "analysis_error_kind": error_kind,
        "analysis_attempts": int(attempts),
        "transcript": "",
        "no_speech_detected": False,
        "estimated_level": "측정 대기",
        "estimated_level_display": "측정 대기",
        "estimated_range": "",
        "summary_speech_rehab": summary,
        "prescription": body,
        "tense_appropriateness_feedback": "",
        "wpm": 0,
        "sentence_count": 0,
        "word_count": 0,
        "fact_scores": {"text_type": 0.0, "accuracy": 0.0},
        "rubric_scores": {"fluency": 0, "lexical": 0, "logic": 0, "grammar": 0},
        "semantic_feedback": "",
        "semantic_dimensions": {},
        "question_type": q.get("type") or "A",
        "final_grade_score": None,
        "acting_feedback": "",
        "raw_text_parse_failed": "",
    }


def classify_analysis_error(message: str) -> str:
    """Pick a coarse category from an arbitrary error string.

    Used only to select friendly Korean copy in the recovery panel — never
    affects retry logic or state transitions.
    """
    if not message:
        return "unknown"
    if message.strip().upper() == NO_SPEECH_ERROR_SENTINEL:
        return "no_speech"
    upper = message.upper()
    if "503" in upper or "OVERLOAD" in upper or "UNAVAILABLE" in upper:
        return "overload"
    if "429" in upper or "RESOURCE_EXHAUSTED" in upper or "할당량" in message:
        return "rate_limit"
    if "TIMEOUT" in upper or "DEADLINE" in upper or "504" in upper:
        return "timeout"
    if "404" in upper or "NOT_FOUND" in upper or "엔진 경로" in message:
        return "engine_path"
    return "unknown"


def mark_pending_recovery(
    mx: Dict[str, Any],
    *,
    q_id: int,
    audio_key: str,
    error_message: str,
    attempts: int,
    transcript_preview: Optional[str] = None,
) -> None:
    """Record that the current question's analysis failed but audio + any
    in-flight transcript are still preserved, so the user can safely retry
    the SAME question without re-recording.

    Critical: this function NEVER appends to ``mx["results"]`` and NEVER
    advances ``current_idx``. Failure is transient state, not exam progress.
    """
    mx["pending_recovery"] = {
        "q_id": int(q_id),
        "audio_key": audio_key,
        "error_message": (error_message or "").strip(),
        "error_kind": classify_analysis_error(error_message or ""),
        "attempts": int(attempts),
        "last_attempted_at": iso_now(),
        "transcript_preview": (transcript_preview or "").strip() or None,
    }
    # Reset the analysis status flags — recovery is user-driven now.
    mx["analysis_status"] = ""
    mx["analysis_done"] = False
    mx["analysis_error_msg"] = ""


def clear_pending_recovery(mx: Dict[str, Any]) -> None:
    """Drop the recovery state. Audio and transcript stay in ``mx``."""
    mx["pending_recovery"] = None


def has_pending_recovery_for(mx: Dict[str, Any], q_id: int) -> bool:
    """True iff there is a pending recovery snapshot targeting *this*
    question. Pending recoveries from other questions are ignored — they
    cannot leak across questions because ``current_idx`` is reconciled to
    the next unanswered slot after each successful analysis."""
    pr = mx.get("pending_recovery")
    if not isinstance(pr, dict):
        return False
    try:
        return int(pr.get("q_id") or 0) == int(q_id)
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Resumable / completed predicates  (single source of truth)
# ---------------------------------------------------------------------------
#
# Both predicates accept either:
#   • the live ``mx`` session-namespace dict, or
#   • a loaded ``mock_snapshot`` dict from ``user_progress.json``.
#
# The shape is identical, so views, the home dashboard, the router, and
# the mock view itself can all consult the same function instead of
# re-implementing the "is this exam still alive?" check four different
# ways. Misaligned checks were the historical cause of "이어하기 ▶ SURVEY"
# regressions.


def _row_counts_as_answered(row: Dict[str, Any]) -> bool:
    """True when a result row represents a saved answer that may advance the exam."""
    res = row.get("result") if isinstance(row.get("result"), dict) else row
    if not isinstance(res, dict):
        return bool(row)
    ast = str(res.get("analysis_status") or "").lower()
    dst = str(res.get("diagnosis_status") or "").lower()
    if ast in ("no_speech", "no_audio", "failed") or dst in ("no_speech", "no_audio"):
        return False
    return True


def _prefix_completed_matching_exam_order(exam: List[Any], results: List[Any]) -> int:
    """Count how many leading ``exam[i]`` slots have a matching ``results[i].q_id``.

    Duplicate or out-of-order rows (historical bugs) stop the prefix at the
    first mismatch so ``이어하기`` never skips a real unanswered question.
    Rows marked ``no_speech`` do not advance the prefix (re-record required).
    """
    if not isinstance(exam, list) or not isinstance(results, list):
        return 0
    n = min(len(exam), len(results))
    prefix = 0
    for i in range(n):
        row = results[i]
        q = exam[i]
        if not isinstance(row, dict) or not isinstance(q, dict):
            break
        try:
            rq = int(row.get("q_id"))
            eq = int(q.get("id"))
        except (TypeError, ValueError):
            break
        if rq != eq:
            break
        if not _row_counts_as_answered(row):
            break
        prefix += 1
    return prefix


def count_completed_exam_prefix(snap: Dict[str, Any]) -> int:
    """Number of leading exam questions that already have a matching result row."""
    if not isinstance(snap, dict):
        return 0
    exam = snap.get("current_exam") or []
    results = snap.get("results") or []
    return _prefix_completed_matching_exam_order(exam, results)


def dedupe_consecutive_mock_results(mx: Dict[str, Any]) -> None:
    """Collapse consecutive rows with the same ``q_id`` (keep the latest)."""
    results = mx.get("results")
    if not isinstance(results, list) or len(results) < 2:
        return
    out: List[Any] = []
    for r in results:
        if not isinstance(r, dict):
            out.append(r)
            continue
        try:
            qid = int(r.get("q_id"))
        except (TypeError, ValueError):
            out.append(r)
            continue
        if out and isinstance(out[-1], dict):
            try:
                prev = int(out[-1].get("q_id", -2))
            except (TypeError, ValueError):
                prev = -2
            if prev == qid:
                out[-1] = r
                continue
        out.append(r)
    mx["results"] = out


def upsert_mock_exam_result(mx: Dict[str, Any], row: Dict[str, Any]) -> None:
    """Append a per-question result, or replace an existing row with the same ``q_id``.

    Prevents duplicate rows on retry, Streamlit reruns, and final-report
  re-analysis for the same question.
    """
    results = mx.setdefault("results", [])
    if not isinstance(results, list):
        mx["results"] = []
        results = mx["results"]
    try:
        qid = int(row.get("q_id"))
    except (TypeError, ValueError):
        results.append(row)
        return
    for i, existing in enumerate(results):
        if not isinstance(existing, dict):
            continue
        try:
            if int(existing.get("q_id", -1)) == qid:
                results[i] = row
                return
        except (TypeError, ValueError):
            continue
    results.append(row)


def _result_row(
    q: Dict[str, Any],
    *,
    q_id: int,
    question_index: int,
    audio_key: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "q_id": int(q_id),
        "question_index": int(question_index),
        "question": q.get("question", ""),
        "type": q.get("type", ""),
        "topic": q.get("topic", ""),
        "audio_key": audio_key,
        "result": result,
    }


def save_answer_placeholder_before_ai(
    mx: Dict[str, Any],
    q: Dict[str, Any],
    *,
    q_id: int,
    question_index: int,
    audio_key: str,
    audio_bytes: bytes,
) -> None:
    """Persist recording + pending result row **before** calling Gemini."""
    rec = mx.setdefault("recordings", {})
    if not isinstance(rec, dict):
        rec = {}
        mx["recordings"] = rec
    rec[audio_key] = audio_bytes
    mx["audio_bytes"] = audio_bytes

    pending = build_analysis_pending_result(q, "unknown", 0)
    pending["analysis_status"] = "pending"
    pending["saved_before_ai"] = True
    upsert_mock_exam_result(
        mx,
        _result_row(
            q,
            q_id=q_id,
            question_index=question_index,
            audio_key=audio_key,
            result=pending,
        ),
    )


def apply_completed_analysis_result(
    mx: Dict[str, Any],
    q: Dict[str, Any],
    *,
    q_id: int,
    question_index: int,
    audio_key: str,
    result: Dict[str, Any],
) -> Dict[str, Any]:
    """Update the existing row for this question with a completed analysis."""
    stored = dict(result)
    stored["analysis_status"] = "completed"
    if stored.get("diagnosis_status") not in ("no_speech", "no_audio"):
        stored["diagnosis_status"] = stored.get("diagnosis_status") or "ok"
    stored.pop("analysis_pending", None)
    upsert_mock_exam_result(
        mx,
        _result_row(
            q,
            q_id=q_id,
            question_index=question_index,
            audio_key=audio_key,
            result=stored,
        ),
    )
    return stored


def apply_no_speech_result(
    mx: Dict[str, Any],
    q: Dict[str, Any],
    *,
    q_id: int,
    question_index: int,
    audio_key: str,
) -> Dict[str, Any]:
    """Mark answer as no-speech — does not advance exam pointer."""
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
    upsert_mock_exam_result(
        mx,
        _result_row(
            q,
            q_id=q_id,
            question_index=question_index,
            audio_key=audio_key,
            result=res,
        ),
    )
    return res


def apply_pending_analysis_result(
    mx: Dict[str, Any],
    q: Dict[str, Any],
    *,
    q_id: int,
    question_index: int,
    audio_key: str,
    error_message: str,
    attempts: int,
    transcript: str = "",
) -> Dict[str, Any]:
    """Keep saved answer; mark analysis as pending (API/parse/exception path)."""
    err_kind = classify_analysis_error(error_message)
    pending = build_analysis_pending_result(q, err_kind, attempts)
    pending["analysis_status"] = "pending"
    if transcript:
        pending["transcript"] = transcript.strip()
    upsert_mock_exam_result(
        mx,
        _result_row(
            q,
            q_id=q_id,
            question_index=question_index,
            audio_key=audio_key,
            result=pending,
        ),
    )
    return pending


def find_result_row(mx: Dict[str, Any], q_id: int) -> Optional[Dict[str, Any]]:
    for item in mx.get("results") or []:
        if not isinstance(item, dict):
            continue
        try:
            if int(item.get("q_id", -1)) == int(q_id):
                return item
        except (TypeError, ValueError):
            continue
    return None


def stored_audio_for_row(mx: Dict[str, Any], row: Dict[str, Any]) -> Optional[bytes]:
    audio_key = (row.get("audio_key") or "").strip()
    if audio_key:
        blob = (mx.get("recordings") or {}).get(audio_key)
        if blob:
            return blob
    try:
        qid = int(row.get("q_id", -1))
    except (TypeError, ValueError):
        return None
    return (mx.get("recordings") or {}).get(f"q_{qid}") or mx.get("audio_bytes")


def reconcile_mock_exam_pointer(mx: Dict[str, Any]) -> int:
    """Dedupe results and set ``current_idx`` to the next unanswered question.

    ``current_idx`` is always the index into ``current_exam`` for the question
    the user should speak next. After finishing question *k* (0-based), this
    becomes *k+1* (clamped), even while ``mock_page`` is still ``REPORT``, so
    disk snapshots never point at a completed question after a successful
    analysis — fixing the duplicate-Q1 / ``이어하기`` regression.
    """
    dedupe_consecutive_mock_results(mx)
    exam = mx.get("current_exam") or mx.get("exam") or []
    if not isinstance(exam, list) or not exam:
        mx["current_idx"] = 0
        return 0
    total = len(exam)
    results = mx.get("results") or []
    if not isinstance(results, list):
        results = []
    prefix = _prefix_completed_matching_exam_order(exam, results)
    if mx.get("exam_finished") and prefix >= total:
        mx["current_idx"] = max(0, total - 1)
        return int(mx["current_idx"])
    next_idx = min(prefix, max(total - 1, 0))
    mx["current_idx"] = next_idx
    return next_idx


def has_resumable_exam(snap: Dict[str, Any]) -> bool:
    """True iff the dict represents an in-progress, non-finished exam.

    Conditions:
      1. ``current_exam`` is a non-empty list.
      2. ``exam_finished`` is not truthy.
      3. We haven't already collected results for every question (avoids
         showing the resume CTA in the gap between Q15 analysis success
         and the FINAL transition committing ``exam_finished=True``).
    """
    if not isinstance(snap, dict):
        return False
    exam = snap.get("current_exam")
    if not isinstance(exam, list) or not exam:
        return False
    if snap.get("exam_finished"):
        return False
    total = len(exam)
    prefix = count_completed_exam_prefix(snap)
    if prefix >= total:
        return False
    return True


def is_completed_exam(snap: Dict[str, Any]) -> bool:
    """True iff this dict represents a finished, finalized exam."""
    if not isinstance(snap, dict):
        return False
    return bool(snap.get("exam_finished"))


def is_completed_mock(mx: Dict[str, Any]) -> bool:
    """Finished attempt — not an active in-progress test (Mock tab landing)."""
    if not isinstance(mx, dict):
        return False
    if mx.get("exam_finished"):
        return True
    page = mx.get("mock_page")
    if page in ("FINAL", "REPORT") and (mx.get("results") or mx.get("analytics_cache")):
        exam = mx.get("current_exam") or mx.get("exam") or []
        if isinstance(exam, list) and exam:
            return count_completed_exam_prefix(mx) >= len(exam)
    return False


def has_active_unfinished_mock(mx: Dict[str, Any]) -> bool:
    """In-progress exam the user can resume — never a completed session."""
    if is_completed_mock(mx):
        return False
    return has_resumable_exam(mx)


def format_mock_attempt_label(
    mx: Dict[str, Any],
    *,
    q_id: Optional[int] = None,
    total: Optional[int] = None,
) -> str:
    """Human-readable attempt label for top bars (e.g. ``2회 모의고사 · Q1 / 15``)."""
    n = int(mx.get("attempt_no") or 1)
    base = f"{n}회 모의고사"
    if q_id is not None and total is not None and int(total) > 0:
        return f"{base} · Q{q_id} / {total}"
    return base


def start_new_mock_attempt(mx: Dict[str, Any], ss: MutableMapping[str, Any]) -> bool:
    """Archive the finished attempt (if any) and start a fresh exam using saved survey.

    Does not clear ``survey_results`` or ``onboarding``. Does not set
    ``_suppress_disk_restore`` so the next ``sync_user_progress`` can persist
    the new in-progress snapshot.
    """
    if not mx.get("exam_finished"):
        return False
    survey = mx.get("survey_results")
    if not isinstance(survey, dict) or not survey:
        return False

    from services.mock_exam.mock_exam_test_set_generator import generate_test_set
    from utils.session_state import settings_session

    prev_no = int(mx.get("attempt_no") or 1)
    completed: List[Any] = list(mx.get("completed_attempts") or [])
    if not isinstance(completed, list):
        completed = []

    rows = mx.get("results") or []
    if isinstance(rows, list) and rows:
        try:
            results_copy = deepcopy(rows)
        except Exception:
            results_copy = list(rows)
        try:
            agg_copy = deepcopy(mx.get("analytics_cache")) if mx.get("analytics_cache") is not None else None
        except Exception:
            agg_copy = None
        completed.append(
            {
                "attempt_no": prev_no,
                "results": results_copy,
                "analytics_cache": agg_copy,
                "overall_estimated_level": mx.get("overall_estimated_level"),
                "final_report_generated": bool(mx.get("final_report_generated")),
                "completed_at": iso_now(),
            }
        )

    mx["completed_attempts"] = completed
    mx["attempt_no"] = prev_no + 1

    clear_pending_recovery(mx)
    for key in _POP_KEYS:
        mx.pop(key, None)
    for k in (
        "final_report_generated",
        "overall_estimated_level",
        "analytics_cache",
        "downloadable_report_bytes",
        "_analytics_sig",
        "_show_exam_celebration",
    ):
        mx.pop(k, None)
    mx.pop("_final_report_demo", None)
    mx.pop("_demo_preview_loaded", None)
    mx.pop("_view_completed_report", None)

    mx["exam_finished"] = False
    mx["results"] = []
    mx["last_result"] = None
    mx["recordings"] = {}
    mx["question_play_counts"] = {}
    mx["exam_listen_nonce"] = secrets.token_hex(8)
    mx["analysis_status"] = ""
    mx["analysis_done"] = False
    mx["analysis_error_msg"] = ""
    mx["analysis_result"] = None
    mx["audio_bytes"] = None
    mx["preview_transcript"] = None
    mx["mock_page"] = "TEST"
    mx["current_idx"] = 0

    diff = int(survey.get("difficulty") or int(settings_session().get("difficulty", 5)))
    new_exam = generate_test_set(survey, difficulty=diff)
    mx["current_exam"] = new_exam
    mx["exam"] = new_exam

    _now = iso_now()
    mx["exam_started_at"] = _now
    mx["exam_last_seen_at"] = _now
    mx["survey_completed"] = True

    reconcile_mock_exam_pointer(mx)
    ss.pop("_progress_sig", None)
    md = ss.get("mock_data")
    if isinstance(md, dict):
        md["recording_active"] = False
    return True
