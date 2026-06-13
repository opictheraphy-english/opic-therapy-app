"""Final report completion hero — display markup only."""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional

from components.brand_character import render_celebration_scene


def _format_duration(seconds: float) -> str:
    total = int(round(seconds))
    if total <= 0:
        return ""
    minutes, secs = divmod(total, 60)
    if minutes and secs:
        return f"{minutes}분 {secs}초"
    if minutes:
        return f"{minutes}분"
    return f"{secs}초"


def _grade_pill_visible(overall_display: str, pending: int) -> bool:
    if pending > 0:
        return False
    label = str(overall_display or "").strip()
    return bool(label) and label != "분석 대기"


def _is_valid_answer_row(row: Dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False
    if str(row.get("status") or "").strip() == "saved":
        return True
    wc = row.get("word_count")
    if isinstance(wc, (int, float)) and wc > 0:
        return True
    for key in ("transcript", "raw_transcript", "student_answer"):
        if str(row.get(key) or "").strip():
            return True
    return False


def collect_hero_display_metrics(
    results: List[Dict[str, Any]],
    answers: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Read already-computed row fields for hero stat chips (no scoring changes)."""
    answered = len([row for row in results if isinstance(row, dict)])
    if answered == 0:
        answered = len([row for row in answers if _is_valid_answer_row(row)])

    total_words = 0
    words_available = False
    for row in results:
        if not isinstance(row, dict):
            continue
        res = row.get("result") if isinstance(row.get("result"), dict) else {}
        wc = res.get("word_count")
        if wc is None:
            metrics = res.get("metrics") if isinstance(res.get("metrics"), dict) else {}
            wc = metrics.get("word_count")
        if isinstance(wc, (int, float)) and wc > 0:
            total_words += int(wc)
            words_available = True

    if not words_available:
        for row in answers:
            if not isinstance(row, dict):
                continue
            wc = row.get("word_count")
            if isinstance(wc, (int, float)) and wc > 0:
                total_words += int(wc)
                words_available = True

    total_duration = 0.0
    duration_available = False
    for row in answers:
        if not isinstance(row, dict):
            continue
        dur = row.get("duration_seconds")
        if isinstance(dur, (int, float)) and dur > 0:
            total_duration += float(dur)
            duration_available = True

    if not duration_available:
        for row in results:
            if not isinstance(row, dict):
                continue
            res = row.get("result") if isinstance(row.get("result"), dict) else {}
            dur = res.get("duration_seconds")
            if isinstance(dur, (int, float)) and dur > 0:
                total_duration += float(dur)
                duration_available = True

    return {
        "answered": answered,
        "total_words": total_words if words_available else None,
        "total_duration": total_duration if duration_available else None,
    }


def render_final_report_completion_hero_html(
    *,
    answered_count: int,
    overall_display: str,
    pending_count: int,
    total_words: Optional[int] = None,
    total_duration: Optional[float] = None,
    note: str = "",
    eyebrow: str = "오늘의 진료 완료",
) -> str:
    """Two-zone celebration hero card for mock final report completion."""
    n = max(0, int(answered_count))
    title = f"{n}문항을 끝까지 해냈어요!"
    scene = render_celebration_scene(240)
    eyebrow_text = str(eyebrow or "오늘의 진료 완료").strip() or "오늘의 진료 완료"

    if _grade_pill_visible(overall_display, pending_count):
        grade_block = (
            '<div class="mx-fr-hero-grade">'
            '<span class="mx-fr-hero-grade-label">추정 등급</span>'
            f'<span class="mx-fr-hero-grade-value">{html.escape(str(overall_display))}</span>'
            "</div>"
        )
    elif pending_count > 0:
        grade_block = (
            '<p class="mx-fr-hero-pending">일부 문항은 AI 분석 대기 중입니다. '
            "분석이 완료된 답변을 기준으로 리포트를 먼저 보여드릴게요.</p>"
        )
    else:
        grade_block = ""

    chips: List[str] = []
    if n > 0:
        chips.append(
            '<div class="mx-fr-hero-chip">'
            '<span class="mx-fr-hero-chip-label">답변 문항</span>'
            f'<span class="mx-fr-hero-chip-val">{n}</span>'
            "</div>"
        )
    if total_words is not None and total_words > 0:
        chips.append(
            '<div class="mx-fr-hero-chip">'
            '<span class="mx-fr-hero-chip-label">총 발화(단어 수)</span>'
            f'<span class="mx-fr-hero-chip-val">{int(total_words):,}</span>'
            "</div>"
        )
    if total_duration is not None and total_duration > 0:
        dur_label = _format_duration(total_duration)
        if dur_label:
            chips.append(
                '<div class="mx-fr-hero-chip">'
                '<span class="mx-fr-hero-chip-label">소요 시간</span>'
                f'<span class="mx-fr-hero-chip-val">{html.escape(dur_label)}</span>'
                "</div>"
            )

    chips_block = ""
    if chips:
        chips_block = f'<div class="mx-fr-hero-chips">{"".join(chips)}</div>'

    note_block = ""
    note_text = str(note or "").strip()
    if note_text:
        note_block = f'<p class="mx-fr-hero-note">{html.escape(note_text)}</p>'

    return f"""
<section class="mx-fr-hero" role="region" aria-label="모의고사 완료">
  <div class="mx-fr-hero-stage">{scene}</div>
  <div class="mx-fr-hero-body">
    <p class="mx-fr-hero-eyebrow">{html.escape(eyebrow_text)}</p>
    <h2 class="mx-fr-hero-title">{html.escape(title)}</h2>
    {grade_block}
    {chips_block}
    {note_block}
  </div>
</section>
"""
