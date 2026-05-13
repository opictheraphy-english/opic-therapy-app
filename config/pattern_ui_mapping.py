"""
UI grouping for pattern drills (MVP): 탭 → accordion 서브섹션 → 1줄 패턴.
"""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from config.comparison_patterns import bucket_comparison_rows
from config.experience_patterns import bucket_experience_rows
from config.pattern_config import ALLOWED_CATEGORIES, flat_patterns_with_audio
from config.routine_patterns import bucket_routine_rows

TAB_DEFINITIONS: Sequence[Tuple[str, str]] = (
    ("describe", "묘사"),
    ("routine", "루틴"),
    ("experience", "경험"),
    ("comparison", "비교"),
    ("opinion", "의견"),
    ("roleplay", "롤플레이"),
)

# 묘사: 서브카테고리 → UI 섹션 id
_DESCRIBE_SUB_TO_SECTION: Dict[str, str] = {}
for _sid, _subs in (
    ("exterior_look", frozenset({"exterior", "appearance", "visuals"})),
    (
        "mood_atmosphere",
        frozenset({"atmosphere", "lighting", "comfort", "sound", "crowd", "opening_intro"}),
    ),
    (
        "structure_space",
        frozenset(
            {
                "layout",
                "environment",
                "interior_space",
                "interior",
                "space",
                "favorite_space",
                "location",
                "size",
                "details",
                "daily_routine",
                "companions",
                "responsibilities",
            }
        ),
    ),
    (
        "emotion",
        frozenset(
            {
                "features_love",
                "emphasis",
                "personal_view",
                "preference_reason",
                "strengths",
                "benefits",
                "features",
                "overall_impression",
                "recommendation",
                "conclusion",
                "comparison_phrase",
                "preference_type",
            }
        ),
    ),
    ("weather", frozenset({"weather", "condition"})),
):
    for _sub in _subs:
        _DESCRIBE_SUB_TO_SECTION[_sub] = _sid

_DESCRIBE_SECTION_META: Sequence[Tuple[str, str]] = (
    ("exterior_look", "외관 묘사"),
    ("mood_atmosphere", "분위기 묘사"),
    ("structure_space", "구조·공간 묘사"),
    ("emotion", "감정 묘사"),
    ("weather", "날씨 묘사"),
    ("misc_describe", "기타 묘사"),
)

_OTHER_GENERIC_SECTION = "패턴 모음"


def _patterns_for_category(
    rows: List[Dict[str, Any]], category_id: str
) -> List[Dict[str, Any]]:
    return [r for r in rows if r.get("category") == category_id]


def _bucket_describe(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid, _ in _DESCRIBE_SECTION_META}
    for r in rows:
        sub = (r.get("subcategory") or "general").strip().lower().replace(" ", "_")
        sid = _DESCRIBE_SUB_TO_SECTION.get(sub, "misc_describe")
        if sid not in buckets:
            sid = "misc_describe"
        buckets[sid].append(r)
    return _sections_from_buckets(buckets, _DESCRIBE_SECTION_META)


def _sections_from_buckets(
    buckets: Dict[str, List[Dict[str, Any]]],
    meta: Sequence[Tuple[str, str]],
) -> List[Dict[str, Any]]:
    sections_out: List[Dict[str, Any]] = []
    for sid, title in meta:
        items = buckets.get(sid) or []
        if not items:
            continue
        sections_out.append({"section_id": sid, "title": title, "patterns": items})
    return sections_out


def _bucket_generic_category(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    return [
        {
            "section_id": "generic",
            "title": _OTHER_GENERIC_SECTION,
            "patterns": rows,
        }
    ]


def build_pattern_tabs_model() -> List[Dict[str, Any]]:
    rows = flat_patterns_with_audio()

    tabs_out: List[Dict[str, Any]] = []

    for tab_id, label in TAB_DEFINITIONS:
        cat_rows = _patterns_for_category(rows, tab_id)
        if tab_id == "describe":
            sections = _bucket_describe(cat_rows)
        elif tab_id == "routine":
            sections = bucket_routine_rows(cat_rows) if cat_rows else []
        elif tab_id == "experience":
            sections = bucket_experience_rows(cat_rows) if cat_rows else []
        elif tab_id == "comparison":
            sections = bucket_comparison_rows(cat_rows) if cat_rows else []
        elif tab_id in ALLOWED_CATEGORIES:
            sections = _bucket_generic_category(cat_rows)
        else:
            sections = []

        empty_message = None
        if not cat_rows and tab_id == "routine":
            empty_message = (
                "루틴 패턴이 아직 없습니다. "
                "master_patterns.json 등에 category=routine 데이터를 넣으면 아래 그룹으로 표시됩니다."
            )
        elif not cat_rows and tab_id == "experience":
            empty_message = (
                "경험 패턴이 아직 없습니다. "
                "master_patterns.json 등에 category=experience 데이터를 넣으면 아래 그룹으로 표시됩니다."
            )
        elif not cat_rows and tab_id == "comparison":
            empty_message = (
                "비교 패턴이 아직 없습니다. "
                "master_patterns.json 등에 category=comparison 데이터를 넣으면 아래 그룹으로 표시됩니다."
            )
        elif not cat_rows and tab_id not in ("routine", "experience", "comparison"):
            labels_ko = {
                "opinion": "의견",
                "roleplay": "롤플레이",
            }
            if tab_id in labels_ko:
                empty_message = f"{labels_ko[tab_id]} 패턴은 DB에 없습니다."

        tabs_out.append(
            {
                "tab_id": tab_id,
                "label": label,
                "sections": sections,
                "empty_message": empty_message,
            }
        )

    return tabs_out
