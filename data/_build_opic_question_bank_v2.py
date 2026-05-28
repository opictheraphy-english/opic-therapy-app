"""One-off generator for opic_question_bank_v2.py — run from repo root; not imported by app."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

_RAW_PATH = Path(__file__).resolve().parent / "raw_opic_questions_v2.txt"
_OUT_PATH = Path(__file__).resolve().parent / "opic_question_bank_v2.py"

_KO_HELPER = "이 질문에 대해 영어로 답변해 보세요."

_TOPIC_META: List[Tuple[str, str, str]] = [
    ("home", "집", "Home"),
    ("family_home", "가족·집안일", "Family & Home"),
    ("movies_tv", "영화·TV", "Movies & TV"),
    ("performances", "공연", "Performances"),
    ("park", "공원", "Park"),
    ("beach", "해변", "Beach"),
    ("sports", "스포츠", "Sports"),
    ("cafe", "카페", "Cafe"),
    ("shopping", "쇼핑", "Shopping"),
    ("music", "음악", "Music"),
    ("singing", "노래", "Singing"),
    ("instruments", "악기", "Instruments"),
    ("cooking", "요리", "Cooking"),
    ("books", "독서", "Books"),
    ("walking", "걷기", "Walking"),
    ("jogging", "조깅", "Jogging"),
    ("gym", "헬스·운동", "Gym"),
    ("travel", "여행", "Travel"),
    ("vacation", "휴가", "Vacation"),
    ("neighborhood", "동네", "Neighborhood"),
    ("furniture", "가구", "Furniture"),
    ("holidays", "명절·휴일", "Holidays"),
    ("recycling", "재활용", "Recycling"),
    ("country_places", "나라·지역", "Country & Places"),
    ("free_time", "여가", "Free Time"),
    ("gatherings", "모임·행사", "Gatherings"),
    ("hotels", "호텔", "Hotels"),
    ("technology", "기술·가전", "Technology"),
    ("phone", "휴대폰", "Phone"),
    ("internet", "인터넷", "Internet"),
    ("industry", "산업·기업", "Industry"),
    ("transportation", "교통", "Transportation"),
    ("restaurant", "식당", "Restaurant"),
    ("food", "음식", "Food"),
    ("health", "건강", "Health"),
    ("bank", "은행", "Bank"),
    ("appointments", "예약·병원", "Appointments"),
    ("weather", "날씨·계절", "Weather"),
    ("fashion", "옷·패션", "Fashion"),
]

# topic_id -> (icon name, color name) for topic-practice cards.
_TOPIC_VISUAL: Dict[str, Tuple[str, str]] = {
    "home": ("home", "teal"),
    "family_home": ("users", "teal"),
    "movies_tv": ("device-tv", "purple"),
    "performances": ("masks-theater", "purple"),
    "park": ("tree", "teal"),
    "beach": ("beach", "blue"),
    "sports": ("ball-football", "amber"),
    "cafe": ("coffee", "amber"),
    "shopping": ("shopping-bag", "pink"),
    "music": ("music", "pink"),
    "singing": ("microphone-2", "pink"),
    "instruments": ("guitar-pick", "purple"),
    "cooking": ("chef-hat", "coral"),
    "books": ("book", "amber"),
    "walking": ("walk", "teal"),
    "jogging": ("run", "amber"),
    "gym": ("barbell", "amber"),
    "travel": ("plane", "blue"),
    "vacation": ("umbrella", "blue"),
    "neighborhood": ("map-pin", "teal"),
    "furniture": ("sofa", "teal"),
    "holidays": ("gift", "pink"),
    "recycling": ("recycle", "teal"),
    "country_places": ("world", "blue"),
    "free_time": ("mood-smile", "amber"),
    "gatherings": ("confetti", "pink"),
    "hotels": ("building-skyscraper", "blue"),
    "technology": ("device-laptop", "purple"),
    "phone": ("device-mobile", "purple"),
    "internet": ("wifi", "purple"),
    "industry": ("building-factory", "purple"),
    "transportation": ("bus", "blue"),
    "restaurant": ("tools-kitchen-2", "coral"),
    "food": ("soup", "coral"),
    "health": ("heartbeat", "coral"),
    "bank": ("building-bank", "teal"),
    "appointments": ("calendar-event", "coral"),
    "weather": ("cloud", "blue"),
    "fashion": ("shirt", "pink"),
}

# (topic_id, keywords) — earlier rows win on first match
_TOPIC_RULES: List[Tuple[str, Tuple[str, ...]]] = [
    ("family_home", ("chores", "responsibilities at home", "family at home", "family member", "relative", "relatives", "lunch with your friend’s family", "family party", "family gathering", "help preparing for a large family", "schedule at home", "take care of things at home")),
    ("furniture", ("furniture",)),
    ("movies_tv", ("movie theater", "rental store", "movie together", "movie won’t play", "movie or tv", "tv show", "actor", "actress", "mp3 player", "watch a movie", "movies are", "movie you", "last movie")),
    ("performances", ("theater", "musical", "concert", "live performance", "live music", "performance", "performances", "play or musical", "ticket office", "voice lessons", "music academy", "singing lessons")),
    ("park", ("park",)),
    ("beach", ("beach",)),
    ("sports", ("sports game", "sports event", "ticket agent", "enjoy watching on tv", "sports do you")),
    ("cafe", ("coffee shop", "café", "café", "coffee for delivery",)),
    ("shopping", ("shopping", "clothing store", "big sale", "sale this weekend", "store and explain", "store manager", "sports store", "bookstore", "music store", "furniture store")),
    ("music", ("listen to music", "kind of music", "into music", "mp3", "electronics")),
    ("singing", ("singing", "sing often", "voice lesson")),
    ("instruments", ("instrument", "playing an instrument", "practice your instrument", "musical instrument")),
    ("cooking", ("cooking", "cook a meal", "meal you cooked", "dinner party", "dish you made", "nutritionist", "diet plan", "eating healthier")),
    ("books", ("book", "reading", "author", "bookstore")),
    ("walking", ("for a walk", "walking shoes", "go for walks", "long-distance walking")),
    ("jogging", ("jogging",)),
    ("gym", ("gym", "fitness center", "working out", "workout")),
    ("vacation", ("vacation", "staycation", "vacation package", "on vacation", "spent at home")),
    ("travel", ("travel agency", "trip abroad", "overseas trip", "airport", "flight has been canceled", "plane ticket", "rent a car", "rental company", "traveling abroad", "short trip", "prepare for a trip", "during a trip", "planning a vacation", "unforgettable travel", "places do you enjoy traveling")),
    ("neighborhood", ("neighborhood", "neighbor", "apartment building", "new resident", "area where you live", "real estate", "apartment in the city", "moved into a new apartment", "new apartment")),
    ("holidays", ("holiday",)),
    ("recycling", ("recycling", "recycle", "garbage")),
    ("country_places", ("in your country", "famous place in your country", "famous company", "geography", "mountains or beaches", "traditional food", "mealtimes usually", "outdoor activities are popular", "korea")),
    ("free_time", ("free time", "time off from work")),
    ("gatherings", ("gathering", "celebration", "party after", "invite another family", "old friend invited you to a party")),
    ("hotels", ("hotel",)),
    ("phone", ("smartphone", "phone call", "talking on the phone", "your phone",)),
    ("internet", ("internet", "website", "online", "apps do you")),
    ("industry", ("industry", "company", "companies in your country")),
    ("transportation", ("transportation", "get around", "unusual transportation", "rental car", "driver’s license")),
    ("restaurant", ("restaurant", "dinner at a restaurant")),
    ("food", ("traditional food", "memorable meal", "mealtimes", "lunch sometime")),
    ("health", ("healthy", "nutritionist", "diet", "being healthy", "stay healthy")),
    ("bank", ("bank", "bank account", "financial problem", "banking trouble", "losing a card")),
    ("appointments", ("appointment", "hospital", "clinic", "doctor", "schedule an appointment", "dentist")),
    ("weather", ("weather", "season", "climate", "weather forecast", "dressed up for a special event")),
    ("fashion", ("clothes", "clothing", "wearing today", "dress code", "fashion")),
    ("technology", ("technology", "appliance", "dvd player", "device", "equipment stopped")),
    ("home", ("home", "house", "apartment", "room", "layout", "walk me through your home", "broken window", "repair shop", "window", "key isn’t")),
]

_SECTION_MARKERS = {
    "Q1": "q1",
    "Q2": "q2",
    "Q3": "q3",
    "Q4": "q4",
    "Q6": "q6",
    "Q7": "q7",
    "Q8": "q8",
}

_KOREAN_SECTION_ALIASES = {
    "Q2 자연스럽게 리라이팅": "q2",
    "Q3 자연스럽게 리라이팅": "q3",
    "Q4 자연스럽게 리라이팅": "q4",
}


def _normalize_line(line: str) -> str:
    return line.strip()


def _is_section_header(line: str) -> Optional[str]:
    raw = _normalize_line(line)
    if not raw:
        return None
    for alias, key in _KOREAN_SECTION_ALIASES.items():
        if raw == alias or raw.startswith(alias):
            return key
    m = re.match(r"^Q([1-8])\s*$", raw, re.IGNORECASE)
    if m and m.group(1) != "5":
        return _SECTION_MARKERS.get(f"Q{m.group(1)}")
    return None


def _parse_topic_override(line: str) -> Optional[str]:
    """Return the topic_id from a '>> topic_id' line.

    - '>> gatherings'  -> 'gatherings'
    - '>> auto' / '>>' -> ''  (empty string = explicit "return to auto")
    - anything else    -> None  (not an override line)
    """
    raw = (line or "").strip()
    if not raw.startswith(">>"):
        return None
    body = raw[2:].strip().lower()
    if not body or body == "auto":
        return ""  # explicit reset to keyword classification
    return body


def parse_raw_sections(path: Path) -> Dict[str, List[Tuple[str, Optional[str]]]]:
    """Parse the raw question file into per-slot lists.

    Each slot maps to a list of (question_text, topic_override) tuples.
    topic_override is None when the question should be keyword-classified,
    or a topic_id string when a preceding '>> topic_id' line forced it.

    A '>> topic_id' line applies to all following questions until the next
    '>>' line or the next section header. Section headers reset the
    override to None (a fresh section starts with auto classification).
    """
    text = path.read_text(encoding="utf-8")
    sections: Dict[str, List[Tuple[str, Optional[str]]]] = {
        k: [] for k in ("q1", "q2", "q3", "q4", "q6", "q7", "q8")
    }
    current: Optional[str] = None
    topic_override: Optional[str] = None

    for line in text.splitlines():
        sec = _is_section_header(line)
        if sec:
            current = sec
            topic_override = None  # new section → back to auto
            continue

        override = _parse_topic_override(line)
        if override is not None:
            # '>> topic_id' sets the override; '>> auto' / '>>' clears it.
            topic_override = override or None
            continue

        body = _normalize_line(line)
        if not body or current is None:
            continue
        sections[current].append((body, topic_override))

    return sections


def classify_topic(text: str) -> str:
    low = text.lower()
    for topic_id, keywords in _TOPIC_RULES:
        for kw in keywords:
            if kw.lower() in low:
                return topic_id
    return "home"


def question_kind_for(opic_type: str, text: str) -> str:
    low = text.lower()
    if opic_type == "Q1":
        return "description"
    if opic_type == "Q2":
        return "routine"
    if opic_type == "Q3":
        return "experience"
    if opic_type == "Q4":
        if "problem" in low or "challenge" in low or "difficult" in low or "solved" in low:
            return "problem_solution"
        if "different" in low or "changed" in low or "first moved" in low:
            return "comparison"
        return "memorable_experience"
    if opic_type == "Q6":
        return "roleplay_question"
    if opic_type == "Q7":
        return "roleplay_problem"
    if opic_type == "Q8":
        return "roleplay_past_experience"
    return "description"


def build_questions(
    sections: Dict[str, List[Tuple[str, Optional[str]]]],
) -> Tuple[
    Dict[str, Dict[str, List[Dict[str, Any]]]],
    Dict[str, int],
    Dict[str, List[Dict[str, Any]]],
]:
    """Build the topic-practice bank and roleplay rows from parsed sections.

    For each question, the topic is the explicit override when present,
    otherwise classify_topic() — identical to the previous behaviour for
    every question that has no '>> topic_id' marker.
    """
    counters: Dict[str, Dict[str, int]] = {}
    bank: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        tid: {"q1": [], "q2": [], "q3": [], "q4": []} for tid, _, _ in _TOPIC_META
    }
    type_map = {"q1": "Q1", "q2": "Q2", "q3": "Q3", "q4": "Q4"}
    counts = {k: 0 for k in ("Q1", "Q2", "Q3", "Q4", "Q6", "Q7", "Q8")}
    def _resolve_topic(text: str, override: Optional[str]) -> str:
        # Explicit override wins; fall back to keyword classification.
        if override:
            if override not in {tid for tid, _, _ in _TOPIC_META}:
                # Unknown topic_id in a ">>" line — warn and auto-classify
                # so a typo never silently drops the question.
                print(
                    f"  [WARN] unknown topic override '>> {override}' — "
                    f"falling back to classify_topic for: {text[:60]}"
                )
                return classify_topic(text)
            return override
        return classify_topic(text)

    for qkey, opic in type_map.items():
        for text, override in sections.get(qkey, []):
            topic_id = _resolve_topic(text, override)
            counts[opic] += 1
            if topic_id not in bank:
                bank[topic_id] = {"q1": [], "q2": [], "q3": [], "q4": []}
            ctr = counters.setdefault(topic_id, {})
            n = ctr.get(qkey, 0) + 1
            ctr[qkey] = n
            bank[topic_id][qkey].append(
                {
                    "id": f"{topic_id}_{qkey}_{n:03d}",
                    "opic_type": opic,
                    "topic_id": topic_id,
                    "question_text": text,
                    "ko_helper": _KO_HELPER,
                    "question_kind": question_kind_for(opic, text),
                }
            )

    roleplay_rows: Dict[str, List[Dict[str, Any]]] = {k: [] for k in ("q6", "q7", "q8")}
    for qkey, opic in (("q6", "Q6"), ("q7", "Q7"), ("q8", "Q8")):
        for text, override in sections.get(qkey, []):
            counts[opic] += 1
            topic_id = _resolve_topic(text, override)
            ctr = counters.setdefault(topic_id, {})
            n = ctr.get(qkey, 0) + 1
            ctr[qkey] = n
            roleplay_rows[qkey].append(
                {
                    "id": f"{topic_id}_{qkey}_{n:03d}",
                    "opic_type": opic,
                    "topic_id": topic_id,
                    "question_text": text,
                    "ko_helper": _KO_HELPER,
                    "question_kind": question_kind_for(opic, text),
                }
            )
    return bank, counts, roleplay_rows


def build_roleplay_sets(roleplay_rows: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    q6 = roleplay_rows["q6"]
    q7 = roleplay_rows["q7"]
    q8 = roleplay_rows["q8"]
    n = min(len(q6), len(q7), len(q8))
    sets: List[Dict[str, Any]] = []
    for i in range(n):
        item6, item7, item8 = q6[i], q7[i], q8[i]
        topic_id = item6.get("topic_id") or item7.get("topic_id") or "home"
        title_ko = next((ko for tid, ko, _ in _TOPIC_META if tid == topic_id), topic_id)
        sets.append(
            {
                "set_id": f"roleplay_{i + 1:03d}",
                "topic_id": topic_id,
                "title_ko": f"{title_ko} 롤플레이",
                "questions": {"q6": item6, "q7": item7, "q8": item8},
            }
        )
    return sets


def _py_repr(obj: Any, indent: int = 0) -> str:
    sp = " " * indent
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        lines = ["{"]
        for k, v in obj.items():
            lines.append(f'{sp}    "{k}": {_py_repr(v, indent + 4)},')
        lines.append(f"{sp}}}")
        return "\n".join(lines)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        if all(isinstance(x, dict) for x in obj) and len(obj) > 8:
            lines = ["["]
            for x in obj:
                lines.append(f"{sp}    {_py_repr(x, indent + 4)},")
            lines.append(f"{sp}]")
            return "\n".join(lines)
        return repr(obj)
    if isinstance(obj, str):
        return repr(obj)
    return repr(obj)


# Kept in sync with data/opic_question_bank_v2.py — spliced into generated module.
_EMIT_GET_TOPIC_PRACTICE_SET = '''
def get_topic_practice_set(topic_id: str) -> List[Dict[str, Any]]:
    """Assemble a 3-question topic-practice set for a topic.

    Strategy: prefer the canonical OPIc ordering (one from q1, q2, then q3
    or q4). If that yields fewer than 3 — because some slots are empty —
    backfill from ALL slots (q1..q4) with any not-yet-used question until
    the set has 3, or the topic's question pool is exhausted.

    The UI only reads each question's `opic_type` field and its list
    index, never the slot name, so backfilled questions render correctly
    even when their OPIc type ordering is mixed.

    Returns 0-3 question dicts, each a copy of the bank's 6-key dict.
    """
    tid = str(topic_id or "").strip()
    bucket = TOPIC_PRACTICE_QUESTIONS.get(tid) or {}

    out: List[Dict[str, Any]] = []
    used_ids: set = set()

    def _take(row: Dict[str, Any]) -> bool:
        """Add a question if it is a dict and not already used. True if added."""
        if not isinstance(row, dict):
            return False
        rid = str(row.get("id") or "").strip()
        # Rows without an id can't be deduped reliably; fall back to identity.
        key = rid or id(row)
        if key in used_ids:
            return False
        used_ids.add(key)
        out.append(dict(row))
        return True

    # --- Pass 1: canonical ordering — q1, then q2, then q3 (else q4) -------
    for slot in ("q1", "q2"):
        rows = bucket.get(slot) or []
        if rows:
            _take(rows[0])
    q3_rows = bucket.get("q3") or []
    q4_rows = bucket.get("q4") or []
    if q3_rows:
        _take(q3_rows[0])
    elif q4_rows:
        _take(q4_rows[0])

    if len(out) >= 3:
        return out[:3]

    # --- Pass 2: backfill from the whole pool until we have 3 -------------
    # Walk every slot in order; take any question not used in pass 1.
    for slot in ("q1", "q2", "q3", "q4"):
        for row in bucket.get(slot) or []:
            if len(out) >= 3:
                return out[:3]
            _take(row)

    # Topic genuinely has fewer than 3 distinct questions — return what we
    # have. The caller still shows the "not enough questions" notice.
    return out[:3]
'''.strip()


def emit_module(
    bank: Dict[str, Dict[str, List[Dict[str, Any]]]],
    roleplay_sets: List[Dict[str, Any]],
) -> str:
    topics = [
        {
            "topic_id": tid,
            "title_ko": ko,
            "title_en": en,
            "icon": _TOPIC_VISUAL.get(tid, ("circle", "teal"))[0],
            "accent": _TOPIC_VISUAL.get(tid, ("circle", "teal"))[1],
        }
        for tid, ko, en in _TOPIC_META
    ]
    lines = [
        '"""Structured OPIc question bank v2 — generated from data/raw_opic_questions_v2.txt."""',
        "",
        "from __future__ import annotations",
        "",
        "from typing import Any, Dict, List, Optional",
        "",
        "_KO_HELPER_DEFAULT = " + repr(_KO_HELPER),
        "",
        "TOPIC_PRACTICE_TOPICS: List[Dict[str, str]] = " + repr(topics),
        "",
        "TOPIC_PRACTICE_QUESTIONS: Dict[str, Dict[str, List[Dict[str, Any]]]] = "
        + repr(bank),
        "",
        "ROLEPLAY_PRACTICE_SETS: List[Dict[str, Any]] = " + repr(roleplay_sets),
        "",
        "_ROLEPLAY_BY_ID: Dict[str, Dict[str, Any]] = {",
        '    s["set_id"]: s for s in ROLEPLAY_PRACTICE_SETS',
        "}",
        "",
        "_TOPIC_TITLE_BY_ID: Dict[str, str] = {",
        '    t["topic_id"]: t["title_ko"] for t in TOPIC_PRACTICE_TOPICS',
        "}",
        "",
        "def list_topic_ids() -> List[str]:",
        '    return [t["topic_id"] for t in TOPIC_PRACTICE_TOPICS]',
        "",
        "def get_topic_title(topic_id: str) -> str:",
        '    return _TOPIC_TITLE_BY_ID.get(str(topic_id or "").strip(), "")',
        "",
        "def get_topic_questions(topic_id: str) -> Dict[str, List[Dict[str, Any]]]:",
        '    tid = str(topic_id or "").strip()',
        "    empty = {\"q1\": [], \"q2\": [], \"q3\": [], \"q4\": []}",
        "    return dict(TOPIC_PRACTICE_QUESTIONS.get(tid) or empty)",
        "",
        *_EMIT_GET_TOPIC_PRACTICE_SET.splitlines(),
        "",
        "def list_roleplay_set_ids() -> List[str]:",
        '    return [s["set_id"] for s in ROLEPLAY_PRACTICE_SETS]',
        "",
        "def get_roleplay_practice_set(set_id: str) -> List[Dict[str, Any]]:",
        '    sid = str(set_id or "").strip()',
        "    ent = _ROLEPLAY_BY_ID.get(sid)",
        "    if not ent:",
        "        return []",
        "    qs = ent.get(\"questions\") or {}",
        "    out: List[Dict[str, Any]] = []",
        "    for key in (\"q6\", \"q7\", \"q8\"):",
        "        row = qs.get(key)",
        "        if isinstance(row, dict):",
        "            out.append(dict(row))",
        "    return out",
        "",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    sections = parse_raw_sections(_RAW_PATH)
    bank, counts, roleplay_rows = build_questions(sections)
    roleplay_sets = build_roleplay_sets(roleplay_rows)
    _OUT_PATH.write_text(emit_module(bank, roleplay_sets), encoding="utf-8")
    try:
        logger.info(
            "[BUILD_OPIC_BANK_V2] Q1=%s Q2=%s Q3=%s Q4=%s Q6=%s Q7=%s Q8=%s topics=%s roleplay_sets=%s",
            counts["Q1"],
            counts["Q2"],
            counts["Q3"],
            counts["Q4"],
            counts["Q6"],
            counts["Q7"],
            counts["Q8"],
            len(_TOPIC_META),
            len(roleplay_sets),
        )
    except Exception:
        pass


if __name__ == "__main__":
    main()
