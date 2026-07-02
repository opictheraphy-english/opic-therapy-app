#!/usr/bin/env python3
"""One-off diagnostic: mock_v2 final report — model quality / latency / cost comparison.

Does NOT modify app/service code. Console output only.

Compares mock exam report generation across:
  (a) gpt-5-nano          — current production OpenAI primary
  (b) gpt-5.4-mini        — candidate upgrade (reasoning_effort low/medium when supported)
  (c) gemini-2.5-flash    — historical baseline (detailed Korean feedback)

Run (local):
  OPENAI_API_KEY=sk-... GEMINI_API_KEY=... python3 tools/check_openai_mock_v2_report.py

Options:
  python3 tools/check_openai_mock_v2_report.py --sample ih
  python3 tools/check_openai_mock_v2_report.py --sample al
  python3 tools/check_openai_mock_v2_report.py --sample both
  python3 tools/check_openai_mock_v2_report.py --sample real_ih
  python3 tools/check_openai_mock_v2_report.py --sample im_low
  python3 tools/check_openai_mock_v2_report.py --sample calibration
  python3 tools/check_openai_mock_v2_report.py --sample al --skip-gemini

Requires: repo root on PYTHONPATH (script adds it). Keys read ONLY from env vars
via utils.secrets (OPENAI_API_KEY / GEMINI_API_KEY).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Sequence, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.mock_v2_analysis import (
    GEMINI_REQUEST_TIMEOUT_MS,
    MOCK_V2_REPORT_MAX_OUTPUT_TOKENS,
    _parse_report_response,
    build_mock_v2_report_payload,
)
from services.gemini_json_client import (
    OPENAI_FALLBACK_MODEL,
    _is_truncated_finish_reason,
    _openai_chat_completions_create,
    _openai_extract_choice_text,
    _openai_model_restricts_sampling,
    invoke_gemini_report_text_json,
)
from services.mock_v2_rubric import build_mock_v2_rubric_prompt
from utils.secrets import get_gemini_api_key, get_openai_api_key

_EXPECTED_Q_FEEDBACK = 15
_OPENAI_JSON_SYSTEM = (
    "You must respond with a single valid JSON object only. "
    "반드시 JSON만 반환하세요. No markdown fences, no prose."
)
_GEMINI_BASELINE_MODEL = "gemini-2.5-flash"
_GPT54_MINI_CANDIDATES = ("gpt-5.4-mini", "gpt-5.4-mini-2026-03-17")
_SCORE_KEYS = (
    "response_amount",
    "relevance",
    "structure",
    "grammar",
    "vocabulary",
    "naturalness",
)

# Rough USD / 1M tokens (diagnostic estimate only — verify against OpenAI pricing page).
_COST_PER_1M = {
    "gpt-5-nano": {"input": 0.10, "output": 0.40},
    "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60},
}


def _t(*parts: str) -> str:
    return " ".join(parts)


def _question_bank() -> List[Dict[str, Any]]:
    return [
        {"question_index": 0, "question_number": 1, "opic_type": "Intro", "combo": "Intro", "step": "Self-Introduction", "topic": "intro", "question_text": "Hi, I'm Ava. Tell me about yourself in as much detail as possible."},
        {"question_index": 1, "question_number": 2, "opic_type": "Q1", "combo": "Combo1", "step": "Description", "topic": "movies_tv", "question_text": "What TV shows or movies do you enjoy watching the most? Why do you like them?"},
        {"question_index": 2, "question_number": 3, "opic_type": "Q2", "combo": "Combo1", "step": "Routine", "topic": "movies_tv", "question_text": "How often do you watch movies or TV shows, and who do you usually watch with?"},
        {"question_index": 3, "question_number": 4, "opic_type": "Q3", "combo": "Combo1", "step": "Experience", "topic": "movies_tv", "question_text": "Tell me about the last movie you watched. What did you do before and after?"},
        {"question_index": 4, "question_number": 5, "opic_type": "Q1", "combo": "Combo2", "step": "Description", "topic": "park", "question_text": "Is there a park you really like going to? What's special about it?"},
        {"question_index": 5, "question_number": 6, "opic_type": "Q2", "combo": "Combo2", "step": "Routine", "topic": "park", "question_text": "What do you usually do when you visit that park?"},
        {"question_index": 6, "question_number": 7, "opic_type": "Q3", "combo": "Combo2", "step": "Experience", "topic": "park", "question_text": "Tell me about the last time you went to a park. Who went with you and what happened?"},
        {"question_index": 7, "question_number": 8, "opic_type": "Q1", "combo": "Combo3", "step": "Description", "topic": "music", "question_text": "What kind of music do you listen to these days? Why do you like it?"},
        {"question_index": 8, "question_number": 9, "opic_type": "Q2", "combo": "Combo3", "step": "Routine", "topic": "music", "question_text": "When and where do you usually listen to music?"},
        {"question_index": 9, "question_number": 10, "opic_type": "Q3", "combo": "Combo3", "step": "Experience", "topic": "music", "question_text": "Tell me about a memorable concert or live performance you attended."},
        {"question_index": 10, "question_number": 11, "opic_type": "Roleplay", "combo": "Roleplay", "step": "Roleplay", "topic": "hotel", "question_text": "You are at a hotel front desk. The clerk asks what kind of room you need. Respond and ask two questions."},
        {"question_index": 11, "question_number": 12, "opic_type": "Roleplay", "combo": "Roleplay", "step": "Roleplay", "topic": "restaurant", "question_text": "You received the wrong dish at a restaurant. Explain the problem politely and ask for a solution."},
        {"question_index": 12, "question_number": 13, "opic_type": "Roleplay", "combo": "Roleplay", "step": "Roleplay", "topic": "travel", "question_text": "Your friend is planning a trip. Give advice and ask about their budget and dates."},
        {"question_index": 13, "question_number": 14, "opic_type": "Comparison", "combo": "Advanced", "step": "Comparison", "topic": "neighborhood", "question_text": "Tell me about your neighborhood when you were younger and how it is different now."},
        {"question_index": 14, "question_number": 15, "opic_type": "News/Issue", "combo": "Advanced", "step": "News/Issue", "topic": "city_problems", "question_text": "What problems has your city or town faced recently? What caused them and how do they affect people?"},
    ]


def _ih_answers(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Original IH-level synthetic 15Q sample (~110 wpm, solid IM3–IH)."""
    texts = [
        _t(
            "My name is Minho and I work as a marketing coordinator at a small tech company in Seoul.",
            "I graduated from university about four years ago and I live with my wife in a quiet neighborhood.",
            "In my free time I enjoy hiking on weekends and trying new coffee shops around the city.",
            "I also like reading business books because they help me think about my career goals more clearly.",
            "Overall I would describe myself as curious, organized, and pretty outgoing when I meet new people.",
        ),
        _t(
            "These days I mostly watch Korean dramas and a few American series on streaming platforms.",
            "I especially enjoy character-driven stories because I like seeing how people change over time.",
            "My favorite show lately is a workplace drama that mixes humor with realistic office problems.",
            "I also rewatch classic films on weekends when I want something more thoughtful and slower paced.",
        ),
        _t(
            "I usually watch TV about three or four nights a week after dinner when I need to unwind.",
            "On weekdays I watch alone for thirty or forty minutes, but on Friday I often watch with my wife.",
            "We pick something light so we can talk about the plot while we eat snacks on the sofa.",
            "If we finish early we sometimes start another episode, but we try not to stay up too late.",
        ),
        _t(
            "The last movie I watched was a science-fiction film at a local cinema with two close friends.",
            "Before the movie we met at a noodle restaurant nearby and talked about our busy week at work.",
            "During the film I was impressed by the visual effects and the way the story handled time travel.",
            "Afterward we walked to a café and debated the ending for almost an hour because it was ambiguous.",
            "It was a fun night and reminded me why I prefer watching big movies on a large screen.",
        ),
        _t(
            "My favorite park is a riverside park about twenty minutes from my apartment by subway.",
            "It has wide walking paths, cherry trees, and a small pond where ducks gather in the spring.",
            "What makes it special is the view of the city skyline at sunset, which looks really peaceful.",
            "There are also outdoor fitness machines that older residents use every morning.",
        ),
        _t(
            "When I visit the park I usually walk briskly for thirty minutes to get light exercise.",
            "Sometimes I bring a book and read on a bench near the water if the weather is comfortable.",
            "On weekends I might jog slowly while listening to a podcast about current events.",
            "I also enjoy people-watching because families and cyclists create a lively atmosphere.",
        ),
        _t(
            "Last month I went to the park with my wife and her parents during a mild autumn afternoon.",
            "We packed sandwiches and thermoses of tea, then spread a blanket under a gingko tree.",
            "My father-in-law told stories about his childhood while we watched children fly kites nearby.",
            "Later we walked along the river and took photos because the yellow leaves looked beautiful.",
            "We stayed until the sun went down and then took a taxi home because we were tired but happy.",
        ),
        _t(
            "Recently I listen to a mix of indie pop and soft rock, especially when I am commuting.",
            "I like those genres because the melodies are catchy but the lyrics still feel meaningful.",
            "Some Korean indie bands have interesting arrangements that combine acoustic guitar with synth sounds.",
            "When I need focus at work I switch to instrumental playlists without vocals.",
        ),
        _t(
            "I mostly listen to music on the subway in the morning and while doing chores at home.",
            "I use noise-canceling earphones so I can hear details even in crowded trains.",
            "At home I play music on a small speaker in the kitchen when I cook dinner after work.",
            "I avoid listening too loudly because I worry about damaging my hearing over time.",
        ),
        _t(
            "One memorable concert was an outdoor jazz festival I attended two summers ago with college friends.",
            "We arrived early to get good seats near the stage and bought cold drinks from a food truck.",
            "The headline band played energetic sets that had the whole crowd clapping along.",
            "After the show we talked about starting a band ourselves, though we never actually did.",
            "The night ended with fireworks, and I still remember how warm the air felt.",
        ),
        _t(
            "Hello, I have a reservation under the name Minho Park for two nights starting today.",
            "I would prefer a quiet room on a higher floor away from the elevator if possible.",
            "Could you tell me whether breakfast is included and what time the gym opens tomorrow?",
            "Also, is late checkout available on Sunday because my flight is in the evening?",
        ),
        _t(
            "Excuse me, I ordered the grilled salmon, but this looks like a chicken dish instead.",
            "I am not upset, but I cannot eat chicken because of an allergy, so I need a replacement.",
            "Could you ask the kitchen to prepare the salmon again and let me know how long it will take?",
            "If there is a delay, may I have a simple salad while I wait so I am not hungry?",
        ),
        _t(
            "Since you are planning your first solo trip, I suggest choosing a city with good public transit.",
            "Book accommodations near a subway line so you can save time and taxi fares.",
            "What dates are you considering, and do you have a rough budget for hotels and meals?",
            "If you share that information I can recommend neighborhoods that are safe and convenient.",
        ),
        _t(
            "Driving my own car is convenient because I can leave whenever I want and carry heavy bags easily.",
            "However, parking downtown is expensive and traffic jams make me stressed during rush hour.",
            "Public transportation is cheaper and better for the environment, and I can read on the train.",
            "On the other hand, trains are crowded in the morning and less flexible if I work late.",
            "Overall I use the subway on weekdays but drive when I visit my parents outside the city.",
        ),
        _t(
            "Air quality is the environmental issue that worries me most because smog has worsened in recent years.",
            "On bad days I check fine dust levels before exercising outdoors with my running club.",
            "I think the city should expand bus lanes and subsidize electric vehicles to reduce emissions.",
            "Individuals can also help by using reusable containers and conserving energy at home.",
            "If everyone makes small changes, the air could improve for children and older residents.",
        ),
    ]
    durations = [58, 52, 48, 62, 50, 46, 60, 47, 45, 58, 44, 46, 48, 55, 57]
    return _rows_from_texts(questions, texts, durations)


