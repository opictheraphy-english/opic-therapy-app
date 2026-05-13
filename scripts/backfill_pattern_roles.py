#!/usr/bin/env python3
"""Add pattern_role to every row in data/patterns/master_patterns.json (idempotent)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config.pattern_roles import infer_pattern_role, normalize_role

MASTER = ROOT / "data" / "patterns" / "master_patterns.json"


def main() -> None:
    if not MASTER.is_file():
        print(f"Missing {MASTER}", file=sys.stderr)
        raise SystemExit(1)
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        print("[error] master must be a JSON array", file=sys.stderr)
        raise SystemExit(1)
    for rec in data:
        if not isinstance(rec, dict):
            continue
        existing = normalize_role(rec.get("pattern_role"))
        rec["pattern_role"] = existing or infer_pattern_role(rec)

    MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] wrote pattern_role on {len(data)} rows → {MASTER}")


if __name__ == "__main__":
    main()
