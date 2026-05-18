"""Aggregate mini mock results into a concise diagnostic report (no Gemini)."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from services.exam_analytics import result_display_status, weighted_overall_level
from services.feedback.feedback_builder import (
    build_student_feedback,
    safe_get_transcript,
)
from services.final_report_preview import build_final_report_preview
from utils.text_utils import is_real_speech_transcript

_MINI_MOCK_TOTAL = 3

_TYPE_MISSIONS: Dict[str, str] = {
    "description": "묘사: 위치 → 특징 → 좋은 점 순서로 말하기",
    "memorable_experience": "경험: 사건 → 감정 → 배운 점 순서로 말하기",
    "roleplay": "롤플레이: 문제 설명 → 사과/이유 → 대안 제안 순서로 말하기",
}


def _preview_rows_for_builder(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from utils.mini_mock_state import row_result

    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append({"result": row_result(row)})
    return out


def _key_correction(feedback: Dict[str, Any]) -> str:
    grammar = feedback.get("grammar_corrections") or []
    if isinstance(grammar, list) and grammar:
        g0 = grammar[0]
        if isinstance(g0, dict):
            before = (g0.get("before") or g0.get("wrong") or "").strip()
            after = (g0.get("after") or g0.get("right") or "").strip()
            if before and after:
                return f"{before} → {after}"
    expr = feedback.get("expression_upgrades") or []
    if isinstance(expr, list) and expr:
        e0 = expr[0]
        if isinstance(e0, dict):
            phrase = (e0.get("phrase") or e0.get("before") or "").strip()
            alts = e0.get("alternatives") or []
            if phrase and isinstance(alts, list) and alts:
                return f"{phrase} → {str(alts[0]).strip()}"
    return ""


def _collect_fix_now(rows: List[Dict[str, Any]], *, limit: int = 3) -> List[str]:
    bullets: List[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        text = (line or "").strip()
        if not text or text in seen or len(bullets) >= limit:
            return
        seen.add(text)
        bullets.append(text)

    from utils.mini_mock_state import row_result

    for row in rows:
        res = row_result(row)
        if result_display_status(res) != "분석 완료":
            continue
        fb = build_student_feedback(res, question_text=str(row.get("question_text") or ""))
        for g in fb.get("grammar_corrections") or []:
            if not isinstance(g, dict):
                continue
            before = (g.get("before") or g.get("wrong") or "").strip()
            after = (g.get("after") or g.get("right") or "").strip()
            if before and after:
                add(f"문법: {before} → {after}")
        structure = fb.get("structure_feedback")
        if isinstance(structure, dict):
            for m in structure.get("missing") or []:
                add(f"구조: {str(m).strip()}")
        for e in fb.get("expression_upgrades") or []:
            if not isinstance(e, dict):
                continue
            phrase = (e.get("phrase") or e.get("before") or "").strip()
            alts = e.get("alternatives") or []
            if phrase and isinstance(alts, list) and alts:
                add(f"표현: {phrase} → {str(alts[0]).strip()}")
        coach = (fb.get("coach_summary") or fb.get("coach_body") or "").strip()
        if coach and len(coach) > 12:
            add(coach[:140])

    if not bullets:
        bullets.append("완료된 답변에서 눈에 띄는 큰 오류는 많지 않았어요. 다음엔 문장 끝을 조금 더 분명하게 마무리해 보세요.")
    return bullets[:limit]


def _collect_strengths(rows: List[Dict[str, Any]], *, limit: int = 2) -> List[str]:
    bullets: List[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        text = (line or "").strip()
        if not text or text in seen or len(bullets) >= limit:
            return
        seen.add(text)
        bullets.append(text)

    from utils.mini_mock_state import row_result

    for row in rows:
        res = row_result(row)
        if result_display_status(res) != "분석 완료":
            continue
        fb = build_student_feedback(res, question_text=str(row.get("question_text") or ""))
        for s in fb.get("strengths") or []:
            add(str(s))

    if len(bullets) < limit:
        for row in rows:
            res = row_result(row)
            summary = (res.get("summary_speech_rehab") or "").strip()
            if summary and result_display_status(res) == "분석 완료":
                add(summary[:120])
                if len(bullets) >= limit:
                    break

    if not bullets:
        bullets.append("질문 주제에 맞게 답을 이어 간 흐름이 좋아요.")
    return bullets[:limit]


def build_mini_mock_report_data(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build report payload from saved mini-mock rows (existing per-answer results only)."""
    sorted_rows = sorted(
        [r for r in rows if isinstance(r, dict)],
        key=lambda x: int(x.get("question_index") or 0),
    )
    preview = build_final_report_preview(
        _preview_rows_for_builder(sorted_rows),
        total_count=_MINI_MOCK_TOTAL,
    )

    level_items: List[Dict[str, Any]] = []
    per_question: List[Dict[str, Any]] = []

    from utils.mini_mock_state import row_result

    for row in sorted_rows:
        res = row_result(row)
        status = result_display_status(res)
        q_idx = int(row.get("question_index") or 0)
        q_label = str(row.get("question_label") or "")
        q_type = str(row.get("question_type") or "")
        transcript = safe_get_transcript(res)
        if status == "분석 완료" and is_real_speech_transcript(transcript):
            level_items.append({"q_id": q_idx + 1, "result": res})

        short_feedback = ""
        key_correction = ""
        if status == "분석 완료":
            fb = build_student_feedback(
                res, question_text=str(row.get("question_text") or "")
            )
            short_feedback = (fb.get("coach_summary") or fb.get("coach_body") or "").strip()
            if len(short_feedback) > 220:
                short_feedback = short_feedback[:217] + "…"
            key_correction = _key_correction(fb)

        preview_tx = transcript
        if preview_tx and len(preview_tx) > 180:
            preview_tx = preview_tx[:177] + "…"

        per_question.append(
            {
                "question_index": q_idx,
                "question_label": q_label,
                "question_type": q_type,
                "status": status,
                "transcript_preview": preview_tx,
                "short_feedback": short_feedback,
                "key_correction": key_correction,
                "word_count": res.get("word_count"),
                "sentence_count": res.get("sentence_count"),
                "wpm": res.get("wpm"),
                "estimated_level": (
                    res.get("estimated_level_display") or res.get("estimated_level") or ""
                ),
            }
        )

    estimated_display = ""
    estimated_note = "분석 완료된 답변 기준으로 표시됩니다"
    if level_items:
        estimated_display, _raw = weighted_overall_level(level_items)
        estimated_note = ""
    elif preview.get("completed_count", 0) > 0:
        estimated_note = "분석 완료된 답변 기준으로 표시됩니다"

    missions: List[str] = []
    for row in sorted_rows:
        q_type = str(row.get("question_type") or "")
        mission = _TYPE_MISSIONS.get(q_type)
        if mission and mission not in missions:
            missions.append(mission)
    for q_type, mission in _TYPE_MISSIONS.items():
        if mission not in missions:
            missions.append(mission)
        if len(missions) >= 3:
            break

    return {
        "summary": preview,
        "per_question": per_question,
        "strengths": _collect_strengths(sorted_rows, limit=2),
        "fix_now": _collect_fix_now(sorted_rows, limit=3),
        "missions": missions[:3],
        "estimated_level": estimated_display,
        "estimated_level_note": estimated_note,
        "has_pending": int(preview.get("pending_count") or 0) > 0,
        "answered_count": int(preview.get("answered_count") or 0),
    }


