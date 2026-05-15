"""
Aggregate mock-exam results without calling Gemini — semantic scores from cached analysis only.
"""

from __future__ import annotations

from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple

from services.evaluation.eval_config import LEVEL_COMPRESS, LEVEL_ORDER

_SEMANTIC_KEYS_AVG = (
    "semantic_density",
    "discourse_continuity",
    "narrative_depth",
    "elaboration_quality",
    "spontaneity_score",
    "naturalness",
    "tense_stability",
)


def _compress_display(lv: str) -> str:
    return LEVEL_COMPRESS.get(lv, lv)


def parse_level_to_token(text: Optional[str]) -> Optional[str]:
    """Map arbitrary estimated_level string to LEVEL_ORDER token."""
    if not text:
        return None
    t = str(text).upper()
    for lv in ("AL", "IH", "IM3", "IM2", "IM1", "IL", "NH"):
        if lv in t.replace(" ", ""):
            return lv
    if "IM" in t and "IM3" not in t and "IM2" not in t and "IM1" not in t:
        return "IM2"
    return None


def level_to_index(level: Optional[str]) -> int:
    if not level:
        return 0
    lv = parse_level_to_token(level) or "NH"
    try:
        return LEVEL_ORDER.index(lv)
    except ValueError:
        return 0


def index_to_level(idx: int) -> str:
    idx = max(0, min(len(LEVEL_ORDER) - 1, int(idx)))
    return LEVEL_ORDER[idx]


