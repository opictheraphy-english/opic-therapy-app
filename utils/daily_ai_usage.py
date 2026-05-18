"""Daily AI analysis usage counter (local session + disk).

Disabled by default — API stability is handled via one-call mini reports,
429 non-retry policy, and fail-safe recovery instead of student quotas.
"""

from __future__ import annotations

from datetime import date
from typing import Any, MutableMapping, Tuple

import streamlit as st

from utils.local_profile import load_app_session, merge_app_session

ENABLE_DAILY_AI_LIMIT = False
DAILY_AI_LIMIT = 10
_SESSION_KEY = "daily_ai_usage_date"
_COUNT_KEY = "daily_ai_usage_count"


def is_daily_ai_limit_enabled() -> bool:
    return bool(ENABLE_DAILY_AI_LIMIT)


def _today_key() -> str:
    return date.today().isoformat()


def _hydrate_from_disk(ss: MutableMapping[str, Any]) -> None:
    if ss.get("_daily_ai_hydrated"):
        return
    disk = load_app_session()
    if disk.get("daily_ai_usage_date") == _today_key():
        ss[_SESSION_KEY] = disk["daily_ai_usage_date"]
        ss[_COUNT_KEY] = int(disk.get("daily_ai_usage_count") or 0)
    ss["_daily_ai_hydrated"] = True


def get_daily_ai_usage(ss: MutableMapping[str, Any] | None = None) -> Tuple[int, int]:
    """Return ``(used_today, limit)``."""
    if not ENABLE_DAILY_AI_LIMIT:
        return 0, DAILY_AI_LIMIT
    target = ss if ss is not None else st.session_state
    _hydrate_from_disk(target)
    if target.get(_SESSION_KEY) != _today_key():
        target[_SESSION_KEY] = _today_key()
        target[_COUNT_KEY] = 0
    used = int(target.get(_COUNT_KEY) or 0)
    return used, DAILY_AI_LIMIT


def format_daily_ai_usage_label(ss: MutableMapping[str, Any] | None = None) -> str:
    if not ENABLE_DAILY_AI_LIMIT:
        return ""
    used, limit = get_daily_ai_usage(ss)
    return f"오늘의 AI 코칭 {used}/{limit}회"


def try_consume_daily_ai_slot(ss: MutableMapping[str, Any] | None = None) -> Tuple[bool, str]:
    """Consume one slot when a Gemini-backed mini report / analysis starts."""
    if not ENABLE_DAILY_AI_LIMIT:
        return True, ""
    target = ss if ss is not None else st.session_state
    used, limit = get_daily_ai_usage(target)
    if used >= limit:
        return False, f"오늘 AI 분석 한도({limit}회)를 모두 사용했어요. 내일 다시 시도해 주세요."
    target[_COUNT_KEY] = used + 1
    merge_app_session(
        {
            "daily_ai_usage_date": _today_key(),
            "daily_ai_usage_count": int(target[_COUNT_KEY]),
        }
    )
    return True, ""
