"""
OPIc speech-rate scoring — words per 90 seconds (1m30s) reference window.

Used by Mini Mock V2, Mock V2 final report, and Topic Practice V2 feedback calibration.

SINGLE SOURCE OF TRUTH for speech-rate bands:
- WORDS_IN_90S_BANDS below is the ONLY place band numbers are defined.
- All human-readable band strings are generated from it via describe_words_in_90s_bands().
- Do NOT hardcode band numbers ("NH~10, IL 20-30, ...") anywhere else.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from services.evaluation.eval_config import LEVEL_ORDER

# Reference speaking window (user spec: "일반적으로 1분 30초")
REFERENCE_SPEECH_SECONDS = 90.0

# Words expected in 90s at each level (inclusive ranges; AL is open-ended).
# THIS DICTIONARY IS THE SINGLE SOURCE OF TRUTH. Edit bands here only.
WORDS_IN_90S_BANDS: Dict[str, Tuple[int, int]] = {
    "NH": (0, 12),       # ~10 words
    "IL": (13, 30),      # 20–30
    "IM1": (31, 60),     # 30–60
    "IM2": (61, 90),     # 60–90
    "IM3": (91, 120),    # 90–120
    "IH": (121, 155),    # 120–155 (widened: was a 10-wide sliver; speed alone must not grant AL)
    "AL": (156, 10_000),  # 156+ (≈160+ typical)
}

# Midpoints for 0–100 response_amount mapping
_SCORE_ANCHORS: Tuple[Tuple[float, int], ...] = (
    (0.0, 8),
    (10.0, 18),
    (25.0, 38),
    (45.0, 52),
    (75.0, 68),
    (105.0, 80),
    (120.0, 88),
    (160.0, 96),
    (220.0, 100),
)

RESPONSE_AMOUNT_BLEND_RULE = 0.65  # rule layer weight vs Gemini response_amount
RESPONSE_AMOUNT_BLEND_GEMINI = 1.0 - RESPONSE_AMOUNT_BLEND_RULE


def describe_words_in_90s_bands() -> str:
    """Human-readable band string generated from WORDS_IN_90S_BANDS.

    Returns e.g. "NH 0-12, IL 13-30, IM1 31-60, ..., AL 131+".
    This is the ONLY approved way to render band numbers as text — never hardcode.
    """
    parts: List[str] = []
    for level in LEVEL_ORDER:
        lo, hi = WORDS_IN_90S_BANDS[level]
        if hi >= 10_000:
            parts.append(f"{level} {lo}+")
        else:
            parts.append(f"{level} {lo}-{hi}")
    return ", ".join(parts)


def compute_wpm(word_count: int, duration_seconds: float) -> float:
    try:
        wc = max(0, int(word_count))
        dur = float(duration_seconds)
    except (TypeError, ValueError):
        return 0.0
    if dur <= 0 or wc <= 0:
        return 0.0
    return round(wc / (dur / 60.0), 1)


def words_normalized_to_90s(word_count: int, duration_seconds: float) -> float:
    """Scale word count to a 90-second equivalent (when duration known).

    DOWNWARD-ONLY normalization: we only scale DOWN answers LONGER than the 90s
    reference window. We must NOT extrapolate a short, fast burst UP to a full 90s
    window — speaking 18 words in 7 seconds is not evidence of ~230 words of content,
    it is simply a short answer. Upward extrapolation previously let a 7-second answer
    score ~100 on response_amount (and read as AL on quantity). Response amount =
    how much was actually said; a brief answer stays brief regardless of pace.
    """
    try:
        wc = max(0, int(word_count))
        dur = float(duration_seconds)
    except (TypeError, ValueError):
        return float(max(0, int(word_count or 0)))
    if dur <= 0 or dur <= REFERENCE_SPEECH_SECONDS:
        return float(wc)
    return round(wc * (REFERENCE_SPEECH_SECONDS / dur), 1)


def infer_level_from_words_90s(words_90s: float) -> str:
    try:
        w = float(words_90s)
    except (TypeError, ValueError):
        w = 0.0
    for level in LEVEL_ORDER:
        lo, hi = WORDS_IN_90S_BANDS[level]
        if lo <= w <= hi:
            return level
    return "AL" if w > WORDS_IN_90S_BANDS["IH"][1] else "NH"


def response_amount_score_from_words_90s(words_90s: float) -> int:
    """0–100 score from 90s-normalized word count."""
    try:
        w = float(words_90s)
    except (TypeError, ValueError):
        w = 0.0
    if w <= _SCORE_ANCHORS[0][0]:
        return _SCORE_ANCHORS[0][1]
    for i in range(1, len(_SCORE_ANCHORS)):
        w0, s0 = _SCORE_ANCHORS[i - 1]
        w1, s1 = _SCORE_ANCHORS[i]
        if w <= w1:
            if w1 <= w0:
                return int(s1)
            t = (w - w0) / (w1 - w0)
            return int(max(0, min(100, round(s0 + t * (s1 - s0)))))
    return 100


def _level_index(level: str) -> int:
    lv = str(level or "").strip().upper()
    if lv not in LEVEL_ORDER:
        return 0
    return LEVEL_ORDER.index(lv)


def cap_level_by_speech_rate(gemini_level: str, speech_level: str) -> str:
    """Do not allow overall level above speech-rate quantity ceiling.

    NOTE: This is a DOWNWARD-ONLY cap. A fast speech rate never raises the level;
    it can only fail to lower it. This keeps STT mis-recognition (e.g. duplicated
    words inflating the count) from pushing a learner into an undeserved IH/AL.
    """
    from services.exam_analytics import parse_level_to_token

    g = str(gemini_level or "").strip()
    if "응답" in g or not g:
        return g
    g_tok = parse_level_to_token(g) or ""
    if not g_tok:
        return g
    g_idx = _level_index(g_tok)
    s_idx = _level_index(speech_level)
    if s_idx < g_idx:
        return speech_level
    return g


def build_per_answer_speech_metrics(
    word_count: int,
    duration_seconds: float,
) -> Dict[str, Any]:
    wpm = compute_wpm(word_count, duration_seconds)
    words_90s = words_normalized_to_90s(word_count, duration_seconds)
    dur_ok = float(duration_seconds or 0) > 0
    return {
        "word_count": int(word_count),
        "duration_seconds": round(float(duration_seconds or 0), 1),
        "wpm": wpm,
        "wpm_available": dur_ok and wpm > 0,
        "words_normalized_90s": words_90s,
        "speech_rate_level": infer_level_from_words_90s(words_90s),
        "response_amount_score_rule": response_amount_score_from_words_90s(words_90s),
        "reference_window_seconds": REFERENCE_SPEECH_SECONDS,
    }


def build_exam_aggregate_speech_metrics(
    items: List[Dict[str, Any]],
    *,
    level_basis: str = "sum",
) -> Dict[str, Any]:
    """
    Derive exam-level speech-rate signals from saved answers.
    Each item may include word_count, duration_seconds, wpm, wpm_available.

    level_basis:
      - "sum" (default, Mini Mock V2): combine all answers' words/duration and
        normalize the TOTAL to one 90s window. Matches the 3-question combined
        anchor design of the mini mock.
      - "per_answer" (Mock V2 / 15-question exam): the level signal is the AVERAGE
        of each answered question's per-answer words_normalized_90s. Summing 15
        answers into one 90s window inflates the count into the AL band (and, when
        duration is missing, returns the raw total word count = hundreds → AL),
        which is wrong for a multi-question exam. Per-answer averaging reflects the
        student's typical answer rate instead.
    """
    total_words = 0
    total_duration = 0.0
    wpm_vals: List[float] = []
    per_answer_words_90s: List[float] = []
    for row in items:
        if not isinstance(row, dict):
            continue
        wc = int(row.get("word_count") or 0)
        total_words += wc
        try:
            dur = float(row.get("duration_seconds") or 0.0)
        except (TypeError, ValueError):
            dur = 0.0
        if dur > 0:
            total_duration += dur
        if wc > 0:
            per_answer_words_90s.append(words_normalized_to_90s(wc, dur))
        if row.get("wpm_available") and float(row.get("wpm") or 0) > 0:
            try:
                wpm_vals.append(float(row.get("wpm") or 0))
            except (TypeError, ValueError):
                pass

    if level_basis == "per_answer":
        words_90s = (
            round(sum(per_answer_words_90s) / len(per_answer_words_90s), 1)
            if per_answer_words_90s
            else 0.0
        )
    else:
        words_90s = words_normalized_to_90s(total_words, total_duration)
    avg_wpm = round(sum(wpm_vals) / len(wpm_vals), 1) if wpm_vals else compute_wpm(
        total_words, total_duration
    )
    dur_ok = total_duration > 0

    return {
        "reference_window_seconds": REFERENCE_SPEECH_SECONDS,
        "words_in_90s_bands": WORDS_IN_90S_BANDS,
        "total_word_count": total_words,
        "total_duration_seconds": round(total_duration, 1),
        "words_normalized_90s": words_90s,
        "average_wpm": avg_wpm,
        "wpm_available": dur_ok and (avg_wpm > 0 or total_words > 0),
        "speech_rate_level": infer_level_from_words_90s(words_90s),
        "response_amount_score_rule": response_amount_score_from_words_90s(words_90s),
        "scoring_note": (
            "90초(1분30초) 기준 환산 단어 수로 response_amount·등급 상한을 보정합니다. "
            f"레벨별 90초 단어 밴드: {describe_words_in_90s_bands()}."
        ),
    }


def apply_speech_rate_to_report(
    report: Dict[str, Any],
    speech_aggregate: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Blend rule-based response_amount and cap overall_level by speech-rate quantity.
    Mutates and returns report.
    """
    if not isinstance(report, dict) or not report.get("ok"):
        return report
    rule_ra = int(speech_aggregate.get("response_amount_score_rule") or 0)
    breakdown = report.get("score_breakdown")
    if not isinstance(breakdown, dict):
        breakdown = {}
    try:
        gemini_ra = int(breakdown.get("response_amount") or 0)
    except (TypeError, ValueError):
        gemini_ra = 0
    blended = int(
        max(
            0,
            min(
                100,
                round(
                    RESPONSE_AMOUNT_BLEND_GEMINI * gemini_ra
                    + RESPONSE_AMOUNT_BLEND_RULE * rule_ra
                ),
            ),
        )
    )
    breakdown["response_amount"] = blended
    report["score_breakdown"] = breakdown

    speech_lv = str(speech_aggregate.get("speech_rate_level") or "")
    if speech_lv:
        report["overall_level"] = cap_level_by_speech_rate(
            str(report.get("overall_level") or ""),
            speech_lv,
        )
    report["speech_rate_metrics"] = speech_aggregate
    return report


def format_speech_rate_rules_for_prompt() -> str:
    """JSON block for Gemini rubric injection."""
    import json

    return json.dumps(
        {
            "reference_window_seconds": REFERENCE_SPEECH_SECONDS,
            "words_in_90s_by_level": {
                k: {"min": v[0], "max": v[1]} for k, v in WORDS_IN_90S_BANDS.items()
            },
            "bands_human_readable": describe_words_in_90s_bands(),
            "scoring_policy": (
                "Use aggregate_metrics.words_normalized_90s and speech_rate_level. "
                "response_amount must reflect the 90s word bands in words_in_90s_by_level. "
                "Do not assign IH/AL if words_normalized_90s is far below band. "
                "Speech rate is a DOWNWARD-ONLY signal: a low words_normalized_90s caps "
                "the level, but a high one never raises it on its own (protects against "
                "STT mis-recognition). "
                "WPM = word_count / (duration_minutes); prefer words_normalized_90s for level."
            ),
        },
        ensure_ascii=False,
        indent=2,
    )
