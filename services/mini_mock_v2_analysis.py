"""Gemini diagnostic report for Mini Mock V2 — transcript text only, no raw audio."""

from __future__ import annotations

import concurrent.futures
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from services.stt_service import count_english_words
from utils.text_utils import is_real_speech_transcript

logger = logging.getLogger(__name__)

ANALYSIS_TIMEOUT_SEC = 60
MIN_USABLE_WORDS = 5

_SCORE_KEYS = (
    "response_amount",
    "relevance",
    "structure",
    "grammar",
    "vocabulary",
    "naturalness",
)


def _empty_score_breakdown() -> Dict[str, int]:
    return {k: 0 for k in _SCORE_KEYS}


def _student_answer_text(row: Dict[str, Any]) -> str:
    val = str(row.get("student_answer") or "").strip()
    if val:
        return val
    for key in ("transcript", "placeholder_text", "stt_transcript"):
        val = str(row.get(key) or "").strip()
        if val:
            return val
    return ""


def _row_analysis_status(row: Dict[str, Any], text: str) -> str:
    """Whether a saved row is sent to Gemini as analyzable."""
    word_count = count_english_words(text)
    if word_count < MIN_USABLE_WORDS:
        return "insufficient_response"
    if str(row.get("stt_status") or "").strip() == "manual_text":
        return "saved"
    raw_status = str(row.get("status") or "saved").strip().lower()
    if not text or raw_status == "insufficient_response":
        return "insufficient_response"
    if not is_real_speech_transcript(text):
        return "insufficient_response"
    return "saved"


def _log_v2_analysis_input(
    answers: List[Dict[str, Any]],
    inputs: List[Dict[str, Any]],
) -> None:
    """Per-answer lengths before Gemini; full text only when show_dev_debug."""
    show_full = False
    try:
        import streamlit as st

        show_full = bool(st.session_state.get("show_dev_debug"))
    except Exception:
        pass
    try:
        for row in sorted(
            [a for a in answers if isinstance(a, dict)],
            key=lambda x: int(x.get("question_index") or 0),
        ):
            q_idx = int(row.get("question_index") or 0)
            q_display = q_idx + 1
            transcript = str(row.get("transcript") or "")
            raw_transcript = str(row.get("raw_transcript") or "")
            student_answer = str(row.get("student_answer") or "")
            answer_text = str(row.get("answer_text") or "")
            audio_bytes = row.get("audio_bytes")
            audio_len = 0
            try:
                audio_len = int(row.get("audio_len") or 0)
            except (TypeError, ValueError):
                audio_len = 0
            if audio_len <= 0 and audio_bytes is not None:
                try:
                    audio_len = len(audio_bytes)
                except Exception:
                    audio_len = 0
            resolved = _student_answer_text(row)
            logger.info(
                "[MINI_V2_ANALYSIS_INPUT] q=%s status=%s student_answer_len=%s "
                "transcript_len=%s raw_transcript_len=%s answer_text_len=%s "
                "audio_len=%s audio_saved=%s resolved_text_len=%s",
                q_display,
                row.get("status"),
                len(student_answer),
                len(transcript),
                len(raw_transcript),
                len(answer_text),
                audio_len,
                row.get("audio_saved"),
                len(resolved),
            )
            if show_full and resolved:
                logger.debug(
                    "[MINI_V2_ANALYSIS_INPUT] q=%s resolved_text_preview=%s",
                    q_display,
                    resolved[:500],
                )
        for item in inputs:
            logger.info(
                "[MINI_V2_ANALYSIS_INPUT] gemini_payload q=%s status=%s student_answer_len=%s",
                item.get("question_index"),
                item.get("status"),
                len(str(item.get("student_answer") or "")),
            )
    except Exception:
        logger.debug("[MINI_V2_ANALYSIS_INPUT] log_failed", exc_info=True)


