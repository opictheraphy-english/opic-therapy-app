"""Keyword constraint practice — code metrics + lightweight Gemini judgement."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from services.api_retry_policy import (
    GEMINI_JSON_FEEDBACK_MAX_OUTPUT_TOKENS,
    STT_RETRY_DELAYS_SEC,
    is_retryable_error,
    sleep_before_retry,
)
from services.evaluation.eval_config import build_topic_feedback_model_candidates
from services.gemini_json_client import parse_llm_json_response
from services.keyword_constraint_metrics import compute_keyword_constraint_metrics
from services.stt_service import count_english_words

logger = logging.getLogger(__name__)

GEMINI_REQUEST_TIMEOUT_SEC = 20
GEMINI_REQUEST_TIMEOUT_MS = GEMINI_REQUEST_TIMEOUT_SEC * 1000
_MIN_ANSWER_WORDS = 5
_MODEL_ATTEMPTS = 2

_UNAVAILABLE = (
    "AI 코칭 서버가 잠시 바빠요.\n\n"
    "목표·금지 표현 체크리스트는 아래에서 확인할 수 있어요.\n\n"
    "45초쯤 지난 뒤 「피드백 다시 받기」를 한 번만 눌러 주세요."
)

_RUBRIC = """
You are an OPIc speaking coach for a keyword-constraint drill.
The student's transcript and CODE-COMPUTED expression metrics are provided as JSON.
Do NOT recount target/banned hits — trust code_metrics exactly.

COACHING TONE RULES (critical — apply to naturalness_note AND coaching):

TARGET expressions (target_expressions in code_metrics):
- These are REQUIRED practice phrases the student MUST use. Never tell them to stop
  using a target expression or to replace it with a different word/synonym.
- If a target was used WELL and naturally → praise briefly in Korean.
- If a target was used AWKWARDLY or with wrong grammar/collocation → do NOT say
  "use another word instead" or "don't use hooked on". Teach the CORRECT form of
  THAT SAME expression.
  Bad: "hooked on 대신 다른 단어를 써 보세요."
  Good: "hooked on the park라고 하면 자연스러워요. to는 빼세요."
- Never negate the target phrase itself; only fix how to attach or phrase it.

BANNED expressions (banned in code_metrics with hit=true):
- Opposite rule: if the student used a banned expression, coach them to AVOID it.
  Briefly note it is below their target level (IL~IM band) and suggest a concrete
  alternative, e.g. "like는 피하고, enjoy / be into를 써 보세요."

Judge ONLY these axes:
1) patterns_used — did the student use an expansion pattern naturally (e.g. "What I like about ___ is that...")?
2) pattern_quote — short exact quote from the transcript if a pattern was used, else "".
3) naturalness_note — one sentence on target-expression naturalness (Korean). Follow TARGET rules above.
4) summary — one short overall line in Korean (max ~40 chars tone).
5) coaching — one practical coaching line in Korean (max ~60 chars tone). Follow TARGET/BANNED rules above.

