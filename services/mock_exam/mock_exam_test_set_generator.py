import random
import re
from collections import defaultdict

from .exam_questions import exam_questions

HANGUL_RE = re.compile(r"[가-힣]")

TOPIC_TRANSLATIONS = {
    "영화 보기": "Movies",
    "클럽/나이트클럽 가기": "Nightlife",
    "공연 보기": "Live Performances",
    "콘서트 보기": "Concerts",
    "박물관 가기": "Museums",
    "공원 가기": "Parks",
    "캠핑 하기": "Camping",
    "해변 가기": "Beaches",
    "게임 하기": "Gaming",
    "SNS/블로그에 글 올리기": "Social Media and Blogging",
    "피규어 만들기": "Model Figure Making",
    "음악 감상하기": "Listening to Music",
    "악기 연주하기": "Playing Musical Instruments",
    "요리하기": "Cooking",
    "혼자 노래 부르기": "Singing Alone",
    "글쓰기": "Writing",
    "그림 그리기": "Drawing",
    "조깅": "Jogging",
    "걷기": "Walking",
    "자전거": "Cycling",
    "수영": "Swimming",
    "테니스": "Tennis",
    "축구": "Soccer",
    "농구": "Basketball",
    "야구": "Baseball",
    "골프": "Golf",
    "헬스(Gym)": "Gym Workouts",
    "요가": "Yoga",
    "운동을 전혀 하지 않음": "No Exercise",
    "국내 여행": "Domestic Travel",
    "해외 여행": "International Travel",
    "집에서 보내는 휴가(스테이케이션)": "Staycation",
}

SURVEY_TO_BANK_TOPICS = {
    "Movies": ["Movies"],
    "Live Performances": ["Shows", "Music"],
    "Concerts": ["Music", "Shows"],
    "Nightlife": ["Restaurant", "Coffee"],
    "Museums": ["Country", "Travel"],
    "Parks": ["Park"],
    "Camping": ["Travel", "Country", "Park"],
    "Beaches": ["Beach"],
    "Gaming": ["Internet", "Phones"],
    "Social Media and Blogging": ["Internet"],
    "Model Figure Making": ["Shopping"],
    "Listening to Music": ["Music"],
    "Playing Musical Instruments": ["Instrument"],
    "Cooking": ["Cooking", "Food"],
    "Singing Alone": ["Music"],
    "Writing": ["Books"],
    "Drawing": ["Books", "Shopping"],
    "Walking": ["Walking"],
    "Cycling": ["Country", "Walking"],
    "Swimming": ["Exercise", "Beach"],
    "Tennis": ["Sports", "Exercise"],
    "Soccer": ["Sports", "Country"],
    "Basketball": ["Sports"],
    "Baseball": ["Sports"],
    "Golf": ["Sports", "Travel"],
    "Gym Workouts": ["Exercise"],
    "Yoga": ["Exercise", "Health"],
    "No Exercise": ["Health", "Walking", "Country"],
    "Domestic Travel": ["Travel", "Country"],
    "International Travel": ["Travel"],
    "Staycation": ["Travel", "Home"],
    "Jogging": ["Exercise", "Walking"],
}

# IH (difficulty 5): 비교·사회 이슈 고득점용 독립 문항 (bank에 없는 타입은 여기서만 출제)
COMPARISON_POOL_IH = [
    {
        "topic": "Comparison",
        "question": (
            "I'd like to hear how homes from your childhood compare with homes people live in today—"
            "what's the biggest shift you've noticed?"
        ),
    },
    {
        "topic": "Comparison",
        "question": (
            "Walk me through how living alone stacks up against living with family for you—"
            "convenience, stress, and lifestyle—what fits you better?"
        ),
    },
    {
        "topic": "Comparison",
        "question": (
            "Compare apartments and standalone houses from your experience—which wins on convenience "
            "and daily rhythm, and why?"
        ),
    },
    {
        "topic": "Comparison",
        "question": (
            "Tell me how city life and suburban life feel different from where you've actually lived—"
            "pace, noise, anything that stuck with you?"
        ),
    },
]

NEWS_ISSUE_POOL_IH = [
    {
        "topic": "News_Issue",
        "question": (
            "What's been in the conversation lately around housing where you're from—rent jumps, "
            "supply, younger buyers—and how do people around you react?"
        ),
    },
    {
        "topic": "News_Issue",
        "question": (
            "Pick something tech-related that's been trending—short video, AI tools, whatever—and "
            "tell me why it's blowing up and whether that worries or excites you."
        ),
    },
    {
        "topic": "News_Issue",
        "question": (
            "Talk about a workplace or career shift you've seen in the news or among friends—"
            "remote work, layoffs, side gigs—and what that says about where things are headed."
        ),
    },
    {
        "topic": "News_Issue",
        "question": (
            "Environmental headlines pop up every season—anything local you've noticed "
            "(floods, heat, recycling drives) and how everyday people respond?"
        ),
    },
]

