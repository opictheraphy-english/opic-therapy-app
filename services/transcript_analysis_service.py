"""Transcript-first mock evaluation — text in, no raw answer audio for scoring."""

from __future__ import annotations

import concurrent.futures
import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from services.evaluation.eval_config import MODEL_NAME
from services.stt_service import count_english_words
from utils.text_utils import is_real_speech_transcript

logger = logging.getLogger(__name__)

MINI_MOCK_REPORT_TIMEOUT_SEC = 60
REAL_MOCK_FINAL_TIMEOUT_SEC = 90
TOPIC_REPORT_TIMEOUT_SEC = 60

MIN_ENGLISH_WORDS_USABLE = 5


def _row_result(row: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(row, dict):
        return {}
    res = row.get("analysis_result")
    if isinstance(res, dict):
        return res
    res = row.get("result")
    return res if isinstance(res, dict) else {}


def normalize_analysis_row(row: Dict[str, Any], *, mode: str = "") -> Dict[str, Any]:
    """Flatten a saved answer row for transcript-based report analysis."""
    res = _row_result(row)
    q_idx = int(row.get("question_index") if row.get("question_index") is not None else res.get("question_index") or 0)
    question_id = str(row.get("question_id") or res.get("question_id") or "")
    question_text = str(
        row.get("question_text")
        or row.get("question")
        or res.get("question_text")
        or ""
    )
    q_type = str(
        row.get("question_type")
        or row.get("type")
        or row.get("question_label")
        or res.get("question_type")
        or ""
    )
    transcript = (res.get("transcript") or row.get("transcript") or "").strip()
    stt_status = str(res.get("stt_status") or row.get("stt_status") or "").strip().lower()
    word_count = int(
        res.get("stt_word_count")
        or res.get("word_count")
        or count_english_words(transcript)
        or 0
    )
    return {
        "mode": mode,
        "question_index": q_idx,
        "question_id": question_id,
        "question_text": question_text,
        "question_type": q_type,
        "transcript": transcript,
        "stt_status": stt_status,
        "word_count": word_count,
        "audio_key": str(row.get("audio_key") or res.get("audio_key") or ""),
        "audio_len": int(row.get("audio_len") or res.get("source_audio_size_bytes") or 0),
        "row": row,
    }


def _classify_row_usability(norm: Dict[str, Any]) -> str:
    """usable | insufficient | pending."""
    stt = str(norm.get("stt_status") or "").lower()
    if stt == "stt_pending":
        return "pending"
    if stt == "insufficient_response":
        return "insufficient"
    transcript = str(norm.get("transcript") or "").strip()
    wc = int(norm.get("word_count") or 0)
    if wc < MIN_ENGLISH_WORDS_USABLE or not is_real_speech_transcript(transcript):
        return "insufficient"
    return "usable"


def _build_transcript_scoring_prompt(
    question_text: str,
    transcript: str,
    *,
    difficulty: int = 5,
) -> str:
    from services.mock_exam.gemini_mock_exam_prompt import build_mock_exam_analysis_prompt

    base = build_mock_exam_analysis_prompt(question_text, difficulty)
    return (
        f"{base}\n\n"
        "[TRANSCRIPT-FIRST MODE — MANDATORY]\n"
        "- The student's answer has ALREADY been transcribed by STT.\n"
        "- Do NOT listen to audio. Do NOT re-transcribe or improve the transcript.\n"
        "- Use EXACTLY this transcript for all scoring and feedback.\n"
        "- In JSON output, set \"transcript\" to the same text as below (verbatim).\n\n"
        f"[STT TRANSCRIPT]\n{transcript.strip()}\n"
    )


def _extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    from services.gemini_json_client import parse_llm_json_response

    parsed, _err = parse_llm_json_response(raw_text, log_tag="TRANSCRIPT_ANALYSIS")
    return parsed


def _gemini_text_json(
    api_key: str,
    prompt: str,
    *,
    path: str = "transcript",
) -> Tuple[Optional[Dict[str, Any]], str, str]:
    from google import genai
    from google.genai import types as genai_types
    from services.evaluation.gemini_multimodal_pipeline import _build_model_candidates

    client = genai.Client(api_key=api_key)
    parts = [genai_types.Part.from_text(text=prompt)]
    contents = [genai_types.Content(role="user", parts=parts)]
    config = genai_types.GenerateContentConfig(temperature=0.25, max_output_tokens=4096)
    last_error = ""
    for candidate in _build_model_candidates():
        try:
            response = client.models.generate_content(
                model=candidate,
                contents=contents,
                config=config,
            )
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            err_text = str(exc)
            if "429" in err_text or "RESOURCE_EXHAUSTED" in err_text:
                return None, last_error, candidate
            if "404" in err_text or "NOT_FOUND" in err_text:
                continue
            continue
        raw_text = (getattr(response, "text", "") or "").strip()
        if not raw_text:
            for cand in getattr(response, "candidates", None) or []:
                content = getattr(cand, "content", None)
                for part in getattr(content, "parts", None) or []:
                    t = getattr(part, "text", None)
                    if t:
                        raw_text = (raw_text + "\n" + t).strip()
        if not raw_text:
            last_error = "empty_response"
            continue
        parsed = _extract_json_object(raw_text)
        if parsed:
            return parsed, "", candidate
        last_error = "json_parse_failed"
    return None, last_error or "gemini_failed", ""


def _estimate_audio_info(transcript: str, source_bytes: int = 0) -> Dict[str, Any]:
    wc = count_english_words(transcript)
    duration = max(8.0, wc / 2.0) if wc else 8.0
    return {
        "duration_seconds": duration,
        "duration_method": "estimated_from_transcript",
        "source_bytes": int(source_bytes or 0),
    }


def _finalize_transcript_analysis(
    parsed: Dict[str, Any],
    *,
    transcript: str,
    question_text: str,
    source_bytes: int = 0,
    model_used: str = "",
) -> Dict[str, Any]:
    from services.evaluation.gemini_multimodal_pipeline import (
        SEMANTIC_KEYS,
        run_hybrid_grading,
    )
    from services.report_service import normalize_result_score_fields
    from utils.language_detection import detect_language_mismatch, language_mismatch_body

    raw_transcription = transcript.strip()
    lang_kind = detect_language_mismatch(raw_transcription)
    if lang_kind:
        preview = raw_transcription[:120]
        grading = run_hybrid_grading(
            _estimate_audio_info("", source_bytes),
            "",
            question_text,
            semantic={},
            q_label=(question_text or "")[:40],
        )
        metrics = grading.get("metrics") or {}
        return normalize_result_score_fields(
            {
                "diagnosis_status": "non_english",
                "analysis_status": "non_english",
                "transcript": "",
                "raw_transcript": raw_transcription,
                "non_english_preview": preview,
                "language_mismatch_kind": lang_kind,
                "estimated_level": "측정 불가",
                "estimated_level_display": "측정 불가",
                "summary_speech_rehab": language_mismatch_body(lang_kind),
                "prescription": language_mismatch_body(lang_kind),
                "wpm": metrics.get("wpm", 0),
                "word_count": 0,
                "sentence_count": 0,
                "model_used": model_used or MODEL_NAME,
                "source_audio_size_bytes": source_bytes,
                "analysis_source": "transcript_text",
            }
        )

    semantic_slice = {k: parsed.get(k) for k in SEMANTIC_KEYS if k in parsed}
    audio_info = _estimate_audio_info(transcript, source_bytes)
    grading = run_hybrid_grading(
        audio_info,
        transcript,
        question_text,
        semantic=semantic_slice,
        q_label=(question_text or "")[:40],
    )
    metrics = grading.get("metrics") or {}
    priority_scores = grading.get("priority_scores") or {}
    sem_flat = grading.get("semantic_dimensions") or {}
    ai_grade_hint = (parsed.get("estimated_level") or "").strip()
    final_level = grading.get("estimated_level") or ai_grade_hint or "측정 불가"
    summary_ai = (parsed.get("feedback") or parsed.get("summary_speech_rehab") or "").strip()
    summary_rule = (grading.get("summary_line") or "").strip()
    summary_parts = [p for p in (summary_ai, summary_rule) if p]
    summary_speech_rehab = " ".join(summary_parts).strip() or "분석 피드백이 비어 있습니다."
    tense_feedback = (grading.get("tense_appropriateness_feedback") or "").strip()
    prescription = " ".join(
        [parsed.get("prescription") or "", summary_speech_rehab, tense_feedback]
    ).strip() or summary_speech_rehab

    out = normalize_result_score_fields(
        {
            "diagnosis_status": "ok",
            "analysis_status": "completed",
            "transcript": transcript,
            "raw_transcript": transcript,
            "estimated_level": final_level,
            "estimated_level_display": grading.get("estimated_level_display") or final_level,
            "summary_speech_rehab": summary_speech_rehab,
            "prescription": prescription,
            "tense_appropriateness_feedback": tense_feedback,
            "wpm": metrics.get("wpm", 0),
            "sentence_count": metrics.get("sentence_count", 0),
            "word_count": metrics.get("word_count", count_english_words(transcript)),
            "fact_scores": {
                "text_type": round(
                    (sem_flat.get("discourse_continuity", 50) + sem_flat.get("narrative_depth", 50)) / 2.0,
                    1,
                ),
                "accuracy": round(sem_flat.get("grammar_score", 50), 1),
            },
            "rubric_scores": {
                "fluency": priority_scores.get("fluency", 0),
                "lexical": priority_scores.get("lexical", 0),
                "logic": priority_scores.get("logic", 0),
                "grammar": priority_scores.get("grammar", 0),
            },
            "priority_scores": dict(priority_scores),
            "semantic_dimensions": sem_flat,
            "semantic_feedback": summary_ai,
            "model_used": model_used or MODEL_NAME,
            "source_audio_size_bytes": source_bytes,
            "question_type": grading.get("question_type", "A"),
            "final_grade_score": grading.get("final_grade_score", 0),
            "analysis_source": "transcript_text",
            "stt_status": "transcript_ready",
            "is_gradable": True,
        }
    )
    return out


def analyze_single_transcript(
    transcript: str,
    question_text: str,
    api_key: str,
    *,
    difficulty: int = 5,
    source_bytes: int = 0,
) -> Tuple[Optional[Dict[str, Any]], str]:
    """One Gemini text scoring call for a single answer transcript."""
    if not api_key:
        return None, "missing_api_key"
    if count_english_words(transcript) < MIN_ENGLISH_WORDS_USABLE:
        return None, "insufficient_transcript"
    prompt = _build_transcript_scoring_prompt(question_text, transcript, difficulty=difficulty)
    parsed, err, model = _gemini_text_json(api_key, prompt, path="single_transcript")
    if not parsed:
        return None, err or "gemini_failed"
    try:
        result = _finalize_transcript_analysis(
            parsed,
            transcript=transcript,
            question_text=question_text,
            source_bytes=source_bytes,
            model_used=model,
        )
        return result, ""
    except Exception as exc:
        logger.exception("Transcript analysis finalize failed")
        return None, f"{type(exc).__name__}: {exc}"


def _insufficient_result(*, source_bytes: int = 0) -> Dict[str, Any]:
    return {
        "analysis_status": "insufficient_response",
        "diagnosis_status": "no_speech",
        "insufficient_response": True,
        "no_speech_detected": True,
        "is_gradable": False,
        "transcript": "",
        "estimated_level": "측정 불가",
        "estimated_level_display": "응답 부족",
        "summary_speech_rehab": "응답이 충분하지 않았어요.",
        "prescription": "다시 녹음할 때는 20~30초 이상 영어로 답변해 주세요.",
        "source_audio_size_bytes": source_bytes,
        "analysis_source": "transcript_text",
        "stt_status": "insufficient_response",
    }


def _run_batch_with_deadline(
    fn: Callable[[], Dict[str, Any]],
    *,
    timeout_sec: float,
) -> Dict[str, Any]:
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout_sec)
        except concurrent.futures.TimeoutError:
            return {
                "ok": False,
                "timed_out": True,
                "error_category": "timeout",
                "error_message": f"analysis_timeout_over_{int(timeout_sec)}s",
            }


