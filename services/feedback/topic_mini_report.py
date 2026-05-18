"""
Topic-practice mini report — local aggregation from per-answer analysis results.

Does not call Gemini or change scoring.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.feedback.feedback_builder import (
    merge_expression_upgrades_for_display,
    merge_grammar_corrections_for_display,
    safe_get_transcript,
)
from services.feedback.missions import build_next_missions
from services.feedback.structure_feedback import build_structure_feedback
from utils.text_utils import is_real_speech_transcript


def _row_result(row: Dict[str, Any]) -> Dict[str, Any]:
    res = row.get("analysis_result")
    return res if isinstance(res, dict) else {}


def _per_question_issue_note(row: Dict[str, Any]) -> str:
    qn = int(row.get("question_index") or 0) + 1
    status = str(row.get("analysis_status") or "").lower()
    res = _row_result(row)
    diag = str(res.get("diagnosis_status") or status).lower()
    if status == "saved_unanalyzed" or diag == "saved_unanalyzed":
        return f"Q{qn} 답변은 아직 분석되지 않았어요."
    if status in ("pending",) or diag == "analysis_pending":
        return f"Q{qn} 답변 분석이 아직 완료되지 않았어요."
    if status in ("non_english",) or diag == "non_english":
        return f"Q{qn} 답변이 영어가 아닌 언어로 인식되었어요. 영어로 다시 말해보세요."
    if status in ("no_speech", "unclear_speech", "needs_review") or diag in (
        "no_speech",
        "unclear_speech",
        "needs_review",
    ):
        return f"Q{qn} 답변은 영어 발화가 충분히 인식되지 않았어요."
    transcript = safe_get_transcript(res)
    if not is_real_speech_transcript(transcript):
        return f"Q{qn} 답변은 영어 발화가 충분히 인식되지 않았어요."
    return ""


def build_topic_mini_report(
    topic_title: str,
    rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build UI-ready mini report dict from topic practice result rows."""
    ordered = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda x: int(x.get("question_index") or 0),
    )
    issue_notes = [n for n in (_per_question_issue_note(r) for r in ordered) if n]

    transcripts: List[str] = []
    combined_parts: List[str] = []
    ok_count = 0
    for row in ordered:
        res = _row_result(row)
        t = safe_get_transcript(res)
        qtext = str(row.get("question_text") or "")
        if is_real_speech_transcript(t):
            ok_count += 1
            transcripts.append(t)
            combined_parts.append(t)
        elif qtext:
            combined_parts.append(qtext)

    combined = " ".join(combined_parts).strip()
    sample_q = str(ordered[0].get("question_text") or "") if ordered else ""

    structure = build_structure_feedback(combined, sample_q) if combined else {}
    grammar = merge_grammar_corrections_for_display(combined, None)[:4]
    expressions = merge_expression_upgrades_for_display(combined, None)[:4]
    missions = build_next_missions(combined, structure)[:2]

    strengths: List[str] = []
    if ok_count >= 2:
        strengths.append("세 문항 모두 질문 주제에 맞게 답을 이어갔어요.")
    if structure.get("good"):
        strengths.append(str(structure["good"][0]))
    elif ok_count >= 1:
        strengths.append("핵심 내용을 중심으로 답을 시작했어요.")
    if len(strengths) < 2:
        strengths.append("짧은 연습 안에서도 끝까지 말해 본 점이 좋아요.")
    strengths = strengths[:2]

    if ok_count >= 2 and structure.get("good"):
        flow = (
            f"「{topic_title}」 주제로 세 답변을 이어 말했어요. "
            "전체적으로 주제에 맞는 내용이 들어갔고, "
            "세부 설명과 마무리를 조금 더 분명히 하면 한 단계 더 좋아져요."
        )
    elif ok_count >= 1:
        flow = (
            f"「{topic_title}」 주제로 세 답변 중 일부는 잘 들렸어요. "
            "인식되지 않은 답변이 있으면 같은 질문만 다시 녹음해 보세요."
        )
    else:
        flow = (
            f"「{topic_title}」 주제 답변에서 영어 발화가 충분히 인식되지 않았어요. "
            "조용한 곳에서 또렷하게 다시 말해 보세요."
        )

    retry_sentences: List[str] = []
    for row in ordered:
        res = _row_result(row)
        t = safe_get_transcript(res)
        if not is_real_speech_transcript(t):
            continue
        improved = (res.get("improved_answer") or res.get("sample_answer") or "").strip()
        if improved:
            first = improved.split(".")[0].strip()
            if first and not first.endswith("."):
                first += "."
            retry_sentences.append(first)
        elif t:
            snippet = t.split(".")[0].strip()
            if len(snippet) > 20:
                retry_sentences.append(snippet[:120] + ("…" if len(snippet) > 120 else ""))
    if len(retry_sentences) < 3:
        for row in ordered:
            if len(retry_sentences) >= 3:
                break
            q = str(row.get("question_text") or "")
            if q and q not in retry_sentences:
                retry_sentences.append(
                    f"Overall, I'd say {q.rstrip('?').lower()} is important to me."
                )
    retry_sentences = retry_sentences[:3]

    if not missions:
        missions = [
            "각 답변 마지막에 Overall, I'd say... 로 마무리해 보세요.",
            "이유를 말한 뒤 To be more specific,... 으로 예시를 하나 붙여 보세요.",
        ]

    return {
        "topic_title": topic_title,
        "flow_summary": flow,
        "strengths": strengths,
        "grammar_corrections": grammar,
        "expression_upgrades": expressions,
        "structure_missions": missions[:2],
        "retry_sentences": retry_sentences,
        "issue_notes": issue_notes,
        "analyzed_count": ok_count,
    }
