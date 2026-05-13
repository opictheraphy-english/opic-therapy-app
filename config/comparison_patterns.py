"""
비교 탭: ``category == comparison`` 행을 아코디언 섹션으로 분류.

``routine_patterns.routine_row_ui_schema``와 동일한 경량 UI dict를 사용합니다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from config.routine_patterns import routine_row_ui_schema

COMPARISON_SECTION_META: Sequence[Tuple[str, str]] = (
    ("cmp_pros_cons", "장단점 비교"),
    ("cmp_past_present", "과거 vs 현재"),
    ("cmp_people", "사람 비교"),
    ("cmp_place", "장소 비교"),
    ("cmp_choice_pref", "선택·선호 비교"),
    ("cmp_experience", "경험 비교"),
    ("cmp_atmosphere", "분위기 비교"),
    ("cmp_lifestyle", "생활 방식 비교"),
)

COMPARISON_SECTION_IDS: frozenset[str] = frozenset(sid for sid, _ in COMPARISON_SECTION_META)

_LEGACY_SUB_TO_SECTION: Dict[str, str] = {
    "pros_cons": "cmp_pros_cons",
    "advantage": "cmp_pros_cons",
    "drawback": "cmp_pros_cons",
    "past_present": "cmp_past_present",
    "past": "cmp_past_present",
    "present": "cmp_past_present",
    "people": "cmp_people",
    "person": "cmp_people",
    "place": "cmp_place",
    "location_compare": "cmp_place",
    "choice": "cmp_choice_pref",
    "preference": "cmp_choice_pref",
    "prefer": "cmp_choice_pref",
    "experience_compare": "cmp_experience",
    "atmosphere": "cmp_atmosphere",
    "vibe": "cmp_atmosphere",
    "lifestyle": "cmp_lifestyle",
    "comparison_phrase": "cmp_place",
    "cmp_pros_cons": "cmp_pros_cons",
    "cmp_past_present": "cmp_past_present",
    "cmp_people": "cmp_people",
    "cmp_place": "cmp_place",
    "cmp_choice_pref": "cmp_choice_pref",
    "cmp_experience": "cmp_experience",
    "cmp_atmosphere": "cmp_atmosphere",
    "cmp_lifestyle": "cmp_lifestyle",
}


def _meaning_hint_section(blob: str) -> Optional[str]:
    if any(k in blob for k in ("장점", "단점", "drawback", "advantage", "문제점", "긍정")):
        return "cmp_pros_cons"
    if any(k in blob for k in ("과거", "예전", "요즘", "these days", "used to")):
        return "cmp_past_present"
    if any(k in blob for k in ("친구", "형", "동료", "부모", "unlike", "공통")):
        return "cmp_people"
    if any(k in blob for k in ("고향", "장소", "도시", "카페", "crowded", "hometown", "neighborhood")):
        return "cmp_place"
    if any(k in blob for k in ("prefer", "rather", "선호", "차라리", "굳이")):
        return "cmp_choice_pref"
    if any(k in blob for k in ("경험", "previous experience", "last time", "different from")):
        return "cmp_experience"
    if any(k in blob for k in ("분위기", "vibe", "atmosphere", "느낌이")):
        return "cmp_atmosphere"
    if any(k in blob for k in ("루틴", "생활", "습관", "nowadays", "lifestyle")):
        return "cmp_lifestyle"
    return None


def _comparison_section_for_row(row: Dict[str, Any]) -> str:
    sub = (row.get("subcategory") or "general").strip().lower().replace(" ", "_")
    if sub in COMPARISON_SECTION_IDS:
        return sub
    if sub in _LEGACY_SUB_TO_SECTION:
        return _LEGACY_SUB_TO_SECTION[sub]

    blob = f"{sub} {(row.get('meaning') or '')} {(row.get('pattern_en') or '')}"
    hinted = _meaning_hint_section(blob)
    if hinted:
        return hinted

    b = blob.lower()
    if any(w in b for w in ("advantage", "drawback", "pros and cons", "on the plus side")):
        return "cmp_pros_cons"
    if any(w in b for w in ("compared to the past", "these days", "used to", "back then")):
        return "cmp_past_present"
    if any(w in b for w in ("unlike me", "in common", "my friend", "my brother", "my parents")):
        return "cmp_people"
    if any(w in b for w in ("hometown", "crowded than", "this place", "neighborhood", "compared to other")):
        return "cmp_place"
    if any(w in b for w in ("prefer", "rather than", "i'd rather")):
        return "cmp_choice_pref"
    if any(w in b for w in ("previous experience", "different from", "last time i")):
        return "cmp_experience"
    if any(w in b for w in ("atmosphere", "vibe", "relaxed than")):
        return "cmp_atmosphere"
    if any(w in b for w in ("routine is", "nowadays", "people tend to", "lifestyle")):
        return "cmp_lifestyle"
    return "cmp_place"


def bucket_comparison_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid, _ in COMPARISON_SECTION_META}
    for r in rows:
        sid = _comparison_section_for_row(r)
        if sid not in buckets:
            sid = "cmp_place"
        buckets[sid].append(routine_row_ui_schema(r))

    out: List[Dict[str, Any]] = []
    for sid, title in COMPARISON_SECTION_META:
        items = buckets.get(sid) or []
        if not items:
            continue
        out.append({"section_id": sid, "title": title, "patterns": items})
    return out