def _analyze_rows_core(
    rows: List[Dict[str, Any]],
    *,
    mode: str,
    difficulty: int,
    api_key: str,
    timeout_sec: float,
) -> Dict[str, Any]:
    started = time.time()
    normalized = [normalize_analysis_row(r, mode=mode) for r in rows if isinstance(r, dict)]
    per_question: List[Dict[str, Any]] = []
    usable_count = 0
    insufficient_count = 0
    pending_count = 0

    for norm in normalized:
        usability = _classify_row_usability(norm)
        q_idx = int(norm.get("question_index") or 0)
        base = {
            "question_index": q_idx,
            "question_id": norm.get("question_id") or "",
            "audio_key": norm.get("audio_key") or "",
            "usability": usability,
        }
        if usability == "pending":
            pending_count += 1
            per_question.append({**base, "status": "pending", "result": None})
            continue
        if usability == "insufficient":
            insufficient_count += 1
            per_question.append(
                {
                    **base,
                    "status": "insufficient",
                    "result": _insufficient_result(source_bytes=int(norm.get("audio_len") or 0)),
                }
            )
            continue
        usable_count += 1
        per_question.append({**base, "status": "pending_analysis", "result": None})

    if usable_count == 0:
        return {
            "ok": True,
            "timed_out": False,
            "quota": False,
            "all_insufficient": True,
            "overall_level_display": "응답 부족",
            "usable_count": 0,
            "insufficient_count": insufficient_count,
            "pending_count": pending_count,
            "per_question": per_question,
            "error_category": "",
            "error_message": "",
        }

    if not api_key:
        return {
            "ok": False,
            "all_insufficient": False,
            "error_category": "missing_api_key",
            "error_message": "API key not configured",
            "per_question": per_question,
        }

    for item in per_question:
        if item.get("status") != "pending_analysis":
            continue
        if time.time() - started > timeout_sec:
            return {
                "ok": False,
                "timed_out": True,
                "partial": True,
                "error_category": "timeout",
                "error_message": f"analysis_timeout_over_{int(timeout_sec)}s",
                "per_question": per_question,
                "usable_count": usable_count,
                "insufficient_count": insufficient_count,
            }
        norm = next(
            (n for n in normalized if int(n.get("question_index") or 0) == int(item["question_index"])),
            {},
        )
        transcript = str(norm.get("transcript") or "")
        result, err = analyze_single_transcript(
            transcript,
            str(norm.get("question_text") or ""),
            api_key,
            difficulty=difficulty,
            source_bytes=int(norm.get("audio_len") or 0),
        )
        if result:
            item["status"] = "completed"
            item["result"] = result
        else:
            err_l = (err or "").lower()
            if "429" in err_l or "quota" in err_l or "resource_exhausted" in err_l:
                return {
                    "ok": False,
                    "quota": True,
                    "error_category": "quota_or_rate_limit",
                    "error_message": err,
                    "per_question": per_question,
                }
            item["status"] = "failed"
            item["error"] = err

    completed = sum(1 for p in per_question if p.get("status") == "completed")
    failed = sum(1 for p in per_question if p.get("status") == "failed")
    if failed and completed == 0 and usable_count > 0:
        return {
            "ok": False,
            "error_category": "analysis_failed",
            "error_message": "all_usable_answers_failed",
            "per_question": per_question,
        }

    overall = ""
    if usable_count > 0 and completed == 0:
        overall = "응답 부족" if insufficient_count == len(normalized) else ""
    elif completed > 0:
        from services.exam_analytics import weighted_overall_level

        level_items = [
            {"q_id": int(p["question_index"]) + 1, "result": p["result"]}
            for p in per_question
            if p.get("status") == "completed" and isinstance(p.get("result"), dict)
        ]
        if level_items:
            overall, _ = weighted_overall_level(level_items)

    return {
        "ok": True,
        "timed_out": False,
        "quota": False,
        "all_insufficient": usable_count == 0,
        "overall_level_display": overall or ("응답 부족" if usable_count == 0 else ""),
        "usable_count": usable_count,
        "insufficient_count": insufficient_count,
        "pending_count": pending_count,
        "completed_count": completed,
        "per_question": per_question,
        "error_category": "",
        "error_message": "",
    }


