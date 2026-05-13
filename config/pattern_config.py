"""Pattern banks + production pattern DB (master_patterns.json only)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.pattern_roles import infer_pattern_role, normalize_role

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_MASTER_JSON = _DATA_DIR / "patterns" / "master_patterns.json"

logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = frozenset(
    {"describe", "routine", "experience", "comparison", "opinion", "roleplay"}
)

PATTERN_BANK = {
    "Step 1. 외과적 스캔 (공간/외관)": [
        {"p": "Let me tell you about ~", "t": "묘사 시작"},
        {"p": "It's located in ~", "t": "장소 위치"},
        {"p": "From the outside, it looks ~", "t": "외부 모습"},
        {"p": "Inside, it's ~", "t": "내부 모습"},
        {"p": "The layout is ~", "t": "구조 설명"},
        {"p": "The atmosphere is ~", "t": "분위기 묘사"},
        {"p": "It's quite [adjective] ~", "t": "묘사 강조"},
    ],
    "Step 2. 기능적 분석 (활동/사람)": [
        {"p": "My favorite space is ~", "t": "최애 공간"},
        {"p": "I usually spend my time ~", "t": "일상 활동"},
        {"p": "I like to go with ~", "t": "함께하는 사람"},
        {"p": "We share responsibilities by ~", "t": "책임 분담"},
        {"p": "I would recommend it because ~", "t": "추천 이유"},
    ],
    "Step 3. 심리적 진단 (이유/비교/결론)": [
        {"p": "I enjoy [type] because ~", "t": "선호 유형/이유"},
        {"p": "The reason I like it is ~", "t": "선호 이유"},
        {"p": "What I love about it is ~", "t": "특징/매력"},
        {"p": "It offers me ~", "t": "제공 혜택"},
        {"p": "The best thing about it is ~", "t": "장점 강조"},
        {"p": "Compared to ~, it's ~", "t": "비교 설명"},
        {"p": "Personally, I think ~", "t": "개인적 소견"},
        {"p": "That's why I like ~", "t": "마무리"},
    ],
}


def _normalize_master_record(rec: Dict[str, Any]) -> Dict[str, Any]:
    """레거시 single example → examples[] + meaning 필드 통일."""
    r = dict(rec)
    ex_list: List[Dict[str, Any]] = []
    if isinstance(r.get("examples"), list) and r["examples"]:
        for x in r["examples"]:
            if not isinstance(x, dict):
                continue
            en = (x.get("en") or "").strip()
            if not en:
                continue
            item: Dict[str, Any] = {"en": en, "ko": (x.get("ko") or "").strip()}
            af = (x.get("audio_file") or "").strip()
            if af:
                item["audio_file"] = af
            ex_list.append(item)
    elif isinstance(r.get("example"), dict) and (r["example"].get("en") or "").strip():
        ex = r["example"]
        ex_list.append(
            {
                "en": (ex.get("en") or "").strip(),
                "ko": (ex.get("ko") or "").strip(),
            }
        )
    r["examples"] = ex_list
    r.pop("example", None)
    if not r.get("meaning"):
        r["meaning"] = (r.get("pattern_ko") or "").strip()
    r.pop("pattern_ko", None)
    return r


def load_master_patterns_flat() -> List[Dict[str, Any]]:
    """Production DB: pattern master rows (고유 pattern_en, examples[])."""
    if not _MASTER_JSON.is_file():
        logger.error("Missing master pattern DB: %s", _MASTER_JSON)
        return []
    raw = json.loads(_MASTER_JSON.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for rec in raw:
        if not isinstance(rec, dict):
            continue
        cat = (rec.get("category") or "describe").strip().lower()
        if cat not in ALLOWED_CATEGORIES:
            logger.warning(
                "Skipping pattern_id=%r (invalid category %r; allowed: %s)",
                rec.get("pattern_id"),
                cat,
                sorted(ALLOWED_CATEGORIES),
            )
            continue
        out.append(_normalize_master_record(rec))
    return out


def _audio_filename(global_index: int) -> str:
    return f"pattern_{global_index:04d}.mp3"


def flat_patterns_with_audio() -> List[Dict[str, Any]]:
    """
    UI/매핑용 flat 리스트. 각 항목 = 고유 패턴 1개 + examples[] 전체.
    기본 재생: 첫 예문 + 해당 audio_file (병합 시 레거시 파일명 유지).
    """
    raw = load_master_patterns_flat()
    out: List[Dict[str, Any]] = []
    for i, rec in enumerate(raw, start=1):
        pid = str(rec.get("pattern_id") or "")
        cat = (rec.get("category") or "describe").strip().lower()
        sub = (rec.get("subcategory") or "general").strip().lower().replace(" ", "_")
        tags = rec.get("tags") if isinstance(rec.get("tags"), list) else []
        examples = rec.get("examples") if isinstance(rec.get("examples"), list) else []
        first = examples[0] if examples else {}
        ex_en = (first.get("en") or "").strip()
        ex_ko = (first.get("ko") or "").strip()
        audio_explicit = (first.get("audio_file") or "").strip()
        if audio_explicit:
            audio_file: Optional[str] = audio_explicit
        elif ex_en:
            audio_file = _audio_filename(i)
        else:
            audio_file = None
        role_src = normalize_role(rec.get("pattern_role")) or infer_pattern_role(rec)
        out.append(
            {
                "pattern_id": pid,
                "category": cat,
                "subcategory": sub,
                "pattern_role": role_src,
                "pattern_en": (rec.get("pattern_en") or "").strip(),
                "meaning": (rec.get("meaning") or "").strip(),
                "examples": examples,
                "example_en": ex_en,
                "example_ko": ex_ko,
                "audio_file": audio_file,
                "tags": tags,
                "difficulty": rec.get("difficulty"),
            }
        )
    return out


def load_grouped_patterns_for_ui() -> List[Dict[str, Any]]:
    """
    Expander-ready blocks: {category: display title, sentences: [...]}.
    Audio filenames follow global order in master file (pattern_0001.mp3 …).
    """
    flat = flat_patterns_with_audio()
    seen_order: List[tuple] = []
    groups: Dict[tuple, Dict[str, Any]] = {}

    for row in flat:
        cat = row.get("category") or "describe"
        sub = (row.get("subcategory") or "general").strip().lower().replace(" ", "_")
        key = (cat, sub)
        if key not in groups:
            sub_disp = sub.replace("_", " ").title()
            groups[key] = {
                "category": f"{cat.title()} · {sub_disp}",
                "sentences": [],
            }
            seen_order.append(key)

        pid = str(row.get("pattern_id") or "")
        groups[key]["sentences"].append(
            {
                "en": row.get("example_en") or "",
                "ko": row.get("example_ko") or "",
                "pattern_id": pid,
                "pattern_en": row.get("pattern_en"),
                "meaning": row.get("meaning"),
                "examples": row.get("examples"),
                "difficulty": row.get("difficulty"),
                "tags": row.get("tags"),
                "audio_file": row.get("audio_file") or "",
            }
        )

    return [groups[k] for k in seen_order]


def load_description_patterns() -> List[Dict[str, Any]]:
    """Backward-compatible name: UI expects grouped description-style drills."""
    return load_grouped_patterns_for_ui()
