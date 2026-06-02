"""Step 3 — connect report completion to the user's saved history.

Each ``save_*`` helper is called once at a report's *completion transition*
(button handler / analysis-once), never inside a passive render. To stay safe
against Streamlit reruns we also keep a per-report session guard so the same
report is never inserted twice, while a genuinely new attempt (new signature)
saves a fresh append-only row.

Everything fails soft: guests are skipped, and any error is logged and swallowed
so saving history can never block the learning flow.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import streamlit as st

from services.history_store import save_history_record

logger = logging.getLogger(__name__)

_SCORE_AXES = (
    "fluency",
    "delivery",
    "grammar",
    "vocabulary",
    "coherence",
    "response_amount",
)


def _is_logged_in() -> bool:
    return bool(st.session_state.get("user_authenticated"))


def _json_safe(obj: Any) -> Any:
    """Coerce any report payload into JSON-serializable form for JSONB storage."""
    try:
        return json.loads(json.dumps(obj, default=str, ensure_ascii=False))
    except Exception:
        return {}


def _avg_score(breakdown: Any) -> Optional[float]:
    """Average of the numeric score axes, if a breakdown dict is present."""
    if not isinstance(breakdown, dict):
        return None
    vals: List[float] = []
    for axis in _SCORE_AXES:
        v = breakdown.get(axis)
        if isinstance(v, dict):
            v = v.get("score")
        try:
            if v is not None:
                vals.append(float(v))
        except (TypeError, ValueError):
            continue
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)


def _save_once(
    guard_key: str,
    *,
    practice_type: str,
    content: Dict[str, Any],
    subtype: Optional[str] = None,
    title: Optional[str] = None,
    overall_level: Optional[str] = None,
    score: Optional[float] = None,
) -> None:
    if not _is_logged_in():
        return
    if st.session_state.get(guard_key):
        return
    # Optimistically set the guard so concurrent reruns don't double-insert; if
    # the save fails we clear it so a later rerun can retry.
    st.session_state[guard_key] = True
    try:
        saved = save_history_record(
            practice_type=practice_type,
            content=_json_safe(content or {}),
            subtype=subtype,
            title=title,
            overall_level=overall_level,
            score=score,
        )
    except Exception:
        logger.exception("[HISTORY_SYNC] save failed guard=%s", guard_key)
        saved = None
    if not saved:
        st.session_state[guard_key] = False
    else:
        logger.info("[HISTORY_SYNC] saved %s/%s", practice_type, subtype)


def save_mock_v2_report(result: Dict[str, Any], *, sig: str) -> None:
    """Full 15-question mock (mock_v2 pipeline) report."""
    if not isinstance(result, dict) or not result.get("ok"):
        return
    _save_once(
        f"_hist_saved_mock_v2_{sig}",
        practice_type="mock_exam",
        subtype="mock_v2",
        title="실전 모의고사 15문항",
        overall_level=str(result.get("overall_level") or "") or None,
        score=_avg_score(result.get("score_breakdown")),
        content=result,
    )


def save_real_mock_report(
    *,
    sig: str,
    overall_level: str,
    score_breakdown: Any,
    content: Dict[str, Any],
) -> None:
    """Live 실전 모의고사 (real_mock pipeline) final report."""
    _save_once(
        f"_hist_saved_real_mock_{sig}",
        practice_type="mock_exam",
        subtype="real_mock",
        title="실전 모의고사 15문항",
        overall_level=str(overall_level or "") or None,
        score=_avg_score(score_breakdown),
        content=content or {},
    )


def save_topic_report(report: Dict[str, Any], *, topic_title: str, sig: str) -> None:
    """Topic practice full report."""
    if not isinstance(report, dict):
        return
    _save_once(
        f"_hist_saved_topic_{sig}",
        practice_type="topic_practice",
        subtype="topic_practice",
        title=str(topic_title or "주제별 연습") or "주제별 연습",
        overall_level=str(report.get("overall_level") or "") or None,
        score=_avg_score(report.get("score_breakdown")),
        content=report,
    )


def save_script_diagnose(result: Dict[str, Any], *, question: str, sig: str) -> None:
    """Script coaching — diagnose result."""
    if not isinstance(result, dict) or not result.get("ok"):
        return
    title = str(question or "").strip() or "스크립트 첨삭"
    if len(title) > 80:
        title = title[:77] + "…"
    _save_once(
        f"_hist_saved_script_diag_{sig}",
        practice_type="script_coaching",
        subtype="diagnose",
        title=title,
        overall_level=str(result.get("overall_level") or "") or None,
        score=_avg_score(result.get("score_breakdown")),
        content=result,
    )


def save_script_upgrade(result: Dict[str, Any], *, sig: str) -> None:
    """Script coaching — upgrade result."""
    if not isinstance(result, dict) or not result.get("ok"):
        return
    target = str(result.get("target_level") or "").strip()
    title = f"스크립트 업그레이드 → {target}" if target else "스크립트 업그레이드"
    _save_once(
        f"_hist_saved_script_up_{sig}",
        practice_type="script_coaching",
        subtype="upgrade",
        title=title,
        overall_level=str(result.get("target_level") or "") or None,
        score=None,
        content=result,
    )
