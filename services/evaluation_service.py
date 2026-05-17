"""Facade over hybrid evaluation — UI should call this instead of the
pipeline module directly.

Adds two stability features on top of the underlying engine:

* **Process-wide lock.** ``analyze_audio_with_retry`` serializes Gemini
  analysis requests across every Streamlit session running on this server
  via a module-level ``threading.Lock``. The lock is released *between*
  retries so a backed-off attempt never blocks another user for the full
  backoff duration — cross-session prevention of overload cascades.

* **Smart retry.** Only transient categories (5xx / 429 / timeout /
  deadline / quota / our own ``엔진 경로`` Korean signal) are retried
  with exponential-ish backoff (0s → 1s → 2s). Invalid-request errors
  (400 / 401 / 403 / structural validation) short-circuit and surface
  directly — retrying them would only waste the user's time.

The function is engine-agnostic. ``views/mock_exam.py`` no longer cares
about HTTP status codes, Gemini exception types, or retry timing — all
of that lives here so the call site stays a single line.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, Mapping, Optional, Tuple

from services.evaluation import ai_diag

# NOTE: The Gemini pipeline is imported **lazily** below.
#
# ``services.evaluation.gemini_multimodal_pipeline`` pulls in the ~400ms
# ``from google import genai`` SDK. Importing this facade at module load
# would force every MOCK survey/test screen to pay that cost up-front,
# even for users who only browse questions and never submit an answer.
# Deferring the import keeps ``views/mock_exam.py``'s cold-import time
# at ~20ms instead of ~400ms — only users who actually run an analysis
# pay the SDK init cost (and only on the FIRST analysis per process).
#
# All public symbols (``analyze_audio_with_ai``, ``analyze_audio_with_retry``,
# ``analyze_answer``, ``is_transient_error``) still resolve at module load;
# only the heavy dependency is deferred.

logger = logging.getLogger(__name__)


def _load_engine() -> Tuple[Callable[..., Dict[str, Any]], Callable[..., Dict[str, Any]]]:
    """Lazy-import the Gemini multimodal pipeline.

    Returns ``(analyze_audio_with_ai, analyze_answer)`` from the engine
    module. The first call pays the Gemini SDK init cost; subsequent
    calls are essentially free thanks to Python's module cache.
    """
    from services.evaluation.gemini_multimodal_pipeline import (
        analyze_answer as _engine_analyze_answer,
        analyze_audio_with_ai as _engine_analyze_audio,
    )

    return _engine_analyze_audio, _engine_analyze_answer

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

# Total attempts (initial + retries). Two keeps end-to-end wait bounded; the
# multimodal engine tries at most two model ids per attempt.
_MAX_ATTEMPTS = 2

# Backoff applied BEFORE the corresponding attempt. ``0s → 1s → 2s`` is the
# classic doubling pattern with a small ceiling that keeps the median fast
# while still riding out two consecutive transient failures.
_BACKOFF_SECONDS: Tuple[float, ...] = (0.0, 1.0, 2.0)

# Generous per-attempt lock timeout — large enough to wait through a slow
# Gemini response (~20–30s typical, occasional ~45s), but bounded so a wedged
# request can't permanently lock out other users.
_LOCK_ACQUIRE_TIMEOUT = 60.0

# Process-wide lock shared by every Streamlit session on this server. The
# free-tier Gemini Flash quota is the bottleneck in practice; serializing
# requests prevents the overload→503→retry→overload cascade.
_GEMINI_LOCK = threading.Lock()


# ---------------------------------------------------------------------------
# Transient classification
# ---------------------------------------------------------------------------

# Substring tokens (case-insensitive) that mark an error as worth retrying.
# Keep the list conservative — anything that looks like a permanent client
# error (400, 401, 403, malformed JSON, missing fields) intentionally falls
# through to the non-transient branch.
_TRANSIENT_TOKENS: Tuple[str, ...] = (
    "503",
    "504",
    "429",
    "OVERLOAD",
    "UNAVAILABLE",
    "TIMEOUT",
    "DEADLINE",
    "TEMPORARILY",
    "TEMPORARY",
    "RETRY",
    "RATE_LIMIT",
    "RESOURCE_EXHAUSTED",
)

# Korean phrases our own facade / pipeline surface when the upstream signal
# was a transient routing or quota hiccup.
_TRANSIENT_KOREAN: Tuple[str, ...] = (
    "할당량",      # quota exhausted
    "엔진 경로",   # internal routing temporarily re-resolving
    "혼잡",        # congestion
    "지연",        # delay
)


def is_transient_error(message: str) -> bool:
    """True iff the error string is something a short retry could fix.

    Returns False for invalid-request errors (400 / 401 / 403 / validation),
    malformed-JSON errors, and any other case the model would re-emit
    deterministically. Used by :func:`analyze_audio_with_retry` to decide
    whether to back off or surface immediately.
    """
    if not message:
        return False
    upper = message.upper()
    for tok in _TRANSIENT_TOKENS:
        if tok in upper:
            return True
    for kw in _TRANSIENT_KOREAN:
        if kw in message:
            return True
    return False


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

def analyze_audio_with_ai(
    audio_bytes: bytes,
    question_text: str,
    api_key: str,
    difficulty: int = 5,
    *,
    mime_guess: Optional[str] = None,
) -> Dict[str, Any]:
    """Single-shot Gemini analysis (no retry, no lock).

    Kept as the lowest-level facade for any caller that wants to drive its
    own retry / queuing policy. The mock-exam UI uses
    :func:`analyze_audio_with_retry` instead.
    """
    _engine_analyze_audio, _ = _load_engine()
    return _engine_analyze_audio(
        audio_bytes,
        question_text,
        api_key,
        difficulty,
        mime_guess=mime_guess,
    )


def analyze_audio_with_retry(
    audio_bytes: bytes,
    question_text: str,
    api_key: str,
    difficulty: int = 5,
    *,
    mime_guess: Optional[str] = None,
    on_status: Optional[Callable[[str, str], None]] = None,
    diag: Optional[Mapping[str, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], str, int]:
    """Smart-retry wrapper.

    Returns ``(result, error_message, attempts)``:
      * On success: ``(result_dict, "", n)`` where ``n`` is how many calls
        it took (1, 2, or 3).
      * On failure: ``(None, last_error_message, n)``.

    Behavior contract:
      1. Acquires a process-wide lock *per attempt* so concurrent Streamlit
         sessions can't pile on Gemini. Lock is released during the backoff
         sleep so a queued user only waits for an actual in-flight request,
         not for someone else's backoff.
      2. Retries up to ``_MAX_ATTEMPTS`` times with backoff
         ``_BACKOFF_SECONDS``, but ONLY when :func:`is_transient_error`
         classifies the last error as transient.
      3. Non-transient errors short-circuit the loop so users don't sit
         through retries for a permanent failure (e.g. bad audio format).

    ``on_status`` is an optional callback ``(stage, label)`` used by the
    caller to update a live status indicator. Recognized stages:

      * ``"queued"``    — waiting for the lock (another session is ahead)
      * ``"running"``   — analysis in flight to Gemini
      * ``"retrying"``  — between-attempt backoff after a transient failure
    """

    def _emit(stage: str, label: str) -> None:
        if on_status is None:
            return
        try:
            on_status(stage, label)
        except Exception:  # pragma: no cover — UI callback must never break logic
            logger.exception("on_status callback raised; ignoring")

    # Resolve the engine once per call. The import is a no-op after the
    # first invocation (module already in ``sys.modules``), but keeping it
    # *inside* the function means importing this facade module stays cheap.
    _engine_analyze_audio, _ = _load_engine()

    ctx = dict(diag or {})
    ctx.setdefault("caller", "analyze_audio_with_retry")
    ctx["audio_bytes_len"] = len(audio_bytes or b"")
    ai_diag.set_diag_context(ctx)
    ai_diag.log_retry_start()

    last_error = ""
    attempts = 0

    for attempt_idx in range(_MAX_ATTEMPTS):
        attempts = attempt_idx + 1
        ai_diag.update_diag_context(retry_attempt=attempts)

        if attempt_idx > 0:
            _emit(
                "retrying",
                "AI 응답이 잠시 혼잡한 상태예요. 자동으로 다시 시도하고 있어요... 🙏",
            )
            time.sleep(_BACKOFF_SECONDS[attempt_idx])

        # Non-blocking try first so we can surface a "queued" hint instead
        # of silently freezing the UI when another session holds the lock.
        acquired = _GEMINI_LOCK.acquire(blocking=False)
        if not acquired:
            _emit(
                "queued",
                "현재 분석 요청이 많아 잠시 대기 중이에요. 답변은 안전하게 보관됩니다.",
            )
            acquired = _GEMINI_LOCK.acquire(timeout=_LOCK_ACQUIRE_TIMEOUT)
            if not acquired:
                last_error = "분석 대기열 타임아웃 (다른 분석이 너무 오래 걸리고 있어요)"
                logger.warning("Gemini lock acquire timeout on attempt %d", attempts)
                # Treat as transient — likely a stuck request, worth one more try.
                continue

        try:
            _emit("running", "AI가 발화를 진단 중입니다…")
            try:
                response = _engine_analyze_audio(
                    audio_bytes,
                    question_text,
                    api_key,
                    difficulty,
                    mime_guess=mime_guess,
                )
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                result: Optional[Dict[str, Any]] = None
            else:
                if not response:
                    last_error = "결과값이 비어있습니다."
                    result = None
                elif "error" in response:
                    last_error = (response.get("error") or "").strip() or "AI 응답 오류"
                    result = None
                else:
                    last_error = ""
                    result = response
        finally:
            _GEMINI_LOCK.release()

        if result is not None and not last_error:
            ai_diag.log_retry_success(attempts=attempts)
            return result, "", attempts

        if not is_transient_error(last_error):
            # Permanent / structural failure — don't waste user time.
            logger.info(
                "Non-transient analysis error on attempt %d/%d (giving up): %s",
                attempts,
                _MAX_ATTEMPTS,
                last_error,
            )
            ai_diag.log_retry_failure(attempts=attempts, error_message=last_error)
            return None, last_error, attempts

        logger.warning(
            "Transient analysis error on attempt %d/%d (will retry): %s",
            attempts,
            _MAX_ATTEMPTS,
            last_error,
        )

    logger.error(
        "Gemini analyze_audio_with_retry exhausted after %d attempts: %s",
        attempts,
        last_error,
    )
    ai_diag.log_retry_failure(attempts=attempts, error_message=last_error)
    return None, last_error, attempts


def analyze_answer(audio_bytes: bytes, question_text: str, api_key: str) -> Dict[str, Any]:
    """Legacy single-shot answer-only entrypoint (unchanged)."""
    _, _engine_analyze_answer = _load_engine()
    return _engine_analyze_answer(audio_bytes, question_text, api_key)
