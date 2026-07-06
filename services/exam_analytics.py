"""
Aggregate mock-exam results without calling Gemini — semantic scores from cached analysis only.
"""

from __future__ import annotations

import logging
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional, Tuple

from services.evaluation.eval_config import LEVEL_COMPRESS, LEVEL_ORDER

logger = logging.getLogger(__name__)

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
    lv = parse_level_to_token(level)
    if not lv:
        return 0
    try:
        return LEVEL_ORDER.index(lv)
    except ValueError:
        return 0


def index_to_level(idx: int) -> str:
    idx = max(0, min(len(LEVEL_ORDER) - 1, int(idx)))
    return LEVEL_ORDER[idx]


def result_is_no_speech_row(res: Dict[str, Any]) -> bool:
    if not isinstance(res, dict):
        return False
    if res.get("no_speech_detected") or res.get("insufficient_response"):
        return True
    stt = str(res.get("stt_status") or "").lower()
    if stt == "insufficient_response":
        return True
    ast = str(res.get("analysis_status") or "").lower()
    diag = str(res.get("diagnosis_status") or "").lower()
    return ast in ("no_speech", "insufficient_response") or diag == "no_speech"


def result_is_api_pending_row(res: Dict[str, Any]) -> bool:
    if not isinstance(res, dict):
        return False
    if result_is_no_speech_row(res):
        return False
    ast = str(res.get("analysis_status") or "").lower()
    diag = str(res.get("diagnosis_status") or "").lower()
    return diag == "analysis_pending" or ast == "pending" or bool(res.get("analysis_pending"))


def result_is_gradable_for_aggregate(res: Dict[str, Any]) -> bool:
    """Only completed analyses with real level/score data affect overall level."""
    if not isinstance(res, dict):
        return False
    if res.get("is_gradable") is False:
        return False
    if result_is_no_speech_row(res):
        return False
    if result_display_status(res) != "분석 완료":
        return False
    diag = str(res.get("diagnosis_status") or "").lower()
    if diag not in ("ok", ""):
        return False
    return True


def _level_token_for_aggregate(res: Dict[str, Any]) -> Optional[str]:
    """Resolve OPIc token from completed result — never invent NH for missing fields."""
    if not result_is_gradable_for_aggregate(res):
        return None
    lvl = res.get("estimated_level") or res.get("estimated_level_display") or ""
    tok = parse_level_to_token(str(lvl))
    if tok:
        return tok
    fg = res.get("final_grade_score")
    if isinstance(fg, (int, float)):
        return _score_to_level(float(fg))
    return None


def level_display_for_summary(res: Dict[str, Any]) -> str:
    """Row level column — status label for non-completed rows, never NH for pending."""
    status = result_display_status(res)
    if status in ("분석 대기", "AI 분석 대기 중"):
        return "분석 대기"
    if status == "응답 부족":
        return "응답 부족"
    if status == "말소리 인식 불명확":
        return "음성 확인 필요"
    if status == "영어 답변 필요":
        return "영어 답변 필요"
    if status == "음성 미감지":
        return "음성 미감지"
    if status == "녹음 없음":
        return "녹음 없음"
    if status != "분석 완료":
        return "—"
    disp = str(res.get("estimated_level_display") or res.get("estimated_level") or "").strip()
    if not disp or disp in ("측정 대기", "측정 불가"):
        return "—"
    tok = parse_level_to_token(disp)
    if tok:
        return _compress_display(tok)
    return disp


def _count_aggregate_buckets(items: List[Dict[str, Any]]) -> Tuple[int, int, int]:
    gradable = 0
    no_speech = 0
    pending = 0
    for row in items:
        if not isinstance(row, dict):
            continue
        res = row.get("result") or {}
        if not isinstance(res, dict):
            continue
        if result_is_gradable_for_aggregate(res):
            gradable += 1
        elif result_is_no_speech_row(res):
            no_speech += 1
        elif result_is_api_pending_row(res):
            pending += 1
    return gradable, no_speech, pending


def resolve_overall_level_display(items: List[Dict[str, Any]]) -> Tuple[str, str]:
    """Overall predicted level — never show 분석 대기 when only silence rows exist."""
    gradable, no_speech, pending = _count_aggregate_buckets(items)
    if gradable > 0:
        disp, raw = weighted_overall_level(items)
    elif pending > 0:
        disp, raw = "분석 대기", "UNKNOWN"
    elif no_speech > 0:
        disp, raw = "응답 부족", "NO_SPEECH"
    else:
        disp, raw = "측정 불가 · 응답 부족", "NO_SPEECH"
    try:
        logger.debug(
            "[FINAL_AGGREGATE] gradable_count=%s no_speech_count=%s pending_count=%s overall=%s",
            gradable,
            no_speech,
            pending,
            disp,
        )
    except Exception:
        pass
    return disp, raw