def weighted_overall_level(items: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Ordinal median with slight weight on Q14–15 (comparison / issue).
    Returns (compressed_display, raw_token).
    """
    weights: List[float] = []
    indices: List[int] = []
    for row in items:
        qid = int(row.get("q_id") or 0)
        res = row.get("result") or {}
        w = 1.35 if qid >= 14 else 1.0
        lvl = res.get("estimated_level") or res.get("estimated_level_display") or ""
        tok = parse_level_to_token(str(lvl))
        if not tok:
            fg = res.get("final_grade_score")
            if isinstance(fg, (int, float)):
                tok = _score_to_level(float(fg))
            else:
                tok = "NH"
        idx = level_to_index(tok)
        weights.append(w)
        indices.append(idx)

    if not indices:
        return "NH", "NH"

    acc = sum(i * w for i, w in zip(indices, weights))
    sw = sum(weights)
    w_avg = acc / sw if sw else mean(indices)
    rounded = int(round(w_avg))
    raw = index_to_level(rounded)
    disp = _compress_display(raw)
    return disp, raw


def _score_to_level(score: float) -> str:
    if score >= 82:
        return "AL"
    if score >= 73:
        return "IH"
    if score >= 65:
        return "IM3"
    if score >= 56:
        return "IM2"
    if score >= 47:
        return "IM1"
    if score >= 38:
        return "IL"
    return "NH"


def confidence_from_results(items: List[Dict[str, Any]]) -> Tuple[float, str]:
    """0–100 confidence + short English rationale."""
    densities: List[float] = []
    discs: List[float] = []
    grades: List[float] = []
    for row in items:
        res = row.get("result") or {}
        sem = res.get("semantic_dimensions") or {}
        d = sem.get("semantic_density")
        c = sem.get("discourse_continuity")
        if isinstance(d, (int, float)):
            densities.append(float(d))
        if isinstance(c, (int, float)):
            discs.append(float(c))
        fg = res.get("final_grade_score")
        if isinstance(fg, (int, float)):
            grades.append(float(fg))

    parts = [densities, discs, grades]
    spreads = [pstdev(p) for p in parts if len(p) > 1]
    base = 88.0
    penalty = sum(min(12.0, s * 0.35) for s in spreads)
    conf = max(52.0, min(96.0, base - penalty))

    avg_d = mean(densities) if densities else 50.0
    avg_c = mean(discs) if discs else 50.0
    if avg_d >= 58 and avg_c >= 58:
        note = (
            "Natural narration and stable discourse continuity stand out across the session."
        )
    elif avg_d >= 48:
        note = "Semantic density is adequate; continue expanding concrete detail and examples."
    else:
        note = "Focus on elaboration and clearer sequencing — several responses stayed narrow."

    return round(conf, 1), note


def strongest_weakest_topic(items: List[Dict[str, Any]]) -> Tuple[str, str]:
    by_topic: Dict[str, List[float]] = {}
    for row in items:
        topic = str(row.get("topic") or "—")
        res = row.get("result") or {}
        fg = res.get("final_grade_score")
        if isinstance(fg, (int, float)):
            by_topic.setdefault(topic, []).append(float(fg))
    if not by_topic:
        return "—", "—"
    avgs = {t: mean(v) for t, v in by_topic.items()}
    mx_t = max(avgs, key=avgs.get)
    mn_t = min(avgs, key=avgs.get)
    return mx_t, mn_t


def filler_trend_note(items: List[Dict[str, Any]]) -> str:
    hits = []
    for row in items:
        res = row.get("result") or {}
        m = res.get("metrics") or {}
        fh = m.get("filler_hits")
        if isinstance(fh, (int, float)):
            hits.append(float(fh))
    if not hits:
        return "Filler usage was light overall."
    av = mean(hits)
    if av <= 3:
        return "Filler usage stayed in a natural range."
    if av <= 6:
        return "Occasional fillers — monitor rhythm on comparison/issue prompts."
    return "Higher filler density detected — prioritize pausing over verbal fillers."


def compute_exam_aggregates(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Single dict for final report + PDF + JSON."""
    items = [r for r in results if isinstance(r, dict)]
    disp, raw = weighted_overall_level(items)
    conf, conf_note = confidence_from_results(items)
    strong, weak = strongest_weakest_topic(items)

    wpms: List[float] = []
    sents: List[float] = []
    sem_dns: List[float] = []
    for row in items:
        res = row.get("result") or {}
        m = res.get("metrics") or {}
        w = m.get("wpm")
        if isinstance(w, (int, float)):
            wpms.append(float(w))
        sc = m.get("sentence_count")
        if isinstance(sc, (int, float)):
            sents.append(float(sc))
        sem = res.get("semantic_dimensions") or {}
        sd = sem.get("semantic_density")
        if isinstance(sd, (int, float)):
            sem_dns.append(float(sd))

    radar_dims: Dict[str, float] = {}
    for key in _SEMANTIC_KEYS_AVG:
        vals: List[float] = []
        for row in items:
            sem = (row.get("result") or {}).get("semantic_dimensions") or {}
            v = sem.get(key)
            if isinstance(v, (int, float)):
                vals.append(float(v))
        if vals:
            radar_dims[key.replace("_", " ").title()] = round(mean(vals), 1)

    rubric_avg = {"fluency": 0.0, "lexical": 0.0, "logic": 0.0, "grammar": 0.0}
    rs_counts = {k: 0 for k in rubric_avg}
    for row in items:
        rs = (row.get("result") or {}).get("rubric_scores") or {}
        for k in rubric_avg:
            v = rs.get(k)
            if isinstance(v, (int, float)):
                rubric_avg[k] += float(v)
                rs_counts[k] += 1
    for k in rubric_avg:
        if rs_counts[k]:
            rubric_avg[k] = round(rubric_avg[k] / rs_counts[k], 1)

    return {
        "overall_display": disp,
        "overall_raw": raw,
        "confidence": conf,
        "confidence_note": conf_note,
        "avg_wpm": round(mean(wpms), 1) if wpms else 0.0,
        "avg_sentence_count": round(mean(sents), 1) if sents else 0.0,
        "avg_semantic_density": round(mean(sem_dns), 1) if sem_dns else 0.0,
        "strongest_topic": strong,
        "weakest_topic": weak,
        "filler_trend": filler_trend_note(items),
        "radar_dimensions": radar_dims,
        "rubric_averages": rubric_avg,
        "item_count": len(items),
    }


def summary_rows_for_table(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for row in sorted(items, key=lambda x: int(x.get("q_id") or 0)):
        qid = row.get("q_id")
        res = row.get("result") or {}
        rs = res.get("rubric_scores") or {}
        lvl = res.get("estimated_level_display") or res.get("estimated_level") or "—"
        fg = res.get("final_grade_score")
        rows.append(
            {
                "Q": qid,
                "Topic": row.get("topic") or "—",
                "Type": row.get("type") or "—",
                "Est. Level": lvl,
                "Fluency": rs.get("fluency", "—"),
                "Logic": rs.get("logic", "—"),
                "Grammar": rs.get("grammar", "—"),
                "Overall": fg if fg is not None else "—",
            }
        )
    return rows


def detect_risk_flags(result: Dict[str, Any]) -> List[str]:
    """Rule flags + heuristic warnings for one question."""
    flags: List[str] = []
    rf = (result.get("grading_rule_flags") or {}) if isinstance(result.get("grading_rule_flags"), dict) else {}
    if rf.get("fake_fluency_cap"):
        flags.append("⚠️ Possible fake fluency pattern (high velocity vs. low semantic density)")
    if rf.get("im3_gate_trim"):
        flags.append("⚠️ Narrative/discourse signals below IM3 gate — progression capped")
    sem = result.get("semantic_dimensions") or {}
    rep = sem.get("repetition_ratio")
    if isinstance(rep, (int, float)) and rep > 72:
        flags.append("⚠️ Repetitive vocabulary pattern detected")
    m = result.get("metrics") or {}
    fh = m.get("filler_hits")
    if isinstance(fh, (int, float)) and fh >= 7:
        flags.append("⚠️ Excessive filler usage detected")
    wpm = result.get("wpm")
    sd = sem.get("semantic_density")
    if isinstance(wpm, (int, float)) and wpm >= 150 and isinstance(sd, (int, float)) and sd < 48:
        flags.append("⚠️ High WPM with shallow semantic density — review pacing")
    pc = sem.get("pronunciation_clarity")
    ir = sem.get("intonation_control")
    sr = sem.get("stress_rhythm")
    if any(
        isinstance(v, (int, float)) and v < 35
        for v in (pc, ir, sr)
        if v is not None
    ):
        flags.append("발음·강세 전달력이 낮아 이해도가 떨어질 수 있습니다.")
    return flags
