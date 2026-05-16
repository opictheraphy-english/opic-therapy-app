"""Temporary P0 diagnostics — local terminal + server logs (search ``[AI_DIAG]``).

Remove after call-count investigation is complete.
"""

from __future__ import annotations

import logging
import sys
import time
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_DIAG_CTX: ContextVar[Dict[str, Any]] = ContextVar("ai_diag_ctx", default={})

_SESSION_EVENTS_KEY = "ai_diag_events"
_DEBUG_FLAG_KEY = "debug_ai_diag"


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _short_msg(message: str, limit: int = 120) -> str:
    one_line = " ".join((message or "").split())
    if len(one_line) <= limit:
        return one_line
    return one_line[: limit - 3] + "..."


def _q_label() -> str:
    c = _DIAG_CTX.get()
    if c.get("question_index") not in (None, ""):
        return str(c.get("question_index"))
    if c.get("question_id") not in (None, ""):
        return f"id:{c.get('question_id')}"
    return ""


def _emit_terminal(line: str) -> None:
    """Stdout print for ``streamlit run`` in Cursor — never raises."""
    try:
        print(line, flush=True)
    except Exception:
        try:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()
        except Exception:
            pass


def ensure_ai_diag_session() -> None:
    """Init developer-only in-app diagnostic flags (local testing)."""
    try:
        import streamlit as st
    except Exception:
        return
    if _DEBUG_FLAG_KEY not in st.session_state:
        st.session_state[_DEBUG_FLAG_KEY] = False
    if _SESSION_EVENTS_KEY not in st.session_state:
        st.session_state[_SESSION_EVENTS_KEY] = []


def clear_ai_diag_events() -> None:
    try:
        import streamlit as st
    except Exception:
        return
    st.session_state[_SESSION_EVENTS_KEY] = []


def _record_session_event(event: Dict[str, Any]) -> None:
    """Append to in-app event log — never stores keys, audio, or transcript."""
    try:
        import streamlit as st
    except Exception:
        return
    if not st.session_state.get(_DEBUG_FLAG_KEY):
        return
    ensure_ai_diag_session()
    events = st.session_state.get(_SESSION_EVENTS_KEY)
    if not isinstance(events, list):
        events = []
    events.append(event)
    # Cap history so reruns do not grow without bound during long sessions.
    if len(events) > 200:
        events = events[-200:]
    st.session_state[_SESSION_EVENTS_KEY] = events


def _event_question_fields() -> Dict[str, Any]:
    c = _DIAG_CTX.get()
    out: Dict[str, Any] = {"timestamp": time.time()}
    if c.get("submission_id"):
        out["submission_id"] = c.get("submission_id")
    if c.get("question_index") not in (None, ""):
        out["question_index"] = c.get("question_index")
    if c.get("question_id") not in (None, ""):
        out["question_id"] = c.get("question_id")
    return out


