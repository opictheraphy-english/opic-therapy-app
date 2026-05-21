"""Mock V2 question set builder — opic_question_bank_v2 + 15-seat OPIc matrix."""

from __future__ import annotations

import logging
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

from data.opic_question_bank_v2 import (
    get_topic_questions,
    get_topic_title,
    get_roleplay_practice_set,
    list_roleplay_set_ids,
    list_topic_ids,
)
from services.mock_exam.mock_exam_test_set_generator import (
    COMPARISON_POOL_AL,
    COMPARISON_POOL_IH,
    NEWS_ISSUE_POOL_AL,
    NEWS_ISSUE_POOL_IH,
    TOPIC_TRANSLATIONS,
    SURVEY_TO_BANK_TOPICS,
)

logger = logging.getLogger(__name__)

_KO_HELPER_DEFAULT = "이 질문에 대해 영어로 답변해 보세요."

_INTRO_TEXT = (
    "Hi, I'm Ava. Let's begin. Tell me about yourself in as much detail as possible."
)

# Legacy survey English labels → topic_practice_v2 topic_id
_BANK_ENGLISH_TO_V2_TOPIC_ID: Dict[str, str] = {
    "Movies": "movies_tv",
    "Shows": "performances",
    "Music": "music",
    "Nightlife": "cafe",
    "Museums": "country_places",
    "Park": "park",
    "Camping": "travel",
    "Beaches": "beach",
    "Beach": "beach",
    "Gaming": "internet",
    "Social Media and Blogging": "internet",
    "Model Figure Making": "shopping",
    "Listening to Music": "music",
    "Playing Musical Instruments": "instruments",
    "Cooking": "cooking",
    "Singing Alone": "singing",
    "Writing": "books",
    "Drawing": "books",
    "Walking": "walking",
    "Cycling": "walking",
    "Swimming": "gym",
    "Tennis": "sports",
    "Soccer": "sports",
    "Basketball": "sports",
    "Baseball": "sports",
    "Golf": "sports",
    "Gym Workouts": "gym",
    "Yoga": "health",
    "No Exercise": "health",
    "Domestic Travel": "travel",
    "International Travel": "travel",
    "Staycation": "vacation",
    "Jogging": "jogging",
    "Country": "country_places",
    "Home": "home",
    "Health": "health",
    "Restaurant": "restaurant",
    "Coffee": "cafe",
    "Internet": "internet",
    "Phones": "phone",
    "Shopping": "shopping",
    "Instrument": "instruments",
    "Food": "food",
    "Exercise": "gym",
    "Sports": "sports",
    "Travel": "travel",
    "General Topic": "home",
}

_FALLBACK_TOPIC_IDS: Tuple[str, ...] = (
    "home",
    "travel",
    "movies_tv",
    "music",
    "park",
    "walking",
    "cooking",
    "cafe",
    "restaurant",
)

_SLOT_TO_STEP: Dict[str, str] = {
    "q1": "Description",
    "q2": "Routine",
    "q3": "Experience",
    "q4": "Memorable",
    "q6": "Request Information",
    "q7": "Problem/Solution",
    "q8": "Related Experience",
}

_KIND_TO_STEP: Dict[str, str] = {
    "description": "Description",
    "routine": "Routine",
    "experience": "Experience",
    "memorable_experience": "Memorable",
    "comparison": "Comparison_Change",
    "problem_solution": "Problem/Solution",
    "roleplay_question": "Request Information",
    "roleplay_problem": "Problem/Solution",
    "roleplay_past_experience": "Related Experience",
}


def _to_english_survey_label(label: str) -> str:
    if not label:
        return ""
    if label in TOPIC_TRANSLATIONS:
        return TOPIC_TRANSLATIONS[label]
    return label


