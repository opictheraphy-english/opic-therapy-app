"""Central Gemini API retry policy — STT and report analysis."""

from __future__ import annotations

import logging
import random
import time
from typing import FrozenSet, List, Tuple

logger = logging.getLogger(__name__)

RETRYABLE_ERRORS: FrozenSet[str] = frozenset(
    {
        "temporary_overload",
        "quota_or_rate_limit",
        "rate_limit",
        "timeout",
        "unavailable",
        "api_error",  # 5xx-style failures from classifiers
        # Mock V2 report — truncated JSON / parse after MAX_TOKENS (report only).
        "output_truncated",
        "json_parse_failed",
    }
)

# Errors that should advance to the next model candidate (not only backoff).
MODEL_FALLBACK_ERRORS: FrozenSet[str] = frozenset(
    {
        "temporary_overload",
        "unavailable",
        "timeout",
    }
)

# STT only — quota / rate-limit (429). Retrying or falling back to another model
# cannot succeed on the same API key and only multiplies billed error calls.
STT_QUOTA_ERRORS: FrozenSet[str] = frozenset(
    {
        "quota_or_rate_limit",
        "rate_limit",
    }
)

# --- STT retry policy --------------------------------------------------------
# STT runs on the Streamlit main thread (single-threaded). Long retry loops
# block the event loop, which kills the browser websocket via keepalive ping
# timeout (observed: "sent 1011 ... keepalive ping timeout" on Render).
#
# So STT must fail FAST. One attempt; on a retryable error (e.g. Gemini
# `temporary_overload`) we do NOT keep hammering — the answer is saved as
# `stt_pending` and the student re-runs STT later from the saved-answer
# screen ("음성 인식 다시 시도" button already exists). A short 2nd attempt is
# kept ONLY for model fallback so a single dead model does not strand STT.
# gemini-2.5-flash is the only audio-capable model on this key, and it returns
# intermittent 503 "high demand" (≈1 in 5 calls) that clears within seconds.
# 503s fail fast (not the 20s call timeout), so we can afford a few retries of
# the SAME model with escalating backoff and still finish well under the 25s
# wrapper timeout. This turns a 2-strikes-and-out flow into one that rides out
# a transient spike. (If all attempts still 503, the answer is saved as
# stt_pending and the student re-runs from the saved-answer screen.)
# 429 / quota (STT_QUOTA_ERRORS): fail immediately — same key, no point retrying
# or falling back to another model; student uses "음성 인식 다시 시도" after quota resets.
STT_MAX_ATTEMPTS = 4
STT_RETRY_DELAYS_SEC: Tuple[int, ...] = (1, 2, 3)

# Report analysis runs inside a ThreadPoolExecutor with its own wrapper
# timeout, so it does not block the websocket — longer backoff is safe here.
REPORT_MAX_ATTEMPTS = 2
REPORT_RETRY_DELAYS_SEC: Tuple[int, ...] = (3, 8)

# Gemini text→JSON feedback / script coaching — exponential backoff + jitter.
GEMINI_JSON_RETRY_BASE_SEC: Tuple[float, ...] = (0.5, 1.5, 3.0)
GEMINI_JSON_RETRY_JITTER_SEC = 0.3
GEMINI_JSON_MAX_TOTAL_SLEEP_SEC = 8.0
OPENAI_FALLBACK_MAX_ATTEMPTS = 2

# Per-model transient retry caps (inclusive: value N allows N+1 calls).
GEMINI_JSON_TRANSIENT_RETRIES_FULL = 3
GEMINI_JSON_TRANSIENT_RETRIES_FAST = 1
# OpenAI key present: trip circuit after this many consecutive transient failures.
GEMINI_JSON_CIRCUIT_BREAK_TRANSIENT = 2

_gemini_json_sleep_accumulator = 0.0


def reset_gemini_json_sleep_budget() -> None:
    global _gemini_json_sleep_accumulator
    _gemini_json_sleep_accumulator = 0.0


def record_gemini_json_sleep(delay_sec: float) -> None:
    global _gemini_json_sleep_accumulator
    _gemini_json_sleep_accumulator += max(0.0, float(delay_sec))


def gemini_json_total_sleep_budget_exceeded() -> bool:
    return _gemini_json_sleep_accumulator >= GEMINI_JSON_MAX_TOTAL_SLEEP_SEC


def gemini_json_retry_delay_sec(attempt_index: int) -> float:
    """attempt_index is 1-based count of completed failures before next retry."""
    if attempt_index <= 0:
        return 0.0
    idx = min(attempt_index - 1, len(GEMINI_JSON_RETRY_BASE_SEC) - 1)
    base = float(GEMINI_JSON_RETRY_BASE_SEC[idx])
    jitter = random.uniform(-GEMINI_JSON_RETRY_JITTER_SEC, GEMINI_JSON_RETRY_JITTER_SEC)
    return max(0.0, base + jitter)


def is_retryable_error(category: str) -> bool:
    return str(category or "").strip().lower() in RETRYABLE_ERRORS


def is_stt_retryable_error(category: str) -> bool:
    """Whether the STT loop should retry or try the next model candidate."""
    cat = str(category or "").strip().lower()
    if cat in STT_QUOTA_ERRORS:
        return False
    return is_retryable_error(cat)


def should_try_next_model(category: str) -> bool:
    return str(category or "").strip().lower() in MODEL_FALLBACK_ERRORS


def retry_delay_before_attempt(attempt_index: int, delays: Tuple[int, ...]) -> float:
    """attempt_index is 1-based; first attempt has no delay."""
    if attempt_index <= 1:
        return 0.0
    idx = min(attempt_index - 2, len(delays) - 1)
    return float(delays[idx]) if delays else 0.0


def sleep_before_retry(attempt_index: int, delays: Tuple[int, ...]) -> None:
    delay = retry_delay_before_attempt(attempt_index, delays)
    if delay > 0:
        time.sleep(delay)


def log_api_call_result(
    *,
    service: str,
    model_used: str,
    attempts: int,
    success: bool,
    error_category: str,
    elapsed: float,
) -> None:
    try:
        logger.info(
            "[API_CALL_RESULT] service=%s model_used=%s attempts=%s success=%s "
            "error_category=%s elapsed=%.2f",
            service,
            model_used or "—",
            attempts,
            success,
            error_category or "—",
            elapsed,
        )
    except Exception:
        pass