COMPARISON_POOL_AL = [
    {
        "topic": "Comparison",
        "question": (
            "Compare renting long-term with buying a home—stability, monthly cash flow, "
            "and personal freedom—which trade-offs matter most to people you know?"
        ),
    },
    {
        "topic": "Comparison",
        "question": (
            "Urban redevelopment versus preserving older neighborhoods—if you had to choose a priority "
            "for your city, what would you defend and why?"
        ),
    },
    {
        "topic": "Comparison",
        "question": (
            "Contrast online-only learning with in-person classes beyond convenience—social capital, "
            "motivation, long-term outcomes."
        ),
    },
]

NEWS_ISSUE_POOL_AL = [
    {
        "topic": "News_Issue",
        "question": (
            "Discuss the social ripple effects of rising housing prices—who gets squeezed hardest and "
            "what patterns you see among peers?"
        ),
    },
    {
        "topic": "News_Issue",
        "question": (
            "Remote and hybrid work reshaped where people live—talk about that shift as a news-level "
            "story: winners, losers, unexpected side effects."
        ),
    },
    {
        "topic": "News_Issue",
        "question": (
            "Should governments actively cool housing markets or let them run—give two reasons for "
            "intervention and one honest counterargument you'd respect."
        ),
    },
    {
        "topic": "News_Issue",
        "question": (
            "Pick a sustainability or climate policy you've seen debated recently—what's the headline "
            "takeaway and what would you push policymakers to fix first?"
        ),
    },
]

_FALLBACK_TOPICS = ["Country", "Home", "Travel", "Movies", "Music", "Exercise", "Park"]


def _build_bank_index():
    idx = defaultdict(lambda: defaultdict(list))
    for row in exam_questions:
        idx[row["topic"]][row["type"]].append(row)
    return idx


_BANK_INDEX = _build_bank_index()


def _rows(topic, typ):
    return list(_BANK_INDEX.get(topic, {}).get(typ, []))


def _all_bank_topics():
    return list(_BANK_INDEX.keys())


def _contains_hangul(text):
    return bool(HANGUL_RE.search(text or ""))


def _to_english_topic(topic):
    if not topic:
        return "Daily Life"
    if topic in TOPIC_TRANSLATIONS:
        return TOPIC_TRANSLATIONS[topic]
    if _contains_hangul(topic):
        return "General Topic"
    return topic


def _survey_bank_topics(survey_results):
    topics = []
    if survey_results:
        for key in ("leisure", "interests", "sports", "travel", "hobbies"):
            vals = survey_results.get(key, [])
            if not isinstance(vals, list):
                continue
            for v in vals:
                eng = _to_english_topic(v)
                topics.extend(SURVEY_TO_BANK_TOPICS.get(eng, [eng]))
    return list(dict.fromkeys(topics))


def _initiation_suggests_change(row):
    q = (row.get("question") or "").lower()
    keys = (
        "different",
        "change",
        "compared",
        "than before",
        "used to",
        "grown",
        "these days",
        "no longer",
        "before and after",
        "shift",
        "transition",
        "how has",
        "how have",
    )
    return any(k in q for k in keys)


def _topics_combo1_eligible():
    out = []
    for t in _all_bank_topics():
        if str(t).startswith("Bundle"):
            continue
        if _rows(t, "Description") and _rows(t, "Routine") and _rows(t, "Initiation"):
            out.append(t)
    return out


def _topics_flexible_eligible():
    out = []
    for t in _all_bank_topics():
        if str(t).startswith("Bundle"):
            continue
        if not _rows(t, "Description"):
            continue
        if not (_rows(t, "Routine") or _rows(t, "Initiation")):
            continue
        mem = _rows(t, "Memorable")
        chg = [r for r in _rows(t, "Initiation") if _initiation_suggests_change(r)]
        if mem or chg:
            out.append(t)
    return out


def _roleplay_bundle_ready():
    buckets = defaultdict(lambda: defaultdict(list))
    for row in exam_questions:
        topic = row["topic"]
        if not str(topic).startswith("Bundle"):
            continue
        typ = row.get("type")
        if typ in ("Roleplay_Request", "Roleplay_Problem", "Related_Experience"):
            buckets[topic][typ].append(row)
    ready_topics = []
    for topic, b in buckets.items():
        if b.get("Roleplay_Request") and b.get("Roleplay_Problem") and b.get("Related_Experience"):
            ready_topics.append(topic)
    return ready_topics, buckets


