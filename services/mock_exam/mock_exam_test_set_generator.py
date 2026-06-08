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
    "Live Performances": ["Shows"],
    "Concerts": ["Shows"],
    "Nightlife": ["Nightlife"],
    "Museums": ["Museums"],
    "Parks": ["Park"],
    "Camping": ["Camping"],
    "Beaches": ["Beach"],
    "Gaming": ["Gaming"],
    "Social Media and Blogging": ["Internet"],
    "Model Figure Making": ["Figure Collecting"],
    "Listening to Music": ["Music"],
    "Playing Musical Instruments": ["Instrument"],
    "Cooking": ["Cooking", "Food"],
    "Singing Alone": ["Singing"],
    "Writing": ["Writing"],
    "Drawing": ["Drawing"],
    "Walking": ["Walking"],
    "Cycling": ["Cycling"],
    "Swimming": ["Swimming"],
    "Tennis": ["Sports"],
    "Soccer": ["Sports"],
    "Basketball": ["Sports"],
    "Baseball": ["Sports"],
    "Golf": ["Sports"],
    "Gym Workouts": ["Exercise"],
    "Yoga": ["Yoga"],
    "No Exercise": ["Health"],
    "Domestic Travel": ["Travel", "Country"],
    "International Travel": ["Travel"],
    "Staycation": ["Vacation"],
    "Jogging": ["Jogging"],
}

