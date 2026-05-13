#!/usr/bin/env python3
"""Merge flat pattern-library JSON into archived legacy app-format JSON (nested blocks).

Production UI reads only data/patterns/master_patterns.json. After merging legacy batches,
run: python scripts/build_master_patterns.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
LEGACY_DESC = DATA / "patterns" / "archive" / "description_patterns_pre_reset.json"


def pretty_sub(sub: str) -> str:
    return " ".join(w.capitalize() for w in sub.replace("-", "_").split("_"))


def strip_audio_meta(blocks: list) -> None:
    for block in blocks:
        for s in block.get("sentences") or []:
            if isinstance(s, dict):
                s.pop("id", None)
                s.pop("audio_file", None)


def merge_batch(src_path: Path, category_prefix: str = "Describe ·") -> None:
    if not LEGACY_DESC.is_file():
        print(
            f"Missing {LEGACY_DESC}\n"
            "Restore or copy a legacy nested description_patterns JSON into that path first.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    flat = json.loads(src_path.read_text(encoding="utf-8"))
    existing = json.loads(LEGACY_DESC.read_text(encoding="utf-8"))
    strip_audio_meta(existing)

    order: list[str] = []
    groups: dict[str, list] = defaultdict(list)

    for item in flat:
        sub = item.get("subcategory") or "general"
        if sub not in order:
            order.append(sub)
        ex = item.get("example") or {}
        sentence = {
            "en": (ex.get("en") or "").strip(),
            "ko": (ex.get("ko") or "").strip(),
            "pattern_en": item.get("pattern_en"),
            "pattern_ko": item.get("pattern_ko"),
            "library_category": item.get("category"),
            "subcategory": sub,
            "difficulty": item.get("difficulty"),
            "tags": item.get("tags"),
        }
        groups[sub].append(sentence)

    for sub in order:
        existing.append(
            {
                "category": f"{category_prefix} {pretty_sub(sub)}",
                "sentences": groups[sub],
            }
        )

    LEGACY_DESC.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] Appended {len(flat)} sentences in {len(order)} categories → {LEGACY_DESC}")
    print("[next] python scripts/build_master_patterns.py")


if __name__ == "__main__":
    default_src = DATA / "patterns" / "archive" / "pattern_library_pre_reset" / "describe_batch1.json"
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else default_src
    merge_batch(src)
