"""Shared Gemini text→JSON invoke, robust parsing, and model-fallback retries."""

from __future__ import annotations

import json
import logging
import random
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.api_retry_policy import (
    GEMINI_JSON_CIRCUIT_BREAK_UNPRODUCTIVE,
    GEMINI_JSON_TRANSIENT_RETRIES_FAST,
    GEMINI_JSON_TRANSIENT_RETRIES_FULL,
    OPENAI_FALLBACK_MAX_ATTEMPTS,
    gemini_json_retry_delay_sec,
    gemini_json_total_sleep_budget_exceeded,
    record_gemini_json_sleep,
    reset_gemini_json_sleep_budget,
)
from utils.secrets import get_openai_api_key

logger = logging.getLogger(__name__)

_PARSE_LOG_SNIPPET_LEN = 200
OPENAI_FALLBACK_MODEL = "gpt-5-nano"
OPENAI_FALLBACK_MAX_COMPLETION_TOKENS = 4096
OPENAI_FALLBACK_EMPTY_RETRY_MAX_COMPLETION_TOKENS = 8192
_OPENAI_JSON_SYSTEM = (
    "You must respond with a single valid JSON object only. "
    "반드시 JSON만 반환하세요. No markdown fences, no prose."
)

# Per same-model attempt caps (see product spec).
_MAX_TRANSIENT_RETRIES_PER_MODEL = GEMINI_JSON_TRANSIENT_RETRIES_FULL
_MAX_JSON_PARSE_RETRIES_PER_MODEL = 1  # 1 retry after first parse fail

_TRANSIENT_ERROR_TOKENS = frozenset(
    {"api_error", "quota_or_rate_limit", "empty_response"}
)
_UNPRODUCTIVE_ERROR_TOKENS = _TRANSIENT_ERROR_TOKENS | frozenset({"json_parse_failed"})


def strip_json_code_fences(text: str) -> str:
    """Remove ```json ... ``` or bare ``` fences."""
    from services.evaluation.gemini_multimodal_pipeline import strip_json_fence

    return strip_json_fence(text or "")


def _fix_trailing_commas(json_str: str) -> str:
    return re.sub(r",\s*([}\]])", r"\1", json_str)


