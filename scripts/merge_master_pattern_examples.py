#!/usr/bin/env python3
"""
동일 pattern_en → 1 master row, 예문은 examples[] 로 병합.
기존 행 순번 i → audio pattern_{i:04d}.mp3 를 각 예문에 보존.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MASTER = ROOT / "data" / "patterns" / "master_patterns.json"
ARCHIVE = ROOT / "data" / "patterns" / "archive" / "master_patterns_pre_merge_flat.json"


def _norm_pattern_key(pe: str) -> str:
    s = (pe or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s


def _examples_from_row(rec: Dict[str, Any], row_index: int) -> List[Dict[str, Any]]:
    """레거시 example 단일 또는 이미 병합된 examples[] 모두 처리."""
    out: List[Dict[str, Any]] = []
    if isinstance(rec.get("examples"), list):
        for ex in rec["examples"]:
            if not isinstance(ex, dict):
                continue
            en = (ex.get("en") or "").strip()
            if not en:
                continue
            af = (ex.get("audio_file") or "").strip() or f"pattern_{row_index:04d}.mp3"
            out.append({"en": en, "ko": (ex.get("ko") or "").strip(), "audio_file": af})
        if out:
            return out
    ex = rec.get("example") if isinstance(rec.get("example"), dict) else {}
    en = (ex.get("en") or "").strip()
    if en:
        out.append(
            {
                "en": en,
                "ko": (ex.get("ko") or "").strip(),
                "audio_file": f"pattern_{row_index:04d}.mp3",
            }
        )
    return out


def _merge_rows(raw: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """첫 등장 순서 유지, 같은 템플릿 키끼리 병합."""
    order: List[str] = []
    buckets: "OrderedDict[str, List[Tuple[int, Dict[str, Any]]]]" = OrderedDict()

    for idx, rec in enumerate(raw, start=1):
        if not isinstance(rec, dict):
            continue
        pe = (rec.get("pattern_en") or "").strip()
        key = _norm_pattern_key(pe)
        if not key:
            continue
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append((idx, rec))

    out: List[Dict[str, Any]] = []
    for key in order:
        rows = buckets[key]
        rows.sort(key=lambda x: x[0])
        _, first = rows[0]

        pattern_display = (first.get("pattern_en") or "").strip()
        meaning = (first.get("meaning") or first.get("pattern_ko") or "").strip()
        cat = (first.get("category") or "describe").strip().lower()
        sub = (first.get("subcategory") or "general").strip().lower().replace(" ", "_")

        examples: List[Dict[str, Any]] = []
        seen_en: set[str] = set()

        for orig_idx, r in rows:
            for ex in _examples_from_row(r, orig_idx):
                ek = ex["en"].lower().strip()
                if ek in seen_en:
                    continue
                seen_en.add(ek)
                examples.append(ex)

        diffs = [r.get("difficulty") for _, r in rows if isinstance(r.get("difficulty"), int)]
        diff_min = min(diffs) if diffs else first.get("difficulty")

        tag_set: set[str] = set()
        for _, r in rows:
            t = r.get("tags")
            if isinstance(t, list):
                tag_set.update(str(x) for x in t if x)

        pid_new = f"DES_{len(out) + 1:03d}"
        merged: Dict[str, Any] = {
            "pattern_id": pid_new,
            "category": cat,
            "subcategory": sub,
            "pattern_en": pattern_display,
            "meaning": meaning,
            "examples": examples,
            "difficulty": diff_min,
            "tags": sorted(tag_set),
        }
        pr = first.get("pattern_role")
        if pr:
            merged["pattern_role"] = pr
        out.append(merged)

    return out


def main() -> None:
    if not MASTER.is_file():
        print(f"Missing {MASTER}", file=sys.stderr)
        raise SystemExit(1)

    raw = json.loads(MASTER.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise SystemExit("master must be a JSON array")

    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(MASTER, ARCHIVE)
    print(f"[backup] {ARCHIVE}")

    merged = _merge_rows(raw)
    MASTER.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] merged {len(raw)} rows → {len(merged)} pattern masters → {MASTER}")


if __name__ == "__main__":
    main()
