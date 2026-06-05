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
# Per-browser subdirectories. The app is a single server process shared by every
# student, so all on-disk state MUST be keyed by a per-browser device id — never
# a single global file (that is what previously leaked one user's login/progress
# into everyone else's session).
_SESSIONS_DIR = LOCAL_DIR / "sessions"
_PROGRESS_DIR = LOCAL_DIR / "progress"


def _device_id() -> str:
    """Per-browser id used to key disk files. Falls back to ``_shared`` only when
    no Streamlit/browser context exists (e.g. scripts/tests) — never in a real
    request, where the cookie-backed id is always available."""
    try:
        from utils.browser_session import get_or_create_device_id

        did = get_or_create_device_id()
        return did or "_shared"
    except Exception:
        return "_shared"


def _app_session_file() -> Path:
    return _SESSIONS_DIR / f"{_device_id()}.json"


def _user_progress_file() -> Path:
    return _PROGRESS_DIR / f"{_device_id()}.json"

MOCK_SNAPSHOT_KEYS = (
    "results",
    "exam_finished",
    "analytics_cache",
    "overall_estimated_level",
    "final_report_generated",
    "attempt_no",
    "completed_attempts",
    "survey_completed",
    "current_idx",
    "mock_page",
    "survey_results",
    "current_exam",
    "exam",
    # Resume-mode metadata — populated by views/mock_exam.py.
    "exam_started_at",
    "exam_last_seen_at",
)


# Legacy single-file paths (pre per-device isolation). These were shared by ALL
# users and leaked login identity/progress across browsers — purge them once per
# process so no stale secret lingers on the deployed server's disk.
_LEGACY_APP_SESSION = LOCAL_DIR / "app_session.json"
_LEGACY_USER_PROGRESS = LOCAL_DIR / "user_progress.json"
_legacy_purged = False


def _purge_legacy_global_files() -> None:
    global _legacy_purged
    if _legacy_purged:
        return
    _legacy_purged = True
    for path in (_LEGACY_APP_SESSION, _LEGACY_USER_PROGRESS):
        try:
            if path.is_file():
                path.unlink()
                logger.warning("[SECURITY] purged legacy shared session file: %s", path.name)
        except Exception as e:  # pragma: no cover - best effort
            logger.warning("legacy purge failed for %s: %s", path.name, e)


def ensure_local_dir() -> None:
    LOCAL_DIR.mkdir(parents=True, exist_ok=True)
    _SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    _PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    _purge_legacy_global_files()


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def iso_now() -> str:
    """Public ISO-8601 UTC timestamp helper (used by view layer)."""
    return _iso_now()


def new_guest_id() -> str:
    return f"guest_{uuid.uuid4().hex[:12]}"


def load_app_session() -> Dict[str, Any]:
    ensure_local_dir()
    path = _app_session_file()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("app_session read failed: %s", e)
        return {}


def save_app_session(data: Dict[str, Any]) -> None:
    ensure_local_dir()
    payload = dict(data)
    payload["updated_at"] = _iso_now()
    _app_session_file().write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def merge_app_session(updates: Dict[str, Any]) -> Dict[str, Any]:
    """Merge ``updates`` into on-disk app session and persist (full JSON)."""
    base = load_app_session()
    base.update(updates)
    save_app_session(base)
    return base


