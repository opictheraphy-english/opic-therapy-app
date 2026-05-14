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


_MASTER_CACHE: Optional[List[Dict[str, Any]]] = None
_FLAT_CACHE: Optional[List[Dict[str, Any]]] = None


def _load_master_patterns_flat_uncached() -> List[Dict[str, Any]]:
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


def load_master_patterns_flat() -> List[Dict[str, Any]]:
    """Production DB: pattern master rows (process-cached, JSON read once)."""
    global _MASTER_CACHE
    if _MASTER_CACHE is None:
        _MASTER_CACHE = _load_master_patterns_flat_uncached()
    return _MASTER_CACHE


def _audio_filename(global_index: int) -> str:
    return f"pattern_{global_index:04d}.mp3"


def _flat_patterns_with_audio_uncached() -> List[Dict[str, Any]]:
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


def flat_patterns_with_audio() -> List[Dict[str, Any]]:
    """
    UI/매핑용 flat 리스트 (process-cached). 각 항목 = 고유 패턴 1개 + examples[].
    JSON 파싱 + 정규화는 첫 호출에서만 수행하고 이후 같은 리스트를 재사용합니다.
    """
    global _FLAT_CACHE
    if _FLAT_CACHE is None:
        _FLAT_CACHE = _flat_patterns_with_audio_uncached()
    return _FLAT_CACHE


def invalidate_pattern_cache() -> None:
    """Test/CLI helper — drop in-process pattern caches."""
    global _MASTER_CACHE, _FLAT_CACHE
    _MASTER_CACHE = None
    _FLAT_CACHE = None