def _find_balanced_json_object(text: str) -> Optional[str]:
    """Extract the first top-level {…} block with balanced braces."""
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _try_load_dict(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _json_looks_truncated(text: str) -> bool:
    """Heuristic: response started a JSON object but braces never balanced."""
    stripped = strip_json_code_fences(text or "")
    if not stripped or "{" not in stripped:
        return False
    return _find_balanced_json_object(stripped) is None


def parse_llm_json_response(
    raw_text: str,
    *,
    log_tag: str = "",
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Parse model text into a JSON object; tolerate fences and leading prose."""
    text = strip_json_code_fences(raw_text or "")
    if not text:
        return None, "empty_response"

    candidates: List[str] = [text]
    balanced = _find_balanced_json_object(text)
    if balanced and balanced not in candidates:
        candidates.append(balanced)
    if balanced:
        fixed = _fix_trailing_commas(balanced)
        if fixed not in candidates:
            candidates.append(fixed)

    for candidate in candidates:
        parsed = _try_load_dict(candidate)
        if parsed:
            return parsed, ""

    tag = log_tag or "GEMINI_JSON"
    snippet = (raw_text or "")[:_PARSE_LOG_SNIPPET_LEN]
    truncated = _json_looks_truncated(raw_text or "")
    try:
        if truncated:
            logger.warning(
                "[%s] json_truncated snippet=%r",
                tag,
                snippet,
            )
        logger.warning(
            "[%s] json_parse_failed truncated=%s snippet=%r",
            tag,
            truncated,
            snippet,
        )
    except Exception:
        pass
    return None, "json_parse_failed"


def classify_gemini_exception(exc: BaseException) -> str:
    """Map SDK/HTTP errors to retry/fallback tokens."""
    msg = f"{type(exc).__name__}: {exc}"
    low = msg.lower()
    if "429" in msg or "resource_exhausted" in low or "rate limit" in low:
        return "quota_or_rate_limit"
    status = getattr(exc, "status_code", None)
    if status == 429:
        return "quota_or_rate_limit"
    if status == 404 or "404" in msg:
        return "model_not_found"
    if "not_found" in low or "not found" in low or "model_not_found" in low:
        return "model_not_found"
    if "no longer available" in low or "not available" in low:
        return "model_not_found"
    if status in (400, 401, 403, 404, 422):
        return "client_error" if status != 404 else "model_not_found"
    if "invalid" in low and "argument" in low:
        return "client_error"
    if "permission" in low or "forbidden" in low:
        return "client_error"
    if status and 500 <= int(status) < 600:
        return "api_error"
    if "servererror" in low or "internal" in low or "unavailable" in low:
        return "api_error"
    if "503" in msg or "502" in msg or "500" in msg:
        return "api_error"
    return "api_error"


def classify_openai_exception(exc: BaseException) -> str:
    """Map OpenAI SDK/HTTP errors to retry/fallback tokens."""
    return classify_gemini_exception(exc)


def _is_openai_auth_skip_error(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}".lower()
    if "authentication" in msg or "invalid_api_key" in msg or "incorrect api key" in msg:
        return True
    status = getattr(exc, "status_code", None)
    return status in (401, 403)


def _openai_model_restricts_sampling(model: str) -> bool:
    """GPT-5 / o-series: custom temperature etc. often rejected (default only)."""
    low = (model or "").lower()
    return any(token in low for token in ("gpt-5", "o1", "o3", "o4"))


def _openai_param_rejected(exc: BaseException, param: str) -> bool:
    msg = str(exc).lower()
    needle = param.lower()
    return needle in msg and (
        "unsupported" in msg or "not supported" in msg or "does not support" in msg
    )


def _openai_chat_completions_create(
    client: Any,
    *,
    model: str,
    messages: List[Dict[str, str]],
    max_completion_tokens: int,
    temperature: float,
    reasoning_effort: Optional[str] = None,
) -> Any:
    """Prefer max_completion_tokens (GPT-5); fall back to max_tokens for legacy models."""
    kwargs: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "max_completion_tokens": max_completion_tokens,
    }
    if not _openai_model_restricts_sampling(model):
        kwargs["temperature"] = temperature
    if reasoning_effort and _openai_model_restricts_sampling(model):
        kwargs["reasoning_effort"] = reasoning_effort

    try:
        return client.chat.completions.create(**kwargs)
    except Exception as exc:
        if reasoning_effort and _openai_param_rejected(exc, "reasoning_effort"):
            retry = {k: v for k, v in kwargs.items() if k != "reasoning_effort"}
            try:
                return client.chat.completions.create(**retry)
            except Exception as exc2:
                exc = exc2
        if (
            reasoning_effort == "minimal"
            and _openai_model_restricts_sampling(model)
            and _openai_param_rejected(exc, "minimal")
        ):
            retry = dict(kwargs)
            retry["reasoning_effort"] = "low"
            try:
                return client.chat.completions.create(**retry)
            except Exception as exc2:
                exc = exc2
        if _openai_param_rejected(exc, "max_completion_tokens"):
            legacy = dict(kwargs)
            legacy.pop("max_completion_tokens", None)
            legacy["max_tokens"] = max_completion_tokens
            if "temperature" not in legacy and not _openai_model_restricts_sampling(model):
                legacy["temperature"] = temperature
            return client.chat.completions.create(**legacy)
        if "temperature" in kwargs and _openai_param_rejected(exc, "temperature"):
            retry = {k: v for k, v in kwargs.items() if k != "temperature"}
            return client.chat.completions.create(**retry)
        raise


def _openai_extract_choice_text(response: Any) -> Tuple[str, str]:
    choice = (getattr(response, "choices", None) or [None])[0]
    if choice is None:
        return "", ""
    finish_reason = str(getattr(choice, "finish_reason", "") or "")
    raw_text = ""
    if getattr(choice, "message", None) is not None:
        raw_text = (getattr(choice.message, "content", "") or "").strip()
    return raw_text, finish_reason


def _log_openai_finish_reason(
    *,
    log_tag: str,
    model: str,
    finish_reason: str,
    note: str = "",
) -> None:
    suffix = f" {note}" if note else ""
    line = (
        f"[{log_tag}] openai_fallback model={model} "
        f"finish_reason={finish_reason or '—'}{suffix}"
    )
    try:
        print(line, flush=True)
    except Exception:
        pass
    try:
        logger.info(
            "[%s] openai_fallback model=%s finish_reason=%s%s",
            log_tag,
            model,
            finish_reason or "—",
            suffix,
        )
    except Exception:
        pass


def invoke_openai_text_json(
    *,
    prompt: str,
    model: str = OPENAI_FALLBACK_MODEL,
    system: Optional[str] = None,
    log_tag: str = "",
    max_output_tokens: int = OPENAI_FALLBACK_MAX_COMPLETION_TOKENS,
    temperature: float = 0.2,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Single OpenAI chat completion with JSON mode. Returns (parsed_dict, error_token)."""
    api_key = get_openai_api_key()
    if not api_key:
        return None, "openai_skipped"

    try:
        from openai import OpenAI
    except ImportError:
        return None, "openai_skipped"

    client = OpenAI(api_key=api_key)
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system or _OPENAI_JSON_SYSTEM},
        {"role": "user", "content": prompt},
    ]

    reasoning_effort = "minimal" if _openai_model_restricts_sampling(model) else None

    try:
        response = _openai_chat_completions_create(
            client,
            model=model,
            messages=messages,
            max_completion_tokens=max_output_tokens,
            temperature=temperature,
            reasoning_effort=reasoning_effort,
        )
    except Exception as exc:
        if _is_openai_auth_skip_error(exc):
            return None, "openai_skipped"
        err = classify_openai_exception(exc)
        try:
            logger.warning(
                "[%s] openai_fallback model=%s error_category=%s exc_type=%s",
                log_tag,
                model,
                err,
                type(exc).__name__,
            )
        except Exception:
            pass
        return None, err

    raw_text, finish_reason = _openai_extract_choice_text(response)
    _log_openai_finish_reason(log_tag=log_tag, model=model, finish_reason=finish_reason)

    if not raw_text and _openai_model_restricts_sampling(model):
        retry_tokens = OPENAI_FALLBACK_EMPTY_RETRY_MAX_COMPLETION_TOKENS
        retry_effort = "minimal"
        try:
            response = _openai_chat_completions_create(
                client,
                model=model,
                messages=messages,
                max_completion_tokens=retry_tokens,
                temperature=temperature,
                reasoning_effort=retry_effort,
            )
            raw_text, finish_reason = _openai_extract_choice_text(response)
            _log_openai_finish_reason(
                log_tag=log_tag,
                model=model,
                finish_reason=finish_reason,
                note="empty_retry",
            )
        except Exception as exc:
            try:
                logger.warning(
                    "[%s] openai_fallback model=%s empty_retry_failed exc_type=%s",
                    log_tag,
                    model,
                    type(exc).__name__,
                )
            except Exception:
                pass

    if not raw_text:
        _log_openai_finish_reason(
            log_tag=log_tag,
            model=model,
            finish_reason=finish_reason,
            note="empty_response",
        )
        return None, "empty_response"

    parsed, parse_err = parse_llm_json_response(raw_text, log_tag=log_tag)
    if parsed:
        return parsed, ""
    return None, parse_err or "json_parse_failed"