def build_mini_mock_v2_analysis_inputs(answers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Shape answers for Gemini — no audio blobs."""
    items: List[Dict[str, Any]] = []
    for row in sorted(
        [a for a in answers if isinstance(a, dict)],
        key=lambda x: int(x.get("question_index") or 0),
    ):
        text = _student_answer_text(row)
        status = _row_analysis_status(row, text)
        if status == "insufficient_response":
            text = ""
        q_idx = int(row.get("question_index") or 0)
        items.append(
            {
                "question_index": q_idx + 1,
                "question_type": str(row.get("question_type") or ""),
                "question_text": str(row.get("question_text") or ""),
                "student_answer": text,
                "status": status,
            }
        )
    return items


def _all_insufficient_report(inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    q_feedback = []
    for item in inputs:
        q_feedback.append(
            {
                "question_index": int(item.get("question_index") or 0),
                "status": "insufficient_response",
                "feedback": "답변 텍스트가 없거나 분량이 부족해 이 문항은 상세 피드백을 제공하지 않았습니다.",
                "better_direction": "20~30초 이상 영어로 답변한 뒤 다시 시도해 주세요.",
            }
        )
    return {
        "ok": True,
        "overall_level": "응답 부족",
        "summary": "답변량이 부족해 정상적인 등급 산정이 어렵습니다.",
        "score_breakdown": _empty_score_breakdown(),
        "question_feedback": q_feedback,
        "practice_mission": (
            "세 문항 모두 영어로 20~30초 이상 답변한 뒤, 다시 5분 진단을 받아 보세요."
        ),
        "strengths": [],
        "weaknesses": ["답변 분량 부족"],
        "sample_upgrade_direction": "",
        "error_category": "",
        "error_message": "",
        "all_insufficient": True,
    }


def _build_gemini_prompt(inputs: List[Dict[str, Any]]) -> str:
    lines = [
        "You are an expert OPIc (Oral Proficiency Interview - computer) speaking coach for Korean learners.",
        "Evaluate THREE mini mock answers using standard OPIc-style criteria.",
        "Use ONLY the student_answer text provided. Do NOT invent transcripts.",
        "Write feedback in Korean. estimated levels use OPIc bands: NH, IL, IM1, IM2, IM3, IH, AL.",
        "",
        "Evaluation criteria (apply across all answers):",
        "1. Overall estimated OPIc level",
        "2. Response amount (quantity / development)",
        "3. Question relevance",
        "4. Answer structure (organization, discourse)",
        "5. Grammar control",
        "6. Vocabulary range",
        "7. Naturalness / conversational flow",
        "8. Repetition (penalize excessive repetition)",
        "9. Strengths",
        "10. Weaknesses",
        "11. Next practice mission",
        "12. Sample upgraded answer direction (brief, not a full script)",
        "",
        "For items with status insufficient_response: do NOT fabricate grammar fixes; "
        'set feedback to note insufficient response only.',
        "",
        "Return ONLY one JSON object (no markdown fences):",
        "{",
        '  "overall_level": "<NH|IL|IM1|IM2|IM3|IH|AL or Korean label>",',
        '  "summary": "<2-4 Korean sentences>",',
        '  "score_breakdown": {',
        '    "response_amount": <0-100 integer>,',
        '    "relevance": <0-100 integer>,',
        '    "structure": <0-100 integer>,',
        '    "grammar": <0-100 integer>,',
        '    "vocabulary": <0-100 integer>,',
        '    "naturalness": <0-100 integer>',
        "  },",
        '  "question_feedback": [',
        "    {",
        '      "question_index": 1,',
        '      "status": "saved|insufficient_response",',
        '      "feedback": "<Korean>",',
        '      "better_direction": "<Korean upgrade hint>"',
        "    }",
        "  ],",
        '  "strengths": ["...", "..."],',
        '  "weaknesses": ["...", "..."],',
        '  "practice_mission": "<one concrete Korean mission>",',
        '  "sample_upgrade_direction": "<short Korean direction>"',
        "}",
        "",
        "Student answers JSON:",
        json.dumps(inputs, ensure_ascii=False, indent=2),
    ]
    return "\n".join(lines)


def _normalize_parsed(
    parsed: Dict[str, Any],
    *,
    inputs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    breakdown_raw = parsed.get("score_breakdown")
    breakdown: Dict[str, int] = _empty_score_breakdown()
    if isinstance(breakdown_raw, dict):
        for key in _SCORE_KEYS:
            try:
                breakdown[key] = max(0, min(100, int(breakdown_raw.get(key) or 0)))
            except (TypeError, ValueError):
                breakdown[key] = 0

    q_fb_raw = parsed.get("question_feedback")
    q_feedback: List[Dict[str, Any]] = []
    if isinstance(q_fb_raw, list):
        for item in q_fb_raw:
            if not isinstance(item, dict):
                continue
            try:
                qn = int(item.get("question_index") or 0)
            except (TypeError, ValueError):
                qn = 0
            q_feedback.append(
                {
                    "question_index": qn,
                    "status": str(item.get("status") or "saved"),
                    "feedback": str(item.get("feedback") or "").strip(),
                    "better_direction": str(item.get("better_direction") or "").strip(),
                }
            )

    if not q_feedback:
        for item in inputs:
            qn = int(item.get("question_index") or 0)
            st = str(item.get("status") or "saved")
            q_feedback.append(
                {
                    "question_index": qn,
                    "status": st,
                    "feedback": "",
                    "better_direction": "",
                }
            )

    strengths = parsed.get("strengths")
    weaknesses = parsed.get("weaknesses")
    return {
        "ok": True,
        "overall_level": str(parsed.get("overall_level") or "측정 불가").strip(),
        "summary": str(parsed.get("summary") or "").strip(),
        "score_breakdown": breakdown,
        "question_feedback": q_feedback,
        "practice_mission": str(parsed.get("practice_mission") or "").strip(),
        "strengths": [str(s).strip() for s in strengths if str(s).strip()]
        if isinstance(strengths, list)
        else [],
        "weaknesses": [str(s).strip() for s in weaknesses if str(s).strip()]
        if isinstance(weaknesses, list)
        else [],
        "sample_upgrade_direction": str(parsed.get("sample_upgrade_direction") or "").strip(),
        "error_category": "",
        "error_message": "",
        "all_insufficient": False,
    }


def _failure(
    *,
    category: str,
    message: str,
    timed_out: bool = False,
    quota: bool = False,
) -> Dict[str, Any]:
    return {
        "ok": False,
        "overall_level": "",
        "summary": "",
        "score_breakdown": _empty_score_breakdown(),
        "question_feedback": [],
        "practice_mission": "",
        "strengths": [],
        "weaknesses": [],
        "sample_upgrade_direction": "",
        "error_category": category,
        "error_message": message,
        "timed_out": timed_out,
        "quota": quota,
        "all_insufficient": False,
    }


def _call_gemini(api_key: str, prompt: str) -> Tuple[Optional[Dict[str, Any]], str, str]:
    from services.transcript_analysis_service import _gemini_text_json

    return _gemini_text_json(api_key, prompt, path="mini_mock_v2_report")


def _analyze_core(answers: List[Dict[str, Any]], *, api_key: str) -> Dict[str, Any]:
    inputs = build_mini_mock_v2_analysis_inputs(answers)
    _log_v2_analysis_input(answers, inputs)
    usable = [i for i in inputs if i.get("status") == "saved"]
    if not usable:
        try:
            logger.info("[MINI_MOCK_V2_ANALYSIS] all_insufficient count=%s", len(inputs))
        except Exception:
            pass
        return _all_insufficient_report(inputs)

    prompt = _build_gemini_prompt(inputs)
    parsed, err, model = _call_gemini(api_key, prompt)
    if not parsed:
        err_l = (err or "").lower()
        quota = "429" in err_l or "resource_exhausted" in err_l or "quota" in err_l
        try:
            logger.warning(
                "[MINI_MOCK_V2_ANALYSIS] gemini_failed quota=%s err=%s model=%s",
                quota,
                (err or "")[:200],
                model,
            )
        except Exception:
            pass
        category = "quota" if quota else "gemini_failed"
        try:
            logger.warning(
                "[MINI_V2_ANALYSIS_ERROR] category=%s message=%s",
                category,
                (err or "gemini_failed")[:240],
            )
        except Exception:
            pass
        return _failure(
            category=category,
            message=err or "gemini_failed",
            quota=quota,
        )

    out = _normalize_parsed(parsed, inputs=inputs)
    out["model_used"] = model
    try:
        logger.info(
            "[MINI_MOCK_V2_ANALYSIS] ok level=%s usable=%s",
            out.get("overall_level"),
            len(usable),
        )
    except Exception:
        pass
    return out


def analyze_mini_mock_v2_answers(answers: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Run one Gemini diagnostic report from V2 saved answers (text only).
    Hard deadline 60s. Does not read audio blobs.
    """
    from utils.secrets import get_gemini_api_key

    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        try:
            logger.warning(
                "[MINI_V2_ANALYSIS_ERROR] category=missing_api_key message=missing_api_key"
            )
        except Exception:
            pass
        return _failure(category="missing_api_key", message="missing_api_key")

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_analyze_core, answers, api_key=api_key)
        try:
            return future.result(timeout=ANALYSIS_TIMEOUT_SEC)
        except concurrent.futures.TimeoutError:
            try:
                logger.warning("[MINI_MOCK_V2_ANALYSIS] timeout sec=%s", ANALYSIS_TIMEOUT_SEC)
            except Exception:
                pass
            try:
                logger.warning(
                    "[MINI_V2_ANALYSIS_ERROR] category=timeout message=analysis_timeout"
                )
            except Exception:
                pass
            return _failure(
                category="timeout",
                message=f"analysis_timeout_over_{int(ANALYSIS_TIMEOUT_SEC)}s",
                timed_out=True,
            )
        except Exception as exc:
            try:
                logger.exception(
                    "[MINI_V2_ANALYSIS_ERROR] category=unexpected_error message=%s",
                    f"{type(exc).__name__}: {exc}"[:240],
                )
            except Exception:
                pass
            return _failure(
                category="unexpected_error",
                message=f"{type(exc).__name__}: {exc}",
            )
