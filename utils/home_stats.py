"""Home dashboard stats — aggregate practice_history for the logged-in user."""

from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import streamlit as st

from services.history_store import list_history_stats_rows

logger = logging.getLogger(__name__)

LEVEL_ORDER: Tuple[str, ...] = ("NL", "NM", "NH", "IL", "IM1", "IM2", "IM3", "IH", "AL")
_VALID_LEVELS = frozenset(LEVEL_ORDER)

_CACHE_KEY = "home_stats_cache"
_CACHE_AT_KEY = "home_stats_cache_at"
_CACHE_UID_KEY = "home_stats_cache_uid"
_CACHE_TTL_SEC = 600

_KST = timezone(timedelta(hours=9))


def invalidate_home_stats_cache(ss: Any) -> None:
    """Clear cached home stats (call after a new history row is saved)."""
    ss.pop(_CACHE_KEY, None)
    ss.pop(_CACHE_AT_KEY, None)
    ss.pop(_CACHE_UID_KEY, None)


def resolve_target_level(ss: Any) -> str:
    """Map session difficulty to OPIc target token (default IH)."""
    try:
        diff = int(ss.get("difficulty") or ss.get("settings", {}).get("difficulty") or 5)
    except (TypeError, ValueError):
        diff = 5
    return "AL" if diff >= 6 else "IH"


def _parse_kst_date(created_at: Any) -> Optional[date]:
    raw = str(created_at or "").strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(_KST).date()
    except Exception:
        return None


def _normalize_level(token: Any) -> Optional[str]:
    lv = str(token or "").strip().upper()
    if lv in _VALID_LEVELS:
        return lv
    return None


def _answer_count_for_row(row: Dict[str, Any]) -> int:
    practice_type = str(row.get("practice_type") or "").strip()
    content = row.get("content")
    if not isinstance(content, dict):
        content = {}

    if practice_type == "script_coaching":
        return 1

    if practice_type == "topic_practice":
        ac = content.get("answers_count")
        if isinstance(ac, (int, float)) and int(ac) > 0:
            return int(ac)
        results = content.get("results")
        if isinstance(results, list) and results:
            return len(results)
        return 3

    if practice_type == "mock_exam":
        vac = content.get("valid_answers_count")
        if isinstance(vac, (int, float)) and int(vac) > 0:
            return int(vac)
        ac = content.get("answers_count")
        if isinstance(ac, (int, float)) and int(ac) > 0:
            return int(ac)
        results = content.get("results")
        if isinstance(results, list) and results:
            return len(results)
        return 15

    return 1


def _compute_streak_days(activity_dates: Sequence[date], *, today: date) -> int:
    dates = set(activity_dates)
    if not dates:
        return 0
    yesterday = today - timedelta(days=1)
    if today in dates:
        anchor = today
    elif yesterday in dates:
        anchor = yesterday
    else:
        return 0
    streak = 0
    d = anchor
    while d in dates:
        streak += 1
        d -= timedelta(days=1)
    return streak


def _mode_level(levels: Sequence[str]) -> Optional[str]:
    if not levels:
        return None
    counts = Counter(levels)
    max_count = max(counts.values())
    tied = [lv for lv, n in counts.items() if n == max_count]
    if len(tied) == 1:
        return tied[0]
    return max(tied, key=lambda x: LEVEL_ORDER.index(x))


def level_gap(estimated: str, target: str) -> int:
    est = _normalize_level(estimated)
    tgt = _normalize_level(target)
    if not est or not tgt:
        return 0
    return max(0, LEVEL_ORDER.index(tgt) - LEVEL_ORDER.index(est))


def ring_fill_pct(estimated: Optional[str], target: str) -> int:
    est = _normalize_level(estimated or "")
    tgt = _normalize_level(target)
    if not est or not tgt:
        return 0
    est_i = LEVEL_ORDER.index(est)
    tgt_i = LEVEL_ORDER.index(tgt)
    if est_i >= tgt_i:
        return 100
    span = max(1, tgt_i)
    return max(8, min(100, round(100 * est_i / span)))


def progress_tagline(estimated: Optional[str], target: str) -> str:
    est = _normalize_level(estimated or "")
    tgt = _normalize_level(target) or "IH"
    if not est:
        return "답변이 쌓이면 등급이 표시돼요"
    gap = level_gap(est, tgt)
    if gap <= 0:
        return "목표 달성! 유지해요"
    if gap == 1:
        return f"{tgt}까지 한 계단 남았어요"
    if gap == 2:
        return f"{tgt}까지 두 계단 남았어요"
    return f"{tgt}까지 {gap}계단 남았어요"


