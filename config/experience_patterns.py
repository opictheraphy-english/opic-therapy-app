"""
경험 탭: ``category == experience`` 행을 아코디언 섹션으로 분류.

``routine_patterns.routine_row_ui_schema``와 동일한 경량 UI dict를 사용합니다.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from config.routine_patterns import routine_row_ui_schema

EXPERIENCE_SECTION_META: Sequence[Tuple[str, str]] = (
    ("exp_good", "좋은 경험"),
    ("exp_problem", "문제·실수 경험"),
    ("exp_travel_event", "여행·이벤트 경험"),
    ("exp_emotion_shift", "감정 변화 경험"),
    ("exp_memory", "기억·인상 경험"),
    ("exp_unexpected", "예상 밖 경험"),
    ("exp_learned", "배운 경험"),
    ("exp_longtime", "오랜만 경험"),
)

EXPERIENCE_SECTION_IDS: frozenset[str] = frozenset(sid for sid, _ in EXPERIENCE_SECTION_META)

_LEGACY_SUB_TO_SECTION: Dict[str, str] = {
    "good_experience": "exp_good",
    "positive_experience": "exp_good",
    "problem_experience": "exp_problem",
    "mistake": "exp_problem",
    "travel": "exp_travel_event",
    "event": "exp_travel_event",
    "emotion": "exp_emotion_shift",
    "memory": "exp_memory",
    "unexpected": "exp_unexpected",
    "learned": "exp_learned",
    "longtime": "exp_longtime",
    "exp_good": "exp_good",
    "exp_problem": "exp_problem",
    "exp_travel_event": "exp_travel_event",
    "exp_emotion_shift": "exp_emotion_shift",
    "exp_memory": "exp_memory",
    "exp_unexpected": "exp_unexpected",
    "exp_learned": "exp_learned",
    "exp_longtime": "exp_longtime",
}


def _meaning_hint_section(blob: str) -> Optional[str]:
    if any(k in blob for k in ("여행", "축제", "행사", "콘서트", "비행", "일정")):
        return "exp_travel_event"
    if any(k in blob for k in ("문제", "실수", "망쳐", "안 풀려", "곤란")):
        return "exp_problem"
    if any(k in blob for k in ("처음엔", "나중엔", "결국", "기분이", "긴장", "안도")):
        return "exp_emotion_shift"
    if any(k in blob for k in ("기억", "인상", "기억에 남", "떠오르")):
        return "exp_memory"
    if any(k in blob for k in ("예상", "몰랐", "깜짝", "뜻밖")):
        return "exp_unexpected"
    if any(k in blob for k in ("배웠", "교훈", "느낀 점")):
        return "exp_learned"
    if any(k in blob for k in ("오랜만", "오래간만", "한참 만")):
        return "exp_longtime"
    if any(k in blob for k in ("좋았", "최고", "기억에 남는", "멋진")):
        return "exp_good"
    return None


def _experience_section_for_row(row: Dict[str, Any]) -> str:
    sub = (row.get("subcategory") or "general").strip().lower().replace(" ", "_")
    if sub in EXPERIENCE_SECTION_IDS:
        return sub
    if sub in _LEGACY_SUB_TO_SECTION:
        return _LEGACY_SUB_TO_SECTION[sub]

    blob = f"{sub} {(row.get('meaning') or '')} {(row.get('pattern_en') or '')}"
    hinted = _meaning_hint_section(blob)
    if hinted:
        return hinted

    b = blob.lower()
    if any(w in b for w in ("travel", "trip", "flight", "festival", "concert", "wedding")):
        return "exp_travel_event"
    if any(w in b for w in ("problem", "mistake", "went wrong", "didn't go as planned")):
        return "exp_problem"
    if any(w in b for w in ("at first", "later", "nervous", "felt better")):
        return "exp_emotion_shift"
    if any(w in b for w in ("remember", "stood out", "memorable")):
        return "exp_memory"
    if any(w in b for w in ("unexpected", "didn't expect", "surprise")):
        return "exp_unexpected"
    if any(w in b for w in ("learned", "lesson", "taught me")):
        return "exp_learned"
    if any(w in b for w in ("first time in a long", "after a long", "for the first time in ages")):
        return "exp_longtime"
    if any(w in b for w in ("best experience", "great experience", "wonderful time")):
        return "exp_good"
    return "exp_good"


def bucket_experience_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {sid: [] for sid, _ in EXPERIENCE_SECTION_META}
    for r in rows:
        sid = _experience_section_for_row(r)
        if sid not in buckets:
            sid = "exp_good"
        buckets[sid].append(routine_row_ui_schema(r))

    out: List[Dict[str, Any]] = []
    for sid, title in EXPERIENCE_SECTION_META:
        items = buckets.get(sid) or []
        if not items:
            continue
        out.append({"section_id": sid, "title": title, "patterns": items})
    return out