def hydrate_entry_session(ss: MutableMapping[str, Any]) -> None:
    """Restore entry gate, guest id, user_mode, onboarding + light prefs from disk.

    Called from ``app.py`` on every script rerun. We short-circuit once
    we've hydrated for this session — the entry payload is written
    exclusively by ``complete_entry_*`` helpers which also update
    ``ss`` directly, so a stale disk read can never overwrite a fresher
    in-memory value. Skipping the JSON read on subsequent reruns trims
    one disk hit per tap on the bottom nav.
    """
    if ss.get("_entry_session_hydrated"):
        return
    disk = load_app_session()
    if disk.get("entry_gate_completed"):
        ss["entry_gate_completed"] = True
    if disk.get("guest_id"):
        ss["guest_id"] = disk["guest_id"]
    if disk.get("user_mode"):
        ss["user_mode"] = disk["user_mode"]

    # Onboarding: new installs get ``onboarding_completed: False`` from
    # ``complete_entry_*``. Legacy profiles (entry done before this field
    # existed) are treated as already onboarded once.
    if disk.get("entry_gate_completed"):
        if "onboarding_completed" in disk:
            ss["onboarding_completed"] = bool(disk["onboarding_completed"])
        else:
            ss["onboarding_completed"] = True
            merge_app_session({"onboarding_completed": True})
    else:
        ss["onboarding_completed"] = bool(disk.get("onboarding_completed", False))

    if disk.get("target_level"):
        ss["target_level"] = str(disk["target_level"])
    if disk.get("current_level_label"):
        ss["current_level_label"] = str(disk["current_level_label"])

    ss.setdefault("onboarding_step", 1)
    ss["_entry_session_hydrated"] = True


def complete_entry_guest(ss: MutableMapping[str, Any]) -> None:
    ss["entry_gate_completed"] = True
    ss["user_mode"] = "guest"
    ss.setdefault("guest_id", new_guest_id())
    ss["onboarding_completed"] = False
    ss["onboarding_step"] = 1
    merge_app_session(
        {
            "entry_gate_completed": True,
            "user_mode": "guest",
            "guest_id": ss["guest_id"],
            "onboarding_completed": False,
        }
    )


def complete_entry_login_placeholder(ss: MutableMapping[str, Any]) -> None:
    """Login UI placeholder — still uses local guest id for progress until OAuth exists."""
    ss["entry_gate_completed"] = True
    ss["user_mode"] = "login_placeholder"
    ss.setdefault("guest_id", new_guest_id())
    ss["onboarding_completed"] = False
    ss["onboarding_step"] = 1
    merge_app_session(
        {
            "entry_gate_completed": True,
            "user_mode": "login_placeholder",
            "guest_id": ss["guest_id"],
            "onboarding_completed": False,
        }
    )


def persist_onboarding_completion(
    ss: MutableMapping[str, Any],
    *,
    target_level: Optional[str] = None,
    current_level_label: Optional[str] = None,
    skip_preferences: bool = False,
) -> None:
    """Mark onboarding done; optionally persist goal / level labels (local JSON only)."""
    ss["onboarding_completed"] = True
    ss["onboarding_step"] = 1
    updates: Dict[str, Any] = {"onboarding_completed": True}
    if not skip_preferences:
        if target_level:
            ss["target_level"] = target_level
            updates["target_level"] = target_level
        if current_level_label:
            ss["current_level_label"] = current_level_label
            updates["current_level_label"] = current_level_label
    merge_app_session(updates)


def reset_onboarding_for_rerun(ss: MutableMapping[str, Any]) -> None:
    """Re-show onboarding on next paint (Settings / debug)."""
    ss["onboarding_completed"] = False
    ss["onboarding_step"] = 1
    merge_app_session({"onboarding_completed": False})


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
    """Cheap fingerprint over the slices that actually drive user_progress.json.

    Includes ``len(current_exam)`` and ``exam_started_at`` so the very first
    save (right after ``시험지 생성``) lands on disk even before the user
    answers a question — that's what powers the home "이어하기" card.
    """
    mx = ss.get("mock") if isinstance(ss.get("mock"), dict) else {}
    pd = ss.get("pattern") if isinstance(ss.get("pattern"), dict) else {}
    # Prefix-matched completed count (not raw ``len(results)``) so duplicate
    # rows from historical bugs do not hide progress updates from the
    # signature — the next sync still fires after ``reconcile_mock_exam_pointer``.
    from utils.exam_state import count_completed_exam_prefix

    answered_prefix = count_completed_exam_prefix(mx) if isinstance(mx, dict) else 0
    from utils.v2_flow_persistence import v2_flow_signature_part

    return "|".join(
        str(part)
        for part in (
            ss.get("guest_id") or "",
            ss.get("user_mode") or "",
            mx.get("mock_page") or "",
            mx.get("current_idx") or 0,
            len(mx.get("results") or []),
            answered_prefix,
            len(mx.get("current_exam") or []),
            bool(mx.get("exam_finished")),
            bool(mx.get("analytics_cache")),
            str(mx.get("attempt_no") or 1),
            str(len(mx.get("completed_attempts") or [])),
            mx.get("exam_started_at") or "",
            (pd or {}).get("_pattern_last_visit_at") or "",
            v2_flow_signature_part(ss),
        )
    )


