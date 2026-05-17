"""
Student-facing feedback post-processing — read-only transforms on analysis results.

Does NOT compute scores, levels, WPM, rubric values, or call Gemini.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.feedback.coach_copy import build_coach_summary, collect_transcript_strengths
from services.feedback.improved_answer import build_improved_answer
from services.feedback.missions import build_next_missions
from services.feedback.structure_feedback import build_structure_feedback  # re-exported API
from services.feedback.transcript_rules import (
    extract_expression_upgrades,
    extract_grammar_corrections,
)

GRAMMAR_EMPTY_WITH_ALT = (
    "큰 문법 오류는 많지 않았어요. 대신 표현을 조금 더 자연스럽게 다듬어 볼 수 있어요."
)
GRAMMAR_EMPTY_DEFAULT = (
    "큰 문법 오류는 많지 않았어요. 대신 표현을 조금 더 자연스럽게 다듬어 볼 수 있어요."
)
EXPRESSION_EMPTY_DEFAULT = (
    "눈에 띄는 평이한 표현은 적었어요. 다음엔 구체적인 형용사를 한 번 더 써 보세요."
)

_RUBRIC_LABELS = {
    "fluency": "유창성 · 리듬",
    "lexical": "어휘 다양성",
    "logic": "논리 전개",
    "grammar": "문법 안정감",
}


def safe_get_transcript(result: Optional[Dict[str, Any]]) -> str:
    if not isinstance(result, dict):
        return ""
    for key in (
        "transcript",
        "restored_transcript",
        "heard_text",
        "answer_text",
        "raw_transcription",
    ):
        chunk = (result.get(key) or "").strip()
        if chunk:
            return chunk
    return ""


def safe_get_metrics(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    out: Dict[str, Any] = {}
    for key in ("wpm", "word_count", "sentence_count"):
        if result.get(key) is not None:
            out[key] = result.get(key)
    audio_metrics = result.get("audio_metrics")
    if isinstance(audio_metrics, dict):
        for key in ("duration_seconds", "duration_method"):
            if audio_metrics.get(key) is not None:
                out[key] = audio_metrics.get(key)
    return out


def safe_get_pronunciation_scores(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    pron = result.get("pronunciation_scores")
    if isinstance(pron, dict) and pron:
        return {k: v for k, v in pron.items() if v is not None}
    sem = result.get("semantic_dimensions")
    if not isinstance(sem, dict):
        return {}
    keys = (
        "pronunciation_clarity",
        "intonation_control",
        "stress_rhythm",
        "linking_naturalness",
    )
    return {k: sem.get(k) for k in keys if sem.get(k) is not None}


def safe_get_existing_feedback(result: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not isinstance(result, dict):
        return {}
    return {
        "summary_speech_rehab": (result.get("summary_speech_rehab") or "").strip(),
        "semantic_feedback": (result.get("semantic_feedback") or "").strip(),
        "prescription": (result.get("prescription") or "").strip(),
        "pronunciation_feedback": (result.get("pronunciation_feedback") or "").strip(),
        "tense_appropriateness_feedback": (
            result.get("tense_appropriateness_feedback") or ""
        ).strip(),
    }


def _collect_strengths(
    result: Dict[str, Any],
    transcript: str = "",
) -> List[str]:
    """Transcript-first encouraging bullets; scores only as light fallback."""
    out = collect_transcript_strengths((transcript or "").strip())
    if len(out) >= 2:
        return out[:4]

    rs = result.get("rubric_scores") or {}
    if isinstance(rs, dict):
        for key, label in _RUBRIC_LABELS.items():
            raw = rs.get(key)
            try:
                v = float(raw)
            except (TypeError, ValueError):
                continue
            if v >= 78:
                line = f"{label} 쪽에서 균형이 좋았어요."
                if line not in out:
                    out.append(line)
                    break

    if not out:
        out.append("질문 주제에 맞게 답을 시작했어요.")
    return out[:4]


def _pronunciation_comment_readonly(result: Dict[str, Any]) -> str:
    """WPM-aware comment wording only — does not change WPM or scores."""
    metrics = safe_get_metrics(result)
    try:
        w = float(metrics.get("wpm") or result.get("wpm") or 0)
    except (TypeError, ValueError):
        w = 0.0

    if w >= 260:
        return (
            "속도가 빠르게 측정됐어요. 실제 말하기 속도뿐 아니라 "
            "녹음 길이 계산이나 문장 인식 방식의 영향도 있을 수 있어요. "
            "다음 답변에서는 문장 끝마다 0.5초 정도 쉬어 주세요."
        )
    if w >= 220:
        return (
            "속도가 상당히 빠르게 측정됐어요. 실제 말하기 속도라기보다 "
            "짧은 시간에 문장이 몰려 인식되었을 가능성도 있어요. "
            "다음 답변에서는 문장 끝마다 0.5초 쉬어 주세요."
        )
    if w >= 185:
        return (
            "속도가 빠른 편으로 측정됐어요. 숨을 한 번 넣고 강조할 단어만 "
            "살짝 늘리면 더 안정적으로 들려요."
        )
    if 0 < w < 70:
        return (
            "속도가 다소 느린 편이에요. 자연스러운 리듬을 위해 "
            "문장 사이에 짧은 쉼을 넣어 보세요."
        )

    existing = safe_get_existing_feedback(result)
    base = existing.get("pronunciation_feedback") or ""
    if base and "너무 빠르" not in base and "빠른 편" not in base:
        return base

    pron = safe_get_pronunciation_scores(result)
    if pron:
        try:
            avg = sum(float(v) for v in pron.values()) / max(len(pron), 1)
        except (TypeError, ValueError):
            avg = 0.0
        if avg >= 75:
            return (
                "발음·리듬이 비교적 안정적이에요. 문장 끝을 살짝 내려 말하면 "
                "더 차분하게 들려요."
            )

    return (
        "발음은 전반적으로 이해 가능한 수준이에요. "
        "문장 끝을 너무 올리지 않고 살짝 내려 말하면 차분하게 들려요."
    )


def _grammar_key(row: Dict[str, Any]) -> str:
    return (
        (row.get("before") or row.get("wrong") or "").strip().lower()
    )


def _expression_key(row: Dict[str, Any]) -> str:
    return (row.get("before") or row.get("phrase") or "").strip().lower()


def _normalize_grammar_row(row: Dict[str, Any]) -> Dict[str, str]:
    before = (row.get("before") or row.get("wrong") or "").strip()
    after = (row.get("after") or row.get("right") or "").strip()
    reason = (row.get("reason") or row.get("note") or "").strip()
    return {
        "before": before,
        "after": after,
        "reason": reason,
        "wrong": before,
        "right": after,
        "note": reason,
    }


def _normalize_expression_row(row: Dict[str, Any]) -> Dict[str, Any]:
    before = (row.get("before") or row.get("phrase") or "").strip()
    better = row.get("better") or row.get("alternatives") or []
    if isinstance(better, str):
        better = [better]
    if not isinstance(better, list):
        better = []
    alts = [str(b).strip() for b in better if str(b).strip()]
    reason = (row.get("reason") or row.get("note") or "").strip()
    return {
        "before": before,
        "better": alts,
        "reason": reason,
        "phrase": before,
        "alternatives": alts,
        "note": reason,
    }


def merge_grammar_corrections_for_display(
    transcript: str,
    result: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, str]]:
    """Rule-based + legacy detectors + optional AI rows from result."""
    from utils.coaching_feedback import merge_grammar_hits
    from utils.grammar_corrections import detect_grammar_corrections

    text = (transcript or "").strip()
    res = result if isinstance(result, dict) else {}
    seen: set[str] = set()
    out: List[Dict[str, str]] = []

    def append(row: Dict[str, Any]) -> None:
        if len(out) >= 4:
            return
        norm = _normalize_grammar_row(row)
        key = _grammar_key(norm)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(norm)

    for row in extract_grammar_corrections(text):
        append(row)
    for row in detect_grammar_corrections(text):
        append(row)
    for row in merge_grammar_hits(text, res):
        append(row)

    return out[:4]


def merge_expression_upgrades_for_display(
    transcript: str,
    result: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Rule-based + legacy detectors + optional AI rows from result."""
    from utils.coaching_feedback import merge_alt_hits
    from utils.grammar_corrections import detect_alternative_expressions

    text = (transcript or "").strip()
    res = result if isinstance(result, dict) else {}
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []

    def append(row: Dict[str, Any]) -> None:
        if len(out) >= 4:
            return
        norm = _normalize_expression_row(row)
        key = _expression_key(norm)
        if not key or key in seen:
            return
        seen.add(key)
        out.append(norm)

    for row in extract_expression_upgrades(text):
        append(row)
    for row in detect_alternative_expressions(text):
        append(row)
    for row in merge_alt_hits(text, res):
        append(row)

    return out[:4]