# IH/AL (levels 5–6): Q14 Comparison + Q15 News/Issue — 20 topic sets, picked as a pair
ADVANCED_SET_POOL = [
    {
        "set_id": "phone",
        "comparison": {
            "question": (
                "Think back to how cell phones were used about five years ago. Which features and apps "
                "did people rely on then? In your view, what has shifted the most in the way people "
                "use their phones today?"
            ),
        },
        "news_issue": {
            "question": (
                "Many adults feel that younger people are on their phones too much and may be missing "
                "out on real, in-person conversation. In your country, how do people generally feel "
                "about young people's phone habits?"
            ),
        },
    },
    {
        "set_id": "internet",
        "comparison": {
            "question": (
                "People of different ages tend to use the internet in their own ways. What do younger "
                "users mostly go online for, and how does that differ from what older users do?"
            ),
        },
        "news_issue": {
            "question": (
                "When it comes to the internet, people raise a number of worries — privacy and security "
                "among them. What kinds of concerns come up most, and why do they matter to people?"
            ),
        },
    },
    {
        "set_id": "home",
        "comparison": {
            "question": (
                "When something goes wrong at home, how do you usually handle it? How does your parents' "
                "way of handling it compare to yours? Where do the differences show up?"
            ),
        },
        "news_issue": {
            "question": (
                "Renting a place to live comes with its own set of headaches. What kinds of problems do "
                "renters often run into, and what do they usually do to fix them?"
            ),
        },
    },
    {
        "set_id": "gatherings",
        "comparison": {
            "question": (
                "Get-togethers and celebrations can look quite different depending on where you are. "
                "How do they compare between smaller towns and larger cities in your country?"
            ),
        },
        "news_issue": {
            "question": (
                "Putting together a gathering isn't always easy. What sorts of difficulties come up when "
                "people try to organize one, and how do they usually work around them?"
            ),
        },
    },
    {
        "set_id": "holidays",
        "comparison": {
            "question": (
                "Walk me through some of the holidays celebrated in your country. What do people "
                "typically do, and how do you yourself mark these days?"
            ),
        },
        "news_issue": {
            "question": (
                "Holidays aren't always smooth — people have their share of worries about them. What "
                "bothers people about holidays, and how do they handle it?"
            ),
        },
    },
    {
        "set_id": "industry",
        "comparison": {
            "question": (
                "Pick an industry you keep an eye on — maybe food, tech, mobile, or something else. "
                "What was it like roughly three years ago, and in what ways has it shifted since?"
            ),
        },
        "news_issue": {
            "question": (
                "Can you think of a product that let the public down? Maybe a gaming console that fell "
                "flat, or a phone or app that launched with serious flaws. Walk me through what went wrong."
            ),
        },
    },
    {
        "set_id": "transportation",
        "comparison": {
            "question": (
                "Think about how getting around in your country has changed over time. How did people "
                "travel in earlier days, and how does that compare with how they get around now?"
            ),
        },
        "news_issue": {
            "question": (
                "Public transport isn't without its troubles. What kinds of problems do riders deal "
                "with, and how do they usually cope with them?"
            ),
        },
    },
    {
        "set_id": "technology",
        "comparison": {
            "question": (
                "Take a device you use now and compare it with an older model of the same thing. What "
                "was the earlier one like, and how has it gotten better?"
            ),
        },
        "news_issue": {
            "question": (
                "There's a sense among some people that we lean on technology a little too heavily. What "
                "worries do people in your country voice about this, and where do those worries come from?"
            ),
        },
    },
    {
        "set_id": "environment",
        "comparison": {
            "question": (
                "How did the environment around where you live look in the past, compared with today? "
                "What's gotten better, and what's gotten worse?"
            ),
        },
        "news_issue": {
            "question": (
                "There are several environmental matters people in your country pay attention to. Which "
                "ones come up, and why do people see them as important?"
            ),
        },
    },
    {
        "set_id": "health",
        "comparison": {
            "question": (
                "The way people look after their health now isn't quite the same as before. Where do you "
                "see the biggest differences between then and now?"
            ),
        },
        "news_issue": {
            "question": (
                "These days people have a few worries when it comes to staying healthy. What's behind "
                "those worries, and what do people do to keep themselves well?"
            ),
        },
    },
    {
        "set_id": "weather",
        "comparison": {
            "question": (
                "Weather can shift quite a bit from season to season in your country. Take two seasons "
                "and compare them — how do people's daily activities change?"
            ),
        },
        "news_issue": {
            "question": (
                "Rough weather can cause real trouble. What kinds of problems does extreme weather bring "
                "in your country, and how do people get ready for it or deal with it?"
            ),
        },
    },
    {
        "set_id": "shopping",
        "comparison": {
            "question": (
                "The way people shop has moved on over the years. How does shopping back then compare "
                "with shopping now, online buying included?"
            ),
        },
        "news_issue": {
            "question": (
                "Buying things online doesn't always go smoothly. What problems do shoppers run into on "
                "the web, and how do they sort them out?"
            ),
        },
    },
    {
        "set_id": "restaurants",
        "comparison": {
            "question": (
                "Restaurants today aren't quite what they used to be. Compare them with restaurants "
                "from the past — think food, service, or the overall feel."
            ),
        },
        "news_issue": {
            "question": (
                "Eating out comes with a few worries for people, whether it's the bill or how safe the "
                "food is. Why do these things matter to people?"
            ),
        },
    },
    {
        "set_id": "travel",
        "comparison": {
            "question": (
                "The way people take trips has changed over the years. How does traveling in the past "
                "compare with the way people travel today?"
            ),
        },
        "news_issue": {
            "question": (
                "Trips don't always go as planned. What sorts of problems do travelers run into, and "
                "how do they handle them when they come up?"
            ),
        },
    },
    {
        "set_id": "fashion",
        "comparison": {
            "question": (
                "Fashion in your country has moved quite a bit over the years. Compare what people used "
                "to wear with what they put on these days."
            ),
        },
        "news_issue": {
            "question": (
                "A few concerns come up around fashion — fast fashion or cost, for instance. Why do these "
                "things worry people?"
            ),
        },
    },
    {
        "set_id": "education",
        "comparison": {
            "question": (
                "Learning today doesn't look much like it did years ago. Compare how students used to "
                "study with the way they go about it now."
            ),
        },
        "news_issue": {
            "question": (
                "People hold a number of worries about how education works in your country. What are they, "
                "and why do they matter so much?"
            ),
        },
    },
    {
        "set_id": "jobs",
        "comparison": {
            "question": (
                "The way people do their jobs has shifted in recent years. Compare working in the past "
                "with working now — remote work included."
            ),
        },
        "news_issue": {
            "question": (
                "Work brings its share of struggles these days. What's causing them, and how do people "
                "get through them?"
            ),
        },
    },
    {
        "set_id": "neighborhood",
        "comparison": {
            "question": (
                "How does your neighborhood today compare with how it was a few years back? What's "
                "different about it now?"
            ),
        },
        "news_issue": {
            "question": (
                "Neighborhoods come with their own problems for the people living there. Why do these "
                "come about, and how do people work them out?"
            ),
        },
    },
    {
        "set_id": "banks",
        "comparison": {
            "question": (
                "Banking has come a long way over the years. Compare how people dealt with banks in the "
                "past with how they handle it now, mobile banking included."
            ),
        },
        "news_issue": {
            "question": (
                "People have a few worries when it comes to online banking or managing their money. Why "
                "do these concerns matter to them?"
            ),
        },
    },
    {
        "set_id": "social_media",
        "comparison": {
            "question": (
                "The way people use social media has shifted over the years. Compare how it was used "
                "earlier with how people use it today."
            ),
        },
        "news_issue": {
            "question": (
                "Social media brings up a number of worries for people. What are they anxious about, and "
                "how does it shape their daily lives?"
            ),
        },
    },
]


