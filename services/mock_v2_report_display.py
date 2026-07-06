"""Shared mock_v2 final-report display data (screen + PDF, no Streamlit)."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from services.exam_analytics import result_display_status, result_is_no_speech_row
from utils.home_stats import LEVEL_ORDER, level_gap
from utils.text_utils import is_real_speech_transcript

RUBRIC_LABELS: Dict[str, str] = {
    "fluency": "유창성",
    "grammar": "문법",
    "lexical": "어휘",
    "logic": "논리",
}


def has_hangul(text: str) -> bool:
    return bool(re.search(r"[가-힣]", text or ""))


def hero_note(report: Dict[str, Any], agg: Dict[str, Any]) -> str:
    ko = str(agg.get("mock_v2_summary") or report.get("summary") or "").strip()
    note = str(agg.get("confidence_note") or "").strip()
    if ko and has_hangul(ko):
        return ko
    if note and has_hangul(note):
        return note
    return ko or note


def level_gap_chip_text(overall_raw: str, target_level: str) -> str:
    est = str(overall_raw or "").strip()
    target = str(target_level or "IH").strip()
    if not est:
        return "등급 측정 중"
    gap = level_gap(est, target)
    if gap <= 0:
        return f"{target} 달성"
    if gap == 1:
        return f"{target}까지 한 계단"
    if gap == 2:
        return f"{target}까지 두 계단"
    return f"{target}까지 {gap}계단"


def next_level_token(current: str) -> str:
    cur = str(current or "").strip().upper()
    if cur not in LEVEL_ORDER:
        return "다음 등급"
    idx = LEVEL_ORDER.index(cur)
    if idx >= len(LEVEL_ORDER) - 1:
        return str(LEVEL_ORDER[-1])
    return str(LEVEL_ORDER[idx + 1])


def format_duration(seconds: float) -> str:
    total = int(round(seconds))
    if total <= 0:
        return ""
    minutes, secs = divmod(total, 60)
    if minutes and secs:
        return f"{minutes}분 {secs}초"
    if minutes:
        return f"{minutes}분"
    return f"{secs}초"


def sorted_rubric_bars(rubric: Dict[str, Any]) -> List[Tuple[str, float]]:
    items: List[Tuple[str, float]] = []
    for key, label in RUBRIC_LABELS.items():
        try:
            val = float(rubric.get(key) or 0)
        except (TypeError, ValueError):
            val = 0.0
        items.append((label, max(0.0, min(100.0, val))))
    items.sort(key=lambda x: x[1], reverse=True)
    return items


def diagnosis_tip_text(bars: List[Tuple[str, float]], overall_raw: str) -> str:
    if not bars:
        return ""
    lowest_score = min(v for _, v in bars)
    lowest_labels = [lbl for lbl, v in bars if v == lowest_score]
    lowest_name = lowest_labels[0] if lowest_labels else ""
    next_lv = next_level_token(overall_raw)
    return f"가장 낮은 {lowest_name}부터 잡으면 {next_lv}이 빨라져요"


def row_is_no_response(res: Dict[str, Any]) -> bool:
    return result_is_no_speech_row(res) or result_display_status(res) in (
        "음성 미감지",
        "응답 부족",
    )


def row_feedback_text(res: Dict[str, Any]) -> str:
    return str(
        res.get("semantic_feedback") or res.get("summary_speech_rehab") or ""
    ).strip()


def row_better_direction(res: Dict[str, Any]) -> str:
    return str(res.get("prescription") or "").strip()


def row_level_display(res: Dict[str, Any]) -> str:
    return str(
        res.get("estimated_level_display") or res.get("estimated_level") or ""
    ).strip()


def metric_chip_labels(res: Dict[str, Any]) -> List[str]:
    metrics = res.get("metrics") or {}
    chips: List[str] = []
    wpm = res.get("wpm")
    if wpm is None:
        wpm = metrics.get("wpm")
    try:
        if wpm is not None and float(wpm) > 0:
            chips.append(f"WPM {float(wpm):.0f}")
    except (TypeError, ValueError):
        pass
    dur = metrics.get("duration_seconds") or res.get("duration_seconds")
    try:
        if dur is not None and float(dur) > 0:
            fmt = format_duration(float(dur))
            if fmt:
                chips.append(fmt)
    except (TypeError, ValueError):
        pass
    sc = metrics.get("sentence_count")
    try:
        if sc is not None and float(sc) > 0:
            chips.append(f"문장 {float(sc):.0f}")
    except (TypeError, ValueError):
        pass
    return chips


def transcript_for_export(res: Dict[str, Any]) -> Tuple[str, bool]:
    """Return (text, is_real_speech)."""
    tx_raw = str(res.get("transcript") or "").strip()
    if res.get("diagnosis_status") == "analysis_pending":
        return "음성 인식이 완료되지 않았습니다.", False
    no_speech = row_is_no_response(res)
    if no_speech:
        return "", False
    if tx_raw and is_real_speech_transcript(tx_raw):
        return tx_raw, True
    return "", False


def today_kst_label() -> str:
    return datetime.now().strftime("%Y.%m.%d")


def overall_raw_from_agg(agg: Dict[str, Any]) -> str:
    return str(agg.get("overall_raw") or agg.get("overall_display") or "—")


def answered_summary_label(stats: Dict[str, int], total: int = 15) -> str:
    return f"{int(stats.get('completed') or 0)}/{int(total)}"


def list_strengths_weaknesses(report: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    strengths = [
        str(s).strip()
        for s in (report.get("strengths") or [])
        if str(s).strip()
    ]
    weaknesses = [
        str(w).strip()
        for w in (report.get("weaknesses") or [])
        if str(w).strip()
    ]
    return strengths, weaknesses
