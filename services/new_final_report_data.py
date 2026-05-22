"""Build legacy final-report row/aggregate shapes from Mock V2 exam + AI report."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from services.exam_analytics import (
    _compress_display,
    compute_exam_aggregates,
    parse_level_to_token,
)
from services.stt_service import count_english_words

_MIN_USABLE_WORDS = 5
_QUESTION_COUNT = 15

_MOCK_BREAKDOWN_KEYS = (
    "response_amount",
    "relevance",
    "structure",
    "grammar",
    "vocabulary",
    "naturalness",
)


def breakdown_to_rubric_scores(breakdown: Dict[str, Any]) -> Dict[str, float]:
    """Map Mock V2 six-axis scores to legacy fluency/grammar/lexical/logic rubric."""

    def _score(key: str) -> float:
        try:
            return float(max(0, min(100, breakdown.get(key) or 0)))
        except (TypeError, ValueError):
            return 0.0

    relevance = _score("relevance")
    structure = _score("structure")
    grammar = _score("grammar")
    vocabulary = _score("vocabulary")
    naturalness = _score("naturalness")
    response_amount = _score("response_amount")

    logic = round((structure + relevance) / 2.0, 1) if (structure or relevance) else 0.0
    fluency = round((naturalness * 0.65 + response_amount * 0.35), 1)
    return {
        "fluency": fluency,
        "grammar": round(grammar, 1),
        "lexical": round(vocabulary, 1),
        "logic": logic,
    }


def breakdown_to_semantic_dimensions(breakdown: Dict[str, Any]) -> Dict[str, float]:
    """Semantic radar fields expected by final-report UI and aggregates."""

    def _score(key: str) -> float:
        try:
            return float(max(0, min(100, breakdown.get(key) or 0)))
        except (TypeError, ValueError):
            return 0.0

    relevance = _score("relevance")
    structure = _score("structure")
    grammar = _score("grammar")
    naturalness = _score("naturalness")
    response_amount = _score("response_amount")
    elaboration = round((relevance + structure) / 2.0, 1)
    return {
        "semantic_density": relevance,
        "discourse_continuity": structure,
        "narrative_depth": response_amount,
        "elaboration_quality": elaboration,
        "spontaneity_score": naturalness,
        "naturalness": naturalness,
        "tense_stability": round(grammar * 0.92, 1),
        "repetition_ratio": max(20.0, min(75.0, 100.0 - naturalness * 0.45)),
    }


def breakdown_to_radar_dimensions(breakdown: Dict[str, Any]) -> Dict[str, float]:
    sem = breakdown_to_semantic_dimensions(breakdown)
    return {
        key.replace("_", " ").title(): float(val)
        for key, val in sem.items()
        if key != "repetition_ratio"
    }


def _level_display_from_report(overall_level: str) -> Tuple[str, str]:
    raw = str(overall_level or "").strip()
    if not raw:
        return "측정 불가 · 응답 부족", "UNKNOWN"
    if "응답" in raw:
        return "응답 부족", "NO_SPEECH"
    tok = parse_level_to_token(raw)
    if tok:
        return _compress_display(tok), tok
    return raw, "UNKNOWN"


def _feedback_by_question_number(
    report: Optional[Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    if not isinstance(report, dict):
        return out
    for item in report.get("question_feedback") or []:
        if not isinstance(item, dict):
            continue
        try:
            qnum = int(item.get("question_number") or 0)
        except (TypeError, ValueError):
            qnum = 0
        if qnum <= 0:
            try:
                qnum = int(item.get("question_index") or 0) + 1
            except (TypeError, ValueError):
                continue
        out[qnum] = item
    return out


def _row_is_gradable(answer: Dict[str, Any], fb_status: str) -> bool:
    text = str(
        answer.get("student_answer") or answer.get("transcript") or ""
    ).strip()
    wc = int(answer.get("word_count") or 0) or count_english_words(text)
    stt = str(answer.get("stt_status") or "")
    status = str(answer.get("status") or "")
    if fb_status in ("응답 부족", "음성 인식 실패", "insufficient_response"):
        return False
    if status in ("recording_failed", "stt_failed", "stt_pending"):
        return False
    if stt == "transcript_ready" and wc >= _MIN_USABLE_WORDS:
        return True
    return wc >= _MIN_USABLE_WORDS and bool(text)


def _build_result_blob(
    answer: Dict[str, Any],
    *,
    exam_breakdown: Dict[str, Any],
    overall_level: str,
    fb: Dict[str, Any],
) -> Dict[str, Any]:
    text = str(
        answer.get("student_answer") or answer.get("transcript") or ""
    ).strip()
    fb_status = str(fb.get("status") or answer.get("status") or "")
    gradable = _row_is_gradable(answer, fb_status)

    rubric = breakdown_to_rubric_scores(exam_breakdown)
    sem = breakdown_to_semantic_dimensions(exam_breakdown)
    try:
        wpm = float(answer.get("wpm") or 0.0)
    except (TypeError, ValueError):
        wpm = 0.0
    wc = int(answer.get("word_count") or 0) or count_english_words(text)
    try:
        duration = float(answer.get("duration_seconds") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    sent_est = max(1.0, round(wc / 12.0, 1)) if wc else 0.0
    filler_est = max(0.0, min(12.0, round((100 - sem.get("naturalness", 50)) / 14.0, 1)))

    feedback = str(fb.get("feedback") or "").strip()
    better = str(fb.get("better_direction") or "").strip()
    prescription = better or "구체적 예시와 연결어를 추가해 답을 한 단계 확장해 보세요."

    if not gradable:
        if fb_status in ("음성 인식 실패",) or str(answer.get("stt_status") or "") == "stt_failed":
            return {
                "diagnosis_status": "analysis_pending",
                "analysis_status": "pending",
                "analysis_pending": True,
                "transcript": text,
                "stt_status": str(answer.get("stt_status") or "stt_failed"),
                "semantic_feedback": feedback or "음성 인식이 완료되지 않아 상세 피드백이 제한됩니다.",
                "summary_speech_rehab": feedback or "STT를 다시 시도하거나 마이크 환경을 확인해 주세요.",
                "prescription": prescription,
                "is_gradable": False,
            }
        return {
            "diagnosis_status": "no_speech",
            "analysis_status": "no_speech",
            "no_speech_detected": True,
            "insufficient_response": True,
            "stt_status": "insufficient_response",
            "transcript": "",
            "semantic_feedback": feedback or "응답이 충분하지 않았어요.",
            "summary_speech_rehab": feedback or "최소 20~30초 이상 영어로 답변해 주세요.",
            "prescription": prescription,
            "is_gradable": False,
        }

    fg = round(sum(rubric.values()) / max(len(rubric), 1), 1)
    lvl_tok = parse_level_to_token(overall_level) or "IM2"
    disp = _compress_display(lvl_tok) if parse_level_to_token(overall_level) else overall_level

    return {
        "diagnosis_status": "ok",
        "analysis_status": "completed",
        "is_gradable": True,
        "transcript": text,
        "semantic_feedback": feedback or "—",
        "summary_speech_rehab": (feedback[:120] + "…") if len(feedback) > 120 else (feedback or "—"),
        "prescription": prescription,
        "estimated_level": lvl_tok,
        "estimated_level_display": disp,
        "final_grade_score": fg,
        "rubric_scores": rubric,
        "semantic_dimensions": sem,
        "metrics": {
            "wpm": wpm,
            "sentence_count": sent_est,
            "filler_hits": filler_est,
            "word_count": float(wc),
        },
        "wpm": wpm,
        "grading_rule_flags": {},
    }


def build_mock_v2_exam_results(
    answers: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    report: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Convert Mock V2 answers + optional Gemini report into legacy ``results`` rows."""
    report = report if isinstance(report, dict) else {}
    exam_bd = report.get("score_breakdown")
    if not isinstance(exam_bd, dict):
        exam_bd = {}
    overall_level = str(report.get("overall_level") or "").strip()
    fb_map = _feedback_by_question_number(report)

    q_by_idx: Dict[int, Dict[str, Any]] = {}
    for q in questions:
        if not isinstance(q, dict):
            continue
        try:
            q_by_idx[int(q.get("question_index", -1))] = q
        except (TypeError, ValueError):
            continue

    ans_by_idx: Dict[int, Dict[str, Any]] = {}
    for row in answers:
        if not isinstance(row, dict):
            continue
        try:
            ans_by_idx[int(row.get("question_index", -1))] = row
        except (TypeError, ValueError):
            continue

    indices = sorted(set(q_by_idx.keys()) | set(ans_by_idx.keys()))
    if not indices:
        indices = list(range(_QUESTION_COUNT))

    items: List[Dict[str, Any]] = []
    for idx in indices:
        q = q_by_idx.get(idx, {})
        ans = ans_by_idx.get(idx, {})
        qnum = int(
            ans.get("question_number") or q.get("question_number") or (idx + 1)
        )
        fb = fb_map.get(qnum, {})
        topic = str(ans.get("topic") or q.get("topic") or "—")
        qtype = str(
            ans.get("opic_type") or q.get("opic_type") or q.get("combo") or "—"
        )
        result = _build_result_blob(
            ans,
            exam_breakdown=exam_bd,
            overall_level=overall_level,
            fb=fb,
        )
        items.append(
            {
                "q_id": qnum,
                "question_index": idx,
                "question": str(
                    ans.get("question_text") or q.get("question_text") or ""
                ),
                "type": qtype,
                "topic": topic,
                "result": result,
            }
        )
    return items


def merge_report_into_aggregates(
    agg: Dict[str, Any],
    report: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Overlay Gemini Mock V2 summary onto rule-based aggregates."""
    if not isinstance(report, dict) or not report.get("ok"):
        return agg
    out = dict(agg)
    disp, raw = _level_display_from_report(str(report.get("overall_level") or ""))
    if disp:
        out["overall_display"] = disp
        out["overall_raw"] = raw

    bd = report.get("score_breakdown")
    if isinstance(bd, dict) and bd:
        rubric = breakdown_to_rubric_scores(bd)
        if any(rubric.values()):
            out["rubric_averages"] = rubric
        radar = breakdown_to_radar_dimensions(bd)
        if radar:
            out["radar_dimensions"] = radar

    summary = str(report.get("summary") or "").strip()
    if summary:
        out["mock_v2_summary"] = summary
    return out


def build_mock_v2_final_bundle(
    answers: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    report: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Results list + aggregates dict for ``views/new_final_report``."""
    results = build_mock_v2_exam_results(answers, questions, report)
    agg = compute_exam_aggregates(results)
    agg = merge_report_into_aggregates(agg, report)
    return {"results": results, "analytics": agg, "report": report or {}}
