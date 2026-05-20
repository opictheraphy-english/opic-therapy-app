"""Aggregate mini mock results into a concise diagnostic report (no Gemini)."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from services.exam_analytics import result_display_status, weighted_overall_level
from services.feedback.feedback_builder import (
    merge_grammar_corrections_for_display,
    merge_expression_upgrades_for_display,
    safe_get_transcript,
)
from services.final_report_preview import build_final_report_preview
from utils.text_utils import is_real_speech_transcript

logger = logging.getLogger(__name__)

_MINI_MOCK_TOTAL = 3

_TYPE_MISSIONS: Dict[str, str] = {
    "description": "묘사: 위치 → 특징 → 좋은 점 순서로 말하기",
    "memorable_experience": "경험: 사건 → 감정 → 배운 점 순서로 말하기",
    "roleplay": "롤플레이: 문제 설명 → 사과/이유 → 대안 제안 순서로 말하기",
}

_INDEX_TO_TYPE: Tuple[str, ...] = (
    "description",
    "memorable_experience",
    "roleplay",
)

_DESCRIPTION_LEAK_PHRASES: Tuple[str, ...] = (
    "방/공간",
    "집 묘사",
    "집 구조",
    "월세",
    "거실",
    "화장실",
    "아파트 구조",
    "공간 구성",
    "집을 좋아하는 이유",
    "강아지",
    "구체적인 정보가 많아서",
)

_LEARNING_PATH_BY_TYPE: Dict[str, str] = {
    "description": "묘사형 답변 연습: 위치 → 특징 → 이유",
    "memorable_experience": "경험형 답변 연습: 사건 → 감정 → 배운 점",
    "roleplay": "롤플레이 3단 구조 연습: 사과 → 이유 → 대안",
}

_DEFAULT_LEARNING_PATH = (
    "실전 모의고사 15문항으로 전체 답변 체력을 점검해 보세요."
)


def get_mini_metric(result: Any, key: str, default: Any = None) -> Any:
    """Read a metric from nested or top-level result fields without raising."""
    if not isinstance(result, dict):
        return default
    metrics = result.get("metrics")
    if isinstance(metrics, dict) and metrics.get(key) is not None:
        return metrics.get(key)
    if result.get(key) is not None:
        return result.get(key)
    audio_metrics = result.get("audio_metrics")
    if isinstance(audio_metrics, dict) and key in (
        "duration_seconds",
        "duration_method",
    ):
        val = audio_metrics.get(key)
        if val is not None:
            return val
    return default


def _numeric_metric(result: dict, key: str) -> Optional[float]:
    raw = get_mini_metric(result, key)
    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def format_mini_metric_display(
    result: dict,
    key: str,
    *,
    as_int: bool = False,
    zero_is_missing: bool = True,
) -> str:
    """Student-facing metric chip; missing → em dash (never invent zeros for WPM)."""
    val = _numeric_metric(result, key)
    if val is None:
        return "—"
    if zero_is_missing and key in ("wpm", "word_count", "sentence_count") and val <= 0:
        return "—"
    if key == "filler_hits":
        return str(int(round(val)))
    if as_int:
        return str(int(round(val)))
    if key == "wpm":
        return str(int(round(val)))
    return str(int(round(val))) if val == int(val) else f"{val:.1f}"


def _log_missing_metric(q_idx: int, result: dict, key: str) -> None:
    try:
        logger.debug(
            "[MINI_REPORT_DEBUG] missing %s for q=%s result_keys=%s metrics_keys=%s",
            key,
            q_idx + 1,
            sorted(result.keys()) if isinstance(result, dict) else [],
            sorted((result.get("metrics") or {}).keys())
            if isinstance(result.get("metrics"), dict)
            else [],
        )
    except Exception:
        pass


def _resolve_question_type(row: Dict[str, Any]) -> str:
    q_type = str(row.get("question_type") or "").strip()
    if q_type:
        return q_type
    q_idx = int(row.get("question_index") or 0)
    if 0 <= q_idx < len(_INDEX_TO_TYPE):
        return _INDEX_TO_TYPE[q_idx]
    return ""


def _feedback_blocked_for_type(text: str, q_type: str) -> bool:
    if q_type in ("memorable_experience", "roleplay") and text.strip():
        for phrase in _DESCRIPTION_LEAK_PHRASES:
            if phrase in text:
                return True
        if re.search(r"집\s*묘사|방\s*구성|공간\s*구성", text):
            return True
    return False


def _pull_safe_existing_feedback(res: dict, q_type: str) -> str:
    for field in ("semantic_feedback", "summary_speech_rehab"):
        block = (res.get(field) or "").strip()
        if block and not _feedback_blocked_for_type(block, q_type):
            if len(block) > 220:
                return block[:217] + "…"
            return block
    return ""


def _join_feedback_parts(parts: List[str], res: dict, q_type: str) -> str:
    cleaned = [p.strip() for p in parts if p and p.strip()]
    if not cleaned:
        fallback = _pull_safe_existing_feedback(res, q_type)
        if fallback:
            return fallback
        return "질문 유형에 맞게 답을 이어 갔어요. 아래 교정 포인트를 참고해 보세요."
    text = " ".join(cleaned[:2]).strip()
    if len(text) > 220:
        return text[:217] + "…"
    return text


def _flags_description(lower: str) -> Dict[str, bool]:
    return {
        "location": bool(
            re.search(
                r"\b(?:live|living|located|city|town|neighborhood|area|apartment|place)\b",
                lower,
            )
        )
        or bool(re.search(r"살고|동네|위치|지역", lower)),
        "features": bool(
            re.search(
                r"\b(?:room|quiet|cozy|comfortable|spacious|bathroom|kitchen|view)\b",
                lower,
            )
        )
        or bool(re.search(r"조용|넓|방|특징|분위기", lower)),
        "preference": bool(
            re.search(r"\b(?:love|like|enjoy|favorite|reason|because)\b", lower)
        )
        or bool(re.search(r"좋아|마음에|이유|때문", lower)),
        "closing": bool(
            re.search(r"\b(?:overall|great place|happy here|recommend)\b", lower)
        )
        or bool(re.search(r"전체|결론|만족", lower)),
    }


def _feedback_description(transcript: str, res: dict) -> str:
    lower = transcript.lower()
    flags = _flags_description(lower)
    parts: List[str] = []
    if flags["location"] and flags["preference"]:
        parts.append("장소의 분위기와 좋은 점을 연결해서 말한 점이 좋아요.")
    elif flags["location"] and flags["features"]:
        parts.append("위치와 특징을 나란히 설명해 묘사가 구체적이었어요.")
    elif flags["location"]:
        parts.append("장소 설명으로 시작한 흐름이 자연스러웠어요.")
    if flags["features"] and flags["preference"] and len(parts) < 2:
        parts.append("좋아하는 이유까지 연결해 묘사 답변이 설득력 있었어요.")
    missing: List[str] = []
    if not flags["location"]:
        missing.append("위치")
    if not flags["features"]:
        missing.append("특징")
    if not flags["preference"]:
        missing.append("이유")
    if missing and len(parts) < 2:
        parts.append("위치 → 특징 → 좋아하는 이유 순서가 더 또렷하면 좋아요.")
    elif flags["closing"] and len(parts) < 2:
        parts.append("마무리 의견이 들어가 답변이 정리됐어요.")
    return _join_feedback_parts(parts, res, "description")


def _flags_experience(lower: str) -> Dict[str, bool]:
    return {
        "event": bool(
            re.search(
                r"\b(?:happened|when|one day|suddenly|remember when|experience)\b",
                lower,
            )
        )
        or bool(re.search(r"있었|일이|경험|그때|어느 날", lower)),
        "context": bool(
            re.search(r"\b(?:home|neighborhood|family|friend|last)\b", lower)
        )
        or bool(re.search(r"집|동네|친구|가족", lower)),
        "emotion": bool(
            re.search(
                r"\b(?:felt|feeling|surprised|happy|upset|excited|scared)\b",
                lower,
            )
        )
        or bool(re.search(r"감정|기분|놀랐|행복|슬펐|화가", lower)),
        "memorable": bool(
            re.search(
                r"\b(?:memorable|remember|never forget|still|since then)\b",
                lower,
            )
        )
        or bool(re.search(r"기억|남는|잊지|아직도", lower)),
        "lesson": bool(
            re.search(r"\b(?:learned|realized|lesson|since then)\b", lower)
        )
        or bool(re.search(r"배웠|깨달|교훈", lower)),
    }


def _feedback_experience(transcript: str, res: dict) -> str:
    lower = transcript.lower()
    flags = _flags_experience(lower)
    parts: List[str] = []
    if flags["event"] and flags["emotion"]:
        parts.append("사건과 감정이 함께 전달돼 경험담이 생생했어요.")
    elif flags["event"]:
        parts.append("사건의 흐름은 잘 잡았어요. 마지막에 왜 기억에 남는지 한 문장을 더하면 좋아요.")
    if flags["memorable"] and len(parts) < 2:
        parts.append("기억에 남는 이유를 분명히 말한 점이 좋아요.")
    if flags["lesson"] and len(parts) < 2:
        parts.append("경험에서 얻은 의미까지 연결한 점이 좋아요.")
    if not flags["emotion"] and len(parts) < 2:
        parts.append("경험 답변은 사건 → 감정 → 의미 순서로 정리하면 더 강해져요.")
    elif not flags["memorable"] and flags["event"] and len(parts) < 2:
        parts.append("무슨 일이 있었는지는 전달됐어요. 왜 기억에 남는지 한 문장을 더해 보세요.")
    return _join_feedback_parts(parts, res, "memorable_experience")


def _flags_roleplay(lower: str) -> Dict[str, bool]:
    return {
        "greeting": bool(
            re.search(r"\b(?:hi|hello|hey|thanks for|calling)\b", lower)
        )
        or bool(re.search(r"안녕|여보세요|전화", lower)),
        "problem": bool(
            re.search(
                r"\b(?:schedule|change|can't|cannot|problem|unfortunately|sorry but)\b",
                lower,
            )
        )
        or bool(re.search(r"일정|바뀌|어려|미안하지만|상황", lower)),
        "apology": bool(
            re.search(r"\b(?:sorry|apologize|apologies)\b", lower)
        )
        or bool(re.search(r"미안|죄송", lower)),
        "reason": bool(
            re.search(r"\b(?:because|since|work|busy|meeting)\b", lower)
        )
        or bool(re.search(r"때문|바빠|회의|일이", lower)),
        "alternative": bool(
            re.search(
                r"\b(?:how about|instead|another time|suggest|tomorrow|weekend|can we)\b",
                lower,
            )
        )
        or bool(re.search(r"대신|다른 시간|제안|내일|주말|괜찮", lower)),
        "closing": bool(
            re.search(r"\b(?:talk soon|let me know|see you|thank you)\b", lower)
        )
        or bool(re.search(r"연락|그때|기다릴", lower)),
    }


def _feedback_roleplay(transcript: str, res: dict) -> str:
    lower = transcript.lower()
    flags = _flags_roleplay(lower)
    parts: List[str] = []
    if flags["problem"] and flags["apology"]:
        parts.append("문제 설명과 사과는 자연스러웠어요.")
    elif flags["problem"]:
        parts.append("상황 설명으로 시작한 점이 좋아요. 사과 표현을 한 번 넣어 보세요.")
    if flags["alternative"] and len(parts) < 2:
        parts.append("대안 시간을 제안해 롤플레이 목적에 맞게 마무리했어요.")
    elif flags["problem"] and not flags["alternative"] and len(parts) < 2:
        parts.append("대안 시간을 더 구체적으로 제안하면 좋아요.")
    if flags["reason"] and len(parts) < 2:
        parts.append("이유를 덧붙여 상대가 상황을 이해하기 쉬웠어요.")
    if not parts:
        parts.append("롤플레이는 사과 → 이유 → 대안 제안 순서가 핵심이에요.")
    return _join_feedback_parts(parts, res, "roleplay")


def build_mini_question_feedback(res: dict, row: Dict[str, Any]) -> str:
    """Type-specific coach line for mini mock (no global feedback algorithm changes)."""
    q_type = _resolve_question_type(row)
    transcript = safe_get_transcript(res)
    if not is_real_speech_transcript(transcript):
        return ""
    if q_type == "description":
        return _feedback_description(transcript, res)
    if q_type == "memorable_experience":
        return _feedback_experience(transcript, res)
    if q_type == "roleplay":
        return _feedback_roleplay(transcript, res)
    return _join_feedback_parts([], res, q_type)


def _structure_score_for_learning(res: dict, q_type: str, transcript: str) -> float:
    """Higher = stronger answer for picking weakest area (display-only heuristic)."""
    lower = transcript.lower()
    if q_type == "description":
        flags = _flags_description(lower)
        return float(sum(1 for v in flags.values() if v))
    if q_type == "memorable_experience":
        flags = _flags_experience(lower)
        return float(sum(1 for v in flags.values() if v))
    if q_type == "roleplay":
        flags = _flags_roleplay(lower)
        return float(sum(1 for v in flags.values() if v))
    fg = res.get("final_grade_score")
    if isinstance(fg, (int, float)):
        return float(fg) / 25.0
    return 0.0


def _build_learning_path(
    sorted_rows: List[Dict[str, Any]],
) -> List[str]:
    from utils.mini_mock_state import row_result

    candidates: List[Tuple[float, str]] = []
    for row in sorted_rows:
        res = row_result(row)
        if result_display_status(res) != "분석 완료":
            continue
        q_type = _resolve_question_type(row)
        if not q_type:
            continue
        transcript = safe_get_transcript(res)
        structure = _structure_score_for_learning(res, q_type, transcript)
        grade = res.get("final_grade_score")
        grade_val = float(grade) if isinstance(grade, (int, float)) else 50.0
        weakness = (5.0 - min(structure, 5.0)) * 10.0 + (100.0 - grade_val) * 0.05
        candidates.append((weakness, q_type))

    paths: List[str] = []
    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        seen: set[str] = set()
        for _, q_type in candidates:
            tip = _LEARNING_PATH_BY_TYPE.get(q_type, "")
            if tip and tip not in seen:
                seen.add(tip)
                paths.append(tip)
            if len(paths) >= 2:
                break

    if not paths:
        paths.append(_DEFAULT_LEARNING_PATH)
    elif len(paths) == 1 and paths[0] != _DEFAULT_LEARNING_PATH:
        paths.append(_DEFAULT_LEARNING_PATH)
    return paths[:3]


def _preview_rows_for_builder(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    from utils.mini_mock_state import row_result

    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append({"result": row_result(row)})
    return out


def _key_correction_from_result(res: dict, transcript: str) -> str:
    grammar = merge_grammar_corrections_for_display(transcript, res)
    if grammar:
        g0 = grammar[0]
        before = (g0.get("before") or g0.get("wrong") or "").strip()
        after = (g0.get("after") or g0.get("right") or "").strip()
        if before and after:
            return f"{before} → {after}"
    expr = merge_expression_upgrades_for_display(transcript, res)
    if expr:
        e0 = expr[0]
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
        q_type = _resolve_question_type(row)
        fb_line = build_mini_question_feedback(res, row)
        if fb_line and not _feedback_blocked_for_type(fb_line, q_type):
            add(fb_line)
        transcript = safe_get_transcript(res)
        grammar = merge_grammar_corrections_for_display(transcript, res)
        for g in grammar[:1]:
            if not isinstance(g, dict):
                continue
            before = (g.get("before") or g.get("wrong") or "").strip()
            after = (g.get("after") or g.get("right") or "").strip()
            if before and after:
                add(f"문법: {before} → {after}")

    if not bullets:
        bullets.append(
            "완료된 답변에서 눈에 띄는 큰 오류는 많지 않았어요. 다음엔 문장 끝을 조금 더 분명하게 마무리해 보세요."
        )
    return bullets[:limit]


def _collect_strengths(rows: List[Dict[str, Any]], *, limit: int = 2) -> List[str]:
    bullets: List[str] = []
    seen: set[str] = set()

    def add(line: str) -> None:
        text = (line or "").strip()
        if not text or text in seen or len(bullets) >= limit:
            return
        if _feedback_blocked_for_type(text, "memorable_experience"):
            return
        seen.add(text)
        bullets.append(text)

    from utils.mini_mock_state import row_result

    for row in rows:
        res = row_result(row)
        if result_display_status(res) != "분석 완료":
            continue
        q_type = _resolve_question_type(row)
        transcript = safe_get_transcript(res)
        if q_type == "description":
            flags = _flags_description(transcript.lower())
            if flags["location"] and flags["features"]:
                add("묘사 답변에서 위치와 특징을 함께 잡은 점이 좋아요.")
        elif q_type == "memorable_experience":
            flags = _flags_experience(transcript.lower())
            if flags["event"] and flags["emotion"]:
                add("경험담에서 사건과 감정이 함께 전달된 점이 좋아요.")
        elif q_type == "roleplay":
            flags = _flags_roleplay(transcript.lower())
            if flags["problem"] and flags["alternative"]:
                add("롤플레이에서 상황 설명과 대안 제안이 균형 있었어요.")

    if len(bullets) < limit:
        for row in rows:
            res = row_result(row)
            summary = (res.get("summary_speech_rehab") or "").strip()
            q_type = _resolve_question_type(row)
            if (
                summary
                and result_display_status(res) == "분석 완료"
                and not _feedback_blocked_for_type(summary, q_type)
            ):
                add(summary[:120])
                if len(bullets) >= limit:
                    break

    if not bullets:
        bullets.append("질문 주제에 맞게 답을 이어 간 흐름이 좋아요.")
    return bullets[:limit]


def _aggregate_metrics(per_question: List[Dict[str, Any]]) -> Dict[str, Any]:
    wpms: List[float] = []
    words: List[float] = []
    fillers: List[float] = []
    for item in per_question:
        if str(item.get("status") or "") != "분석 완료":
            continue
        wpm = item.get("wpm")
        if isinstance(wpm, (int, float)) and wpm > 0:
            wpms.append(float(wpm))
        wc = item.get("word_count")
        if isinstance(wc, (int, float)) and wc > 0:
            words.append(float(wc))
        fh = item.get("filler_hits")
        if isinstance(fh, (int, float)):
            fillers.append(float(fh))

    def _avg(vals: List[float]) -> Optional[float]:
        return round(sum(vals) / len(vals), 1) if vals else None

    total_filler: Optional[int] = int(sum(fillers)) if fillers else None

    def _display_avg(vals: List[float]) -> str:
        if not vals:
            return "—"
        return str(int(round(sum(vals) / len(vals))))

    return {
        "avg_wpm": _avg(wpms),
        "avg_word_count": _avg(words),
        "total_filler_hits": total_filler,
        "avg_wpm_display": _display_avg(wpms),
        "avg_word_count_display": _display_avg(words),
        "total_filler_display": (
            str(total_filler) if total_filler is not None else "—"
        ),
    }


def _extract_per_question_metrics(
    res: dict,
    row: Dict[str, Any],
) -> Dict[str, Any]:
    q_idx = int(row.get("question_index") or 0)
    wpm_raw = _numeric_metric(res, "wpm")
    if wpm_raw is None or wpm_raw <= 0:
        _log_missing_metric(q_idx, res, "wpm")
    wc_raw = _numeric_metric(res, "word_count")
    if wc_raw is None or wc_raw <= 0:
        _log_missing_metric(q_idx, res, "word_count")

    wpm_val = wpm_raw if wpm_raw and wpm_raw > 0 else None
    wc_val = wc_raw if wc_raw and wc_raw > 0 else None
    sc_val = _numeric_metric(res, "sentence_count")
    if sc_val is not None and sc_val <= 0:
        sc_val = None
    fh_val = _numeric_metric(res, "filler_hits")
    score_val = res.get("final_grade_score")
    if not isinstance(score_val, (int, float)):
        score_val = None

    return {
        "wpm": wpm_val,
        "word_count": int(wc_val) if wc_val is not None else None,
        "sentence_count": int(sc_val) if sc_val is not None else None,
        "filler_hits": int(fh_val) if fh_val is not None else None,
        "final_grade_score": float(score_val) if score_val is not None else None,
        "wpm_display": format_mini_metric_display(res, "wpm"),
        "word_count_display": format_mini_metric_display(res, "word_count"),
        "sentence_count_display": format_mini_metric_display(
            res, "sentence_count"
        ),
        "filler_display": format_mini_metric_display(
            res, "filler_hits", zero_is_missing=False
        ),
        "score_display": (
            str(int(round(float(score_val))))
            if score_val is not None
            else "—"
        ),
        "duration_display": format_mini_metric_display(
            res, "duration_seconds", as_int=True, zero_is_missing=True
        ),
    }


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
        q_type = _resolve_question_type(row)
        transcript = safe_get_transcript(res)
        stt_status = str(res.get("stt_status") or row.get("stt_status") or "").lower()
        if status == "분석 완료" and is_real_speech_transcript(transcript):
            level_items.append({"q_id": q_idx + 1, "result": res})

        short_feedback = ""
        key_correction = ""
        metrics_block = _extract_per_question_metrics(res, row)
        if status == "분석 완료":
            short_feedback = build_mini_question_feedback(res, row)
            key_correction = _key_correction_from_result(res, transcript)

        preview_tx = transcript
        if preview_tx and len(preview_tx) > 180:
            preview_tx = preview_tx[:177] + "…"
        transcript_display = preview_tx
        if stt_status == "insufficient_response" or status == "응답 부족":
            transcript_display = ""
        elif not transcript_display and status in ("분석 대기", "AI 분석 대기 중"):
            transcript_display = ""

        per_question.append(
            {
                "question_index": q_idx,
                "question_label": q_label,
                "question_type": q_type,
                "status": status,
                "stt_status": stt_status,
                "transcript_preview": preview_tx,
                "transcript_display": transcript_display,
                "short_feedback": short_feedback,
                "key_correction": key_correction,
                "estimated_level": (
                    res.get("estimated_level_display") or res.get("estimated_level") or ""
                ),
                **metrics_block,
            }
        )

    estimated_display = ""
    estimated_note = "분석 완료된 답변 기준으로 표시됩니다"
    if level_items:
        estimated_display, _raw = weighted_overall_level(level_items)
        estimated_note = ""
    elif int(preview.get("no_speech") or 0) >= _MINI_MOCK_TOTAL and not level_items:
        estimated_display = "응답 부족"
        estimated_note = "세 답변 모두 발화가 충분하지 않아 레벨을 산정하지 않았어요."
    elif preview.get("completed_count", 0) > 0:
        estimated_note = "분석 완료된 답변 기준으로 표시됩니다"

    missions: List[str] = []
    for row in sorted_rows:
        q_type = _resolve_question_type(row)
        mission = _TYPE_MISSIONS.get(q_type)
        if mission and mission not in missions:
            missions.append(mission)
    for q_type, mission in _TYPE_MISSIONS.items():
        if mission not in missions:
            missions.append(mission)
        if len(missions) >= 3:
            break

    aggregate = _aggregate_metrics(per_question)
    completed = int(preview.get("completed_count") or 0)

    return {
        "summary": preview,
        "aggregate_metrics": aggregate,
        "per_question": per_question,
        "strengths": _collect_strengths(sorted_rows, limit=2),
        "fix_now": _collect_fix_now(sorted_rows, limit=3),
        "missions": missions[:3],
        "learning_path": _build_learning_path(sorted_rows),
        "estimated_level": estimated_display,
        "estimated_level_note": estimated_note,
        "has_pending": int(preview.get("pending_count") or 0) > 0,
        "answered_count": int(preview.get("answered_count") or 0),
        "completed_count": completed,
        "total_count": _MINI_MOCK_TOTAL,
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
    if status in ("분석 대기", "AI 분석 대기 중"):
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
    completed = int(summary.get("completed_count") or report_data.get("completed_count") or 0)
    pending = int(summary.get("pending_count") or 0)
    total = int(summary.get("total_count") or _MINI_MOCK_TOTAL)
    agg = report_data.get("aggregate_metrics") if isinstance(
        report_data.get("aggregate_metrics"), dict
    ) else {}

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
        f"- 평균 WPM: {agg.get('avg_wpm_display', '—')}",
        f"- 평균 단어 수: {agg.get('avg_word_count_display', '—')}",
        f"- 필러 사용: {agg.get('total_filler_display', '—')}",
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
        metrics_line = (
            f"WPM {per_q.get('wpm_display', '—')} · "
            f"단어 {per_q.get('word_count_display', '—')} · "
            f"필러 {per_q.get('filler_display', '—')}"
        )

        lines.extend(
            [
                f"### Q{qn} {label}".strip(),
                "",
                metrics_line,
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

    lines.extend(["## 추천 학습 경로", ""])
    learning = report_data.get("learning_path") or []
    if learning:
        for bullet in learning:
            lines.append(f"- {str(bullet).strip()}")
    else:
        lines.append(f"- {_DEFAULT_LEARNING_PATH}")
    lines.append("")

    return "\n".join(lines)
