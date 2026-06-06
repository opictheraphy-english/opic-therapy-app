"""Per-device ``user_progress.json`` read/write (no view / V2 persistence imports).

Kept separate from ``utils.local_profile`` so ``v2_flow_persistence`` can patch
disk snapshots without circular-import failures on ``save_user_progress``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent
_PROGRESS_DIR = _ROOT / "local_data" / "progress"


def _device_id() -> str:
    try:
        from utils.browser_session import get_or_create_device_id

        return get_or_create_device_id() or "_shared"
    except Exception:
        return "_shared"


def progress_file_path() -> Path:
    return _PROGRESS_DIR / f"{_device_id()}.json"


def ensure_progress_dir() -> None:
    _PROGRESS_DIR.mkdir(parents=True, exist_ok=True)


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_user_progress() -> Dict[str, Any]:
    ensure_progress_dir()
    path = progress_file_path()
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("user_progress read failed: %s", e)
        return {}


def save_user_progress(data: Dict[str, Any]) -> None:
    """Write the full per-device progress JSON (caller merges updates first)."""
    ensure_progress_dir()
    payload = dict(data)
    payload["updated_at"] = _iso_now()
    try:
        progress_file_path().write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    except Exception as e:
        logger.warning("user_progress write failed: %s", e)