def _survey_preferred_topic_ids(survey_results: Optional[dict]) -> List[str]:
    """Map survey multiselects to opic_question_bank_v2 topic_id list (ordered, unique)."""
    topic_ids: List[str] = []
    if not survey_results:
        return list(_FALLBACK_TOPIC_IDS)
    for key in ("leisure", "interests", "sports", "travel", "hobbies"):
        vals = survey_results.get(key)
        if not isinstance(vals, list):
            continue
        for raw in vals:
            eng = _to_english_survey_label(str(raw))
            for bank_name in SURVEY_TO_BANK_TOPICS.get(eng, [eng]):
                tid = _BANK_ENGLISH_TO_V2_TOPIC_ID.get(bank_name)
                if tid:
                    topic_ids.append(tid)
                else:
                    tid2 = _BANK_ENGLISH_TO_V2_TOPIC_ID.get(eng)
                    if tid2:
                        topic_ids.append(tid2)
    out: List[str] = []
    for tid in topic_ids:
        if tid not in out:
            out.append(tid)
    return out or list(_FALLBACK_TOPIC_IDS)


def _bucket(topic_id: str) -> Dict[str, List[Dict[str, Any]]]:
    return get_topic_questions(str(topic_id or "").strip())


def _has_slot(topic_id: str, slot: str) -> bool:
    rows = _bucket(topic_id).get(slot) or []
    return bool(rows)


def _has_any_slot(topic_id: str, slots: Sequence[str]) -> bool:
    return any(_has_slot(topic_id, s) for s in slots)


def _eligible_combo1_topic_ids() -> List[str]:
    return [tid for tid in list_topic_ids() if _has_slot(tid, "q1") and _has_slot(tid, "q2") and _has_slot(tid, "q3")]


def _eligible_combo2_topic_ids() -> List[str]:
    """Q5=Q1, Q6=Q3, Q7=flex — needs q1, q3, and at least one of q2/q3/q4."""
    return [
        tid
        for tid in list_topic_ids()
        if _has_slot(tid, "q1")
        and _has_slot(tid, "q3")
        and _has_any_slot(tid, ("q2", "q3", "q4"))
    ]


def _eligible_combo3_topic_ids() -> List[str]:
    """Q8=Q1, Q9=flex, Q10=q3|q4 — needs q1 and q3 or q4."""
    return [
        tid
        for tid in list_topic_ids()
        if _has_slot(tid, "q1") and (_has_slot(tid, "q3") or _has_slot(tid, "q4"))
    ]


def _resolve_topic_id(
    pool: List[str],
    preferred: List[str],
    excluded: set[str],
) -> str:
    candidates = [t for t in pool if t not in excluded]
    if not candidates:
        candidates = [t for t in _FALLBACK_TOPIC_IDS if t not in excluded]
    if not candidates:
        raise RuntimeError("No eligible topic in opic_question_bank_v2 for this exam seat.")
    for pref in preferred:
        if pref in candidates:
            return pref
    return random.choice(candidates)


def _pick_row(topic_id: str, slot: str) -> Dict[str, Any]:
    rows = _bucket(topic_id).get(slot) or []
    if not rows:
        raise RuntimeError(f"Topic {topic_id} has no questions for slot {slot}.")
    return dict(random.choice(rows))


def _pick_flex_row(topic_id: str, allowed_slots: Sequence[str]) -> Tuple[Dict[str, Any], str]:
    available = [s for s in allowed_slots if _has_slot(topic_id, s)]
    if not available:
        raise RuntimeError(f"Topic {topic_id} has no flex slot in {allowed_slots}.")
    slot = random.choice(available)
    return _pick_row(topic_id, slot), slot


def _step_label(slot: str, row: Dict[str, Any]) -> str:
    kind = str(row.get("question_kind") or "").strip().lower()
    if kind in _KIND_TO_STEP:
        return _KIND_TO_STEP[kind]
    return _SLOT_TO_STEP.get(slot, slot)


def _topic_label(topic_id: str) -> str:
    title = get_topic_title(topic_id)
    return title or topic_id