def _export_transcript(row: Dict[str, Any], per_q: Dict[str, Any]) -> str:
    from utils.mini_mock_state import row_result

    res = row_result(row) if row else {}
    transcript = safe_get_transcript(res)
    if transcript:
        return transcript
    preview = str(per_q.get("transcript_preview") or "").strip()
    if preview:
        return preview
    return "복원 발화가 아직 준비되지 않았습니다."


def _export_feedback(status: str, per_q: Dict[str, Any]) -> str:
    if status == "분석 완료":
        parts: List[str] = []
        fb = str(per_q.get("short_feedback") or "").strip()
        if fb:
            parts.append(fb)
        corr = str(per_q.get("key_correction") or "").strip()
        if corr:
            parts.append(f"핵심 교정: {corr}")
        if parts:
            return "\n".join(parts)
    if status == "AI 분석 대기 중":
        return "분석 대기 중입니다."
    if status == "영어 답변 필요":
        return "영어로 답변해 주세요."
    if status == "말소리 인식 불명확":
        return "말소리가 불명확합니다. 다시 녹음해 주세요."
    if status in ("음성 미감지", "녹음 없음"):
        return status
    return "분석 대기 중입니다."


def _export_estimated_level(report_data: Dict[str, Any]) -> str:
    level = str(report_data.get("estimated_level") or "").strip()
    if level:
        note = str(report_data.get("estimated_level_note") or "").strip()
        if note:
            return f"{level} ({note})"
        return level
    return "분석 완료 후 표시됩니다."