def _collect_response_text(response: Any) -> str:
    raw_text = (getattr(response, "text", "") or "").strip()
    if raw_text:
        return raw_text
    for cand in getattr(response, "candidates", None) or []:
        content = getattr(cand, "content", None)
        for part in getattr(content, "parts", None) or []:
            t = getattr(part, "text", None)
            if t:
                raw_text = (raw_text + "\n" + str(t)).strip()
    return raw_text


def build_gemini_json_generation_config(
    *,
    temperature: float,
    max_output_tokens: int,
    use_json_mode: bool = True,
) -> Any:
    from google.genai import types as genai_types

    base_kwargs = {
        "temperature": temperature,
        "max_output_tokens": max_output_tokens,
    }
    if not use_json_mode:
        return genai_types.GenerateContentConfig(**base_kwargs)
    try:
        return genai_types.GenerateContentConfig(
            **base_kwargs,
            response_mime_type="application/json",
        )
    except TypeError:
        return genai_types.GenerateContentConfig(**base_kwargs)


def invoke_gemini_text_json(
    *,
    api_key: str,
    prompt: str,
    model_name: str,
    temperature: float,
    max_output_tokens: int,
    timeout_ms: int,
    log_tag: str,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Single generate_content call. Returns (parsed_dict, error_token)."""
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=timeout_ms),
    )
    parts = [genai_types.Part.from_text(text=prompt)]
    contents = [genai_types.Content(role="user", parts=parts)]

    last_exc: Optional[BaseException] = None
    for use_json_mode in (True, False):
        config = build_gemini_json_generation_config(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            use_json_mode=use_json_mode,
        )
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            last_exc = exc
            err = classify_gemini_exception(exc)
            if use_json_mode and err == "client_error":
                continue
            try:
                logger.warning(
                    "[%s] model=%s error_category=%s exc_type=%s",
                    log_tag,
                    model_name,
                    err,
                    type(exc).__name__,
                )
            except Exception:
                pass
            return None, err

        raw_text = _collect_response_text(response)
        if not raw_text:
            return None, "empty_response"
        parsed, parse_err = parse_llm_json_response(raw_text, log_tag=log_tag)
        if parsed:
            return parsed, ""
        return None, parse_err or "json_parse_failed"

    if last_exc is not None:
        return None, classify_gemini_exception(last_exc)
    return None, "api_error"


def _should_retry_same_model(
    err: str,
    transient_attempts: int,
    parse_attempts: int,
    *,
    max_transient_retries: int,
) -> bool:
    if err in ("model_not_found", "client_error"):
        return False
    if err == "json_parse_failed":
        return parse_attempts <= _MAX_JSON_PARSE_RETRIES_PER_MODEL
    if err in _TRANSIENT_ERROR_TOKENS:
        return transient_attempts <= max_transient_retries
    return False


def _gemini_retry_policy() -> Tuple[int, bool, int]:
    """Return (max_transient_retries_per_model, circuit_break_enabled, circuit_threshold)."""
    if get_openai_api_key():
        return (
            GEMINI_JSON_TRANSIENT_RETRIES_FAST,
            True,
            GEMINI_JSON_CIRCUIT_BREAK_UNPRODUCTIVE,
        )
    return (
        GEMINI_JSON_TRANSIENT_RETRIES_FULL,
        False,
        0,
    )


def _record_unproductive_failure(
    err: str,
    *,
    streak: List[str],
) -> Tuple[int, str]:
    if err not in _UNPRODUCTIVE_ERROR_TOKENS:
        return len(streak), (streak[-1] if streak else "")
    streak.append(err)
    return len(streak), err


def _unproductive_breakdown(streak: List[str]) -> Tuple[int, int, int]:
    transient = sum(
        1 for e in streak if e in ("api_error", "quota_or_rate_limit")
    )
    parse_failed = sum(1 for e in streak if e == "json_parse_failed")
    empty = sum(1 for e in streak if e == "empty_response")
    return transient, parse_failed, empty


def _run_openai_fallback(
    *,
    prompt: str,
    temperature: float,
    max_output_tokens: int,
    log_tag: str,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Last-resort OpenAI JSON call after Gemini chain exhaustion."""
    if not get_openai_api_key():
        return None, "openai_skipped"

    try:
        logger.info(
            "[%s] openai_fallback model=%s",
            log_tag,
            OPENAI_FALLBACK_MODEL,
        )
    except Exception:
        pass

    last_err = "api_error"
    for attempt_no in range(1, OPENAI_FALLBACK_MAX_ATTEMPTS + 1):
        parsed, err = invoke_openai_text_json(
            prompt=prompt,
            model=OPENAI_FALLBACK_MODEL,
            log_tag=log_tag,
            max_output_tokens=OPENAI_FALLBACK_MAX_COMPLETION_TOKENS,
            temperature=temperature,
        )
        if parsed:
            try:
                logger.info(
                    "[%s] openai_fallback model=%s success",
                    log_tag,
                    OPENAI_FALLBACK_MODEL,
                )
            except Exception:
                pass
            return parsed, ""
        last_err = err or "api_error"
        if err == "openai_skipped":
            return None, "openai_skipped"
        if err not in ("api_error", "quota_or_rate_limit"):
            break
        if attempt_no >= OPENAI_FALLBACK_MAX_ATTEMPTS:
            break
        if gemini_json_total_sleep_budget_exceeded():
            break
        delay = gemini_json_retry_delay_sec(attempt_no)
        if delay <= 0:
            break
        record_gemini_json_sleep(delay)
        time.sleep(delay)

    try:
        logger.warning(
            "[%s] openai_fallback model=%s failed err=%s",
            log_tag,
            OPENAI_FALLBACK_MODEL,
            last_err,
        )
    except Exception:
        pass
    return None, last_err


def run_gemini_json_model_chain(
    *,
    api_key: str,
    prompt: str,
    models: List[str],
    temperature: float,
    max_output_tokens: int,
    timeout_ms: int,
    log_tag: str,
    on_attempt: Optional[Callable[[str, int], None]] = None,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Try each model with typed retries; respect total sleep budget."""
    reset_gemini_json_sleep_budget()
    max_transient_retries, circuit_enabled, circuit_threshold = _gemini_retry_policy()
    last_err = "api_error"
    saw_model_not_found = False
    saw_other_failure = False
    consecutive_unproductive = 0
    unproductive_streak: List[str] = []
    circuit_tripped = False

    for model_name in models:
        if circuit_tripped:
            break
        transient_attempts = 0
        parse_attempts = 0
        attempt_no = 0
        while True:
            attempt_no += 1
            if on_attempt:
                try:
                    on_attempt(model_name, attempt_no)
                except Exception:
                    pass
            parsed, err = invoke_gemini_text_json(
                api_key=api_key,
                prompt=prompt,
                model_name=model_name,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                timeout_ms=timeout_ms,
                log_tag=log_tag,
            )
            if parsed:
                return parsed, ""
            last_err = err or "api_error"
            if err == "model_not_found":
                saw_model_not_found = True
                unproductive_streak.clear()
                break
            saw_other_failure = True
            if err == "json_parse_failed":
                parse_attempts += 1
            elif err in _TRANSIENT_ERROR_TOKENS:
                transient_attempts += 1
            elif err == "client_error":
                unproductive_streak.clear()
                break

            consecutive_unproductive, last_unproductive_err = _record_unproductive_failure(
                err,
                streak=unproductive_streak,
            )

            if circuit_enabled and consecutive_unproductive >= circuit_threshold:
                transient_n, parse_n, empty_n = _unproductive_breakdown(
                    unproductive_streak
                )
                try:
                    logger.info(
                        "[%s] gemini_circuit_break reason=unproductive "
                        "consecutive=%s transient=%s parse=%s empty=%s "
                        "last=%s threshold=%s → openai_fallback",
                        log_tag,
                        consecutive_unproductive,
                        transient_n,
                        parse_n,
                        empty_n,
                        last_unproductive_err or err,
                        circuit_threshold,
                    )
                except Exception:
                    pass
                circuit_tripped = True
                break

            if not _should_retry_same_model(
                err,
                transient_attempts,
                parse_attempts,
                max_transient_retries=max_transient_retries,
            ):
                break
            if gemini_json_total_sleep_budget_exceeded():
                break
            delay = gemini_json_retry_delay_sec(transient_attempts + parse_attempts)
            if delay <= 0:
                break
            record_gemini_json_sleep(delay)
            time.sleep(delay)

    if saw_model_not_found and not saw_other_failure:
        gemini_err = "model_not_found"
    else:
        gemini_err = last_err

    parsed, openai_err = _run_openai_fallback(
        prompt=prompt,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        log_tag=log_tag,
    )
    if parsed:
        return parsed, ""
    if openai_err != "openai_skipped":
        return None, gemini_err
    return None, gemini_err
