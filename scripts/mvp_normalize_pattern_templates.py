#!/usr/bin/env python3
"""
MVP: pattern_en = 짧은 템플릿(~), example = 실제 문장(청취·TTS).
master_patterns.json in-place 갱신.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MASTER = ROOT / "data" / "patterns" / "master_patterns.json"

# subcategory → 권장 템플릿(이미 ~ 포함)
SUB_TEMPLATE: dict[str, str] = {
    "opening_intro": "Let me tell you about ~",
    "exterior": "From the outside, it looks ~",
    "appearance": "It has a(n) ~ look.",
    "visuals": "Visually, it’s ~",
    "atmosphere": "The atmosphere is ~",
    "lighting": "The lighting is ~",
    "comfort": "It feels ~ in terms of comfort.",
    "sound": "It sounds ~",
    "crowd": "It’s usually ~ in terms of crowd.",
    "interior_space": "Inside, it’s ~",
    "interior": "The interior is ~",
    "space": "The space feels ~",
    "favorite_space": "My favorite space is ~",
    "location": "It’s located in ~",
    "size": "The size is ~",
    "layout": "The layout is ~",
    "environment": "The environment is ~",
    "details": "One detail I like is ~",
    "weather": "The weather there is ~",
    "condition": "The conditions are ~",
    "daily_routine": "I usually spend my time ~",
    "responsibilities": "We share responsibilities by ~",
    "companions": "I like to go with ~",
    "preference_type": "I enjoy ~ because ~",
    "preference_reason": "The reason I like it is ~",
    "features_love": "What I love about it is ~",
    "emphasis": "It’s quite ~",
    "strengths": "The best thing about it is ~",
    "benefits": "It offers me ~",
    "comparison_phrase": "Compared to ~, it’s ~",
    "personal_view": "Personally, I think ~",
    "recommendation": "I would recommend it because ~",
    "conclusion": "Overall, ~",
    "overall_impression": "Overall, I’d describe it as ~",
    "features": "One feature is ~",
}


def _derive_template(rec: dict, ex_en: str, sub: str) -> str:
    pe = (rec.get("pattern_en") or "").strip()
    if "~" in pe and len(pe) < 120:
        return pe
    if sub in SUB_TEMPLATE:
        return SUB_TEMPLATE[sub]
    low = pe.lower()
    if low.startswith("let me tell you about"):
        return "Let me tell you about ~"
    if low.startswith("from the outside"):
        return "From the outside, it looks ~"
    if low.startswith("inside"):
        return "Inside, it’s ~"
    if low.startswith("the atmosphere"):
        return "The atmosphere is ~"
    if low.startswith("the layout"):
        return "The layout is ~"
    if low.startswith("compared to"):
        return "Compared to ~, it’s ~"
    if low.startswith("overall"):
        return "Overall, ~"
    # 마지막 수단: 첫 절만 남기고 ~
    first = pe.split(".")[0].strip()
    if len(first) > 70:
        first = first[:67].rsplit(" ", 1)[0] + "..."
    return (first + " ~").strip() if first else " ~"


def main() -> None:
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("invalid master json")

    for rec in data:
        if not isinstance(rec, dict):
            continue
        ex = rec.get("example") if isinstance(rec.get("example"), dict) else {}
        ex_en = (ex.get("en") or "").strip()
        ex_ko = (ex.get("ko") or "").strip()
        pe_old = (rec.get("pattern_en") or "").strip()
        pk_old = (rec.get("pattern_ko") or "").strip()

        if not ex_en and pe_old:
            ex_en = pe_old
            ex_ko = pk_old or ex_ko
            rec["example"] = {"en": ex_en, "ko": ex_ko}

        sub = (rec.get("subcategory") or "general").strip().lower().replace(" ", "_")

        new_pe = _derive_template(rec, ex_en, sub)
        rec["pattern_en"] = new_pe

        if pk_old and "~" not in pk_old:
            rec["pattern_ko"] = pk_old
        elif not pk_old:
            rec["pattern_ko"] = ""

    MASTER.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] normalized templates → {MASTER}")


if __name__ == "__main__":
    main()