def weighted_overall_level(items: List[Dict[str, Any]]) -> Tuple[str, str]:
    """
    Ordinal median with slight weight on Q14–15 (comparison / issue).
    Returns (compressed_display, raw_token).
    Skips pending/missing rows — they must not count as NH.
    """
    weights: List[float] = []
    indices: List[int] = []
    for row in items:
        qid = int(row.get("q_id") or 0)
        res = row.get("result") or {}
        tok = _level_token_for_aggregate(res)
        if not tok:
            continue
        w = 1.35 if qid >= 14 else 1.0
        idx = level_to_index(tok)
        weights.append(w)
        indices.append(idx)

    if not indices:
        return "분석 대기", "UNKNOWN"

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
        if not result_is_gradable_for_aggregate(res):
            continue
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
        res = row.get("result") or {}
        if not result_is_gradable_for_aggregate(res):
            continue
        topic = str(row.get("topic") or "—")
        fg = res.get("final_grade_score")
        if isinstance(fg, (int, float)):
            by_topic.setdefault(topic, []).append(float(fg))
    if not by_topic:
        return "—", "—"
    avgs = {t: mean(v) for t, v in by_topic.items()}
    if len(avgs) == 1:
        only = next(iter(avgs))
        return only, only
    mx_t = max(avgs, key=avgs.get)
    mn_t = min(avgs, key=avgs.get)
    if mx_t == mn_t and len(set(round(v, 2) for v in avgs.values())) == 1:
        return "—", "—"
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
    gradable, no_speech, pending = _count_aggregate_buckets(items)
    disp, raw = resolve_overall_level_display(items)
    conf, conf_note = confidence_from_results(items)
    if gradable == 0 and no_speech > 0 and pending == 0:
        conf_note = (
            "대부분의 문항에서 충분한 음성이 인식되지 않아 정상적인 등급 산정이 어렵습니다. "
            "실제 시험에서는 매우 낮은 평가로 이어질 수 있습니다."
        )
        conf = min(conf, 55.0)
    strong, weak = strongest_weakest_topic(items)

    wpms: List[float] = []
    sents: List[float] = []
    sem_dns: List[float] = []
    for row in items:
        res = row.get("result") or {}
        if not result_is_gradable_for_aggregate(res):
            continue
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
            res = row.get("result") or {}
            if not result_is_gradable_for_aggregate(res):
                continue
            sem = res.get("semantic_dimensions") or {}
            v = sem.get(key)
            if isinstance(v, (int, float)):
                vals.append(float(v))
        if vals:
            radar_dims[key.replace("_", " ").title()] = round(mean(vals), 1)

    rubric_avg = {"fluency": 0.0, "lexical": 0.0, "logic": 0.0, "grammar": 0.0}
    rs_counts = {k: 0 for k in rubric_avg}
    for row in items:
        res = row.get("result") or {}
        if not result_is_gradable_for_aggregate(res):
            continue
        rs = res.get("rubric_scores") or {}
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
        "gradable_count": gradable,
        "no_speech_count": no_speech,
        "pending_count": pending,
    }


def result_display_status(res: Dict[str, Any]) -> str:
    """Student-facing row status for final report (display only)."""
    if not isinstance(res, dict):
        return "—"
    ast = str(res.get("analysis_status") or "").lower()
    diag = str(res.get("diagnosis_status") or "").lower()
    if result_is_no_speech_row(res):
        if ast == "insufficient_response" or res.get("insufficient_response"):
            return "응답 부족"
        return "음성 미감지"
    if diag == "analysis_pending" or ast == "pending" or res.get("analysis_pending"):
        return "분석 대기"
    if ast == "non_english" or diag == "non_english":
        return "영어 답변 필요"
    if ast in ("unclear_speech", "needs_review") or diag in (
        "unclear_speech",
        "needs_review",
    ):
        return "말소리 인식 불명확"
    if ast in ("no_speech",) or diag in ("no_speech",):
        return "음성 미감지"
    if ast in ("no_audio",) or diag in ("no_audio",):
        return "녹음 없음"
    if ast == "completed" or diag == "ok":
        return "분석 완료"
    return "—"


def exam_results_summary_stats(items: List[Dict[str, Any]]) -> Dict[str, int]:
    """Counts for final report header (includes pending rows)."""
    answered = len([r for r in items if isinstance(r, dict)])
    completed = 0
    pending = 0
    no_speech = 0
    for row in items:
        if not isinstance(row, dict):
            continue
        res = row.get("result") or {}
        status = result_display_status(res)
        if status == "분석 완료":
            completed += 1
        elif status in ("분석 대기", "AI 분석 대기 중"):
            pending += 1
        elif status in ("음성 미감지", "응답 부족"):
            no_speech += 1
    return {
        "answered": answered,
        "completed": completed,
        "pending": pending,
        "no_speech": no_speech,
    }


def summary_rows_for_table(
    items: List[Dict[str, Any]],
    *,
    omit_score_columns: bool = False,
) -> List[Dict[str, Any]]:
    rows = []
    for row in sorted(items, key=lambda x: int(x.get("q_id") or 0)):
        qid = row.get("q_id")
        res = row.get("result") or {}
        rs = res.get("rubric_scores") or {}
        status = result_display_status(res)
        lvl = level_display_for_summary(res)
        fg = res.get("final_grade_score")
        rubric_val = lambda k: rs.get(k, "—") if status == "분석 완료" else "—"
        feedback = (
            (res.get("summary_speech_rehab") or res.get("semantic_feedback") or "")
            .strip()
        )[:80]
        entry: Dict[str, Any] = {
            "Q": qid,
            "Topic": row.get("topic") or "—",
            "Type": row.get("type") or "—",
            "Status": status,
            "Est. Level": lvl,
            "Feedback": feedback or "—",
        }
        if not omit_score_columns:
            entry.update(
                {
                    "Fluency": rubric_val("fluency"),
                    "Logic": rubric_val("logic"),
                    "Grammar": rubric_val("grammar"),
                    "Overall": fg if status == "분석 완료" and fg is not None else "—",
                }
            )
        rows.append(entry)
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
