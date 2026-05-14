"""Local disk profile: guest id, entry gate flags, mock-exam progress JSON (no cloud auth)."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, MutableMapping, Optional

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DIR = _ROOT / "local_data"
APP_SESSION_FILE = LOCAL_DIR / "app_session.json"
USER_PROGRESS_FILE = LOCAL_DIR / "user_progress.json"

MOCK_SNAPSHOT_KEYS = (
    "results",
    "exam_finished",
    "analytics_cache",
    "overall_estimated_level",
    "final_report_generated",
    "current_idx",
    "mock_page",
    "survey_results",
    "current_exam",
    "exam",
)


def ensure_local_dir() -> None:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_guest_id() -> str:
    return f"guest_{uuid.uuid4().hex[:12]}"


def load_app_session() -> Dict[str, Any]:
    ensure_local_dir()
    if not APP_SESSION_FILE.is_file():
        return {}
    try:
        return json.loads(APP_SESSION_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("app_session read failed: %s", e)
        return {}


def save_app_session(data: Dict[str, Any]) -> None:
    ensure_local_dir()
    payload = dict(data)
    payload["updated_at"] = _iso_now()
    APP_SESSION_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def hydrate_entry_session(ss: MutableMapping[str, Any]) -> None:
    """Restore entry_gate_completed, guest_id, user_mode from disk."""
    disk = load_app_session()
    if disk.get("entry_gate_completed"):
        ss["entry_gate_completed"] = True
    if disk.get("guest_id"):
        ss["guest_id"] = disk["guest_id"]
    if disk.get("user_mode"):
        ss["user_mode"] = disk["user_mode"]


def complete_entry_guest(ss: MutableMapping[str, Any]) -> None:
    ss["entry_gate_completed"] = True
    ss["user_mode"] = "guest"
    ss.setdefault("guest_id", new_guest_id())
    save_app_session(
        {
            "entry_gate_completed": True,
            "user_mode": "guest",
            "guest_id": ss["guest_id"],
        }
    )


def complete_entry_login_placeholder(ss: MutableMapping[str, Any]) -> None:
    """Login UI placeholder — still uses local guest id for progress until OAuth exists."""
    ss["entry_gate_completed"] = True
    ss["user_mode"] = "login_placeholder"
    ss.setdefault("guest_id", new_guest_id())
    save_app_session(
        {
            "entry_gate_completed": True,
            "user_mode": "login_placeholder",
            "guest_id": ss["guest_id"],
        }
    )


def _serialize_mock(mx: Dict[str, Any]) -> Dict[str, Any]:
    snap: Dict[str, Any] = {}
    for k in MOCK_SNAPSHOT_KEYS:
        if k not in mx:
            continue
        try:
            json.dumps(mx[k], default=str)
            snap[k] = mx[k]
        except Exception:
            logger.debug("skip snapshot key %s (not serializable)", k)
    return snap


def _progress_signature(ss: MutableMapping[str, Any]) -> str:
    """Cheap fingerprint over the slices that actually drive user_progress.json."""
    mx = ss.get("mock") if isinstance(ss.get("mock"), dict) else {}
    pd = ss.get("pattern") if isinstance(ss.get("pattern"), dict) else {}
    return "|".join(
        str(part)
        for part in (
            ss.get("guest_id") or "",
            ss.get("user_mode") or "",
            mx.get("mock_page") or "",
            mx.get("current_idx") or 0,
            len(mx.get("results") or []),
            bool(mx.get("exam_finished")),
            bool(mx.get("analytics_cache")),
            (pd or {}).get("_pattern_last_visit_at") or "",
        )
    )


def sync_user_progress(ss: MutableMapping[str, Any]) -> None:
    """Write user_progress.json only when meaningful state has changed.

    Streamlit reruns the script on every interaction. Rewriting the same JSON
    each rerun is the most expensive piece of the home/pattern hot path on
    Render Starter, so we short-circuit on an unchanged signature.
    """
    if not ss.get("entry_gate_completed"):
        return

    sig = _progress_signature(ss)
    if ss.get("_progress_sig") == sig:
        return

    ensure_local_dir()
    mx = ss.get("mock") or {}
    if not isinstance(mx, dict):
        mx = {}
    pd = ss.get("pattern") or {}
    pattern_meta: Dict[str, Any] = {}
    if isinstance(pd, dict):
        pattern_meta["last_visit_at"] = pd.get("_pattern_last_visit_at")

    payload: Dict[str, Any] = {
        "guest_id": ss.get("guest_id"),
        "user_mode": ss.get("user_mode"),
        "updated_at": _iso_now(),
        "mock_snapshot": _serialize_mock(mx),
        "pattern_progress": pattern_meta,
    }

    last_at = payload["updated_at"]
    results = mx.get("results") or []
    if results:
        last = results[-1]
        res = last.get("result") or {}
        lv = None
        agg = mx.get("analytics_cache") or {}
        if isinstance(agg, dict):
            lv = agg.get("overall_display")
        lv = lv or res.get("estimated_level_display") or res.get("estimated_level")
        payload["last_activity_card"] = {
            "label": "최근 모의고사",
            "estimated_level": lv,
            "topic": last.get("topic"),
            "question_id": last.get("q_id"),
            "activity_at": last_at,
            "exam_finished": bool(mx.get("exam_finished")),
            "questions_done": len(results),
        }

    try:
        USER_PROGRESS_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        ss["_progress_sig"] = sig
    except Exception as e:
        logger.warning("user_progress write failed: %s", e)


def load_user_progress() -> Dict[str, Any]:
    ensure_local_dir()
    if not USER_PROGRESS_FILE.is_file():
        return {}
    try:
        return json.loads(USER_PROGRESS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("user_progress read failed: %s", e)
        return {}


def maybe_restore_mock_from_disk(ss: MutableMapping[str, Any]) -> None:
    """If mock results are empty but disk has a snapshot, restore into mock namespace."""
    if ss.get("_mock_restored_from_disk"):
        return
    data = load_user_progress()
    snap = data.get("mock_snapshot") or {}
    if not snap:
        ss["_mock_restored_from_disk"] = True
        return
    mx = ss.get("mock")
    if not isinstance(mx, dict):
        return
    if mx.get("results"):
        ss["_mock_restored_from_disk"] = True
        return
    for k in MOCK_SNAPSHOT_KEYS:
        if k in snap:
            mx[k] = snap[k]
    ss["_mock_restored_from_disk"] = True
    logger.info("Restored mock snapshot from local_data")


def human_time_ago(iso_ts: Optional[str]) -> str:
    if not iso_ts:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        sec = int(delta.total_seconds())
        if sec < 60:
            return "방금 전"
        if sec < 3600:
            return f"{sec // 60}분 전"
        if sec < 86400:
            return f"{sec // 3600}시간 전"
        return f"{sec // 86400}일 전"
    except Exception:
        return "—"


def touch_pattern_visit(ss: MutableMapping[str, Any]) -> None:
    pd = ss.get("pattern")
    if not isinstance(pd, dict):
        return
    pd["_pattern_last_visit_at"] = _iso_now()