def grammar_empty_message(
    expression_upgrades: Optional[List[Dict[str, Any]]] = None,
    *,
    grammar_hits: Optional[List[Dict[str, str]]] = None,
) -> str:
    if grammar_hits:
        return ""
    if expression_upgrades:
        return GRAMMAR_EMPTY_WITH_ALT
    return GRAMMAR_EMPTY_DEFAULT


def expression_empty_message(
    expression_upgrades: Optional[List[Dict[str, Any]]] = None,
) -> str:
    if expression_upgrades:
        return ""
    return EXPRESSION_EMPTY_DEFAULT


def _expression_upgrades_from_hits(alt_hits: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in alt_hits:
        if not isinstance(row, dict):
            continue
        phrase = (row.get("phrase") or row.get("before") or "").strip()
        alts = row.get("alternatives") or row.get("better") or []
        if isinstance(alts, str):
            alts = [alts]
        if not isinstance(alts, list):
            alts = []
        out.append(
            {
                "phrase": phrase,
                "alternatives": [str(a).strip() for a in alts if str(a).strip()],
                "note": (row.get("note") or row.get("why") or "").strip(),
            }
        )
    return out


def build_student_feedback(
    result: dict,
    transcript: str = "",
    question_text: str = "",
) -> dict:
    """
    Organize existing analysis + transcript into a UI-ready feedback bundle.

    Post-processing only — does not alter scores or call Gemini.
    """
    res = result if isinstance(result, dict) else {}
    text = (transcript or safe_get_transcript(res) or "").strip()

    grammar_corrections = merge_grammar_corrections_for_display(text, res)
    expression_upgrades = merge_expression_upgrades_for_display(text, res)
    structure_feedback = build_structure_feedback(
        text, question_text=(question_text or "").strip()
    )
    coach_title, coach_body = build_coach_summary(
        text,
        grammar_corrections=grammar_corrections,
        expression_upgrades=expression_upgrades,
        structure_feedback=structure_feedback,
    )
    coach_summary = coach_body.strip()
    if coach_title:
        coach_summary = (
            f"{coach_title}\n{coach_summary}" if coach_summary else coach_title
        )

    metrics = safe_get_metrics(res)
    if not coach_body.strip():
        existing = safe_get_existing_feedback(res)
        for block in (
            existing["summary_speech_rehab"],
            existing["semantic_feedback"],
        ):
            if block and not any(
                b in block
                for b in (
                    "오늘 답변, 전체적으로 좋은 흐름",
                    "천천히 말하려는 태도",
                )
            ):
                coach_body = block.strip()[:360]
                coach_summary = (
                    f"{coach_title}\n{coach_body}" if coach_title else coach_body
                )
                break

    improved_answer = build_improved_answer(
        text,
        question_text=(question_text or "").strip(),
        grammar_corrections=grammar_corrections,
        expression_upgrades=expression_upgrades,
        structure_feedback=structure_feedback,
    )
    wpm_val = metrics.get("wpm", res.get("wpm"))
    next_missions = build_next_missions(
        text,
        grammar_corrections=grammar_corrections,
        expression_upgrades=expression_upgrades,
        structure_feedback=structure_feedback,
        wpm=wpm_val,
    )
    pronunciation_comment = _pronunciation_comment_readonly(res)
    existing = safe_get_existing_feedback(res)

    return {
        "coach_title": coach_title,
        "coach_body": coach_body,
        "coach_summary": coach_summary,
        "strengths": _collect_strengths(res, text),
        "grammar_corrections": grammar_corrections,
        "expression_upgrades": expression_upgrades,
        "grammar_empty_message": grammar_empty_message(expression_upgrades, grammar_hits=grammar_corrections),
        "expression_empty_message": expression_empty_message(expression_upgrades),
        "structure_feedback": structure_feedback,
        "improved_answer": improved_answer,
        "pronunciation_comment": pronunciation_comment,
        "next_missions": next_missions,
        "question_text": (question_text or "").strip(),
        "metrics": safe_get_metrics(res),
        "existing_feedback": existing,
    }
