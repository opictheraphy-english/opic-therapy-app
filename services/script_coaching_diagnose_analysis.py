"""Script Coaching — DIAGNOSE engine: Gemini analysis of one written script.

# Stage 1 of Script Coaching. Follows the topic_practice_v2_analysis.py
# call/retry/parse pattern. Upgrade (stage 2) is a separate engine.
#
# Deterministic text metrics (word/connector counts, quantity score) are
# computed in code via script_coaching_metrics and injected as FACTS.
# Gemini only judges level + the five quality axes + Korean feedback.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from services.evaluation.eval_config import build_topic_feedback_model_candidates
from services.gemini_json_client import run_gemini_json_model_chain
from services.script_coaching_diagnose_rubric import (
    RUBRIC_VERSION,
    build_script_coaching_diagnose_rubric,
)
from services.script_coaching_metrics import build_script_text_metrics

logger = logging.getLogger(__name__)

GEMINI_REQUEST_TIMEOUT_SEC = 35
GEMINI_REQUEST_TIMEOUT_MS = GEMINI_REQUEST_TIMEOUT_SEC * 1000

MIN_SCRIPT_WORDS = 5

_VALID_LEVELS = ("NH", "IL", "IM1", "IM2", "IM3", "IH", "AL")
_SCORE_KEYS = ("response_amount", "vocabulary", "grammar", "context", "structure")

_DIAGNOSE_UNAVAILABLE = (
    "AI 진단 서버가 잠시 바빠요.\n\n"
    "입력하신 스크립트는 그대로 남아 있습니다.\n\n"
    "45초쯤 지난 뒤 「진단 다시 받기」를 한 번만 눌러 주세요."
)


def _coerce_str(val: Any) -> str:
    return str(val or "").strip()


def _coerce_int(val: Any, default: int = 0) -> int:
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _coerce_score(val: Any) -> int:
    return max(0, min(100, _coerce_int(val, 0)))


def _coerce_str_list(val: Any, limit: int = 3) -> List[str]:
    if not isinstance(val, list):
        return []
    out: List[str] = []
    for x in val:
        s = _coerce_str(x)
        if s:
            out.append(s)
    return out[:limit]


def _empty_scores() -> Dict[str, int]:
    return {k: 0 for k in _SCORE_KEYS}


def _normalize_grammar_row(row: Any) -> Dict[str, str]:
    if not isinstance(row, dict):
        return {}
    wrong = _coerce_str(row.get("before") or row.get("wrong") or row.get("original"))
    right = _coerce_str(row.get("after") or row.get("right") or row.get("corrected"))
    note = _coerce_str(row.get("why") or row.get("note") or row.get("reason"))
    if not wrong and not right:
        return {}
    return {"wrong": wrong, "right": right, "note": note}


def _normalize_expression_row(row: Any) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    phrase = _coerce_str(row.get("before") or row.get("phrase") or row.get("original"))
    alts = row.get("better") or row.get("alternatives") or row.get("upgrades") or []
    if isinstance(alts, str):
        alts = [alts]
    alts = [_coerce_str(a) for a in alts if _coerce_str(a)]
    note = _coerce_str(row.get("why") or row.get("note") or row.get("reason"))
    if not phrase and not alts:
        return {}
    return {"phrase": phrase, "alternatives": alts[:3], "note": note}


def _normalize_structure_feedback(val: Any) -> Dict[str, Any]:
    if not isinstance(val, dict):
        return {"good": [], "missing": [], "next": ""}
    return {
        "good": _coerce_str_list(val.get("good"), limit=3),
        "missing": _coerce_str_list(val.get("missing"), limit=3),
        "next": _coerce_str(val.get("next")),
    }


def _normalize_improved_sentences(val: Any) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not isinstance(val, list):
        return out
    for item in val:
        if isinstance(item, dict):
            sent = _coerce_str(item.get("sentence") or item.get("text"))
            lbl = _coerce_str(item.get("question_label") or item.get("label"))
        else:
            sent = _coerce_str(item)
            lbl = ""
        if sent:
            out.append({"question_label": lbl, "sentence": sent})
    return out[:3]


def _failure(*, category: str, message: str) -> Dict[str, Any]:
    return {
        "ok": False,
        "overall_level": "",
        "word_count": 0,
        "connector_summary": {"total_hits": 0, "distinct_count": 0, "found": []},
        "score_breakdown": _empty_scores(),
        "summary": "",
        "connector_feedback": "",
        "vocabulary_feedback": "",
        "context_feedback": "",
        "correction_focus": "",
        "better_expression": "",
        "strengths": [],
        "weaknesses": [],
        "grammar_corrections": [],
        "expression_upgrades": [],
        "structure_feedback": {"good": [], "missing": [], "next": ""},
        "improved_sentences": [],
        "missions": [],
        "error_category": category,
        "error_message": message,
    }


def _build_prompt(
    question_en: str,
    question_ko: str,
    script_text: str,
    metrics: Dict[str, Any],
) -> str:
    rubric = build_script_coaching_diagnose_rubric()
    payload = {
        "rubric_version": RUBRIC_VERSION,
        "question_en": question_en,
        "question_ko": question_ko,
        "transcript": script_text,
        "text_metrics": metrics,
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return rubric + "\n\nScript data JSON:\n" + body


def _normalize_success(
    parsed: Dict[str, Any],
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    """Map model JSON to the diagnose schema.

    word_count and connector_summary are taken from CODE metrics, not the
    model — the model is told to copy them, but code is the source of truth.
    """
    breakdown_raw = parsed.get("score_breakdown")
    breakdown = _empty_scores()
    if isinstance(breakdown_raw, dict):
        for k in _SCORE_KEYS:
            breakdown[k] = _coerce_score(breakdown_raw.get(k))
    # response_amount: trust the code rule as the floor reference.
    rule_amount = _coerce_score(metrics.get("response_amount_score_rule"))
    if breakdown["response_amount"] == 0:
        breakdown["response_amount"] = rule_amount

    level = _coerce_str(parsed.get("overall_level")).upper()
    if level not in _VALID_LEVELS:
        level = _coerce_str(metrics.get("word_count_level_hint")).upper() or "IL"

    return {
        "ok": True,
        "overall_level": level,
        # Code-computed facts — overrides any model recount.
        "word_count": _coerce_int(metrics.get("word_count")),
        "connector_summary": {
            "total_hits": _coerce_int(metrics.get("connector_total_hits")),
            "distinct_count": _coerce_int(metrics.get("connector_distinct_count")),
            "found": list(metrics.get("connectors_found") or []),
        },
        "score_breakdown": breakdown,
        "summary": _coerce_str(parsed.get("summary")),
        "connector_feedback": _coerce_str(parsed.get("connector_feedback")),
        "vocabulary_feedback": _coerce_str(parsed.get("vocabulary_feedback")),
        "context_feedback": _coerce_str(parsed.get("context_feedback")),
        "correction_focus": _coerce_str(parsed.get("correction_focus")),
        "better_expression": _coerce_str(parsed.get("better_expression")),
        "strengths": _coerce_str_list(parsed.get("strengths")),
        "weaknesses": _coerce_str_list(parsed.get("weaknesses")),
        "grammar_corrections": [
            g
            for g in (
                _normalize_grammar_row(r)
                for r in (parsed.get("grammar_corrections") or [])
            )
            if g
        ][:4],
        "expression_upgrades": [
            e
            for e in (
                _normalize_expression_row(r)
                for r in (parsed.get("expression_upgrades") or [])
            )
            if e
        ][:4],
        "structure_feedback": _normalize_structure_feedback(parsed.get("structure_feedback")),
        "improved_sentences": _normalize_improved_sentences(parsed.get("improved_sentences")),
        "missions": _coerce_str_list(parsed.get("missions"), limit=3),
        "error_category": "",
        "error_message": "",
    }


def diagnose_script(
    question_en: str,
    script_text: str,
    question_ko: str = "",
) -> Dict[str, Any]:
    """Diagnose one written OPIc script. Returns the diagnose-schema dict.

    Args:
        question_en: the OPIc question, in English (student-typed).
        script_text: the student's typed answer script.
        question_ko: optional Korean translation/notes for the question.
    """
    script_text = _coerce_str(script_text)
    question_en = _coerce_str(question_en)
    question_ko = _coerce_str(question_ko)

    metrics = build_script_text_metrics(script_text)
    if _coerce_int(metrics.get("word_count")) < MIN_SCRIPT_WORDS:
        return _failure(
            category="insufficient_text",
            message="스크립트가 너무 짧아요. 영어로 몇 문장 이상 적어 주세요.",
        )
    if not question_en:
        return _failure(
            category="missing_question",
            message="질문을 영어로 입력해 주세요. 질문이 있어야 유형에 맞게 진단할 수 있어요.",
        )

    from utils.secrets import get_gemini_api_key

    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        return _failure(
            category="api_key",
            message="API 키가 없습니다. 설정에서 키를 확인해 주세요.",
        )

    prompt = _build_prompt(question_en, question_ko, script_text, metrics)
    models = build_topic_feedback_model_candidates()

    def _log_attempt(model_name: str, attempt_no: int) -> None:
        try:
            logger.info(
                "[SCRIPT_DIAGNOSE] model=%s attempt=%s words=%s",
                model_name,
                attempt_no,
                metrics.get("word_count"),
            )
        except Exception:
            pass

    parsed, err = run_gemini_json_model_chain(
        api_key=api_key,
        prompt=prompt,
        models=models,
        temperature=0.2,
        max_output_tokens=2816,
        timeout_ms=GEMINI_REQUEST_TIMEOUT_MS,
        log_tag="SCRIPT_DIAGNOSE",
        on_attempt=_log_attempt,
    )
    if parsed:
        out = _normalize_success(parsed, metrics)
        if not out["summary"]:
            out["summary"] = "진단 결과가 생성되었어요. 아래 항목을 함께 확인해 주세요."
        try:
            logger.info(
                "[SCRIPT_DIAGNOSE] success level=%s",
                out["overall_level"],
            )
        except Exception:
            pass
        return out

    final_cat = "model_not_found" if err == "model_not_found" else "api_error"
    return _failure(category=final_cat, message=_DIAGNOSE_UNAVAILABLE)
