"""Persist mock V2 / mini mock V2 exam state to per-device disk.

Streamlit may drop ``session_state`` on websocket reconnect (Render log:
"Session ... is already connected! Connecting to a new session."). Legacy
real mock already snapshots ``mx``; isolated V2 flows previously lived only in
memory and were lost on reconnect.
"""

from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, List, MutableMapping, Optional

logger = logging.getLogger(__name__)

_B64_TAG = "__b64__"

# Session keys copied verbatim (JSON-safe after byte encoding).
_MINI_V2_SESSION_KEYS: tuple[str, ...] = (
    "mini_v2_step",
    "mini_v2_index",
    "mini_v2_answers",
    "mini_v2_recording_active",
    "mini_v2_last_saved_index",
    "mini_v2_report_result",
    "mini_v2_analysis_attempt_id",
    "mini_v2_analysis_started_at",
    "mini_v2_analysis_started_attempt",
    "mini_v2_analysis_finished_attempt",
    "mini_v2_audio_blobs",
    "mini_mock_v2_active",
    "active_learning_mode",
)

_MOCK_V2_SESSION_KEYS: tuple[str, ...] = (
    "mock_v2_step",
    "mock_v2_survey_results",
    "mock_v2_questions",
    "mock_v2_index",
    "mock_v2_answers",
    "mock_v2_audio_blobs",
    "mock_v2_started_at",
    "mock_v2_finished_at",
    "mock_v2_report",
)

_IN_PROGRESS_MINI_STEPS = frozenset({"question", "recording", "saved", "ready_report", "analyzing", "pending"})
_IN_PROGRESS_MOCK_STEPS = frozenset({"survey", "question", "saved", "complete", "report_pending"})


