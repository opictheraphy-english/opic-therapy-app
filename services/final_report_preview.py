"""
Final report preview — built from saved mock results only (no Gemini).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from services.exam_analytics import result_display_status
from services.feedback.feedback_builder import safe_get_transcript
from utils.text_utils import is_real_speech_transcript

_DEFAULT_TOTAL = 15


def _row_counts_as_preview_answered(row: Dict[str, Any]) -> bool:
    """Completion preview tally — pending / saved rows count as answered."""
    if not isinstance(row, dict):
        return False
    if row.get("q_id") is None:
        return False
    res = row.get("result") if isinstance(row.get("result"), dict) else {}
    if not res:
        return True
    ast = str(res.get("analysis_status") or "").lower()
    dst = str(res.get("diagnosis_status") or "").lower()
    if int(res.get("source_audio_size_bytes") or 0) > 0:
        return True
    if ast in (
        "saved_unanalyzed",
        "pending",
        "completed",
        "non_english",
        "unclear_speech",
        "needs_review",
        "no_speech",
        "no_audio",
        "failed",
    ) or dst in (
        "saved_unanalyzed",
        "analysis_pending",
        "ok",
        "non_english",
        "unclear_speech",
        "needs_review",
        "no_speech",
        "no_audio",
        "language_mismatch",
    ):
        return True
    return True


def build_final_report_preview(
    results: List[Dict[str, Any]],
    *,
    total_count: int | None = None,
) -> Dict[str, Any]:
    """
    Aggregate counts and 2–3 coaching preview lines for the completion screen.

    Uses existing per-question ``result`` payloads only — no scoring changes.
    """
    items = [r for r in results if isinstance(r, dict)]
    total = int(total_count) if total_count else _DEFAULT_TOTAL
    if total < 1:
        total = _DEFAULT_TOTAL

    answered_count = sum(1 for row in items if _row_counts_as_preview_answered(row))
    completed_count = 0
    pending_count = 0
    no_speech_count = 0
    unclear_count = 0
    non_english_count = 0
    completed_transcripts: List[str] = []

    for row in items:
        res = row.get("result") if isinstance(row.get("result"), dict) else {}
        status = result_display_status(res)
        if status == "분석 완료":
            completed_count += 1
            tx = safe_get_transcript(res)
            if is_real_speech_transcript(tx):
                completed_transcripts.append(tx)
        elif status in ("분석 대기", "AI 분석 대기 중"):
            pending_count += 1
        elif status in ("음성 미감지", "응답 부족"):
            no_speech_count += 1
        elif status == "말소리 인식 불명확":
            unclear_count += 1
        elif status == "영어 답변 필요":
            non_english_count += 1

    preview_insights = _preview_insights_from_transcripts(completed_transcripts)

    return {
        "answered_count": answered_count,
        "total_count": total,
        "completed_count": completed_count,
        "pending_count": pending_count,
        "no_speech_count": no_speech_count,
        "unclear_count": unclear_count,
        "non_english_count": non_english_count,
        "preview_insights": preview_insights,
        "has_enough_analysis": completed_count >= 3,
    }


def _preview_insights_from_transcripts(transcripts: List[str]) -> List[str]:
    if len(transcripts) < 3:
        return []

    combined = " ".join(transcripts).strip()
    if len(combined) < 40:
        return []

    from services.feedback.coach_copy import collect_transcript_strengths
    from services.feedback.structure_feedback import build_structure_feedback
    from utils.grammar_corrections import detect_alternative_expressions

    insights: List[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        text = (line or "").strip()
        if not text or text in seen or len(insights) >= 3:
            return
        seen.add(text)
        insights.append(text)

    for s in collect_transcript_strengths(combined)[:2]:
        add(s)

    structure = build_structure_feedback(combined, "")
    missing = structure.get("missing")
    if isinstance(missing, list) and missing:
        add(str(missing[0]))
    elif isinstance(missing, str) and missing.strip():
        add(missing.strip())

    nxt = structure.get("next")
    if isinstance(nxt, str) and nxt.strip():
        if "마무리" in nxt or "Overall" in nxt or "마지막" in nxt:
            add("문장 끝을 조금 더 분명하게 마무리하면 좋아요.")
        elif "구체" in nxt or "예시" in nxt or "specific" in nxt.lower():
            add("구체적인 예시는 잘 넣고 있어요.")
        else:
            add(nxt.strip()[:120])

    sents = [s.strip() for s in re.split(r"[.!?]+", combined) if s.strip()]
    if sents and len(sents[-1].split()) < 5:
        add("문장 끝 마무리가 조금 짧은 편이에요.")

    alts = detect_alternative_expressions(combined)
    if alts:
        add("표현 반복을 줄이고 더 구체적인 형용사를 써 보세요.")

    if not insights:
        add("질문 주제에 맞게 답을 이어 간 흐름이 좋아요.")
    return insights[:3]
