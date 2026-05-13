#!/usr/bin/env python3
"""Merge experience_core_extension.json into master_patterns.json (idempotent)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "patterns" / "master_patterns.json"
EXT = ROOT / "data" / "patterns" / "experience_core_extension.json"


def main() -> int:
    if not EXT.is_file():
        print("Missing", EXT, file=sys.stderr)
        return 1
    master = json.loads(MASTER.read_text(encoding="utf-8"))
    extra = json.loads(EXT.read_text(encoding="utf-8"))
    if not isinstance(master, list) or not isinstance(extra, list):
        print("Invalid JSON shape", file=sys.stderr)
        return 1
    have = {r.get("pattern_id") for r in master if isinstance(r, dict)}
    added = 0
    for row in extra:
        if not isinstance(row, dict):
            continue
        pid = row.get("pattern_id")
        if pid in have:
            continue
        master.append(row)
        have.add(pid)
        added += 1
    MASTER.write_text(json.dumps(master, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Appended {added} experience patterns (skipped duplicates). Total rows: {len(master)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