def _encode_value(value: Any) -> Any:
    if isinstance(value, bytes):
        return {_B64_TAG: base64.b64encode(value).decode("ascii")}
    if isinstance(value, bytearray):
        return {_B64_TAG: base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            out[str(k)] = _encode_value(v)
        return out
    if isinstance(value, list):
        return [_encode_value(v) for v in value]
    return value


def _decode_value(value: Any) -> Any:
    if isinstance(value, dict):
        if set(value.keys()) == {_B64_TAG}:
            raw = value.get(_B64_TAG)
            if isinstance(raw, str):
                try:
                    return base64.b64decode(raw, validate=False)
                except Exception:
                    return b""
        return {k: _decode_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode_value(v) for v in value]
    return value


def _mini_v2_in_memory(ss: MutableMapping[str, Any]) -> bool:
    try:
        from views.mini_mock_v2 import is_mini_mock_v2_active

        if is_mini_mock_v2_active():
            return True
    except Exception:
        pass
    answers = ss.get("mini_v2_answers")
    return isinstance(answers, list) and len(answers) > 0


def _mock_v2_in_memory(ss: MutableMapping[str, Any]) -> bool:
    if str(ss.get("mock_mode") or "").strip() == "mock_v2":
        return True
    step = str(ss.get("mock_v2_step") or "").strip()
    if step in _IN_PROGRESS_MOCK_STEPS and step != "survey":
        return True
    answers = ss.get("mock_v2_answers")
    if isinstance(answers, list) and len(answers) > 0:
        return True
    questions = ss.get("mock_v2_questions")
    return isinstance(questions, list) and len(questions) > 0


def _snapshot_meaningful_mini(snap: Dict[str, Any]) -> bool:
    if not isinstance(snap, dict) or not snap:
        return False
    answers = snap.get("mini_v2_answers")
    if isinstance(answers, list) and answers:
        return True
    step = str(snap.get("mini_v2_step") or "").strip()
    return step in _IN_PROGRESS_MINI_STEPS and step not in ("question",)


def _snapshot_meaningful_mock(snap: Dict[str, Any]) -> bool:
    if not isinstance(snap, dict) or not snap:
        return False
    answers = snap.get("mock_v2_answers")
    if isinstance(answers, list) and answers:
        return True
    questions = snap.get("mock_v2_questions")
    if isinstance(questions, list) and questions:
        return True
    step = str(snap.get("mock_v2_step") or "").strip()
    return step in _IN_PROGRESS_MOCK_STEPS and step not in ("survey",)


def _build_mini_v2_snapshot(ss: MutableMapping[str, Any]) -> Dict[str, Any]:
    if not _mini_v2_in_memory(ss):
        return {}
    snap: Dict[str, Any] = {}
    for key in _MINI_V2_SESSION_KEYS:
        if key not in ss:
            continue
        try:
            snap[key] = _encode_value(ss[key])
        except Exception:
            logger.debug("skip mini_v2 snapshot key %s", key)
    snap["_resume_hint"] = {
        "flow": "mini_mock_v2",
        "mock_mode": "mini_mock",
        "practice_portal_selected": True,
        "mock_page": "MINI_MOCK",
    }
    return snap


def _build_mock_v2_snapshot(ss: MutableMapping[str, Any]) -> Dict[str, Any]:
    if not _mock_v2_in_memory(ss):
        return {}
    snap: Dict[str, Any] = {}
    for key in _MOCK_V2_SESSION_KEYS:
        if key not in ss:
            continue
        try:
            snap[key] = _encode_value(ss[key])
        except Exception:
            logger.debug("skip mock_v2 snapshot key %s", key)
    snap["_resume_hint"] = {
        "flow": "mock_v2",
        "mock_mode": "mock_v2",
        "practice_portal_selected": True,
        "mock_page": "PICK",
    }
    return snap


def _apply_routing(ss: MutableMapping[str, Any], routing: Dict[str, Any]) -> None:
    """Apply resume navigation — only call when the user explicitly taps 이어하기."""
    if not isinstance(routing, dict):
        return
    if routing.get("practice_portal_selected"):
        ss["practice_portal_selected"] = True
    mock_mode = str(routing.get("mock_mode") or "").strip()
    if mock_mode:
        ss["mock_mode"] = mock_mode
    flow = str(routing.get("flow") or "").strip()
    if flow == "mini_mock_v2":
        ss["mini_mock_v2_active"] = True
        ss["active_learning_mode"] = "mini_mock_v2"
    mx = ss.get("mock")
    if isinstance(mx, dict):
        if mock_mode:
            mx["mock_mode"] = mock_mode
        mock_page = str(routing.get("mock_page") or "").strip()
        if mock_page:
            mx["mock_page"] = mock_page
            ss["mock_page"] = mock_page


def _apply_snapshot(ss: MutableMapping[str, Any], snap: Dict[str, Any]) -> None:
    """Restore exam payload only — never change ``page`` or URL routing."""
    for key, val in snap.items():
        if key.startswith("_"):
            continue
        try:
            decoded = _decode_value(val)
            if key == "mini_v2_audio_blobs" and isinstance(decoded, dict):
                decoded = _coerce_int_dict_keys(decoded)
            ss[key] = decoded
        except Exception:
            logger.debug("skip restore key %s", key)


def _coerce_int_dict_keys(raw: Dict[str, Any]) -> Dict[Any, Any]:
    out: Dict[Any, Any] = {}
    for k, v in raw.items():
        try:
            out[int(k)] = v
        except (TypeError, ValueError):
            out[k] = v
    return out


def v2_flow_signature_part(ss: MutableMapping[str, Any]) -> str:
    """Cheap fingerprint fragment for ``sync_user_progress``."""
    mini = ss.get("mini_v2_answers")
    mini_n = len(mini) if isinstance(mini, list) else 0
    mock = ss.get("mock_v2_answers")
    mock_n = len(mock) if isinstance(mock, list) else 0
    return "|".join(
        str(p)
        for p in (
            ss.get("mini_v2_step") or "",
            ss.get("mini_v2_index") or 0,
            mini_n,
            ss.get("mock_v2_step") or "",
            ss.get("mock_v2_index") or 0,
            mock_n,
            ss.get("mock_mode") or "",
            bool(ss.get("mini_mock_v2_active")),
        )
    )


def persist_v2_flows_now(ss: MutableMapping[str, Any]) -> None:
    """Force-write V2 snapshots (e.g. right after each saved answer)."""
    from utils.local_profile import load_user_progress, save_user_progress

    if not ss.get("entry_gate_completed"):
        return
    mini_snap = _build_mini_v2_snapshot(ss)
    mock_snap = _build_mock_v2_snapshot(ss)
    if not mini_snap and not mock_snap:
        return

    data = load_user_progress()
    if mini_snap:
        data["mini_v2_snapshot"] = mini_snap
    if mock_snap:
        data["mock_v2_snapshot"] = mock_snap
    save_user_progress(data)
    try:
        logger.info(
            "[V2_FLOW_PERSIST] mini=%s mock=%s answers=(%s,%s)",
            bool(mini_snap),
            bool(mock_snap),
            len(mini_snap.get("mini_v2_answers") or []) if mini_snap else 0,
            len(mock_snap.get("mock_v2_answers") or []) if mock_snap else 0,
        )
    except Exception:
        pass


def clear_mini_v2_disk_snapshot(ss: MutableMapping[str, Any]) -> None:
    _clear_disk_key(ss, "mini_v2_snapshot")


def clear_mock_v2_disk_snapshot(ss: MutableMapping[str, Any]) -> None:
    _clear_disk_key(ss, "mock_v2_snapshot")


def _clear_disk_key(ss: MutableMapping[str, Any], key: str) -> None:
    from utils.local_profile import load_user_progress, save_user_progress

    data = load_user_progress()
    if key not in data:
        return
    data.pop(key, None)
    save_user_progress(data)
    ss.pop("_progress_sig", None)


def maybe_restore_v2_flows_from_disk(ss: MutableMapping[str, Any]) -> bool:
    """Restore V2 exam state after a fresh Streamlit session. Returns True if restored."""
    if ss.get("_v2_flow_restored_from_disk"):
        return False
    ss["_v2_flow_restored_from_disk"] = True

    from utils.local_profile import load_user_progress

    data = load_user_progress()
    mini_snap = data.get("mini_v2_snapshot") or {}
    mock_snap = data.get("mock_v2_snapshot") or {}

    restored = False
    if _snapshot_meaningful_mini(mini_snap) and not _mini_v2_in_memory(ss):
        _apply_snapshot(ss, mini_snap)
        ss["mini_mock_v2_active"] = True
        ss.setdefault("active_learning_mode", "mini_mock_v2")
        restored = True
        logger.info(
            "[V2_FLOW_RESTORE] mini_mock_v2 step=%s index=%s answers=%s",
            ss.get("mini_v2_step"),
            ss.get("mini_v2_index"),
            len(ss.get("mini_v2_answers") or []),
        )

    if _snapshot_meaningful_mock(mock_snap) and not _mock_v2_in_memory(ss):
        _apply_snapshot(ss, mock_snap)
        restored = True
        logger.info(
            "[V2_FLOW_RESTORE] mock_v2 step=%s index=%s answers=%s",
            ss.get("mock_v2_step"),
            ss.get("mock_v2_index"),
            len(ss.get("mock_v2_answers") or []),
        )

    if restored:
        logger.info("[V2_FLOW_RESTORE] data_only=True (no forced nav)")
    return restored


def get_v2_resume_offer(
    ss: MutableMapping[str, Any],
    prog_disk: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    """Return resume metadata for the home card, or ``None`` if nothing to offer."""
    data = prog_disk if isinstance(prog_disk, dict) else {}
    mini_snap = data.get("mini_v2_snapshot") or {}
    mock_snap = data.get("mock_v2_snapshot") or {}

    if _mini_v2_in_memory(ss) or _snapshot_meaningful_mini(mini_snap):
        answers = ss.get("mini_v2_answers") if _mini_v2_in_memory(ss) else mini_snap.get("mini_v2_answers")
        if not isinstance(answers, list):
            answers = []
        try:
            idx = int(ss.get("mini_v2_index") if _mini_v2_in_memory(ss) else mini_snap.get("mini_v2_index") or 0)
        except (TypeError, ValueError):
            idx = 0
        return {
            "flow": "mini_mock_v2",
            "label": "5분 진단 모의고사",
            "completed": len(answers),
            "total": 3,
            "question_label": f"Q{min(idx + 1, 3)}",
        }

    if _mock_v2_in_memory(ss) or _snapshot_meaningful_mock(mock_snap):
        answers = ss.get("mock_v2_answers") if _mock_v2_in_memory(ss) else mock_snap.get("mock_v2_answers")
        if not isinstance(answers, list):
            answers = []
        try:
            idx = int(ss.get("mock_v2_index") if _mock_v2_in_memory(ss) else mock_snap.get("mock_v2_index") or 0)
        except (TypeError, ValueError):
            idx = 0
        return {
            "flow": "mock_v2",
            "label": "실전 모의고사",
            "completed": len(answers),
            "total": 15,
            "question_label": f"Q{min(idx + 1, 15)}",
        }
    return None


def resume_v2_flow(ss: MutableMapping[str, Any], *, flow: str) -> None:
    """User tapped 이어하기 — apply routing hints then caller should ``navigate_to``."""
    hint: Dict[str, Any]
    if flow == "mini_mock_v2":
        hint = {
            "flow": "mini_mock_v2",
            "mock_mode": "mini_mock",
            "practice_portal_selected": True,
            "mock_page": "MINI_MOCK",
        }
    elif flow == "mock_v2":
        hint = {
            "flow": "mock_v2",
            "mock_mode": "mock_v2",
            "practice_portal_selected": True,
            "mock_page": "PICK",
        }
    else:
        return
    _apply_routing(ss, hint)
    ss["_v2_user_resumed"] = True


def attach_v2_snapshots_to_progress_payload(
    ss: MutableMapping[str, Any],
    payload: Dict[str, Any],
) -> None:
    mini = _build_mini_v2_snapshot(ss)
    mock = _build_mock_v2_snapshot(ss)
    if mini:
        payload["mini_v2_snapshot"] = mini
    if mock:
        payload["mock_v2_snapshot"] = mock


def v2_flows_empty_in_memory(ss: MutableMapping[str, Any]) -> bool:
    return not _mini_v2_in_memory(ss) and not _mock_v2_in_memory(ss)


def disk_has_meaningful_v2_snapshot(data: Dict[str, Any]) -> bool:
    return _snapshot_meaningful_mini(data.get("mini_v2_snapshot") or {}) or _snapshot_meaningful_mock(
        data.get("mock_v2_snapshot") or {}
    )