def _pick_topic_from_pool(pool, preferred, excluded):
    usable = [t for t in pool if t not in excluded]
    if not usable:
        return None
    pref_hit = [t for t in usable if t in preferred]
    pick_from = pref_hit if pref_hit else usable
    return random.choice(pick_from)


def _resolve_topic(pool, preferred, excluded, label):
    """Pick a topic that satisfies pool constraints; fall back to rotation."""
    t = _pick_topic_from_pool(pool, preferred, excluded)
    if t:
        return t
    for fb in _FALLBACK_TOPICS:
        if fb in excluded:
            continue
        if fb in pool:
            return fb
    remaining = [x for x in pool if x not in excluded]
    if remaining:
        return random.choice(remaining)
    if pool:
        return random.choice(pool)
    raise RuntimeError(f"No topics available for {label}")


def _pick_middle_pair(topic):
    choices = []
    for r in _rows(topic, "Routine"):
        choices.append(("Routine", r))
    for r in _rows(topic, "Initiation"):
        choices.append(("Initiation", r))
    return random.choice(choices) if choices else (None, None)


def _pick_last_flexible(topic):
    mem = _rows(topic, "Memorable")
    if mem:
        return "Memorable", random.choice(mem)
    chg = [r for r in _rows(topic, "Initiation") if _initiation_suggests_change(r)]
    if chg:
        return "Comparison_Change", random.choice(chg)
    ini = _rows(topic, "Initiation")
    if ini:
        return "Initiation", random.choice(ini)
    return None, None


def _exam_item(eid, combo, step, topic, seat_type, question, bank_id=None):
    return {
        "id": eid,
        "combo": combo,
        "step": step,
        "topic": topic,
        "type": seat_type,
        "question": question,
        "bank_row_id": bank_id,
    }


def _ava_question(step, topic):
    if step == "Description":
        return f"I'd like to know about your {topic}. Describe it in detail."
    if step == "Routine":
        return f"Tell me about your usual routine related to {topic}. What do you normally do?"
    return f"Tell me about a memorable experience you had with {topic}. What happened?"


def _sanitize_exam_questions(test_set):
    sanitized = []
    for item in test_set:
        q = item.get("question", "")
        topic = item.get("topic", "Daily Life")
        if topic not in ("Self-Introduction", "Comparison", "News_Issue"):
            topic = _to_english_topic(topic)
        if _contains_hangul(q):
            step = item.get("step", "Description")
            q = _ava_question(step, topic)
        cloned = dict(item)
        cloned["topic"] = topic
        cloned["question"] = q
        sanitized.append(cloned)
    return sanitized


