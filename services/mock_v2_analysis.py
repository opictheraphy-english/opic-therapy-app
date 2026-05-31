"""Mock V2 final AI report — transcript-only Gemini analysis (isolated from real mock)."""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from services.api_retry_policy import (
    REPORT_MAX_ATTEMPTS,
    REPORT_RETRY_DELAYS_SEC,
    is_retryable_error,
    log_api_call_result,
    should_try_next_model,
    sleep_before_retry,
)
from services.evaluation.eval_config import REAL_REPORT_MODEL_NAME, _dedupe_models
from services.mock_v2_rubric import RUBRIC_VERSION, build_mock_v2_rubric_prompt
from services.speech_rate_scoring import (
    apply_speech_rate_to_report,
    build_exam_aggregate_speech_metrics,
    build_per_answer_speech_metrics,
)
from services.stt_service import count_english_words

logger = logging.getLogger(__name__)

GEMINI_REQUEST_TIMEOUT_SEC = 45
GEMINI_REQUEST_TIMEOUT_MS = GEMINI_REQUEST_TIMEOUT_SEC * 1000
ANALYSIS_WRAPPER_TIMEOUT_SEC = 55
# Visible JSON + thinking tokens share this cap (gemini-2.5-flash).
MOCK_V2_REPORT_MAX_OUTPUT_TOKENS = 16384

MIN_USABLE_WORDS = 5
MIN_VALID_ANSWERS_FOR_REPORT = 3
_QUESTION_COUNT = 15

_SCORE_KEYS = (
    "response_amount",
    "relevance",
    "structure",
    "grammar",
    "vocabulary",
    "naturalness",
)


def build_mock_v2_report_model_candidates() -> List[str]:
    """GEMINI_REAL_REPORT_MODEL → GEMINI_REPORT_MODEL → 2.5 flash / lite, then
    3.x cross-family fallback to survive a 503 spike on the 2.5 family."""
    report_env = (os.getenv("GEMINI_REPORT_MODEL") or "").strip()
    return _dedupe_models(
        [
            REAL_REPORT_MODEL_NAME,
            report_env,
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-3.5-flash",
        ]
    )


def _empty_score_breakdown() -> Dict[str, int]:
    return {k: 0 for k in _SCORE_KEYS}


