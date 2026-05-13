"""최근 들은 패턴 (최대 10개) — local_data/recent_patterns.json."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from utils.local_profile import LOCAL_DIR, ensure_local_dir

logger = logging.getLogger(__name__)

RECENT_FILE = LOCAL_DIR / "recent_patterns.json"
MAX_RECENT = 10


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_recent_items() -> List[Dict[str, Any]]:
    ensure_local_dir()
    if not RECENT_FILE.is_file():
        return []
    try:
        data = json.loads(RECENT_FILE.read_text(encoding="utf-8"))
        items = data.get("items")
        if isinstance(items, list):
            return [x for x in items if isinstance(x, dict)]
    except Exception as e:
        logger.warning("recent_patterns read failed: %s", e)
    return []


def save_recent_items(items: List[Dict[str, Any]]) -> None:
    ensure_local_dir()
    payload = {"items": items[:MAX_RECENT], "updated_at": _iso_now()}
    try:
        RECENT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("recent_patterns write failed: %s", e)


def record_pattern_listen(pattern_id: str, pattern_line: str) -> None:
    if not pattern_id:
        return
    line = (pattern_line or "").strip()[:500]
    items = load_recent_items()
    items = [x for x in items if x.get("pattern_id") != pattern_id]
    items.insert(
        0,
        {
            "pattern_id": pattern_id,
            "pattern_line": line,
            "played_at": _iso_now(),
        },
    )
    save_recent_items(items)


def recent_lines_for_home() -> List[str]:
    """Display strings (pattern template lines)."""
    out: List[str] = []
    for x in load_recent_items():
        ln = (x.get("pattern_line") or "").strip()
        if ln:
            out.append(ln)
    return out[:MAX_RECENT]