def generate_test_set(survey_results=None, difficulty=5):
    """
    OPIc IH/AL-style 15-question combo matrix:
      Q1 Intro (Self-Introduction)
      Q2–4 Combo1: Description → Routine → Experience (Initiation bank)
      Q5–7 Combo2: Description → Routine|Initiation → Memorable|Comparison_Change
      Q8–10 Combo3: same flexible pattern, single topic each
      Q11–13 Roleplay: Request → Problem → Related Experience (same Bundle topic)
      Q14 Comparison (standalone pool)
      Q15 News/Issue (standalone pool)
    """
    preferred = _survey_bank_topics(survey_results or {})
    combo1_pool = _topics_combo1_eligible()
    flex_pool = _topics_flexible_eligible()
    roleplay_ready, role_buckets = _roleplay_bundle_ready()

    if not combo1_pool:
        raise RuntimeError("Question bank cannot satisfy Combo1 (Description+Routine+Initiation).")
    if not flex_pool:
        raise RuntimeError("Question bank cannot satisfy Combo2/3 flexible rows.")
    if not roleplay_ready:
        raise RuntimeError("Question bank has no complete Roleplay Bundle (Request+Problem+Related).")

    excluded = set()
    t1 = _resolve_topic(combo1_pool, preferred, excluded, "Combo1")
    excluded.add(t1)

    t2 = _resolve_topic(flex_pool, preferred, excluded, "Combo2")
    excluded.add(t2)

    t3 = _resolve_topic(flex_pool, preferred, excluded, "Combo3")
    excluded.add(t3)

    bundle_topic = random.choice(roleplay_ready)
    bb = role_buckets[bundle_topic]

    lev = int(difficulty) if difficulty is not None else 5
    comp_pool = COMPARISON_POOL_AL if lev >= 6 else COMPARISON_POOL_IH
    news_pool = NEWS_ISSUE_POOL_AL if lev >= 6 else NEWS_ISSUE_POOL_IH

    q14 = random.choice(comp_pool)
    q15_candidates = [x for x in news_pool if x["question"] != q14.get("question")]
    q15 = random.choice(q15_candidates or news_pool)

    test_set = []

    test_set.append(
        _exam_item(
            1,
            "Intro",
            "Self-Introduction",
            "Self-Introduction",
            "Intro",
            "Hi, I'm Ava. Let's begin. Tell me about yourself in as much detail as possible.",
            bank_id=None,
        )
    )

    # Combo 1 — strict Description / Routine / Initiation (display third as Experience)
    d1 = random.choice(_rows(t1, "Description"))
    r1 = random.choice(_rows(t1, "Routine"))
    i1 = random.choice(_rows(t1, "Initiation"))
    test_set.append(_exam_item(2, "Combo1", "Description", t1, "Combo1", d1["question"], d1.get("id")))
    test_set.append(_exam_item(3, "Combo1", "Routine", t1, "Combo1", r1["question"], r1.get("id")))
    test_set.append(_exam_item(4, "Combo1", "Experience", t1, "Combo1", i1["question"], i1.get("id")))

    # Combo 2
    d2 = random.choice(_rows(t2, "Description"))
    mid_typ, mid_row = _pick_middle_pair(t2)
    if mid_row is None:
        raise RuntimeError(f"Combo2 middle slot empty for topic {t2}")
    last_typ, last_row = _pick_last_flexible(t2)
    if last_row is None:
        raise RuntimeError(f"Combo2 last slot empty for topic {t2}")
    step_mid = "Routine" if mid_typ == "Routine" else "Experience"
    step_last = (
        "Memorable"
        if last_typ == "Memorable"
        else ("Comparison_Change" if last_typ == "Comparison_Change" else "Experience")
    )
    test_set.append(_exam_item(5, "Combo2", "Description", t2, "Combo2", d2["question"], d2.get("id")))
    test_set.append(_exam_item(6, "Combo2", step_mid, t2, "Combo2", mid_row["question"], mid_row.get("id")))
    test_set.append(_exam_item(7, "Combo2", step_last, t2, "Combo2", last_row["question"], last_row.get("id")))

    # Combo 3
    d3 = random.choice(_rows(t3, "Description"))
    mid3_typ, mid3_row = _pick_middle_pair(t3)
    if mid3_row is None:
        raise RuntimeError(f"Combo3 middle slot empty for topic {t3}")
    last3_typ, last3_row = _pick_last_flexible(t3)
    if last3_row is None:
        raise RuntimeError(f"Combo3 last slot empty for topic {t3}")
    step_mid3 = "Routine" if mid3_typ == "Routine" else "Experience"
    step_last3 = (
        "Memorable"
        if last3_typ == "Memorable"
        else ("Comparison_Change" if last3_typ == "Comparison_Change" else "Experience")
    )
    test_set.append(_exam_item(8, "Combo3", "Description", t3, "Combo3", d3["question"], d3.get("id")))
    test_set.append(_exam_item(9, "Combo3", step_mid3, t3, "Combo3", mid3_row["question"], mid3_row.get("id")))
    test_set.append(_exam_item(10, "Combo3", step_last3, t3, "Combo3", last3_row["question"], last3_row.get("id")))

    rq = random.choice(bb["Roleplay_Request"])
    rp = random.choice(bb["Roleplay_Problem"])
    rexp = random.choice(bb["Related_Experience"])
    test_set.append(
        _exam_item(
            11,
            "Roleplay",
            "Request Information",
            bundle_topic,
            "Roleplay",
            rq["question"],
            rq.get("id"),
        )
    )
    test_set.append(
        _exam_item(
            12,
            "Roleplay",
            "Problem/Solution",
            bundle_topic,
            "Roleplay",
            rp["question"],
            rp.get("id"),
        )
    )
    test_set.append(
        _exam_item(
            13,
            "Roleplay",
            "Related Experience",
            bundle_topic,
            "Roleplay",
            rexp["question"],
            rexp.get("id"),
        )
    )

    test_set.append(
        _exam_item(
            14,
            "Advanced",
            "Comparison",
            q14["topic"],
            "Comparison",
            q14["question"],
            bank_id=None,
        )
    )
    test_set.append(
        _exam_item(
            15,
            "Advanced",
            "News/Issue",
            q15["topic"],
            "News_Issue",
            q15["question"],
            bank_id=None,
        )
    )

    assert len(test_set) == 15
    return _sanitize_exam_questions(test_set)
