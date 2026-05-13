"""
Routine tab: bucket flat master rows into mobile-first sections.

Each routine row should use ``subcategory`` = one of the six section ids
(``time_routine``, ``habits_expr``, …). Legacy values like ``daily_routine``
are mapped for backward compatibility.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

# Display order (루틴 탭 전용) — must match section ids below
ROUTINE_SECTION_META: Sequence[Tuple[str, str]] = (
    ("time_routine", "시간 루틴"),
    ("habits_expr", "습관 표현"),
    ("planning_routine", "계획·관리 루틴"),
    ("self_care_routine", "자기관리 루틴"),
    ("leisure_routine", "여가 루틴"),
    ("mind_routine", "감정·마인드 루틴"),
)

ROUTINE_SECTION_IDS: frozenset[str] = frozenset(sid for sid, _ in ROUTINE_SECTION_META)

# Old subcategory / free-form labels → canonical section id
_LEGACY_SUBCATEGORY_MAP: Dict[str, str] = {
    "daily_routine": "time_routine",
    "time_routine": "time_routine",
    "morning_routine": "time_routine",
    "evening_routine": "time_routine",
    "weekday_routine": "time_routine",
    "spare_time": "leisure_routine",
    "weekends": "leisure_routine",
    "habits": "habits_expr",
    "preference_type": "habits_expr",
    "preference_reason": "habits_expr",
    "responsibilities": "planning_routine",
    "companions": "leisure_routine",
    "planning_routine": "planning_routine",
    "habits_expr": "habits_expr",
    "self_care_routine": "self_care_routine",
    "leisure_routine": "leisure_routine",
    "mind_routine": "mind_routine",
}

# Keyword fallback when subcategory is still unknown (Korean meaning + EN template)
_MEANING_HINTS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("self_care_routine", ("운동", "건강", "수면", "식사", "다이어트", "헬스", "스트레칭")),
    ("mind_routine", ("기분", "스트레스", "마음", "느낌", "생각", "편안", "불안", "동기")),
    ("planning_routine", ("계획", "일정", "관리", "분담", "정리", "목표", "우선")),
    ("leisure_routine", ("취미", "여가", "주말", "친구", "가족과", "여행", "영화", "음악")),
    ("habits_expr", ("즐깁", "좋아하", "보통", "자주", "습관", "취향")),
    ("time_routine", ("시간", "아침", "저녁", "하루", "보냅", "루틴")),
)


def _tags_blob(row: Dict[str, Any]) -> str:
    tags = row.get("tags")
    if not isinstance(tags, list):
        return ""
    return " ".join(str(t).lower() for t in tags if t is not None)


def routine_row_ui_schema(row: Dict[str, Any]) -> Dict[str, Any]:
    """Canonical lightweight dict for UI (full ``examples`` kept internally)."""
    ex = row.get("examples") if isinstance(row.get("examples"), list) else []
    clean_ex: List[Dict[str, Any]] = []
    for x in ex:
        if not isinstance(x, dict):
            continue
        en = (x.get("en") or "").strip()
        if not en:
            continue
        item: Dict[str, Any] = {"en": en}
        ko = (x.get("ko") or "").strip()
        if ko:
            item["ko"] = ko
        af = (x.get("audio_file") or "").strip()
        if af:
            item["audio_file"] = af
        clean_ex.append(item)
    return {
        "category": (row.get("category") or "routine").strip().lower(),
        "pattern": (row.get("pattern_en") or "").strip(),
        "meaning": (row.get("meaning") or "").strip(),
        "examples": clean_ex,
        "pattern_id": (row.get("pattern_id") or "").strip(),
        "subcategory": (row.get("subcategory") or "general").strip().lower().replace(" ", "_"),
    }


def _keyword_section_from_blob(blob: str) -> Optional[str]:
    for sid, kws in _MEANING_HINTS:
        for kw in kws:
            if kw in blob:
                return sid
    return None


def _routine_section_for_row(row: Dict[str, Any]) -> str:
    sub = (row.get("subcategory") or "general").strip().lower().replace(" ", "_")
    if sub in ROUTINE_SECTION_IDS:
        return sub
    if sub in _LEGACY_SUBCATEGORY_MAP:
        return _LEGACY_SUBCATEGORY_MAP[sub]

    blob = f"{sub} {_tags_blob(row)} {(row.get('meaning') or '')} {(row.get('pattern_en') or '')}"
    blob_l = blob.lower()
    hinted = _keyword_section_from_blob(blob)
    if hinted:
        return hinted

    # English token hints (sub + template)
    if any(w in blob_l for w in ("weekend", "hobby", "leisure", "friend", "family", "together")):
        return "leisure_routine"
    if any(w in blob_l for w in ("plan", "schedule", "organize", "share responsibility", "chore")):
        return "planning_routine"
    if any(w in blob_l for w in ("usually spend", "spend my time", "daily")):
        return "time_routine"
    if any(w in blob_l for w in ("enjoy", "because", "prefer", "habit")):
        return "habits_expr"
    if any(w in blob_l for w in ("feel", "stress", "comfortable because i", "personally")):
        return "mind_routine"
    if any(w in blob_l for w in ("health", "sleep", "exercise", "gym", "meal")):
        return "self_care_routine"
    return "leisure_routine"


def bucket_routine_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Split ``category == routine`` rows into ROUTINE_SECTION_META buckets.
    """
    buckets: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid, _ in ROUTINE_SECTION_META}
    for r in rows:
        sid = _routine_section_for_row(r)
        if sid not in buckets:
            sid = "leisure_routine"
        buckets[sid].append(routine_row_ui_schema(r))

    out: List[Dict[str, Any]] = []
    for sid, title in ROUTINE_SECTION_META:
        items = buckets.get(sid) or []
        if not items:
            continue
        out.append({"section_id": sid, "title": title, "patterns": items})
    return out