def _to_mock_v2_question(
    qnum: int,
    *,
    combo: str,
    step: str,
    topic_id: str,
    row: Dict[str, Any],
    bank_slot: str,
) -> Dict[str, Any]:
    idx = qnum - 1
    return {
        "id": f"mock_v2_q{qnum}",
        "question_index": idx,
        "question_number": qnum,
        "opic_type": str(row.get("opic_type") or "").strip(),
        "combo": combo,
        "step": step,
        "topic": _topic_label(topic_id),
        "topic_id": topic_id,
        "bank_slot": bank_slot,
        "question_text": str(row.get("question_text") or "").strip(),
        "ko_helper": str(row.get("ko_helper") or _KO_HELPER_DEFAULT).strip()
        or _KO_HELPER_DEFAULT,
        "source_id": row.get("id"),
    }


def _intro_question() -> Dict[str, Any]:
    return {
        "id": "mock_v2_q1",
        "question_index": 0,
        "question_number": 1,
        "opic_type": "Intro",
        "combo": "Intro",
        "step": "Self-Introduction",
        "topic": "Self-Introduction",
        "topic_id": "",
        "bank_slot": "",
        "question_text": _INTRO_TEXT,
        "ko_helper": _KO_HELPER_DEFAULT,
        "source_id": None,
    }


def _advanced_question(
    qnum: int,
    *,
    combo: str,
    step: str,
    topic: str,
    question_text: str,
) -> Dict[str, Any]:
    return {
        "id": f"mock_v2_q{qnum}",
        "question_index": qnum - 1,
        "question_number": qnum,
        "opic_type": step,
        "combo": combo,
        "step": step,
        "topic": topic,
        "topic_id": "",
        "bank_slot": "",
        "question_text": question_text,
        "ko_helper": _KO_HELPER_DEFAULT,
        "source_id": None,
    }


def _pick_roleplay_triplet() -> List[Dict[str, Any]]:
    ready: List[str] = []
    for sid in list_roleplay_set_ids():
        if len(get_roleplay_practice_set(sid)) >= 3:
            ready.append(sid)
    if not ready:
        raise RuntimeError("opic_question_bank_v2 has no complete roleplay set (q6–q8).")
    rows = get_roleplay_practice_set(random.choice(ready))
    if len(rows) < 3:
        raise RuntimeError("Selected roleplay set is incomplete.")
    return rows