def _week_daily_counts(
    rows: Sequence[Dict[str, Any]],
    *,
    today: date,
) -> Tuple[int, ...]:
    """Last 7 KST calendar days (oldest → newest) answer counts."""
    day_keys = [today - timedelta(days=i) for i in range(6, -1, -1)]
    buckets = {d: 0 for d in day_keys}
    for row in rows:
        d = _parse_kst_date(row.get("created_at"))
        if d is None or d not in buckets:
            continue
        buckets[d] += _answer_count_for_row(row)
    return tuple(buckets[d] for d in day_keys)


def _week_bar_heights(daily: Sequence[int]) -> Tuple[int, ...]:
    if not daily:
        return tuple(8 for _ in range(7))
    peak = max(daily) if daily else 0
    if peak <= 0:
        return tuple(8 for _ in daily)
    return tuple(max(8, min(100, round(100 * n / peak))) for n in daily)


def get_home_stats(user_id: Optional[str], *, target_level: str = "IH") -> Optional[Dict[str, Any]]:
    """Compute home dashboard stats for a logged-in user.

    Returns ``None`` on fetch failure. Empty history yields zero counts and
    ``estimated_level=None``.
    """
    if not user_id:
        return None

    rows = list_history_stats_rows()
    if rows is None:
        logger.warning("[HOME_STATS] Supabase fetch failed user=%s", str(user_id)[:8])
        return None

    today = datetime.now(_KST).date()
    activity_dates: List[date] = []
    total_answers = 0
    week_start = today - timedelta(days=6)
    week_answers = 0

    recent_levels: List[str] = []
    for row in rows:
        d = _parse_kst_date(row.get("created_at"))
        if d is not None:
            activity_dates.append(d)
        n_ans = _answer_count_for_row(row)
        total_answers += n_ans
        if d is not None and d >= week_start:
            week_answers += n_ans
        if len(recent_levels) < 10:
            lv = _normalize_level(row.get("overall_level"))
            if lv:
                recent_levels.append(lv)

    estimated = _mode_level(recent_levels) if len(recent_levels) >= 3 else None
    tgt = _normalize_level(target_level) or "IH"
    gap = level_gap(estimated, tgt) if estimated else 0
    daily = _week_daily_counts(rows, today=today)

    return {
        "streak_days": _compute_streak_days(activity_dates, today=today),
        "week_answers": week_answers,
        "total_answers": total_answers,
        "estimated_level": estimated,
        "target_level": tgt,
        "level_gap": gap,
        "week_daily_counts": daily,
        "week_bar_heights_pct": _week_bar_heights(daily),
        "ring_fill_pct": ring_fill_pct(estimated, tgt),
        "progress_tagline": progress_tagline(estimated, tgt),
    }


def get_cached_home_stats(ss: Any) -> Optional[Dict[str, Any]]:
    """Session-cached wrapper — avoids Supabase round-trips on every home rerun."""
    if not ss.get("user_authenticated") or ss.get("is_guest"):
        return None

    user_id = str(ss.get("user_id") or "").strip()
    if not user_id:
        return None

    now = time.time()
    cached = ss.get(_CACHE_KEY)
    cached_at = ss.get(_CACHE_AT_KEY)
    cached_uid = ss.get(_CACHE_UID_KEY)
    if (
        isinstance(cached, dict)
        and cached_uid == user_id
        and isinstance(cached_at, (int, float))
        and (now - float(cached_at)) < _CACHE_TTL_SEC
    ):
        logger.info(
            "[HOME_STATS] cache hit user=%s age=%.0fs",
            user_id[:8],
            now - float(cached_at),
        )
        return cached

    logger.info("[HOME_STATS] cache miss — querying Supabase user=%s", user_id[:8])
    try:
        stats = get_home_stats(user_id, target_level=resolve_target_level(ss))
    except Exception:
        logger.exception("[HOME_STATS] compute failed user=%s", user_id[:8])
        return None

    if stats is not None:
        ss[_CACHE_KEY] = stats
        ss[_CACHE_AT_KEY] = now
        ss[_CACHE_UID_KEY] = user_id
    return stats
