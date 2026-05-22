"""Script Coaching — UPGRADE engine: rewrite a script up to a target level.

# Stage 2 of Script Coaching. Separate engine from diagnose.
# Follows the same Gemini call/retry/parse pattern as script_coaching_diagnose.
#
# Honest expansion: the rubric forbids inventing facts; when the original is
# too short to reach the target honestly, the model returns fill_in_guides
# (prompts telling the student what THEY should add) instead of padding.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from services.api_retry_policy import (
    STT_RETRY_DELAYS_SEC,
    is_retryable_error,
    sleep_before_retry,
)
from services.evaluation.eval_config import build_topic_feedback_model_candidates
from services.script_coaching_metrics import build_script_text_metrics
from services.script_coaching_upgrade_rubric import (
    RUBRIC_VERSION,
    build_script_coaching_upgrade_rubric,
    target_levels_for,
)

logger = logging.getLogger(__name__)

GEMINI_REQUEST_TIMEOUT_SEC = 40
GEMINI_REQUEST_TIMEOUT_MS = GEMINI_REQUEST_TIMEOUT_SEC * 1000

MIN_SCRIPT_WORDS = 5
_UPGRADE_MODEL_ATTEMPTS = 2

_LEVEL_ORDER = ("NH", "IL", "IM1", "IM2", "IM3", "IH", "AL")

_UPGRADE_UNAVAILABLE = (
    "AI 변환 서버가 잠시 바빠요.\n\n"
    "진단 결과는 그대로 남아 있습니다.\n\n"
    "45초쯤 지난 뒤 「다시 변환하기」를 한 번만 눌러 주세요."
)


def _coerce_str(val: Any) -> str:
    return str(val or "").strip()


def _coerce_str_list(val: Any, limit: int = 10) -> List[str]:
    if not isinstance(val, list):
        return []
    out: List[str] = []
    for x in val:
        s = _coerce_str(x)
        if s:
            out.append(s)
    return out[:limit]


def _failure(*, category: str, message: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "mode": "",
        "current_level": "",
        "target_level": "",
        "upgraded_script": "",
        "change_notes": [],
        "fill_in_guides": [],
        "error_category": category,
        "error_message": message,
    }


def upgrade_options_for(current_level: str) -> Dict[str, Any]:
    """Resolve which upgrade options to offer for a diagnosed level.

    Returns a dict the UI can render directly:
      {"mode": "upgrade"|"polish",
       "one_step": level|None, "two_step": level|None}
    AL -> polish mode (no level options; UI shows the polish path).
    """
    return target_levels_for(current_level)


def _validate_target(current_level: str, target_level: str) -> Tuple[bool, str]:
    """Ensure target_level is exactly 1 or 2 steps above current_level."""
    cur = str(current_level or "").strip().upper()
    tgt = str(target_level or "").strip().upper()
    if cur not in _LEVEL_ORDER or tgt not in _LEVEL_ORDER:
        return False, "invalid_level"
    gap = _LEVEL_ORDER.index(tgt) - _LEVEL_ORDER.index(cur)
    if gap < 1 or gap > 2:
        return False, "target_out_of_range"
    return True, ""


def _is_model_not_found_error(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}"
    low = msg.lower()
    if "404" in msg or "not_found" in low or "not found" in low:
        return True
    if "no longer available" in low or "not available" in low:
        return True
    return getattr(exc, "status_code", None) == 404


def _parse_json_response(raw_text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    from services.evaluation.gemini_multimodal_pipeline import strip_json_fence
    from services.transcript_analysis_service import _extract_json_object

    parsed = _extract_json_object(raw_text)
    if parsed:
        return parsed, ""
    fence = strip_json_fence(raw_text)
    if fence != raw_text:
        parsed = _extract_json_object(fence)
        if parsed:
            return parsed, ""
    return None, "json_parse_failed"


def _invoke_model(
    api_key: str, prompt: str, model_name: str
) -> Tuple[Optional[Dict[str, Any]], str]:
    """Returns (parsed_json, error_token). error_token is '' on success."""
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=GEMINI_REQUEST_TIMEOUT_MS),
    )
    parts = [genai_types.Part.from_text(text=prompt)]
    contents = [genai_types.Content(role="user", parts=parts)]
    # Higher token budget than diagnose — the upgraded script can be long.
    config = genai_types.GenerateContentConfig(temperature=0.3, max_output_tokens=2048)
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
    except Exception as exc:
        if _is_model_not_found_error(exc):
            return None, "model_not_found"
        try:
            logger.warning(
                "[SCRIPT_UPGRADE] model=%s error_category=api_error exc_type=%s",
                model_name,
                type(exc).__name__,
            )
        except Exception:
            pass
        return None, "api_error"

    raw_text = (getattr(response, "text", "") or "").strip()
    if not raw_text:
        for cand in getattr(response, "candidates", None) or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                t = getattr(part, "text", None)
                if t:
                    raw_text = (raw_text + "\n" + t).strip()
    if not raw_text:
        return None, "empty_response"
    parsed, err = _parse_json_response(raw_text)
    if parsed:
        return parsed, ""
    return None, err or "json_parse_failed"


def _build_prompt(
    question_en: str,
    question_ko: str,
    original_script: str,
    current_level: str,
    target_level: str,
    mode: str,
) -> str:
    rubric = build_script_coaching_upgrade_rubric(mode=mode)
    metrics = build_script_text_metrics(original_script)
    payload = {
        "rubric_version": RUBRIC_VERSION,
        "mode": mode,
        "question_en": question_en,
        "question_ko": question_ko,
        "original_script": original_script,
        "current_level": current_level,
        "target_level": target_level,
        "text_metrics": metrics,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return rubric + "\n\nUpgrade data JSON:\n" + body


def _normalize_success(
    parsed: Dict[str, Any],
    *,
    mode: str,
    current_level: str,
    target_level: str,
) -> Dict[str, Any]:
    """Map model JSON to the upgrade schema; levels/mode forced from code."""
    return {
        "ok": True,
        "mode": mode,
        # current/target come from code, not the model — the model is told
        # to echo them but code is the source of truth.
        "current_level": current_level,
        "target_level": target_level,
        "upgraded_script": _coerce_str(parsed.get("upgraded_script")),
        "change_notes": _coerce_str_list(parsed.get("change_notes")),
        "fill_in_guides": (
            [] if mode == "polish"
            else _coerce_str_list(parsed.get("fill_in_guides"))
        ),
        "error_category": "",
        "error_message": "",
    }


def upgrade_script(
    question_en: str,
    original_script: str,
    current_level: str,
    target_level: str = "",
    question_ko: str = "",
) -> Dict[str, Any]:
    """Rewrite a diagnosed script up to a target level (honest expansion).

    Args:
        question_en: the OPIc question, in English.
        original_script: the student's diagnosed script.
        current_level: the diagnosed level (NH..AL).
        target_level: desired level. Ignored when current_level is AL
            (polish mode). Must be 1-2 steps above current otherwise.
        question_ko: optional Korean question text.

    Returns the upgrade-schema dict; ``ok`` is a bool.
    """
    question_en = _coerce_str(question_en)
    original_script = _coerce_str(original_script)
    current_level = _coerce_str(current_level).upper()
    target_level = _coerce_str(target_level).upper()
    question_ko = _coerce_str(question_ko)

    metrics = build_script_text_metrics(original_script)
    if int(metrics.get("word_count") or 0) < MIN_SCRIPT_WORDS:
        return _failure(
            category="insufficient_text",
            message="원문 스크립트가 너무 짧아 변환할 수 없어요.",
        )

    opts = target_levels_for(current_level)
    mode = opts["mode"]

    if mode == "polish":
        # AL — no target needed; light refinement only.
        target_level = "AL"
    else:
        if not target_level:
            return _failure(
                category="missing_target",
                message="목표 등급을 선택해 주세요.",
            )
        ok, why = _validate_target(current_level, target_level)
        if not ok:
            msg = (
                "목표 등급은 현재 등급보다 한두 단계 위여야 해요."
                if why == "target_out_of_range"
                else "등급 정보를 확인할 수 없어요. 진단을 다시 받아 주세요."
            )
            return _failure(category=why, message=msg)

    from utils.secrets import get_gemini_api_key

    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        return _failure(
            category="api_key",
            message="API 키가 없습니다. 설정에서 키를 확인해 주세요.",
        )

    prompt = _build_prompt(
        question_en, question_ko, original_script, current_level, target_level, mode
    )
    models = build_topic_feedback_model_candidates()
    saw_model_not_found = False
    saw_other_failure = False

    for model_name in models:
        for attempt_idx in range(1, _UPGRADE_MODEL_ATTEMPTS + 1):
            if attempt_idx > 1:
                sleep_before_retry(attempt_idx, STT_RETRY_DELAYS_SEC)
            try:
                logger.info(
                    "[SCRIPT_UPGRADE] model=%s attempt=%s mode=%s %s->%s",
                    model_name,
                    attempt_idx,
                    mode,
                    current_level,
                    target_level,
                )
            except Exception:
                pass
            parsed, err = _invoke_model(api_key, prompt, model_name)
            if parsed:
                out = _normalize_success(
                    parsed,
                    mode=mode,
                    current_level=current_level,
                    target_level=target_level,
                )
                if not out["upgraded_script"]:
                    # A rewrite with no script is not usable.
                    saw_other_failure = True
                    break
                try:
                    logger.info(
                        "[SCRIPT_UPGRADE] success model=%s mode=%s %s->%s guides=%s",
                        model_name,
                        mode,
                        current_level,
                        target_level,
                        len(out["fill_in_guides"]),
                    )
                except Exception:
                    pass
                return out
            if err == "model_not_found":
                saw_model_not_found = True
                break
            saw_other_failure = True
            if attempt_idx < _UPGRADE_MODEL_ATTEMPTS and is_retryable_error(err):
                continue
            break

    final_cat = (
        "model_not_found" if saw_model_not_found and not saw_other_failure else "api_error"
    )
    return _failure(category=final_cat, message=_UPGRADE_UNAVAILABLE)