Return ONLY valid JSON:
{
  "patterns_used": true,
  "pattern_quote": "",
  "naturalness_note": "",
  "summary": "",
  "coaching": ""
}
""".strip()


def _coerce_str(val: Any) -> str:
    return str(val or "").strip()


def _coerce_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return str(val or "").strip().lower() in ("true", "1", "yes", "y")


def _answer_transcript(answer: Dict[str, Any]) -> str:
    for key in ("transcript", "student_answer", "stt_transcript", "raw_transcript"):
        t = _coerce_str(answer.get(key))
        if t:
            return t
    return ""


def _expr_list(val: Any) -> List[str]:
    if not isinstance(val, (list, tuple)):
        return []
    return [_coerce_str(x) for x in val if _coerce_str(x)]


def _failure(*, category: str, message: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "summary": "",
        "coaching": "",
        "naturalness_note": "",
        "patterns_used": False,
        "pattern_quote": "",
        "targets": [],
        "banned": [],
        "target_used_count": 0,
        "target_total": 0,
        "banned_hit_count": 0,
        "error_category": category,
        "error_message": message,
    }


def _merge_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "targets": list(metrics.get("targets") or []),
        "banned": list(metrics.get("banned") or []),
        "target_used_count": int(metrics.get("target_used_count") or 0),
        "target_total": int(metrics.get("target_total") or 0),
        "banned_hit_count": int(metrics.get("banned_hit_count") or 0),
    }


def _normalize_success(parsed: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
    summary = _coerce_str(parsed.get("summary"))
    coaching = _coerce_str(parsed.get("coaching"))
    naturalness = _coerce_str(parsed.get("naturalness_note"))
    pattern_quote = _coerce_str(parsed.get("pattern_quote"))
    patterns_used = _coerce_bool(parsed.get("patterns_used"))
    pattern_quote = _coerce_str(parsed.get("pattern_quote"))
    out = {
        "ok": True,
        "summary": summary or "키워드 표현 사용 결과를 확인해 보세요.",
        "coaching": coaching or "목표 표현을 한 번 더 자연스럽게 녹여 말해 보세요.",
        "naturalness_note": naturalness,
        "patterns_used": patterns_used,
        "pattern_quote": pattern_quote if patterns_used else "",
        "error_category": "",
        "error_message": "",
    }
    out.update(_merge_metrics(metrics))
    return out


def _code_only_fallback(metrics: Dict[str, Any], *, message: str = "") -> Dict[str, Any]:
    msg = _coerce_str(message) or _UNAVAILABLE
    out = {
        "ok": True,
        "summary": "목표·금지 표현 결과는 아래 체크리스트에서 확인할 수 있어요.",
        "coaching": "AI 코칭을 불러오지 못했어요. 체크리스트를 참고해 같은 질문에 다시 말해 보세요.",
        "naturalness_note": "",
        "patterns_used": False,
        "pattern_quote": "",
        "error_category": "api_error",
        "error_message": msg,
    }
    out.update(_merge_metrics(metrics))
    return out


def _is_model_not_found_error(exc: BaseException) -> bool:
    msg = f"{type(exc).__name__}: {exc}"
    low = msg.lower()
    if "404" in msg or "not_found" in low or "not found" in low:
        return True
    if "no longer available" in low or "not available" in low:
        return True
    return getattr(exc, "status_code", None) == 404



def _invoke_model(
    api_key: str, prompt: str, model_name: str
) -> Tuple[Optional[Dict[str, Any]], str]:
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=GEMINI_REQUEST_TIMEOUT_MS),
    )
    parts = [genai_types.Part.from_text(text=prompt)]
    contents = [genai_types.Content(role="user", parts=parts)]
    config = genai_types.GenerateContentConfig(
        temperature=0.2,
        max_output_tokens=GEMINI_JSON_FEEDBACK_MAX_OUTPUT_TOKENS,
    )
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
                "[KEYWORD_CONSTRAINT] model=%s error_category=api_error exc_type=%s",
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
    parsed, err = parse_llm_json_response(raw_text, log_tag="KEYWORD_CONSTRAINT")
    if parsed:
        return parsed, ""
    return None, err or "json_parse_failed"


def _build_prompt(
    *,
    question_en: str,
    question_ko: str,
    transcript: str,
    metrics: Dict[str, Any],
    patterns: List[str],
) -> str:
    payload = {
        "question_en": question_en,
        "question_ko": question_ko,
        "transcript": transcript,
        "code_metrics": metrics,
        "expansion_patterns": patterns,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return _RUBRIC + "\n\nDrill data JSON:\n" + body


def analyze_keyword_constraint_answer(
    row: Dict[str, Any],
    set_meta: Dict[str, Any],
) -> Dict[str, Any]:
    """Analyze one keyword-constraint answer (code metrics + Gemini judgement)."""
    if not isinstance(row, dict):
        return _failure(category="invalid_input", message="answer_must_be_dict")
    if not isinstance(set_meta, dict):
        set_meta = {}

    transcript = _answer_transcript(row)
    wc = count_english_words(transcript)
    if wc < _MIN_ANSWER_WORDS:
        return _failure(
            category="insufficient_text",
            message="답변 텍스트가 너무 짧거나 비어 있어요. 영어로 몇 문장 이상 말해 주세요.",
        )

    targets = set_meta.get("target_expressions")
    banned = _expr_list(set_meta.get("banned_expressions"))
    patterns = _expr_list(set_meta.get("patterns"))
    metrics = compute_keyword_constraint_metrics(transcript, targets or [], banned)

    from utils.secrets import get_gemini_api_key

    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        return _failure(
            category="api_key",
            message="API 키가 없습니다. 설정에서 키를 확인해 주세요.",
        )

    question_en = _coerce_str(set_meta.get("question_text") or row.get("en"))
    question_ko = _coerce_str(set_meta.get("ko_helper") or row.get("ko"))
    prompt = _build_prompt(
        question_en=question_en,
        question_ko=question_ko,
        transcript=transcript,
        metrics=metrics,
        patterns=patterns,
    )

    models = build_topic_feedback_model_candidates()
    saw_model_not_found = False
    saw_other_failure = False

    for model_name in models:
        for attempt_idx in range(1, _MODEL_ATTEMPTS + 1):
            if attempt_idx > 1:
                sleep_before_retry(attempt_idx, STT_RETRY_DELAYS_SEC)
            try:
                logger.info(
                    "[KEYWORD_CONSTRAINT] model=%s attempt=%s words=%s targets_used=%s/%s banned_hits=%s",
                    model_name,
                    attempt_idx,
                    wc,
                    metrics.get("target_used_count"),
                    metrics.get("target_total"),
                    metrics.get("banned_hit_count"),
                )
            except Exception:
                pass
            parsed, err = _invoke_model(api_key, prompt, model_name)
            if parsed:
                out = _normalize_success(parsed, metrics)
                try:
                    logger.info(
                        "[KEYWORD_CONSTRAINT] success model=%s patterns_used=%s",
                        model_name,
                        out.get("patterns_used"),
                    )
                except Exception:
                    pass
                return out
            if err == "model_not_found":
                saw_model_not_found = True
                break
            saw_other_failure = True
            if attempt_idx < _MODEL_ATTEMPTS and is_retryable_error(err):
                continue
            break

    final_cat = (
        "model_not_found" if saw_model_not_found and not saw_other_failure else "api_error"
    )
    try:
        logger.warning("[KEYWORD_CONSTRAINT] ai_unavailable category=%s", final_cat)
    except Exception:
        pass
    return _code_only_fallback(metrics, message=_UNAVAILABLE)