def _student_answer_text(row: Dict[str, Any]) -> str:
    for key in ("student_answer", "transcript", "raw_transcript"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return ""


def _row_feedback_status(row: Dict[str, Any], text: str) -> str:
    row_status = str(row.get("status") or "").strip()
    stt_status = str(row.get("stt_status") or "").strip()
    if row_status == "recording_failed":
        return "응답 부족"
    if stt_status in ("stt_failed", "stt_pending") or row_status in ("stt_failed", "stt_pending"):
        if int(row.get("audio_len") or 0) > 0 or row.get("audio_saved"):
            return "음성 인식 실패"
        return "응답 부족"
    if count_english_words(text) >= MIN_USABLE_WORDS:
        return "saved"
    if text:
        return "응답 부족"
    return "응답 부족"


def _is_usable_answer(row: Dict[str, Any]) -> bool:
    text = _student_answer_text(row)
    return _row_feedback_status(row, text) == "saved"


def _questions_by_index(questions: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    for q in questions:
        if not isinstance(q, dict):
            continue
        try:
            idx = int(q.get("question_index", -1))
        except (TypeError, ValueError):
            continue
        if idx >= 0:
            out[idx] = q
    return out


def build_mock_v2_report_payload(
    answers: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Lean JSON payload for Gemini — no raw audio."""
    qmap = _questions_by_index(questions)
    answer_map: Dict[int, Dict[str, Any]] = {}
    for row in answers:
        if not isinstance(row, dict):
            continue
        try:
            answer_map[int(row.get("question_index", -1))] = row
        except (TypeError, ValueError):
            continue

    indices = sorted(set(qmap.keys()) | set(answer_map.keys()))
    if not indices:
        indices = list(range(_QUESTION_COUNT))

    payload_answers: List[Dict[str, Any]] = []
    total_word_count = 0
    transcript_ready_count = 0
    wpm_vals: List[float] = []

    for idx in indices:
        q = qmap.get(idx, {})
        row = answer_map.get(idx, {})
        text = _student_answer_text(row) if row else ""
        wc = int(count_english_words(text)) if text else 0
        if text and str(row.get("stt_status") or "") == "transcript_ready":
            transcript_ready_count += 1
        total_word_count += wc
        try:
            wpm = float(row.get("wpm") or 0.0)
        except (TypeError, ValueError):
            wpm = 0.0
        if wpm > 0:
            wpm_vals.append(wpm)

        fb_status = _row_feedback_status(row, text) if row else "응답 부족"
        try:
            dur_sec = float(row.get("duration_seconds") or 0.0) if row else 0.0
        except (TypeError, ValueError):
            dur_sec = 0.0
        wpm_avail = wpm > 0 and dur_sec > 0
        speech_row = build_per_answer_speech_metrics(wc, dur_sec)
        payload_answers.append(
            {
                "question_index": idx,
                "question_number": int(
                    row.get("question_number") or q.get("question_number") or (idx + 1)
                ),
                "opic_type": str(row.get("opic_type") or q.get("opic_type") or ""),
                "combo": str(row.get("combo") or q.get("combo") or ""),
                "topic": str(row.get("topic") or q.get("topic") or ""),
                "step": str(q.get("step") or ""),
                "question_text": str(
                    row.get("question_text") or q.get("question_text") or ""
                ),
                "student_answer": text,
                "transcript": str(row.get("transcript") or text),
                "word_count": wc,
                "duration_seconds": dur_sec,
                "wpm": wpm,
                "wpm_available": wpm_avail,
                "words_normalized_90s": speech_row.get("words_normalized_90s"),
                "speech_rate_level": speech_row.get("speech_rate_level"),
                "response_amount_score_rule": speech_row.get("response_amount_score_rule"),
                "stt_status": str(row.get("stt_status") or "") if row else "",
                "status": fb_status,
            }
        )

    saved_count = len([a for a in answers if isinstance(a, dict)])
    valid_count = len([a for a in answers if isinstance(a, dict) and _is_usable_answer(a)])
    speech_agg = build_exam_aggregate_speech_metrics(
        payload_answers, level_basis="per_answer"
    )
    avg_wpm = round(sum(wpm_vals) / len(wpm_vals), 1) if wpm_vals else float(
        speech_agg.get("average_wpm") or 0
    )
    if avg_wpm > 0:
        speech_agg["average_wpm"] = avg_wpm

    return {
        "exam_type": "mock_v2",
        "total_questions": _QUESTION_COUNT,
        "saved_count": saved_count,
        "valid_answers_count": valid_count,
        "transcript_ready_count": transcript_ready_count,
        "total_word_count": total_word_count,
        "average_wpm": avg_wpm,
        "aggregate_metrics": speech_agg,
        "answers": payload_answers,
    }


def _failure(
    *,
    category: str,
    message: str,
    timed_out: bool = False,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "overall_level": "",
        "summary": "",
        "score_breakdown": _empty_score_breakdown(),
        "question_feedback": [],
        "strengths": [],
        "weaknesses": [],
        "practice_mission": "",
        "error_category": category,
        "error_message": message,
        "timed_out": timed_out,
    }


def _insufficient_exam_report(payload: Dict[str, Any]) -> Dict[str, Any]:
    q_feedback: List[Dict[str, Any]] = []
    for item in payload.get("answers") or []:
        if not isinstance(item, dict):
            continue
        q_feedback.append(
            {
                "question_index": int(item.get("question_index") or 0),
                "question_number": int(item.get("question_number") or 0),
                "opic_type": str(item.get("opic_type") or ""),
                "status": str(item.get("status") or "응답 부족"),
                "feedback": "답변 텍스트가 없거나 분량이 부족해 이 문항은 상세 피드백을 제공하지 않았습니다.",
                "better_direction": "영어로 20초 이상 답변한 뒤 다시 시도해 주세요.",
            }
        )
    return {
        "ok": True,
        "overall_level": "응답 부족",
        "summary": (
            "유효한 영어 답변이 충분하지 않아 정상적인 등급 산정이 어렵습니다. "
            f"현재 인식 가능한 답변은 {payload.get('valid_answers_count', 0)}개입니다."
        ),
        "score_breakdown": _empty_score_breakdown(),
        "question_feedback": q_feedback,
        "strengths": [],
        "weaknesses": ["답변 분량 또는 음성 인식 결과 부족"],
        "practice_mission": (
            "최소 3문항 이상 영어로 20~30초 이상 답변한 뒤, 다시 리포트를 받아 보세요."
        ),
        "error_category": "",
        "error_message": "",
    }


def _response_finish_reason(response: Any) -> str:
    for cand in getattr(response, "candidates", None) or []:
        fr = getattr(cand, "finish_reason", None)
        if fr is not None:
            return str(fr).strip()
    return ""


def _is_max_tokens_finish(finish_reason: str) -> bool:
    return "max_tokens" in (finish_reason or "").lower()


def _classify_gemini_error(err: str) -> str:
    err_s = (err or "").strip()
    err_l = err_s.lower()
    if err_l == "output_truncated" or err_l.startswith("output_truncated"):
        return "output_truncated"
    if err_l == "json_parse_failed" or err_l.startswith("json_parse_failed"):
        return "json_parse_failed"
    if any(t in err_l for t in ("timeout", "timed out", "deadline exceeded")):
        return "timeout"
    if "429" in err_l or "quota" in err_l or "resource_exhausted" in err_l:
        return "quota_or_rate_limit"
    if "rate limit" in err_l or "too many requests" in err_l:
        return "rate_limit"
    if any(t in err_l for t in ("api key", "unauthenticated", "401", "permission denied")):
        return "api_key"
    if "503" in err_l or "overloaded" in err_l:
        return "temporary_overload"
    if "unavailable" in err_l:
        return "unavailable"
    if any(t in err_l for t in ("500", "502", "504", "internal error")):
        return "api_error"
    if "404" in err_l or "not_found" in err_l:
        return "model_not_found"
    return "unknown" if err else "api_error"


def _parse_report_response(raw_text: str) -> Tuple[Optional[Dict[str, Any]], str]:
    from services.evaluation.gemini_multimodal_pipeline import strip_json_fence
    from services.transcript_analysis_service import _extract_json_object

    parsed = _extract_json_object(raw_text)
    if parsed:
        return parsed, ""
    fence_text = strip_json_fence(raw_text)
    if fence_text != raw_text:
        parsed = _extract_json_object(fence_text)
        if parsed:
            return parsed, ""
    return None, "json_parse_failed"


def _log_report_call_failure(
    *,
    attempt: int,
    model_name: str,
    error_category: str,
    error_message: str,
    finish_reason: str,
) -> None:
    try:
        logger.warning(
            "[MOCK_V2_REPORT_RETRY] attempt=%s model=%s error_category=%s "
            "error_message=%s finish_reason=%s",
            attempt,
            model_name or "—",
            error_category or "—",
            error_message or "—",
            finish_reason or "—",
        )
    except Exception:
        pass


def _invoke_report_model(
    api_key: str, prompt: str, model_name: str
) -> Tuple[Optional[Dict[str, Any]], str, str, str]:
    from google import genai
    from google.genai import types as genai_types

    client = genai.Client(
        api_key=api_key,
        http_options=genai_types.HttpOptions(timeout=GEMINI_REQUEST_TIMEOUT_MS),
    )
    parts = [genai_types.Part.from_text(text=prompt)]
    contents = [genai_types.Content(role="user", parts=parts)]
    config = genai_types.GenerateContentConfig(
        temperature=0.25,
        max_output_tokens=MOCK_V2_REPORT_MAX_OUTPUT_TOKENS,
    )
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=config,
        )
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}", model_name, ""

    finish_reason = _response_finish_reason(response)
    raw_text = (getattr(response, "text", "") or "").strip()
    if not raw_text:
        for cand in getattr(response, "candidates", None) or []:
            content = getattr(cand, "content", None)
            for part in getattr(content, "parts", None) or []:
                t = getattr(part, "text", None)
                if t:
                    raw_text = (raw_text + "\n" + t).strip()
    if not raw_text:
        err = "empty_response"
        if _is_max_tokens_finish(finish_reason):
            err = "output_truncated"
        return None, err, model_name, finish_reason

    parsed, parse_err = _parse_report_response(raw_text)
    if parsed:
        return parsed, "", model_name, finish_reason

    if _is_max_tokens_finish(finish_reason):
        return None, "output_truncated", model_name, finish_reason
    return None, parse_err or "json_parse_failed", model_name, finish_reason


def _call_gemini(api_key: str, prompt: str) -> Tuple[Optional[Dict[str, Any]], str, str]:
    models = build_mock_v2_report_model_candidates()
    if not models:
        return None, "no_report_models_configured", ""

    t0 = time.perf_counter()
    last_error = ""
    last_category = ""
    last_finish_reason = ""
    model_idx = 0
    attempt_num = 0

    while attempt_num < REPORT_MAX_ATTEMPTS and model_idx < len(models):
        attempt_num += 1
        sleep_before_retry(attempt_num, REPORT_RETRY_DELAYS_SEC)
        model_name = models[model_idx]

        parsed, err_msg, _, finish_reason = _invoke_report_model(
            api_key, prompt, model_name
        )
        if parsed:
            elapsed = time.perf_counter() - t0
            log_api_call_result(
                service="mock_v2_report",
                model_used=model_name,
                attempts=attempt_num,
                success=True,
                error_category="",
                elapsed=elapsed,
            )
            return parsed, "", model_name

        last_error = err_msg or "gemini_failed"
        last_category = _classify_gemini_error(last_error)
        last_finish_reason = finish_reason

        _log_report_call_failure(
            attempt=attempt_num,
            model_name=model_name,
            error_category=last_category,
            error_message=last_error,
            finish_reason=last_finish_reason,
        )

        if last_category == "model_not_found" and model_idx + 1 < len(models):
            model_idx += 1
            continue
        if not is_retryable_error(last_category):
            break
        if should_try_next_model(last_category) and model_idx + 1 < len(models):
            model_idx += 1
            continue
        if attempt_num >= REPORT_MAX_ATTEMPTS:
            break

    elapsed = time.perf_counter() - t0
    log_api_call_result(
        service="mock_v2_report",
        model_used=models[min(model_idx, len(models) - 1)] if models else "",
        attempts=attempt_num,
        success=False,
        error_category=last_category,
        elapsed=elapsed,
    )
    return None, last_error or last_category, models[min(model_idx, len(models) - 1)] if models else ""


def _normalize_parsed(
    parsed: Dict[str, Any],
    *,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    breakdown_raw = parsed.get("score_breakdown")
    breakdown: Dict[str, int] = _empty_score_breakdown()
    if isinstance(breakdown_raw, dict):
        for key in _SCORE_KEYS:
            try:
                breakdown[key] = max(0, min(100, int(breakdown_raw.get(key) or 0)))
            except (TypeError, ValueError):
                breakdown[key] = 0

    q_fb_by_num: Dict[int, Dict[str, Any]] = {}
    q_fb_raw = parsed.get("question_feedback")
    if isinstance(q_fb_raw, list):
        for item in q_fb_raw:
            if not isinstance(item, dict):
                continue
            try:
                qnum = int(item.get("question_number") or item.get("question_index") or 0)
            except (TypeError, ValueError):
                qnum = 0
            if qnum <= 0:
                try:
                    qnum = int(item.get("question_index") or 0) + 1
                except (TypeError, ValueError):
                    qnum = 0
            q_fb_by_num[qnum] = {
                "question_index": max(0, qnum - 1),
                "question_number": qnum,
                "opic_type": str(item.get("opic_type") or "").strip(),
                "status": str(item.get("status") or "saved").strip(),
                "feedback": str(item.get("feedback") or "").strip(),
                "better_direction": str(item.get("better_direction") or "").strip(),
            }

    q_feedback: List[Dict[str, Any]] = []
    for item in payload.get("answers") or []:
        if not isinstance(item, dict):
            continue
        qnum = int(item.get("question_number") or 0)
        qidx = int(item.get("question_index") or max(0, qnum - 1))
        merged = q_fb_by_num.get(qnum) or {}
        q_feedback.append(
            {
                "question_index": qidx,
                "question_number": qnum,
                "opic_type": str(
                    merged.get("opic_type") or item.get("opic_type") or ""
                ).strip(),
                "status": str(
                    merged.get("status") or item.get("status") or "응답 부족"
                ).strip(),
                "feedback": str(merged.get("feedback") or "").strip(),
                "better_direction": str(merged.get("better_direction") or "").strip(),
            }
        )
    q_feedback.sort(key=lambda x: int(x.get("question_number") or 0))

    strengths = parsed.get("strengths")
    weaknesses = parsed.get("weaknesses")
    return {
        "ok": True,
        "overall_level": str(parsed.get("overall_level") or "측정 불가").strip(),
        "summary": str(parsed.get("summary") or "").strip(),
        "score_breakdown": breakdown,
        "question_feedback": q_feedback,
        "strengths": [str(s).strip() for s in strengths if str(s).strip()]
        if isinstance(strengths, list)
        else [],
        "weaknesses": [str(s).strip() for s in weaknesses if str(s).strip()]
        if isinstance(weaknesses, list)
        else [],
        "practice_mission": str(parsed.get("practice_mission") or "").strip(),
        "error_category": "",
        "error_message": "",
    }


def _analyze_core(
    answers: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    *,
    api_key: str,
) -> Dict[str, Any]:
    payload = build_mock_v2_report_payload(answers, questions)
    valid_count = int(payload.get("valid_answers_count") or 0)
    total_wc = int(payload.get("total_word_count") or 0)
    models = build_mock_v2_report_model_candidates()
    model_hint = models[0] if models else ""

    try:
        logger.info(
            "[MOCK_V2_REPORT_REQUEST] answers_count=%s valid_answers_count=%s "
            "total_word_count=%s model=%s rubric=%s",
            len(answers),
            valid_count,
            total_wc,
            model_hint,
            RUBRIC_VERSION,
        )
    except Exception:
        pass

    if valid_count < MIN_VALID_ANSWERS_FOR_REPORT:
        out = _insufficient_exam_report(payload)
        try:
            logger.info(
                "[MOCK_V2_REPORT_RESULT] ok=%s overall_level=%s error_category=%s",
                out.get("ok"),
                out.get("overall_level"),
                out.get("error_category") or "—",
            )
        except Exception:
            pass
        return out

    rubric = build_mock_v2_rubric_prompt()
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    prompt = rubric + "\n\nStudent data JSON:\n" + payload_json

    parsed, err, model = _call_gemini(api_key, prompt)
    if not parsed:
        category = _classify_gemini_error(err or "")
        message = "analysis_timeout" if category == "timeout" else (err or category)
        try:
            logger.warning(
                "[MOCK_V2_REPORT_RESULT] ok=false overall_level=- error_category=%s "
                "error_message=%s",
                category,
                message,
            )
        except Exception:
            pass
        return _failure(category=category, message=message, timed_out=(category == "timeout"))

    out = _normalize_parsed(parsed, payload=payload)
    apply_speech_rate_to_report(out, payload.get("aggregate_metrics") or {})
    out["model_used"] = model
    try:
        logger.info(
            "[MOCK_V2_REPORT_RESULT] ok=%s overall_level=%s error_category=%s",
            out.get("ok"),
            out.get("overall_level"),
            out.get("error_category") or "—",
        )
    except Exception:
        pass
    return out


def analyze_real_mock_overall_level(
    rows: List[Dict[str, Any]],
    questions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Shared-rubric overall OPIc level for a completed 15-question real mock.

    The real mock grades each question with the legacy hybrid engine
    (services/evaluation), which does NOT apply the shared OPIc rubric gates or the
    downward speech-rate cap. To keep the headline level consistent with mini mock /
    topic practice / script coaching, we re-run the SAME shared rubric used by Mock V2
    over the 15 transcripts and use its overall_level as the authoritative grade.

    Real-mock rows are mapped into the Mock V2 answer payload. duration_seconds is
    left at 0 on purpose: the transcript pipeline estimates duration as word_count/2,
    which (since per-answer words_normalized_90s = wc * 90 / (wc/2) = 180) would push
    every answer into the AL band. With duration 0, the per-answer signal falls back
    to the raw word count, a sane per-answer proxy.
    """
    from services.transcript_analysis_service import normalize_analysis_row

    answers: List[Dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        norm = normalize_analysis_row(r, mode="real_mock")
        transcript = str(norm.get("transcript") or "").strip()
        q_idx = int(norm.get("question_index") or 0)
        answers.append(
            {
                "question_index": q_idx,
                "question_number": q_idx + 1,
                "question_text": str(norm.get("question_text") or ""),
                "transcript": transcript,
                "student_answer": transcript,
                "duration_seconds": 0.0,
                "wpm": 0.0,
                "stt_status": "transcript_ready" if transcript else "",
            }
        )

    if not any(a.get("transcript") for a in answers):
        return _failure(category="insufficient", message="no_usable_answers")

    q_list = questions if isinstance(questions, list) else []
    return analyze_mock_v2_answers(answers, q_list)


def analyze_mock_v2_answers(
    answers: List[Dict[str, Any]],
    questions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Run one Mock V2 final report from saved answer rows (text only).
    Does not read audio blobs. Max 2 API attempts (see REPORT_MAX_ATTEMPTS).
    """
    from utils.secrets import get_gemini_api_key

    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        return _failure(category="api_key", message="missing_api_key")

    q_list = questions if isinstance(questions, list) else []
    started = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            _analyze_core,
            answers,
            q_list,
            api_key=api_key,
        )
        try:
            return future.result(timeout=ANALYSIS_WRAPPER_TIMEOUT_SEC)
        except concurrent.futures.TimeoutError:
            try:
                logger.warning(
                    "[MOCK_V2_REPORT_RESULT] ok=false overall_level=- error_category=timeout"
                )
            except Exception:
                pass
            return _failure(
                category="timeout",
                message="analysis_timeout",
                timed_out=True,
            )
        except Exception as exc:
            try:
                logger.exception(
                    "[MOCK_V2_REPORT_RESULT] ok=false error_category=unknown"
                )
            except Exception:
                pass
            return _failure(
                category="unknown",
                message=f"{type(exc).__name__}: {exc}",
            )