def build_mini_mock_report_markdown(
    report_data: Dict[str, Any],
    results: List[Dict[str, Any]],
) -> str:
    """Build downloadable Markdown from cached report data — no API calls."""
    from utils.mini_mock_state import row_result

    summary = report_data.get("summary") if isinstance(report_data.get("summary"), dict) else {}
    answered = int(summary.get("answered_count") or report_data.get("answered_count") or 0)
    completed = int(summary.get("completed_count") or 0)
    pending = int(summary.get("pending_count") or 0)
    total = int(summary.get("total_count") or _MINI_MOCK_TOTAL)

    per_q_list = [
        p for p in (report_data.get("per_question") or []) if isinstance(p, dict)
    ]
    per_q_by_idx = {int(p.get("question_index") or 0): p for p in per_q_list}
    rows_sorted = sorted(
        [r for r in results if isinstance(r, dict)],
        key=lambda x: int(x.get("question_index") or 0),
    )

    lines: List[str] = [
        "# 5분 진단 미니 리포트",
        "",
        f"생성일: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## 진단 요약",
        f"- 답변 완료: {answered}/{total}",
        f"- AI 분석 완료: {completed}/{total}",
        f"- 분석 대기: {pending}",
        f"- 예상 레벨: {_export_estimated_level(report_data)}",
        "",
        "## 문항별 결과",
        "",
    ]

    for row in rows_sorted:
        q_idx = int(row.get("question_index") or 0)
        qn = q_idx + 1
        label = str(row.get("question_label") or per_q_by_idx.get(q_idx, {}).get("question_label") or "")
        per_q = per_q_by_idx.get(q_idx, {})
        status = str(per_q.get("status") or result_display_status(row_result(row) if row else {}))
        question_en = str(row.get("question_text") or "").strip()
        question_ko = str(row.get("question_ko") or "").strip()
        transcript = _export_transcript(row, per_q)
        feedback = _export_feedback(status, per_q)

        lines.extend(
            [
                f"### Q{qn} {label}".strip(),
                "",
                "Question:",
                question_en or "—",
                "",
            ]
        )
        if question_ko:
            lines.extend([question_ko, ""])
        lines.extend(
            [
                "복원 발화:",
                transcript,
                "",
                f"상태: {status}",
                "",
                "핵심 피드백:",
                feedback,
                "",
            ]
        )

    if not rows_sorted:
        for per_q in per_q_list:
            q_idx = int(per_q.get("question_index") or 0)
            qn = q_idx + 1
            label = str(per_q.get("question_label") or "")
            status = str(per_q.get("status") or "—")
            lines.extend(
                [
                    f"### Q{qn} {label}".strip(),
                    "",
                    "Question:",
                    "—",
                    "",
                    "복원 발화:",
                    _export_transcript({}, per_q),
                    "",
                    f"상태: {status}",
                    "",
                    "핵심 피드백:",
                    _export_feedback(status, per_q),
                    "",
                ]
            )

    lines.extend(["## 현재 강점", ""])
    strengths = report_data.get("strengths") or []
    if strengths:
        for bullet in strengths:
            lines.append(f"- {str(bullet).strip()}")
    else:
        lines.append("- —")
    lines.append("")

    lines.extend(["## 바로 고치면 좋은 점", ""])
    fix_now = report_data.get("fix_now") or []
    if fix_now:
        for bullet in fix_now:
            lines.append(f"- {str(bullet).strip()}")
    else:
        lines.append("- 분석이 완료된 문항이 더 있으면 구체적인 교정 포인트가 표시돼요.")
    lines.append("")

    lines.extend(["## 다음 연습 미션", ""])
    missions = report_data.get("missions") or []
    if missions:
        for i, mission in enumerate(missions, start=1):
            lines.append(f"{i}. {str(mission).strip()}")
    else:
        for i, mission in enumerate(_TYPE_MISSIONS.values(), start=1):
            lines.append(f"{i}. {mission}")
    lines.append("")

    lines.extend(
        [
            "## 추천 학습 경로",
            "- 주제별 답변 연습",
            "- 실전 모의고사",
            "",
        ]
    )

    return "\n".join(lines)
