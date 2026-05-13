#!/usr/bin/env python3
"""
Flatten legacy nested description JSON → data/patterns/master_patterns.json
(normalize schema, tags, difficulty, pattern_id DES_xxx).

Source file (after Pattern DB reset): data/patterns/archive/description_patterns_pre_reset.json
If missing, falls back to data/description_patterns.json for one-off migration runs.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.pattern_roles import infer_pattern_role
_ARCHIVE_DESC = ROOT / "data" / "patterns" / "archive" / "description_patterns_pre_reset.json"
_LEGACY_DESC = ROOT / "data" / "description_patterns.json"
DESC = _ARCHIVE_DESC if _ARCHIVE_DESC.is_file() else _LEGACY_DESC
OUT = ROOT / "data" / "patterns" / "master_patterns.json"
STATS = ROOT / "data" / "patterns" / "master_patterns_stats.json"

CANONICAL_CATEGORY = "describe"

# Exact legacy block titles → snake_case subcategory
LEGACY_CATEGORY_TO_SUB: Dict[str, str] = {
    '1. 묘사 시작: "Let me tell you about ~"': "opening_intro",
    '2. 외관 묘사: "From the outside, it looks ~"': "exterior",
    "3. 내부 묘사: \"Inside, it's ~\"": "interior_space",
    '4. 구조 설명: "The layout is ~"': "layout",
    '5. 가장 좋아하는 공간: "My favorite space is ~"': "favorite_space",
    '6. 일상 활동: "I usually spend my time ~"': "daily_routine",
    '7. 책임 분담: "We share responsibilities by ~"': "responsibilities",
    '8. 선호하는 유형: "I enjoy ~ because ~"': "preference_type",
    '9. 선호하는 이유: "The reason I like it is ~"': "preference_reason",
    '10. 함께하는 사람: "I like to go with ~"': "companions",
    "11. 장소 설명: \"It's located in ~\"": "location",
    '12. 분위기 묘사: "The atmosphere is ~"': "atmosphere",
    '13. 특징 설명: "What I love about it is ~"': "features_love",
    '14. 선호하는 이유 : "It offers me ~"': "benefits",
    '15. 추천 이유: "I would recommend it because ~"': "recommendation",
    "16. 묘사 강조: \"It's quite [형용사] ~\"": "emphasis",
    '17. 장점 설명: "The best thing about it is ~"': "strengths",
    "18. 비교 설명: \"Compared to ~, it's ~\"": "comparison_phrase",
    '19. 개인적 의견: "Personally, I think ~"': "personal_view",
    "20. 마무리: \"That's why I like ~\"": "conclusion",
}

LEVEL_FROM_TAGS = {"IM": 1, "IH": 2, "AL": 3}


def title_to_snake(title: str) -> str:
    """Describe · Overall Impression → overall_impression"""
    if title.startswith("Describe · "):
        tail = title.replace("Describe · ", "").strip()
        parts = re.split(r"[\s\-]+", tail.replace("'", ""))
        return "_".join(p.lower() for p in parts if p)
    raise ValueError(f"unknown Describe title: {title}")


def infer_skill_tag(sub: str) -> str:
    if "comparison" in sub:
        return "comparison"
    if sub in {"conclusion", "opening_intro", "daily_routine"}:
        return "narration"
    return "description"


def infer_topic_tag(sub: str) -> str:
    """Map subcategory to topic-style tag when needed."""
    if sub in {"location", "exterior", "interior_space", "layout"}:
        return "daily"
    if sub in {"favorite_space", "atmosphere", "features_love"}:
        return "hobbies"
    if sub in {"recommendation", "restaurants"}:
        return "restaurants"
    if sub in {"companions", "responsibilities", "daily_routine"}:
        return "daily"
    if sub in {"comparison_phrase", "strengths"}:
        return "comparison"
    return "daily"


def normalize_tags(
    raw: Optional[List[str]],
    sub: str,
    difficulty: int,
) -> List[str]:
    cleaned: List[str] = []
    if raw:
        for t in raw:
            if not t:
                continue
            tl = str(t).strip().lower().replace(" ", "_")
            if tl == "describe":
                tl = "description"
            cleaned.append(tl)
    topic = infer_topic_tag(sub)
    skill = infer_skill_tag(sub)
    lvl = "IM" if difficulty <= 1 else ("AL" if difficulty >= 3 else "IH")
    merged: List[str] = []
    seen: set[str] = set()
    for t in cleaned + [topic, skill, lvl]:
        if t and t not in seen:
            seen.add(t)
            merged.append(t)
    pad = ["description", topic, "daily"]
    for t in pad:
        if len(merged) >= 3:
            break
        if t not in seen:
            seen.add(t)
            merged.append(t)
    return merged[:12]


def infer_difficulty(row: Dict[str, Any]) -> int:
    if isinstance(row.get("difficulty"), int) and 1 <= row["difficulty"] <= 3:
        return row["difficulty"]
    tags = row.get("tags") or []
    for t in tags:
        if isinstance(t, str) and t.upper() in LEVEL_FROM_TAGS:
            return LEVEL_FROM_TAGS[t.upper()]
    # Legacy drills: slightly harder framing → 2
    return 2


def clamp_example(en: str, ko: str, max_len: int = 220) -> Tuple[str, str]:
    en = (en or "").strip()
    ko = (ko or "").strip()
    if len(en) > max_len:
        en = en[: max_len - 1].rsplit(" ", 1)[0] + "."
    if len(ko) > max_len + 40:
        ko = ko[: max_len + 20].rsplit(" ", 1)[0] + "."
    return en, ko


def resolve_subcategory(block_category: str, row: Dict[str, Any]) -> str:
    if row.get("subcategory"):
        return str(row["subcategory"]).strip().lower().replace("-", "_")
    if block_category in LEGACY_CATEGORY_TO_SUB:
        return LEGACY_CATEGORY_TO_SUB[block_category]
    if block_category.startswith("Describe · "):
        return title_to_snake(block_category)
    return "general"


def flatten_records() -> Tuple[List[Dict[str, Any]], int]:
    data = json.loads(DESC.read_text(encoding="utf-8"))
    rows_out: List[Dict[str, Any]] = []
    raw_count = 0
    seen_ex: set[str] = set()
    dup_removed = 0

    for block in data:
        cat_title = block.get("category") or ""
        for row in block.get("sentences") or []:
            raw_count += 1
            en, ko = clamp_example(row.get("en"), row.get("ko"))
            if not en:
                continue
            key = en.lower().strip()
            if key in seen_ex:
                dup_removed += 1
                continue
            seen_ex.add(key)

            sub = resolve_subcategory(cat_title, row)
            diff = infer_difficulty(row)
            pat_en = (row.get("pattern_en") or en).strip()
            pat_ko = (row.get("pattern_ko") or ko).strip()

            rec = {
                "pattern_id": "",
                "category": CANONICAL_CATEGORY,
                "subcategory": sub,
                "pattern_en": pat_en,
                "meaning": pat_ko,
                "examples": [{"en": en, "ko": ko}],
                "difficulty": diff,
                "tags": normalize_tags(row.get("tags"), sub, diff),
            }
            rec["pattern_role"] = infer_pattern_role(rec)
            rows_out.append(rec)

    # Keep source order (matches legacy nested JSON & audio pattern_XXXX order).

    # Assign DES_###
    for i, r in enumerate(rows_out, start=1):
        r["pattern_id"] = f"DES_{i:03d}"

    return rows_out, dup_removed


def main() -> None:
    if not DESC.is_file():
        print(f"Missing legacy source JSON: {DESC}", file=sys.stderr)
        raise SystemExit(1)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows, dup_removed = flatten_records()

    OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    cat_ctr = Counter(r["category"] for r in rows)
    diff_ctr = Counter(r["difficulty"] for r in rows)
    sub_ctr = Counter(r["subcategory"] for r in rows)

    stats = {
        "total_patterns": len(rows),
        "source_file": str(DESC.relative_to(ROOT)),
        "duplicate_examples_removed": dup_removed,
        "by_category": dict(sorted(cat_ctr.items())),
        "by_difficulty": {str(k): v for k, v in sorted(diff_ctr.items())},
        "subcategory_count": len(sub_ctr),
        "top_subcategories": sub_ctr.most_common(15),
    }
    STATS.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