def pick_advanced_set() -> dict:
    """Pick one Q14+Q15 topic set (Comparison + News/Issue pair) for IH/AL exams."""
    return random.choice(ADVANCED_SET_POOL)

# Ask-the-interviewer (OPIc Q5): bank 밖 독립 풀 — 레벨 3·4 출제 연결은 별도 단계
Q5_POOL = [
    {
        "topic_id": "home",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I currently reside in a house with my family. To gather more details about our home, "
            "ask me three to four questions."
        ),
        "question_text": (
            "I currently reside in a house with my family. To gather more details about our home, "
            "ask me three to four questions."
        ),
    },
    {
        "topic_id": "movies_tv",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I also enjoy watching movies. Ask me three or four questions about the type of movies "
            "I like to watch."
        ),
        "question_text": (
            "I also enjoy watching movies. Ask me three or four questions about the type of movies "
            "I like to watch."
        ),
    },
    {
        "topic_id": "movies_tv",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I'm a fan of a reality show on TV. Ask me three or four questions about the show, and "
            "based on my answers, decide if it's something you'd be interested in watching too."
        ),
        "question_text": (
            "I'm a fan of a reality show on TV. Ask me three or four questions about the show, and "
            "based on my answers, decide if it's something you'd be interested in watching too."
        ),
    },
    {
        "topic_id": "park",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I also enjoy visiting parks. Ask me three or four questions to learn more about the park "
            "I go to."
        ),
        "question_text": (
            "I also enjoy visiting parks. Ask me three or four questions to learn more about the park "
            "I go to."
        ),
    },
    {
        "topic_id": "cafe",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I like visiting coffee shops. Ask me three or four questions about my favorite coffee shop."
        ),
        "question_text": (
            "I like visiting coffee shops. Ask me three or four questions about my favorite coffee shop."
        ),
    },
    {
        "topic_id": "travel",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I love traveling to new places. Ask me three or four questions about my favorite trip, "
            "and decide if you'd want to go there too."
        ),
        "question_text": (
            "I love traveling to new places. Ask me three or four questions about my favorite trip, "
            "and decide if you'd want to go there too."
        ),
    },
    {
        "topic_id": "sports",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I enjoy playing sports in my free time. Ask me three or four questions about the sport "
            "I play."
        ),
        "question_text": (
            "I enjoy playing sports in my free time. Ask me three or four questions about the sport "
            "I play."
        ),
    },
    {
        "topic_id": "music",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I really enjoy listening to music. Ask me three or four questions about the kind of music "
            "I like."
        ),
        "question_text": (
            "I really enjoy listening to music. Ask me three or four questions about the kind of music "
            "I like."
        ),
    },
    {
        "topic_id": "shopping",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I like going shopping on weekends. Ask me three or four questions about where I usually shop "
            "and what I buy."
        ),
        "question_text": (
            "I like going shopping on weekends. Ask me three or four questions about where I usually shop "
            "and what I buy."
        ),
    },
    {
        "topic_id": "food",
        "topic": "Q5",
        "opic_type": "Q5",
        "question": (
            "I love trying new food. Ask me three or four questions about my favorite food or restaurant."
        ),
        "question_text": (
            "I love trying new food. Ask me three or four questions about my favorite food or restaurant."
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

    adv_set = pick_advanced_set()
    q14 = adv_set["comparison"]
    q15 = adv_set["news_issue"]
    adv_topic = adv_set["set_id"]

    test_set.append(
        _exam_item(
            14,
            "Advanced",
            "Comparison",
            adv_topic,
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
            adv_topic,
            "News_Issue",
            q15["question"],
            bank_id=None,
        )
    )

    assert len(test_set) == 15
    return _sanitize_exam_questions(test_set)