def _mx_is_default_empty(mx: Dict[str, Any]) -> bool:
    """True iff the mock namespace looks freshly initialized.

    A "default-empty" mx is what ``ensure_mock`` produces on a brand-new
    Streamlit session — no exam generated, no answers, no survey. We use
    this check in :func:`sync_user_progress` to prevent the **fresh-session
    clobber bug**: if a returning user opens the app on HOME, their disk
    snapshot is valid but ``mx`` is still empty for the first paint;
    writing the empty signature would overwrite their resumable exam
    before disk-restore had a chance to run.

    In-flight recording / recovery / saved takes are **not** empty: never
    treat them as safe-to-write-through to disk over a meaningful snapshot.
    """
    if not isinstance(mx, dict):
        return True
    if mx.get("audio_bytes"):
        return False
    if mx.get("pending_recovery"):
        return False
    if mx.get("recordings"):
        return False
    if mx.get("current_exam"):
        return False
    if mx.get("results"):
        return False
    if mx.get("survey_results"):
        return False
    if mx.get("analytics_cache"):
        return False
    if mx.get("exam_started_at"):
        return False
    return True


def _snapshot_is_meaningful(snap: Dict[str, Any]) -> bool:
    """True iff the on-disk snapshot has data worth protecting."""
    if not isinstance(snap, dict):
        return False
    if snap.get("current_exam"):
        return True
    if snap.get("results"):
        return True
    if snap.get("exam_finished"):
        return True
    return False