def analyze_mini_mock_transcripts(
    rows: List[Dict[str, Any]],
    *,
    difficulty: int = 5,
    api_key: str | None = None,
) -> Dict[str, Any]:
    if not api_key:
        from utils.secrets import get_gemini_api_key

        api_key = get_gemini_api_key() or ""
    return _run_batch_with_deadline(
        lambda: _analyze_rows_core(
            rows,
            mode="mini_mock",
            difficulty=difficulty,
            api_key=api_key,
            timeout_sec=MINI_MOCK_REPORT_TIMEOUT_SEC,
        ),
        timeout_sec=MINI_MOCK_REPORT_TIMEOUT_SEC + 5,
    )


def analyze_real_mock_transcripts(
    rows: List[Dict[str, Any]],
    *,
    difficulty: int = 5,
    api_key: str | None = None,
) -> Dict[str, Any]:
    if not api_key:
        from utils.secrets import get_gemini_api_key

        api_key = get_gemini_api_key() or ""
    return _run_batch_with_deadline(
        lambda: _analyze_rows_core(
            rows,
            mode="real_mock",
            difficulty=difficulty,
            api_key=api_key,
            timeout_sec=REAL_MOCK_FINAL_TIMEOUT_SEC,
        ),
        timeout_sec=REAL_MOCK_FINAL_TIMEOUT_SEC + 5,
    )


def analyze_topic_practice_transcripts(
    rows: List[Dict[str, Any]],
    *,
    difficulty: int = 5,
    api_key: str | None = None,
) -> Dict[str, Any]:
    """Returns batch metadata; topic full report still built via topic_mini_report text path."""
    if not api_key:
        from utils.secrets import get_gemini_api_key

        api_key = get_gemini_api_key() or ""
    return _run_batch_with_deadline(
        lambda: _analyze_rows_core(
            rows,
            mode="topic_practice",
            difficulty=difficulty,
            api_key=api_key,
            timeout_sec=TOPIC_REPORT_TIMEOUT_SEC,
        ),
        timeout_sec=TOPIC_REPORT_TIMEOUT_SEC + 5,
    )