def build_mock_v2_exam(survey_results: dict, difficulty: int = 5) -> List[Dict[str, Any]]:
    """
    Build 15 Mock V2 questions from opic_question_bank_v2.

    Seat map:
      Q1  Self-Introduction
      Q2–4   topic t1: bank q1, q2, q3
      Q5–7   topic t2: bank q1, q3, flex q2|q3|q4
      Q8–10  topic t3: bank q1, flex q2|q3|q4, flex q3|q4
      Q11–13 roleplay q6, q7, q8 (one set)
      Q14    Comparison pool (IH/AL by difficulty)
      Q15    News/Issue pool (IH/AL by difficulty)
    """
    preferred = _survey_preferred_topic_ids(survey_results)
    combo1_pool = _eligible_combo1_topic_ids()
    combo2_pool = _eligible_combo2_topic_ids()
    combo3_pool = _eligible_combo3_topic_ids()

    if not combo1_pool:
        raise RuntimeError("opic_question_bank_v2 cannot satisfy Combo1 (q1+q2+q3).")
    if not combo2_pool:
        raise RuntimeError("opic_question_bank_v2 cannot satisfy Combo2 (q1+q3+flex).")
    if not combo3_pool:
        raise RuntimeError("opic_question_bank_v2 cannot satisfy Combo3 (q1+q3|q4).")

    excluded: set[str] = set()
    t1 = _resolve_topic_id(combo1_pool, preferred, excluded)
    excluded.add(t1)
    t2 = _resolve_topic_id(combo2_pool, preferred, excluded)
    excluded.add(t2)
    t3 = _resolve_topic_id(combo3_pool, preferred, excluded)
    excluded.add(t3)

    lev = int(difficulty) if difficulty is not None else 5
    comp_pool = COMPARISON_POOL_AL if lev >= 6 else COMPARISON_POOL_IH
    news_pool = NEWS_ISSUE_POOL_AL if lev >= 6 else NEWS_ISSUE_POOL_IH
    q14 = random.choice(comp_pool)
    q15_candidates = [x for x in news_pool if x.get("question") != q14.get("question")]
    q15 = random.choice(q15_candidates or news_pool)

    exam: List[Dict[str, Any]] = [ _intro_question() ]

    r2 = _pick_row(t1, "q1")
    exam.append(
        _to_mock_v2_question(
            2, combo="Combo1", step=_step_label("q1", r2), topic_id=t1, row=r2, bank_slot="q1"
        )
    )
    r3 = _pick_row(t1, "q2")
    exam.append(
        _to_mock_v2_question(
            3, combo="Combo1", step=_step_label("q2", r3), topic_id=t1, row=r3, bank_slot="q2"
        )
    )
    r4 = _pick_row(t1, "q3")
    exam.append(
        _to_mock_v2_question(
            4, combo="Combo1", step=_step_label("q3", r4), topic_id=t1, row=r4, bank_slot="q3"
        )
    )

    r5 = _pick_row(t2, "q1")
    exam.append(
        _to_mock_v2_question(
            5, combo="Combo2", step=_step_label("q1", r5), topic_id=t2, row=r5, bank_slot="q1"
        )
    )
    r6 = _pick_row(t2, "q3")
    exam.append(
        _to_mock_v2_question(
            6, combo="Combo2", step=_step_label("q3", r6), topic_id=t2, row=r6, bank_slot="q3"
        )
    )
    r7, slot7 = _pick_flex_row(t2, ("q2", "q3", "q4"))
    exam.append(
        _to_mock_v2_question(
            7,
            combo="Combo2",
            step=_step_label(slot7, r7),
            topic_id=t2,
            row=r7,
            bank_slot=slot7,
        )
    )

    r8 = _pick_row(t3, "q1")
    exam.append(
        _to_mock_v2_question(
            8, combo="Combo3", step=_step_label("q1", r8), topic_id=t3, row=r8, bank_slot="q1"
        )
    )
    r9, slot9 = _pick_flex_row(t3, ("q2", "q3", "q4"))
    exam.append(
        _to_mock_v2_question(
            9,
            combo="Combo3",
            step=_step_label(slot9, r9),
            topic_id=t3,
            row=r9,
            bank_slot=slot9,
        )
    )
    r10, slot10 = _pick_flex_row(t3, ("q3", "q4"))
    exam.append(
        _to_mock_v2_question(
            10,
            combo="Combo3",
            step=_step_label(slot10, r10),
            topic_id=t3,
            row=r10,
            bank_slot=slot10,
        )
    )

    rp = _pick_roleplay_triplet()
    for qnum, row, slot in ((11, rp[0], "q6"), (12, rp[1], "q7"), (13, rp[2], "q8")):
        tid = str(row.get("topic_id") or "")
        exam.append(
            _to_mock_v2_question(
                qnum,
                combo="Roleplay",
                step=_step_label(slot, row),
                topic_id=tid,
                row=row,
                bank_slot=slot,
            )
        )

    exam.append(
        _advanced_question(
            14,
            combo="Advanced",
            step="Comparison",
            topic=str(q14.get("topic") or "Comparison"),
            question_text=str(q14.get("question") or ""),
        )
    )
    exam.append(
        _advanced_question(
            15,
            combo="Advanced",
            step="News/Issue",
            topic=str(q15.get("topic") or "News_Issue"),
            question_text=str(q15.get("question") or ""),
        )
    )

    if len(exam) != 15:
        raise RuntimeError(f"Mock V2 exam must have 15 questions, got {len(exam)}.")

    try:
        logger.info(
            "[MOCK_V2_EXAM_BUILT] bank=opic_question_bank_v2 questions_count=%s "
            "difficulty=%s topics=%s,%s,%s",
            len(exam),
            lev,
            t1,
            t2,
            t3,
        )
    except Exception:
        pass

    return exam