def sync_user_progress(ss: MutableMapping[str, Any]) -> None:
    """Write user_progress.json only when meaningful state has changed.

    Streamlit reruns the script on every interaction. Rewriting the same JSON
    each rerun is the most expensive piece of the home/pattern hot path on
    Render Starter, so we short-circuit on an unchanged signature.

    Anti-clobber guard
    ------------------
    On a fresh Streamlit session the in-memory ``mx`` starts default-empty.
    If the user is sitting on HOME (a page where the eager disk-restore
    in ``app.py`` may not have populated ``mx`` yet), an unconditional
    write would replace the on-disk snapshot with empty state and the
    user's resumable exam would silently disappear. We refuse to write
    when ``mx`` is default-empty but disk still holds a meaningful
    snapshot — disk wins by inaction.
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

    # Anti-clobber: if in-memory state is empty but disk has real exam data,
    # the in-memory state has not yet been hydrated. Skip this write so the
    # snapshot survives until ``maybe_restore_mock_from_disk`` populates mx.
    # The next rerun (after restore) will write a faithful signature.
    from utils.v2_flow_persistence import (
        attach_v2_snapshots_to_progress_payload,
        disk_has_meaningful_v2_snapshot,
        v2_flows_empty_in_memory,
    )

    if _mx_is_default_empty(mx) and v2_flows_empty_in_memory(ss):
        disk = load_user_progress()
        if _snapshot_is_meaningful(disk.get("mock_snapshot") or {}) or disk_has_meaningful_v2_snapshot(
            disk
        ):
            logger.info(
                "sync_user_progress: skip write (mx empty, disk has live snapshot) "
                "(idx=%s results=%s exam=%s audio=%s)",
                mx.get("current_idx"),
                len(mx.get("results") or []),
                len(mx.get("current_exam") or []),
                bool(mx.get("audio_bytes")),
            )
            return
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
    attach_v2_snapshots_to_progress_payload(ss, payload)

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
        _user_progress_file().write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        ss["_progress_sig"] = sig
        logger.debug(
            "sync_user_progress: wrote user_progress.json (sig_prefix=%s)",
            sig[:120],
        )
    except Exception as e:
        logger.warning("user_progress write failed: %s", e)


def load_user_progress() -> Dict[str, Any]:
    ensure_local_dir()
    path = _user_progress_file()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("user_progress read failed: %s", e)
        return {}


def save_user_progress(data: Dict[str, Any]) -> None:
    """Write the full per-device progress JSON (caller merges updates first)."""
    ensure_local_dir()
    payload = dict(data)
    payload["updated_at"] = _iso_now()
    try:
        _user_progress_file().write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("user_progress write failed: %s", e)


def _apply_snapshot(mx: Dict[str, Any], snap: Dict[str, Any], *, preserve_mock_page: bool) -> None:
    """Copy snapshot keys into ``mx`` in place.

    When ``preserve_mock_page`` is set we keep whatever ``mx["mock_page"]``
    the caller already set (e.g. from the ``?mock=TEST`` URL param). This
    is the critical fix for the historical "이어하기 ▶ SURVEY" bug: the
    URL's navigational intent always beats the snapshot's stale value.
    """
    requested_page = mx.get("mock_page") if preserve_mock_page else None
    for k in MOCK_SNAPSHOT_KEYS:
        if k in snap:
            mx[k] = snap[k]
    if preserve_mock_page and requested_page:
        mx["mock_page"] = requested_page


def maybe_restore_mock_from_disk(ss: MutableMapping[str, Any]) -> None:
    """If mock state is empty but disk has a snapshot, restore into mock namespace.

    Runs at most once per session (gated by ``_mock_restored_from_disk``).
    Skipped entirely when ``_suppress_disk_restore`` is set — that flag is
    raised by ``utils.exam_state.reset_exam_state`` to make sure that a user
    who explicitly chose "처음부터 다시" doesn't get the previous in-progress
    exam silently rehydrated on the very next rerun.

    The snapshot's ``mock_page`` is intentionally **not** copied over a
    page the URL has already set — see :func:`_apply_snapshot`.
    """
    if ss.get("_mock_restored_from_disk"):
        return
    if ss.get("_suppress_disk_restore"):
        # An explicit reset is in flight this session. Mark the restore as
        # done so subsequent reruns don't loop back through here either.
        ss["_mock_restored_from_disk"] = True
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
        # Already mid-session — don't clobber fresher in-memory state.
        ss["_mock_restored_from_disk"] = True
        return
    _apply_snapshot(mx, snap, preserve_mock_page=True)
    from utils.exam_state import reconcile_mock_exam_pointer

    reconcile_mock_exam_pointer(mx)
    ss["_mock_restored_from_disk"] = True
    logger.info("Restored mock snapshot from local_data")


def force_restore_mock_from_disk(mx: Dict[str, Any]) -> bool:
    """Last-ditch restore used by ``_render_test`` when ``current_exam`` is
    unexpectedly empty inside the TEST view.

    Unlike :func:`maybe_restore_mock_from_disk`, this:
      * does **not** check the once-per-session guard, and
      * does **not** require ``mx["results"]`` to be empty.

    It only writes the keys that are present and non-empty on disk, so it
    can never *delete* an in-flight value. Returns ``True`` iff the disk
    had a non-empty ``current_exam`` we could put back.

    Caller is expected to ``st.rerun()`` after a successful restore so the
    view paints with the restored state instead of the partial mx.
    """
    if not isinstance(mx, dict):
        return False
    data = load_user_progress()
    snap = data.get("mock_snapshot") or {}
    if not isinstance(snap.get("current_exam"), list) or not snap["current_exam"]:
        return False
    # Preserve whatever mock_page the caller had (TEST in the usual case)
    # — same rationale as maybe_restore_mock_from_disk.
    _apply_snapshot(mx, snap, preserve_mock_page=True)
    from utils.exam_state import reconcile_mock_exam_pointer

    reconcile_mock_exam_pointer(mx)
    logger.warning(
        "force_restore_mock_from_disk: rehydrated current_exam (idx=%s, results=%d)",
        mx.get("current_idx"),
        len(mx.get("results") or []),
    )
    return True


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