def _al_answers(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """AL challenge-style sample: long past/present Q14, city-problem Q15, stronger roleplay."""
    texts = [
        _t(
            "My name is Jiyeon and I am a product manager at a fintech startup in Seoul.",
            "I have worked there for six years after switching from consulting, and I lead a team of five engineers.",
            "I live in a newly developed district where the skyline changed dramatically since I moved in.",
            "Outside work I train for half marathons, cook Italian food on weekends, and mentor junior PMs online.",
            "I would describe myself as analytical but also empathetic when I listen to customer pain points.",
        ),
        _t(
            "I enjoy documentaries and limited series that explore social issues or historical events in depth.",
            "Recently I finished a series about urban planning because it connected to changes in my own neighborhood.",
            "I prefer subtitles over dubbing so I can catch nuanced expressions in English and Korean.",
            "When a show is too predictable I stop watching, but strong character arcs keep me engaged for weeks.",
        ),
        _t(
            "I watch something almost every night, usually for forty-five minutes after my daughter goes to bed.",
            "On weekdays my husband and I share one episode, but Sunday afternoons we sometimes binge two hours.",
            "We rotate who picks the show so neither of us gets stuck with only thrillers or only romance.",
        ),
        _t(
            "The last film I saw in a theater was an indie drama about immigration at a festival in Busan.",
            "Before the screening we met the director at a small reception and asked how she cast bilingual actors.",
            "The story followed a family split between two countries, which reminded me of my cousins abroad.",
            "Afterward we discussed the ending over ramen because the final scene was intentionally ambiguous.",
            "I left thinking about how language shapes identity, which is a theme I notice in my work too.",
        ),
        _t(
            "There is a waterfront park near my apartment that became my favorite place after the city renovated it.",
            "Ten years ago it was mostly empty grass, but now there are cafés, bike lanes, and night markets.",
            "I love the view of the river at sunset because the light reflects off the new glass buildings.",
            "Families gather on weekends, so the atmosphere feels energetic rather than lonely.",
        ),
        _t(
            "When I go there I usually walk three kilometers while listening to industry podcasts.",
            "Sometimes I bring my laptop and answer emails at an outdoor table if the weather is mild.",
            "In spring I take photos of cherry blossoms for my team chat because it boosts morale.",
        ),
        _t(
            "Last autumn I hosted a small picnic for coworkers who had just shipped a major release.",
            "We bought sandwiches and fruit, spread blankets under maple trees, and played casual trivia games.",
            "One engineer taught us a card game from his hometown, so the conversation stayed lively for hours.",
            "As it got dark we packed up slowly and walked back along the lit bike path together.",
            "It felt like a rare moment to connect outside sprint deadlines and Slack notifications.",
        ),
        _t(
            "These days I listen to jazz fusion and lo-fi beats while I write product specs.",
            "Jazz keeps my brain alert without distracting lyrics, especially during long roadmap sessions.",
            "I also save live recordings because improvisational solos remind me to stay flexible at work.",
        ),
        _t(
            "I listen during my commute on the subway and while cooking dinner at home.",
            "If I need deep focus I switch to noise-canceling mode and a instrumental playlist.",
            "On weekends I sometimes play music on a speaker while my daughter draws at the kitchen table.",
        ),
        _t(
            "A memorable concert was an outdoor jazz festival where it started raining but nobody left.",
            "The band moved under a partial cover and joked with the audience while the drummer kept tempo.",
            "We huddled under umbrellas singing along to a blues standard I still remember vividly.",
            "After the rain stopped the sunset made the stage lights look surreal, like a movie scene.",
            "I bought the album afterward and still associate those songs with that resilient crowd energy.",
        ),
        _t(
            "Hi, I have a booking under Jiyeon Kim for three nights starting tonight.",
            "I would like a high-floor room away from the elevator because I am a light sleeper.",
            "Could you confirm whether breakfast is included and what time the fitness center opens?",
            "Also, do you offer late checkout on Monday since my train is not until the evening?",
        ),
        _t(
            "Excuse me, I ordered the vegetarian pasta, but this plate contains shrimp.",
            "I am not angry, but I cannot eat shellfish, so I need a new dish prepared separately.",
            "Could you ask the kitchen how long a replacement will take and whether you can avoid cross-contamination?",
            "If it will take a while, may I have bread and salad first so my guests do not wait awkwardly?",
        ),
        _t(
            "Since you are planning your first international trip alone, I recommend starting with a walkable city.",
            "Book a hotel near a subway hub so you are not stuck in traffic after late meetings.",
            "What dates are you considering, and what is your approximate budget for lodging and food?",
            "If you share that, I can suggest neighborhoods that are safe and convenient for solo travelers.",
        ),
        _t(
            "Okay, so I do want to talk about my neighborhood when I was younger and right now.",
            "In the past, my neighborhood in San Diego La Jolla was a peaceful coastal town with many retirees and students from UCSD.",
            "People spent quiet afternoons near the beach, and there were fewer restaurants and almost no tech offices.",
            "Now it has become much busier because companies like Meta and Qualcomm expanded nearby.",
            "Employees moved from New York and San Francisco, so rent rose sharply and small shops were replaced by upscale cafés.",
            "For example, a studio that cost fifteen hundred dollars ten years ago now rents for twenty-five hundred.",
            "The city feels more vibrant, but longtime residents struggle because wages at older institutions did not keep up.",
            "Overall the area changed from a relaxed college town into a hustle-and-bustle tech hub with higher living costs.",
        ),
        _t(
            "Recently my city has faced rising living costs because many tech companies moved into the Washington DC area.",
            "Employees relocated from expensive cities, which pushed up housing prices and everyday expenses.",
            "For instance, a fast-food meal that used to cost five dollars now costs more than ten in my neighborhood.",
            "Public services are strained because infrastructure was built for a smaller population decades ago.",
            "I think the city should invest in affordable housing and expand metro lines before approving more office towers.",
            "Individuals can also support local businesses so money stays in the community instead of leaving with commuters.",
            "If policymakers ignore these trends, middle-income families will keep moving outward and the downtown core will hollow out.",
        ),
    ]
    durations = [72, 58, 50, 68, 62, 48, 78, 52, 46, 70, 50, 52, 54, 110, 105]
    return _rows_from_texts(questions, texts, durations)


def _real_ih_q14_san_diego_transcript() -> str:
    """~230-word comparison answer: paragraph form, connectors, light fillers/STT repeats."""
    return _t(
        "Okay, so I want to talk about my neighborhood when I was younger and how it has uh has changed now.",
        "When I was a child, I lived in La Jolla, which is a coastal area in San Diego, and honestly it felt like a quiet college town.",
        "Most people were retirees or UCSD students, and we spent lazy afternoons at the beach or in small local shops.",
        "There were not many tall buildings, parking was easy, and um the rent was pretty affordable for middle-class families.",
        "However, over the past ten years, the neighborhood has has uh has changed a lot because tech companies moved in nearby.",
        "Companies like Qualcomm and other startups opened offices, so young professionals relocated from New York and San Francisco.",
        "As a result, rent went up sharply, and some old bakeries were replaced by fancy coffee places and brunch spots.",
        "For example, a two-bedroom apartment that cost around fifteen hundred dollars before now costs more than twenty-five hundred.",
        "The streets feel busier, traffic is worse during rush hour, but there are also more restaurants, concerts, and weekend events.",
        "So overall, I think my neighborhood became more vibrant and convenient, but longtime residents sometimes struggle with the higher cost of living.",
        "Even though I enjoy the new energy, I miss how peaceful it used to feel when I was growing up there.",
    )


def _real_ih_san_diego_answers(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """15Q IH calibration: solid IH baseline with San Diego-style Q14 (~110s, ~230 words, fillers)."""
    rows = _ih_answers(questions)
    q14_idx = next(i for i, q in enumerate(questions) if q.get("opic_type") == "Comparison")
    transcript = _real_ih_q14_san_diego_transcript()
    duration = 110.0
    rows[q14_idx] = {
        **rows[q14_idx],
        "transcript": transcript,
        "student_answer": transcript,
        "duration_seconds": duration,
        "wpm": round(len(transcript.split()) / max(duration / 60.0, 0.1), 1),
    }
    return rows


def _im_low_regression_answers(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Short list-like answers with repetition — should stay at IM or below (no IH/AL inflation)."""
    texts = [
        "My name Minho. I work office. I live Seoul.",
        "I like TV. Drama good. Funny show.",
        "Watch TV night. Sometimes wife. Friday too.",
        "Last movie cinema. Friends. Fun.",
        "Park nice. Trees green. Walk there.",
        "Go park walk. Sometimes read.",
        "Last park wife. Picnic. Happy.",
        "Music pop. Like melody. Radio.",
        "Listen subway. Home too. Earphones.",
        "Concert friend. Music loud. Good night.",
        "Hotel room. Quiet please. Breakfast?",
        "Wrong food. Allergy chicken. Fix please.",
        "Trip city. Subway good. Budget?",
        "Before small town. Now busy. Many people.",
        "City problem traffic. Bad air. Too many cars.",
    ]
    durations = [18, 16, 14, 15, 12, 11, 14, 13, 12, 15, 12, 13, 12, 14, 13]
    return _rows_from_texts(questions, texts, durations)


_LEVEL_ORDER = ("NL", "NM", "NH", "IL", "IM1", "IM2", "IM3", "IH", "AL")


def _normalize_level_token(level: str) -> str:
    token = str(level or "").strip().upper().replace(" ", "")
    if token in _LEVEL_ORDER:
        return token
    if "응답" in str(level) or "부족" in str(level):
        return "INSUFFICIENT"
    return token or "UNKNOWN"


def _level_index(level: str) -> Optional[int]:
    token = _normalize_level_token(level)
    if token in _LEVEL_ORDER:
        return _LEVEL_ORDER.index(token)
    return None


def _validate_real_ih_level(level: str) -> Tuple[bool, str]:
    """Expect IH ±1 (IM3..AL), not IM2 or below."""
    idx = _level_index(level)
    if idx is None:
        return False, f"unrecognized level {level!r}"
    im3 = _LEVEL_ORDER.index("IM3")
    al = _LEVEL_ORDER.index("AL")
    ok = im3 <= idx <= al
    detail = f"got {_normalize_level_token(level)} (index {idx}); want IM3–AL band"
    return ok, detail


def _validate_im_low_level(level: str) -> Tuple[bool, str]:
    """Low-quality list answers should not inflate to IH/AL."""
    idx = _level_index(level)
    if idx is None:
        return False, f"unrecognized level {level!r}"
    im3 = _LEVEL_ORDER.index("IM3")
    ok = idx <= im3
    detail = f"got {_normalize_level_token(level)} (index {idx}); want IM3 or below"
    return ok, detail


def _print_calibration_gate(sample_name: str, overall_level: str) -> None:
    if sample_name == "real_ih_15q":
        ok, detail = _validate_real_ih_level(overall_level)
        mark = "PASS" if ok else "FAIL"
        print(f"\n  [calibration gate] real_ih: {mark} — {detail}")
    elif sample_name == "im_low_15q":
        ok, detail = _validate_im_low_level(overall_level)
        mark = "PASS" if ok else "FAIL"
        print(f"\n  [calibration gate] im_low regression: {mark} — {detail}")


def _rows_from_texts(
    questions: List[Dict[str, Any]],
    texts: Sequence[str],
    durations: Sequence[float],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i, q in enumerate(questions):
        transcript = texts[i]
        rows.append(
            {
                "question_index": q["question_index"],
                "question_number": q["question_number"],
                "opic_type": q["opic_type"],
                "combo": q["combo"],
                "topic": q["topic"],
                "question_text": q["question_text"],
                "transcript": transcript,
                "student_answer": transcript,
                "stt_status": "transcript_ready",
                "duration_seconds": float(durations[i]),
                "wpm": round(len(transcript.split()) / max(float(durations[i]) / 60.0, 0.1), 1),
            }
        )
    return rows


@dataclass
class CharStats:
    avg: float = 0.0
    min: int = 0
    max: int = 0
    total: int = 0
    count: int = 0


@dataclass
class MeasureResult:
    label: str
    sample_name: str = ""
    skipped: bool = False
    skip_reason: str = ""
    elapsed_sec: float = 0.0
    finish_reason: str = ""
    output_truncated: bool = False
    parse_ok: bool = False
    parse_err: str = ""
    model_requested: str = ""
    model_used: str = ""
    model_note: str = ""
    reasoning_effort: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    est_cost_usd: float = 0.0
    overall_level: str = ""
    q_feedback_count: int = 0
    q_feedback_chars: CharStats = field(default_factory=CharStats)
    summary_chars: int = 0
    strengths_chars: int = 0
    weaknesses_chars: int = 0
    practice_mission_chars: int = 0
    score_breakdown: Dict[str, int] = field(default_factory=dict)
    score_avg: float = 0.0
    sample_q_feedback: List[Tuple[int, str]] = field(default_factory=list)
    parsed: Optional[Dict[str, Any]] = field(default=None, repr=False)


def _char_stats(values: Sequence[int]) -> CharStats:
    if not values:
        return CharStats()
    return CharStats(
        avg=round(mean(values), 1),
        min=min(values),
        max=max(values),
        total=sum(values),
        count=len(values),
    )


def _text_len(val: Any) -> int:
    return len(str(val or "").strip())


def _list_text_len(val: Any) -> int:
    if not isinstance(val, list):
        return _text_len(val)
    return sum(_text_len(x) for x in val)


def _build_prompt(answers: List[Dict[str, Any]], questions: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any]]:
    payload = build_mock_v2_report_payload(answers, questions)
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    prompt = build_mock_v2_rubric_prompt() + "\n\nStudent data JSON:\n" + payload_json
    return prompt, payload


def _estimate_cost(model_key: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _COST_PER_1M.get(model_key)
    if not rates:
        return 0.0
    return round(
        (prompt_tokens * rates["input"] + completion_tokens * rates["output"]) / 1_000_000,
        6,
    )


def _resolve_openai_model(client: Any, candidates: Sequence[str]) -> Tuple[str, str]:
    """Return (model_id, note). Probe models.list when available."""
    last_err = ""
    for model_id in candidates:
        try:
            client.models.retrieve(model_id)
            return model_id, f"validated via models.retrieve({model_id})"
        except Exception as exc:
            last_err = str(exc)
    # Fallback: try a minimal completion with first candidate.
    for model_id in candidates:
        try:
            response = _openai_chat_completions_create(
                client,
                model=model_id,
                messages=[{"role": "user", "content": '{"ok":true}'}],
                max_completion_tokens=16,
                temperature=0.0,
                reasoning_effort="minimal" if _openai_model_restricts_sampling(model_id) else None,
            )
            raw, _ = _openai_extract_choice_text(response)
            if raw:
                return model_id, f"probe completion ok ({model_id})"
        except Exception as exc:
            last_err = str(exc)
    return candidates[0], f"unvalidated — using {candidates[0]} (last error: {last_err[:120]})"


def _extract_usage(response: Any) -> Tuple[int, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return 0, 0
    return int(getattr(usage, "prompt_tokens", 0) or 0), int(
        getattr(usage, "completion_tokens", 0) or 0
    )


def _enrich_from_parsed(result: MeasureResult, parsed: Optional[Dict[str, Any]]) -> None:
    if not isinstance(parsed, dict):
        return
    result.overall_level = str(parsed.get("overall_level") or "")
    q_fb = parsed.get("question_feedback")
    if not isinstance(q_fb, list):
        return
    char_lens: List[int] = []
    for item in q_fb:
        if not isinstance(item, dict):
            continue
        char_lens.append(_text_len(item.get("feedback")))
    result.q_feedback_count = len(q_fb)
    result.q_feedback_chars = _char_stats(char_lens)
    result.summary_chars = _text_len(parsed.get("summary"))
    result.strengths_chars = _list_text_len(parsed.get("strengths"))
    result.weaknesses_chars = _list_text_len(parsed.get("weaknesses"))
    result.practice_mission_chars = _text_len(parsed.get("practice_mission"))
    breakdown = parsed.get("score_breakdown")
    if isinstance(breakdown, dict):
        scores: Dict[str, int] = {}
        for key in _SCORE_KEYS:
            try:
                scores[key] = int(breakdown.get(key) or 0)
            except (TypeError, ValueError):
                scores[key] = 0
        result.score_breakdown = scores
        vals = [v for v in scores.values() if v > 0]
        result.score_avg = round(mean(vals), 1) if vals else 0.0
    # Qualitative samples: Q1, Q14, Q15 (indices 0, 13, 14)
    for idx in (0, 13, 14):
        if idx < len(q_fb) and isinstance(q_fb[idx], dict):
            qnum = int(q_fb[idx].get("question_index") or idx + 1)
            text = str(q_fb[idx].get("feedback") or "").strip()
            if text:
                result.sample_q_feedback.append((qnum, text))


def _result_from_parse(
    *,
    label: str,
    sample_name: str,
    elapsed: float,
    finish_reason: str,
    parsed: Optional[Dict[str, Any]],
    err: str,
    model_requested: str,
    model_used: str,
    model_note: str = "",
    reasoning_effort: str = "",
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_key: str = "",
) -> MeasureResult:
    truncated = err == "output_truncated" or _is_truncated_finish_reason(finish_reason)
    result = MeasureResult(
        label=label,
        sample_name=sample_name,
        elapsed_sec=round(elapsed, 2),
        finish_reason=finish_reason or "—",
        output_truncated=truncated,
        parse_ok=isinstance(parsed, dict),
        parse_err=err if not parsed else "",
        model_requested=model_requested,
        model_used=model_used,
        model_note=model_note,
        reasoning_effort=reasoning_effort or "—",
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        est_cost_usd=_estimate_cost(cost_key, prompt_tokens, completion_tokens),
        parsed=parsed,
    )
    _enrich_from_parsed(result, parsed)
    return result


def _call_gemini_baseline(prompt: str, *, sample_name: str) -> MeasureResult:
    label = "(c) gemini-2.5-flash baseline"
    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        return MeasureResult(label=label, sample_name=sample_name, skipped=True, skip_reason="GEMINI_API_KEY not set")

    t0 = time.perf_counter()
    parsed, err = invoke_gemini_report_text_json(
        api_key=api_key,
        prompt=prompt,
        model_name=_GEMINI_BASELINE_MODEL,
        temperature=0.25,
        max_output_tokens=MOCK_V2_REPORT_MAX_OUTPUT_TOKENS,
        timeout_ms=GEMINI_REQUEST_TIMEOUT_MS,
        log_tag="MOCK_V2_REPORT_DIAG",
        parser_fn=_parse_report_response,
        detect_truncation=True,
    )
    elapsed = time.perf_counter() - t0
    finish_reason = "stop" if parsed else (err or "—")
    return _result_from_parse(
        label=label,
        sample_name=sample_name,
        elapsed=elapsed,
        finish_reason=finish_reason,
        parsed=parsed,
        err=err,
        model_requested=_GEMINI_BASELINE_MODEL,
        model_used=_GEMINI_BASELINE_MODEL,
        model_note="fixed baseline model",
        cost_key="gemini-2.5-flash",
    )


def _call_openai_report(
    prompt: str,
    *,
    sample_name: str,
    label: str,
    model: str,
    model_candidates: Sequence[str] = (),
    max_completion_tokens: int = MOCK_V2_REPORT_MAX_OUTPUT_TOKENS,
    reasoning_effort: Optional[str] = None,
    cost_key: str = "",
) -> MeasureResult:
    api_key = (get_openai_api_key() or "").strip()
    if not api_key:
        return MeasureResult(label=label, sample_name=sample_name, skipped=True, skip_reason="OPENAI_API_KEY not set")

    try:
        from openai import OpenAI
    except ImportError:
        return MeasureResult(label=label, sample_name=sample_name, skipped=True, skip_reason="openai package not installed")

    client = OpenAI(api_key=api_key)
    candidates = tuple(model_candidates) or (model,)
    model_used, model_note = _resolve_openai_model(client, candidates)

    messages = [
        {"role": "system", "content": _OPENAI_JSON_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    effort = reasoning_effort
    if effort is None and "nano" in model_used.lower():
        effort = "minimal"

    t0 = time.perf_counter()
    finish_reason = ""
    err = ""
    parsed: Optional[Dict[str, Any]] = None
    prompt_tokens = 0
    completion_tokens = 0
    reasoning_applied = effort or "—"

    try:
        response = _openai_chat_completions_create(
            client,
            model=model_used,
            messages=messages,
            max_completion_tokens=max_completion_tokens,
            temperature=0.25,
            reasoning_effort=effort,
        )
        raw_text, finish_reason = _openai_extract_choice_text(response)
        prompt_tokens, completion_tokens = _extract_usage(response)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        msg = str(exc)
        if reasoning_effort and "reasoning_effort" in msg.lower():
            reasoning_applied = f"{reasoning_effort} (rejected)"
        return _result_from_parse(
            label=label,
            sample_name=sample_name,
            elapsed=elapsed,
            finish_reason="error",
            parsed=None,
            err=f"{type(exc).__name__}: {exc}",
            model_requested=model,
            model_used=model_used,
            model_note=model_note,
            reasoning_effort=reasoning_applied,
            cost_key=cost_key or model,
        )

    elapsed = time.perf_counter() - t0

    if not raw_text:
        err = "output_truncated" if _is_truncated_finish_reason(finish_reason) else "empty_response"
        return _result_from_parse(
            label=label,
            sample_name=sample_name,
            elapsed=elapsed,
            finish_reason=finish_reason,
            parsed=None,
            err=err,
            model_requested=model,
            model_used=model_used,
            model_note=model_note,
            reasoning_effort=reasoning_applied,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_key=cost_key or model,
        )

    if _is_truncated_finish_reason(finish_reason):
        return _result_from_parse(
            label=label,
            sample_name=sample_name,
            elapsed=elapsed,
            finish_reason=finish_reason,
            parsed=None,
            err="output_truncated",
            model_requested=model,
            model_used=model_used,
            model_note=model_note,
            reasoning_effort=reasoning_applied,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_key=cost_key or model,
        )

    parsed, parse_err = _parse_report_response(raw_text)
    if parsed:
        err = ""
    elif _is_truncated_finish_reason(finish_reason):
        err = "output_truncated"
    else:
        err = parse_err or "json_parse_failed"

    return _result_from_parse(
        label=label,
        sample_name=sample_name,
        elapsed=elapsed,
        finish_reason=finish_reason,
        parsed=parsed,
        err=err,
        model_requested=model,
        model_used=model_used,
        model_note=model_note,
        reasoning_effort=reasoning_applied,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_key=cost_key or model,
    )


def _run_all_for_sample(
    sample_name: str,
    answers: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    *,
    skip_gemini: bool,
) -> Tuple[str, List[MeasureResult]]:
    prompt, payload = _build_prompt(answers, questions)
    total_wc = int(payload.get("total_word_count") or 0)
    print(f"\n{'#' * 72}")
    print(f"SAMPLE: {sample_name}")
    print(f"  questions={len(answers)}  total_word_count={total_wc}")
    print(f"  prompt_chars={len(prompt)}  (~{len(prompt) // 4} tokens est.)")
    print(f"  max_output_tokens={MOCK_V2_REPORT_MAX_OUTPUT_TOKENS}")
    print(f"{'#' * 72}\n")

    results: List[MeasureResult] = []

    results.append(
        _call_openai_report(
            prompt,
            sample_name=sample_name,
            label="(a) gpt-5-nano (production)",
            model=OPENAI_FALLBACK_MODEL,
            max_completion_tokens=MOCK_V2_REPORT_MAX_OUTPUT_TOKENS,
            reasoning_effort="minimal",
            cost_key="gpt-5-nano",
        )
    )
    results.append(
        _call_openai_report(
            prompt,
            sample_name=sample_name,
            label="(b) gpt-5.4-mini",
            model=_GPT54_MINI_CANDIDATES[0],
            model_candidates=_GPT54_MINI_CANDIDATES,
            max_completion_tokens=MOCK_V2_REPORT_MAX_OUTPUT_TOKENS,
            reasoning_effort=None,
            cost_key="gpt-5.4-mini",
        )
    )
    for effort in ("low", "medium"):
        results.append(
            _call_openai_report(
                prompt,
                sample_name=sample_name,
                label=f"(b2) gpt-5.4-mini reasoning={effort}",
                model=_GPT54_MINI_CANDIDATES[0],
                model_candidates=_GPT54_MINI_CANDIDATES,
                max_completion_tokens=MOCK_V2_REPORT_MAX_OUTPUT_TOKENS,
                reasoning_effort=effort,
                cost_key="gpt-5.4-mini",
            )
        )

    if skip_gemini:
        results.append(
            MeasureResult(
                label="(c) gemini-2.5-flash baseline",
                sample_name=sample_name,
                skipped=True,
                skip_reason="--skip-gemini",
            )
        )
    else:
        results.append(_call_gemini_baseline(prompt, sample_name=sample_name))

    return prompt, results


def _print_comparison_table(results: List[MeasureResult]) -> None:
    headers = [
        "sample",
        "run",
        "skip",
        "elapsed_s",
        "model",
        "reasoning",
        "trunc",
        "parse",
        "level",
        "q_fb#",
        "q_fb_chars_avg",
        "q_fb_min",
        "q_fb_max",
        "summary_ch",
        "score_avg",
        "cost_usd",
    ]
    rows: List[List[str]] = []
    for r in results:
        if r.skipped:
            rows.append(
                [
                    r.sample_name,
                    r.label,
                    r.skip_reason,
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                ]
            )
            continue
        rows.append(
            [
                r.sample_name,
                r.label,
                "—",
                f"{r.elapsed_sec:.2f}",
                r.model_used or "—",
                r.reasoning_effort,
                "yes" if r.output_truncated else "no",
                "yes" if r.parse_ok else "no",
                r.overall_level or "—",
                str(r.q_feedback_count),
                f"{r.q_feedback_chars.avg:.0f}" if r.q_feedback_chars.count else "—",
                str(r.q_feedback_chars.min) if r.q_feedback_chars.count else "—",
                str(r.q_feedback_chars.max) if r.q_feedback_chars.count else "—",
                str(r.summary_chars),
                f"{r.score_avg:.1f}" if r.score_avg else "—",
                f"{r.est_cost_usd:.4f}" if r.est_cost_usd else "—",
            ]
        )

    widths = [max(len(h), *(len(row[i]) for row in rows)) for i, h in enumerate(headers)]
    sep = " | "
    print(sep.join(h.ljust(widths[i]) for i, h in enumerate(headers)))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(sep.join(row[i].ljust(widths[i]) for i in range(len(headers))))


def _print_detail_block(r: MeasureResult) -> None:
    print(f"\n{'=' * 72}")
    print(f"{r.sample_name} — {r.label}")
    print(f"{'=' * 72}")
    if r.skipped:
        print(f"SKIP: {r.skip_reason}")
        return
    if r.model_note:
        print(f"model_note: {r.model_note}")
    print(
        f"elapsed={r.elapsed_sec}s  finish_reason={r.finish_reason}  "
        f"truncated={r.output_truncated}  parse_ok={r.parse_ok}"
    )
    if r.parse_err and not r.parse_ok:
        print(f"parse_err: {r.parse_err}")
    print(
        f"tokens: prompt={r.prompt_tokens} completion={r.completion_tokens}  "
        f"est_cost_usd={r.est_cost_usd:.4f} (rough)"
    )
    print(f"overall_level: {r.overall_level or '—'}")
    _print_calibration_gate(r.sample_name, r.overall_level)
    print(
        f"question_feedback chars: avg={r.q_feedback_chars.avg} min={r.q_feedback_chars.min} "
        f"max={r.q_feedback_chars.max} (n={r.q_feedback_chars.count})"
    )
    print(
        f"summary={r.summary_chars}ch  strengths={r.strengths_chars}ch  "
        f"weaknesses={r.weaknesses_chars}ch  practice_mission={r.practice_mission_chars}ch"
    )
    if r.score_breakdown:
        print("score_breakdown:", json.dumps(r.score_breakdown, ensure_ascii=False))
    for qnum, text in r.sample_q_feedback:
        preview = text if len(text) <= 400 else text[:400] + "…"
        print(f"\n--- Q{qnum} feedback (qualitative sample) ---")
        print(preview)


def _print_executive_summary(all_results: List[MeasureResult]) -> None:
    ok = [r for r in all_results if not r.skipped and r.parse_ok]
    if not ok:
        print("\nNo successful parses — cannot recommend a model.")
        return

    print(f"\n{'=' * 72}")
    print("EXECUTIVE SUMMARY (diagnostic only — synthetic samples)")
    print(f"{'=' * 72}")

    by_label: Dict[str, List[MeasureResult]] = {}
    for r in ok:
        by_label.setdefault(r.label, []).append(r)

    summary_rows: List[Tuple[str, float, float, float, float]] = []
    for label, group in by_label.items():
        fb_avg = mean([g.q_feedback_chars.avg for g in group if g.q_feedback_chars.count]) if group else 0.0
        score_avg = mean([g.score_avg for g in group if g.score_avg > 0]) if group else 0.0
        elapsed = mean([g.elapsed_sec for g in group])
        cost = mean([g.est_cost_usd for g in group if g.est_cost_usd > 0]) if any(g.est_cost_usd for g in group) else 0.0
        summary_rows.append((label, fb_avg, score_avg, elapsed, cost))

    summary_rows.sort(key=lambda x: (-x[1], -x[2]))
    print("\nRanked by avg question_feedback chars (detail proxy), then score_avg:")
    print(f"{'run':<42} {'fb_avg_ch':>10} {'score_avg':>10} {'time_s':>8} {'cost_usd':>10}")
    print("-" * 84)
    for label, fb, sc, el, co in summary_rows:
        print(f"{label:<42} {fb:>10.0f} {sc:>10.1f} {el:>8.2f} {co:>10.4f}")

    nano = next((r for r in ok if "(a)" in r.label), None)
    mini = next((r for r in ok if r.label == "(b) gpt-5.4-mini"), None)
    gem = next((r for r in ok if "(c)" in r.label), None)

    print("\nJudgment (for mock_v2 report model selection):")
    if gem and nano:
        fb_delta = gem.q_feedback_chars.avg - nano.q_feedback_chars.avg
        sc_delta = gem.score_avg - nano.score_avg
        print(
            f"- vs gpt-5-nano, Gemini baseline averages +{fb_delta:.0f} feedback chars/q "
            f"and +{sc_delta:.1f} score-axis points (may explain '짧고 짠' complaint)."
        )
    if mini and nano:
        fb_delta = mini.q_feedback_chars.avg - nano.q_feedback_chars.avg
        sc_delta = mini.score_avg - nano.score_avg
        time_delta = mini.elapsed_sec - nano.elapsed_sec
        print(
            f"- gpt-5.4-mini vs nano: feedback chars {fb_delta:+.0f}/q, "
            f"score_avg {sc_delta:+.1f}, time {time_delta:+.1f}s."
        )
        if fb_delta > 30 and sc_delta > -2:
            print(
                "  → gpt-5.4-mini likely restores feedback depth without reverting to Gemini latency."
            )
        elif fb_delta <= 10:
            print(
                "  → gpt-5.4-mini may NOT fix short feedback — tune rubric/prompt or raise reasoning."
            )
    best = summary_rows[0]
    print(
        f"\nBest detail proxy in this run: {best[0]} "
        f"(avg {best[1]:.0f} chars/q, score_avg {best[2]:.1f}, {best[3]:.1f}s)."
    )
    print(
        "Production change is OUT OF SCOPE for this script — use these numbers to pick "
        "OPENAI_FALLBACK_MODEL / reasoning_effort in a follow-up PR."
    )


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mock V2 report model comparison diagnostic")
    p.add_argument(
        "--sample",
        choices=("ih", "al", "both", "real_ih", "im_low", "calibration"),
        default="both",
        help=(
            "Synthetic dataset: IH baseline, AL challenge, real-IH San Diego Q14, "
            "IM-low regression, calibration (real_ih+im_low), or both (ih+al)"
        ),
    )
    p.add_argument("--skip-gemini", action="store_true", help="Skip Gemini baseline (OpenAI-only)")
    return p.parse_args()


def _collect_samples(
    sample: str, questions: List[Dict[str, Any]]
) -> List[Tuple[str, List[Dict[str, Any]]]]:
    samples: List[Tuple[str, List[Dict[str, Any]]]] = []
    if sample in ("ih", "both"):
        samples.append(("ih_15q", _ih_answers(questions)))
    if sample in ("al", "both"):
        samples.append(("al_challenge_15q", _al_answers(questions)))
    if sample in ("real_ih", "calibration"):
        samples.append(("real_ih_15q", _real_ih_san_diego_answers(questions)))
    if sample in ("im_low", "calibration"):
        samples.append(("im_low_15q", _im_low_regression_answers(questions)))
    return samples


def main() -> int:
    args = _parse_args()
    questions = _question_bank()
    samples = _collect_samples(args.sample, questions)

    print("Mock V2 final report — model comparison (gpt-5-nano vs gpt-5.4-mini vs Gemini)")
    print(f"  gemini_key={'set' if get_gemini_api_key() else 'MISSING'}")
    print(f"  openai_key={'set' if get_openai_api_key() else 'MISSING'}")
    print(f"  sample={args.sample}  skip_gemini={args.skip_gemini}")

    all_results: List[MeasureResult] = []
    for sample_name, answers in samples:
        _, results = _run_all_for_sample(
            sample_name,
            answers,
            questions,
            skip_gemini=args.skip_gemini,
        )
        all_results.extend(results)

    print(f"\n{'=' * 72}")
    print("COMPARISON TABLE")
    print(f"{'=' * 72}")
    _print_comparison_table(all_results)

    for r in all_results:
        _print_detail_block(r)

    _print_executive_summary(all_results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