def summarize_latest_batch(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Stats for the most recent answer (latest ``submission_id`` batch)."""
    if not events:
        return {
            "question_label": "—",
            "start_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "models": [],
        }
    latest_sid: Optional[str] = None
    for ev in reversed(events):
        sid = ev.get("submission_id")
        if sid:
            latest_sid = str(sid)
            break
    if latest_sid:
        batch = [e for e in events if e.get("submission_id") == latest_sid]
    else:
        batch = events[-20:]

    starts = [e for e in batch if e.get("type") == "semantic_attempt_start"]
    successes = [e for e in batch if e.get("type") == "semantic_attempt_success"]
    failures = [e for e in batch if e.get("type") == "semantic_attempt_failure"]

    q_label = "—"
    for ev in reversed(batch):
        qid = ev.get("question_id")
        if qid not in (None, ""):
            q_label = f"Q{qid}"
            break
        qidx = ev.get("question_index")
        if qidx not in (None, ""):
            q_label = f"idx {qidx}"
            break

    models: List[str] = []
    for ev in starts:
        mid = ev.get("model_id")
        if mid and mid not in models:
            models.append(str(mid))

    return {
        "question_label": q_label,
        "start_count": len(starts),
        "success_count": len(successes),
        "failure_count": len(failures),
        "models": models,
    }


def render_ai_diag_debug_panel() -> None:
    """Temporary Mock-tab panel — visible when ``debug_ai_diag`` is True."""
    try:
        import streamlit as st
    except Exception:
        return

    ensure_ai_diag_session()
    if not st.session_state.get(_DEBUG_FLAG_KEY):
        return

    events = st.session_state.get(_SESSION_EVENTS_KEY) or []
    summary = summarize_latest_batch(events if isinstance(events, list) else [])

    st.markdown("---")
    st.markdown("##### AI 진단 패널")
    st.caption("개발용 — 최근 답변 1회 기준 Gemini `generate_content` 호출 수")

    models_text = ", ".join(summary["models"]) if summary["models"] else "—"
    st.markdown("**AI 진단 결과**")
    st.write(f"최근 문항: {summary['question_label']}")
    st.write(f"Gemini 시도 횟수: {summary['start_count']}회")
    st.write(f"사용 모델: {models_text}")
    st.write(f"성공: {summary['success_count']}")
    st.write(f"실패: {summary['failure_count']}")

    if summary["start_count"] <= 2:
        st.success("정상 범위입니다. API 호출 수가 과하지 않습니다.")
    elif summary["start_count"] >= 3:
        st.warning(
            "주의: 한 문항에서 Gemini 호출이 과하게 발생하고 있습니다. "
            "fallback/retry 축소가 필요합니다."
        )

    if st.button("AI 진단 기록 초기화", key="ai_diag_reset_btn"):
        clear_ai_diag_events()
        st.rerun()


def set_diag_context(ctx: Optional[Dict[str, Any]]) -> None:
    _DIAG_CTX.set(dict(ctx or {}))


def update_diag_context(**fields: Any) -> None:
    cur = dict(_DIAG_CTX.get())
    cur.update(fields)
    _DIAG_CTX.set(cur)


def _fields(extra: Optional[Dict[str, Any]] = None) -> str:
    c = dict(_DIAG_CTX.get())
    if extra:
        c.update(extra)
    parts = [
        f"ts={_utc_ts()}",
        f"submission_id={c.get('submission_id', '')}",
        f"question_index={c.get('question_index', '')}",
        f"question_id={c.get('question_id', '')}",
        f"mock_mode={c.get('mock_mode', '')}",
        f"mock_page={c.get('mock_page', '')}",
        f"attempt_id={c.get('attempt_id', '')}",
        f"retry_attempt={c.get('retry_attempt', '')}",
        f"fallback_index={c.get('fallback_index', '')}",
        f"caller={c.get('caller', '')}",
        f"audio_bytes={c.get('audio_bytes_len', '')}",
    ]
    if extra and "model_id" in extra:
        parts.append(f"model_id={extra.get('model_id', '')}")
    if extra and "elapsed_ms" in extra:
        parts.append(f"elapsed_ms={extra.get('elapsed_ms', '')}")
    return " ".join(parts)


def log_retry_start() -> None:
    q = _q_label()
    _emit_terminal(f"[AI_DIAG] retry wrapper start | q={q}")
    logger.info("[AI_DIAG] analyze_audio_with_retry start %s", _fields())


def log_retry_success(*, attempts: int) -> None:
    q = _q_label()
    _emit_terminal(f"[AI_DIAG] retry wrapper end | q={q} | status=success")
    logger.info(
        "[AI_DIAG] analyze_audio_with_retry success %s wrapper_attempts=%s",
        _fields(),
        attempts,
    )


def log_retry_failure(*, attempts: int, error_message: str) -> None:
    q = _q_label()
    _emit_terminal(f"[AI_DIAG] retry wrapper end | q={q} | status=failure")
    logger.warning(
        "[AI_DIAG] analyze_audio_with_retry failure %s wrapper_attempts=%s error=%s",
        _fields(),
        attempts,
        _short_msg(error_message),
    )


def log_pipeline_start() -> None:
    logger.info("[AI_DIAG] analyze_audio_with_ai start %s", _fields())


def log_pipeline_end(*, outcome: str) -> None:
    logger.info(
        "[AI_DIAG] analyze_audio_with_ai end %s outcome=%s",
        _fields(),
        outcome,
    )


def log_semantic_start(*, model_id: str) -> None:
    c = _DIAG_CTX.get()
    q = _q_label()
    audio_len = c.get("audio_bytes_len", "")
    retry = c.get("retry_attempt", "")
    fallback = c.get("fallback_index", "")
    _emit_terminal(
        f"[AI_DIAG] semantic attempt start | q={q} | model={model_id} | "
        f"retry={retry} | fallback={fallback} | audio_bytes={audio_len}"
    )
    logger.info(
        "[AI_DIAG] semantic attempt start %s model_id=%s",
        _fields({"model_id": model_id}),
        model_id,
    )
    ev = {"type": "semantic_attempt_start", "model_id": model_id}
    ev.update(_event_question_fields())
    _record_session_event(ev)


def log_semantic_success(*, model_id: str, elapsed_ms: int) -> None:
    q = _q_label()
    _emit_terminal(
        f"[AI_DIAG] semantic attempt success | q={q} | model={model_id} | "
        f"elapsed_ms={elapsed_ms}"
    )
    logger.info(
        "[AI_DIAG] semantic attempt success %s model_id=%s elapsed_ms=%s",
        _fields({"model_id": model_id, "elapsed_ms": elapsed_ms}),
        model_id,
        elapsed_ms,
    )
    ev = {"type": "semantic_attempt_success", "model_id": model_id}
    ev.update(_event_question_fields())
    _record_session_event(ev)


def log_semantic_failure(
    *,
    model_id: str,
    elapsed_ms: int,
    error_type: str,
    error_message: str,
) -> None:
    q = _q_label()
    _emit_terminal(
        f"[AI_DIAG] semantic attempt failure | q={q} | model={model_id} | "
        f"error={error_type} | elapsed_ms={elapsed_ms}"
    )
    logger.warning(
        "[AI_DIAG] semantic attempt failure %s model_id=%s elapsed_ms=%s "
        "error_type=%s error_message_short=%s",
        _fields({"model_id": model_id, "elapsed_ms": elapsed_ms}),
        model_id,
        elapsed_ms,
        error_type,
        _short_msg(error_message),
    )
    ev = {
        "type": "semantic_attempt_failure",
        "model_id": model_id,
        "error": error_type,
    }
    ev.update(_event_question_fields())
    _record_session_event(ev)
