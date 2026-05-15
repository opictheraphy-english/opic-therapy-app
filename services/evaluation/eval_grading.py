"""Hybrid OPIc calibration: semantic-primary + audio metrics + rule corrections."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from .eval_config import (
    FAKE_FLUENCY_WPM_MIN,
    GRADING_THRESHOLDS,
    IDIOM_SMALL_BONUS_PHRASES,
    LEVEL_COMPRESS,
    LEVEL_ORDER,
    QUALITY_SCORE_BANDS,
)
from .eval_rules import (
    apply_fake_fluency_cap,
    im3_quality_gate,
    merge_quantity_quality_soft,
    novice_sub_band,
    shallow_template_penalty,
)
from .eval_text import (
    abandoned_fragments,
    connector_variation_score,
    count_spoken_units,
    count_words,
    filler_hits,
    filler_tier_adjustment,
    lexical_modifier_metrics,
    repetition_ratio_percent,
)

_SEMANTIC_DEFAULTS: Dict[str, float] = {
    "fluency_score": 48.0,
    "grammar_score": 48.0,
    "lexical_score": 48.0,
    "logic_score": 48.0,
    "semantic_density": 45.0,
    "discourse_continuity": 45.0,
    "narrative_depth": 45.0,
    "elaboration_quality": 45.0,
    "spontaneity_score": 48.0,
    "naturalness": 48.0,
    "tense_stability": 50.0,
    "pause_stability": 50.0,
    "repetition_ratio": 35.0,
    "abandoned_sentence_ratio": 28.0,
    "pronunciation_clarity": 50.0,
    "intonation_control": 50.0,
    "stress_rhythm": 50.0,
    "linking_naturalness": 50.0,
}

_PRONUNCIATION_KEYS = (
    "pronunciation_clarity",
    "intonation_control",
    "stress_rhythm",
    "linking_naturalness",
)


def normalize_semantic(raw: Optional[Dict[str, Any]]) -> Dict[str, float]:
    base = dict(_SEMANTIC_DEFAULTS)
    if not raw:
        return base
    for k, v in raw.items():
        if k in base and v is not None:
            try:
                base[k] = float(max(0.0, min(100.0, float(v))))
            except (TypeError, ValueError):
                pass
    return base


def _detect_question_type(question_text: str) -> str:
    q = (question_text or "").lower()
    comparison_cues = ["compare", "how have", "difference", "changed", "than before", "stack up"]
    past_cues = ["experience", "memorable", "happened", "had", "time when", "what happened"]
    present_cues = ["routine", "usually", "describe", "tell me about your", "what do you"]
    if any(c in q for c in comparison_cues):
        return "C"
    if any(c in q for c in past_cues):
        return "B"
    if any(c in q for c in present_cues):
        return "A"
    return "A"


def _score_level_from_composite(composite: float) -> str:
    for threshold, lvl in QUALITY_SCORE_BANDS:
        if composite >= threshold:
            return lvl
    return "NH"


def _idiom_bonus(lower: str) -> float:
    return float(sum(3 for phrase in IDIOM_SMALL_BONUS_PHRASES if phrase in lower))


def _pronunciation_delivery_low(semantic: Dict[str, float]) -> bool:
    """Mild intelligibility warning only — never auto-drop level on accent alone."""
    for k in ("pronunciation_clarity", "intonation_control", "stress_rhythm"):
        v = semantic.get(k, 50.0)
        if v < 35.0:
            return True
    return False


def _pronunciation_feedback(semantic: Dict[str, float]) -> str:
    """One short Korean sentence for report UI (accent-fair)."""
    clarity = semantic.get("pronunciation_clarity", 50.0)
    intonation = semantic.get("intonation_control", 50.0)
    stress = semantic.get("stress_rhythm", 50.0)
    linking = semantic.get("linking_naturalness", 50.0)
    avg = (clarity + intonation + stress + linking) / 4.0

    if clarity < 35 or stress < 35 or intonation < 35:
        return (
            "단어 하나하나를 또박또박 읽는 느낌이 있어요. "
            "문장 단위로 묶어서 말하고, 핵심 단어에 힘을 주는 연습이 필요합니다."
        )
    if avg >= 72:
        return (
            "발음은 전반적으로 이해 가능해요. "
            "중요한 단어에 강세를 조금 더 주면 답변이 더 자연스럽게 들릴 수 있어요."
        )
    if clarity < 50 or stress < 50:
        return (
            "발음은 대체로 따라오지만, 강세와 리듬이 평평하면 청자가 피로할 수 있어요. "
            "핵심 단어를 살짝 길게, 나머지는 짧게 이어 보세요."
        )
    return (
        "발음은 전반적으로 이해 가능하지만, 억양과 강세를 조금 더 살리면 "
        "답변이 더 자연스럽게 들릴 수 있어요."
    )


def _composite_quality(semantic: Dict[str, float], filler_adj: float, shallow_pen: float, idiom_b: float) -> float:
    w = {
        "fluency_score": 0.09,
        "grammar_score": 0.14,
        "lexical_score": 0.10,
        "logic_score": 0.10,
        "semantic_density": 0.12,
        "discourse_continuity": 0.12,
        "narrative_depth": 0.09,
        "elaboration_quality": 0.09,
        "spontaneity_score": 0.025,
        "naturalness": 0.025,
        "pronunciation_clarity": 0.04,
        "intonation_control": 0.03,
        "stress_rhythm": 0.03,
        "linking_naturalness": 0.02,
    }
    acc = sum(semantic.get(k, 50.0) * wt for k, wt in w.items())
    acc += filler_adj
    acc -= shallow_pen
    acc += min(5.0, idiom_b)
    tense = semantic.get("tense_stability", 50.0)
    pause = semantic.get("pause_stability", 50.0)
    acc += (tense - 50.0) * 0.04 + (pause - 50.0) * 0.02

    rep_r = semantic.get("repetition_ratio", 35.0)
    if rep_r > 82:
        acc -= 6.0
    ab = semantic.get("abandoned_sentence_ratio", 28.0)
    if ab > 70:
        acc -= 8.0

    return float(max(0.0, min(100.0, acc)))


def evaluate_grading_logic(
    audio_info: Dict[str, Any],
    transcript: str,
    question_text: str = "",
    *,
    semantic: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Full hybrid pipeline. `semantic` should be Gemini JSON (0–100 scales).
    """
    sem = normalize_semantic(semantic)
    duration_sec = float(audio_info.get("duration_seconds") or 0.0)
    lower = (transcript or "").lower()
    words = count_words(transcript)
    word_list = lower.split()
    spoken_units = float(count_spoken_units(transcript))

    fh = filler_hits(lower)
    filler_adj = filler_tier_adjustment(fh)
    lx = lexical_modifier_metrics(lower)
    shallow_pen = shallow_template_penalty(
        lx["simple_pattern_hits"],
        lx["movie_repeats"],
        lx["has_movie_synonym"],
    )
    idiom_b = _idiom_bonus(lower)
    connector_sc = connector_variation_score(lower)
    rep_heuristic = repetition_ratio_percent(lower, word_list)
    abandoned_r = max(float(sem.get("abandoned_sentence_ratio", 0)), abandoned_fragments(lower))

    composite = _composite_quality(sem, filler_adj, shallow_pen, idiom_b)

    # Ultra-short response dampening (rule layer)
    if words < 22:
        composite *= 0.82
    if duration_sec < 11 and words < 35:
        composite = min(composite, 44.0)

    score_level = _score_level_from_composite(composite)

    # Quantity tier from speech length (NOT from WPM)
    quantity_level = "NH"
    for lv in ["IL", "IM1", "IM2", "IM3", "IH", "AL"]:
        t = GRADING_THRESHOLDS[lv]
        if (
            duration_sec >= t["min_seconds"]
            and spoken_units >= t["min_units"]
            and words >= t["min_words"]
        ):
            quantity_level = lv

    minutes = duration_sec / 60.0 if duration_sec > 0 else 0.0
    wpm = round(words / minutes, 1) if minutes > 0 else 0.0

    merged = merge_quantity_quality_soft(quantity_level, score_level)

    merged, _fake_hit = apply_fake_fluency_cap(
        merged,
        wpm,
        sem.get("semantic_density", 50.0),
        sem.get("discourse_continuity", 50.0),
    )

    merged, _im3_hit = im3_quality_gate(merged, sem, connector_sc)

    novice = novice_sub_band(
        words,
        int(spoken_units),
        sem.get("semantic_density", 40.0),
        abandoned_r,
        sem.get("grammar_score", 40.0),
    )

    estimated_level = LEVEL_COMPRESS.get(merged, merged)
    display = f"{estimated_level} (추정)" if merged != "NH" else "NH"
    if novice and merged in {"NH", "IL"}:
        display = f"{estimated_level} · novice {novice} (추정)"

    q_type = _detect_question_type(question_text)
    if q_type == "A":
        tense_feedback = "현재 시제 서술의 안정성과 자연스러운 전개를 중심으로 점검했습니다."
    elif q_type == "B":
        tense_feedback = "과거 경험 서술에서 시제 일관성·줄거리 연결을 중심으로 점검했습니다."
    else:
        tense_feedback = "비교·대조 질문에서 시제 전환과 논리 연결을 중심으로 점검했습니다."

    summary_parts: List[str] = []
    if wpm >= FAKE_FLUENCY_WPM_MIN and sem.get("semantic_density", 60) < 50:
        summary_parts.append(
            "발화 속도는 빠르지만 의미 밀도·담화 연속성이 충분히 따라오지 않습니다. 암기형 유창 의심 구간입니다."
        )
    if fh >= 7:
        summary_parts.append("필러 과다 사용으로 리듬이 산만해 보일 수 있습니다.")
    if _pronunciation_delivery_low(sem):
        summary_parts.append("발음·강세 전달력이 낮아 이해도가 떨어질 수 있습니다.")

    pronunciation_feedback = _pronunciation_feedback(sem)
    pronunciation_scores = {k: round(sem[k], 1) for k in _PRONUNCIATION_KEYS}

    final_grade_score = round(composite, 1)

    return {
        "quantity_level": quantity_level,
        "score_level_raw": score_level,
        "estimated_level": estimated_level,
        "estimated_level_display": display,
        "estimated_range": "",
        "novice_band": novice,
        "question_type": q_type,
        "tense_appropriateness_feedback": tense_feedback,
        "metrics": {
            "duration_seconds": duration_sec,
            "duration_method": audio_info.get("duration_method", ""),
            "word_count": words,
            "sentence_count": int(spoken_units),
            "spoken_units_detail": spoken_units,
            "wpm": wpm,
            "filler_hits": fh,
            "connector_variation_score": connector_sc,
            "repetition_heuristic": rep_heuristic,
            "abandoned_ratio_effective": abandoned_r,
        },
        "priority_scores": {
            "fluency": round(sem["fluency_score"], 1),
            "lexical": round(sem["lexical_score"], 1),
            "logic": round(sem["logic_score"], 1),
            "grammar": round(sem["grammar_score"], 1),
        },
        "semantic_dimensions": {k: round(v, 1) for k, v in sem.items()},
        "pronunciation_scores": pronunciation_scores,
        "pronunciation_feedback": pronunciation_feedback,
        "final_grade_score": final_grade_score,
        "summary_line": " ".join(summary_parts).strip(),
        "rule_flags": {
            "fake_fluency_cap": _fake_hit,
            "im3_gate_trim": _im3_hit,
            "shallow_template_penalty": shallow_pen,
            "filler_adjustment": filler_adj,
            "pronunciation_delivery_low": _pronunciation_delivery_low(sem),
        },
    }


def strip_json_fence(text: str) -> str:
    return re.sub(r"```(?:json)?|```", "", text or "", flags=re.IGNORECASE).strip()
