"""Reusable in-flight / cooldown guards for AI analysis & feedback request buttons.

Extracted from the Topic Practice V2 feedback guard (views/topic_practice_v2.py).
Callers pass a session-state mapping (e.g. ``st.session_state``) — no Streamlit import.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Mapping, MutableMapping, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Defaults aligned with Topic V2 short-feedback guard.
DEFAULT_STALE_SEC = 55.0
DEFAULT_COOLDOWN_BASE_SEC = 45
DEFAULT_COOLDOWN_STEP_SEC = 15
DEFAULT_COOLDOWN_MAX_SEC = 90
DEFAULT_MAX_ATTEMPTS = 4

COOLDOWN_EXEMPT_CATEGORIES = frozenset(
    {
        "api_key",
        "insufficient_text",
        "cooldown",
        "blocked",
    }
)

DEFAULT_BLOCK_IN_FLIGHT = (
    "요청을 처리 중입니다. 완료될 때까지 잠시만 기다려 주세요."
)
DEFAULT_BLOCK_COOLDOWN = (
    "서버가 잠시 바빠요. {remaining}초 후에 다시 시도해 주세요. "
    "연속으로 누르면 API 호출만 늘고 같은 오류가 반복될 수 있어요."
)
DEFAULT_BLOCK_MAX_ATTEMPTS = (
    "자동 분석 시도 횟수에 도달했어요. 잠시 후 다시 시도하거나 "
    "새 답변으로 요청해 보세요."
)

CooldownLabel = Union[str, Callable[[int], str]]


def key_in_flight(prefix: str) -> str:
    return f"{prefix}_in_flight"


def key_in_flight_at(prefix: str) -> str:
    return f"{prefix}_in_flight_at"


def key_cooldown_until(prefix: str) -> str:
    return f"{prefix}_cooldown_until"


def key_attempts(prefix: str) -> str:
    return f"{prefix}_attempts"


def key_user_notice(prefix: str) -> str:
    return f"{prefix}_user_notice"


def _now(now: Optional[float]) -> float:
    return time.time() if now is None else float(now)


def _attempt_counts(ss: Mapping[str, Any], prefix: str) -> dict[str, int]:
    raw = ss.get(key_attempts(prefix))
    if not isinstance(raw, dict):
        return {}
    out: dict[str, int] = {}
    for k, v in raw.items():
        try:
            out[str(k)] = max(0, int(v))
        except (TypeError, ValueError):
            continue
    return out


def _category_sets_cooldown(category: str) -> bool:
    return str(category or "").strip() not in COOLDOWN_EXEMPT_CATEGORIES


def _format_cooldown_label(cooldown_label: CooldownLabel, remaining_sec: int) -> str:
    if callable(cooldown_label):
        return cooldown_label(remaining_sec)
    return str(cooldown_label).format(remaining=remaining_sec)


def set_in_flight(
    ss: MutableMapping[str, Any],
    prefix: str,
    active: bool,
    *,
    now: Optional[float] = None,
) -> None:
    """Mark analysis/feedback request in progress, or clear the flag."""
    if active:
        ss[key_in_flight(prefix)] = True
        ss[key_in_flight_at(prefix)] = _now(now)
        return
    ss.pop(key_in_flight(prefix), None)
    ss.pop(key_in_flight_at(prefix), None)


def clear_stale_in_flight(
    ss: MutableMapping[str, Any],
    prefix: str,
    *,
    stale_sec: float = DEFAULT_STALE_SEC,
    now: Optional[float] = None,
) -> None:
    """Force-clear in_flight when timestamp is missing or older than *stale_sec*."""
    if not ss.get(key_in_flight(prefix)):
        return
    at_key = key_in_flight_at(prefix)
    try:
        started = float(ss.get(at_key) or 0.0)
    except (TypeError, ValueError):
        started = 0.0
    current = _now(now)
    if started <= 0 or (current - started) > float(stale_sec):
        try:
            logger.warning(
                "[ANALYSIS_GUARD] clearing stale in_flight prefix=%s started=%s age=%.1fs",
                prefix,
                started,
                current - started if started > 0 else -1.0,
            )
        except Exception:
            pass
        set_in_flight(ss, prefix, False)


def cooldown_remaining(
    ss: Mapping[str, Any],
    prefix: str,
    *,
    now: Optional[float] = None,
) -> int:
    """Seconds until cooldown expires (0 if none active)."""
    try:
        until = float(ss.get(key_cooldown_until(prefix)) or 0.0)
    except (TypeError, ValueError):
        until = 0.0
    return max(0, int(until - _now(now)))


def can_request(
    ss: MutableMapping[str, Any],
    prefix: str,
    entity_id: str,
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    stale_sec: float = DEFAULT_STALE_SEC,
    now: Optional[float] = None,
    block_in_flight: str = DEFAULT_BLOCK_IN_FLIGHT,
    block_cooldown: str = DEFAULT_BLOCK_COOLDOWN,
    block_max_attempts: str = DEFAULT_BLOCK_MAX_ATTEMPTS,
) -> Tuple[bool, Optional[str]]:
    """Return whether a new analysis/feedback request is allowed.

    Checks (in order): stale in_flight clear → in_flight → cooldown → attempt limit.
    """
    clear_stale_in_flight(ss, prefix, stale_sec=stale_sec, now=now)
    if ss.get(key_in_flight(prefix)):
        return False, block_in_flight
    rem = cooldown_remaining(ss, prefix, now=now)
    if rem > 0:
        return False, block_cooldown.format(remaining=rem)
    entity = str(entity_id or "default")
    n = _attempt_counts(ss, prefix).get(entity, 0)
    if n >= int(max_attempts):
        return False, block_max_attempts
    return True, None


def register_failure(
    ss: MutableMapping[str, Any],
    prefix: str,
    entity_id: str,
    category: str,
    *,
    base_cooldown: int = DEFAULT_COOLDOWN_BASE_SEC,
    step: int = DEFAULT_COOLDOWN_STEP_SEC,
    max_cooldown: int = DEFAULT_COOLDOWN_MAX_SEC,
    now: Optional[float] = None,
) -> int:
    """Increment failure count; set cooldown unless *category* is exempt. Returns new count."""
    entity = str(entity_id or "default")
    counts = _attempt_counts(ss, prefix)
    n = counts.get(entity, 0) + 1
    counts[entity] = n
    ss[key_attempts(prefix)] = counts
    if not _category_sets_cooldown(category):
        return n
    cd = min(
        int(max_cooldown),
        int(base_cooldown) + int(step) * max(0, n - 1),
    )
    ss[key_cooldown_until(prefix)] = _now(now) + cd
    return n


def clear_guard(
    ss: MutableMapping[str, Any],
    prefix: str,
    entity_id: str,
) -> None:
    """Clear cooldown, notice, and attempt count for *entity_id* after success."""
    ss.pop(key_cooldown_until(prefix), None)
    ss.pop(key_user_notice(prefix), None)
    counts = _attempt_counts(ss, prefix)
    counts.pop(str(entity_id or "default"), None)
    ss[key_attempts(prefix)] = counts


def reset_guard(ss: MutableMapping[str, Any], prefix: str) -> None:
    """Reset all guard state for *prefix* (e.g. on screen entry)."""
    ss.pop(key_cooldown_until(prefix), None)
    ss.pop(key_user_notice(prefix), None)
    set_in_flight(ss, prefix, False)
    ss[key_attempts(prefix)] = {}


def button_state(
    ss: MutableMapping[str, Any],
    prefix: str,
    entity_id: str,
    *,
    labels: Mapping[str, CooldownLabel],
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    stale_sec: float = DEFAULT_STALE_SEC,
    now: Optional[float] = None,
) -> Tuple[bool, str]:
    """Return ``(disabled, label)`` for a request/retry button.

    *labels* must include keys: ``in_flight``, ``cooldown``, ``maxed``, ``idle``.
    ``cooldown`` may be a format string with ``{remaining}`` or ``callable(int) -> str``.
    """
    clear_stale_in_flight(ss, prefix, stale_sec=stale_sec, now=now)
    if ss.get(key_in_flight(prefix)):
        return True, str(labels["in_flight"])
    rem = cooldown_remaining(ss, prefix, now=now)
    if rem > 0:
        return True, _format_cooldown_label(labels["cooldown"], rem)
    entity = str(entity_id or "default")
    n = _attempt_counts(ss, prefix).get(entity, 0)
    if n >= int(max_attempts):
        return True, str(labels["maxed"])
    return False, str(labels["idle"])
