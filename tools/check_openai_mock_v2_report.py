#!/usr/bin/env python3
"""One-off diagnostic: mock_v2 final report — Gemini vs OpenAI (gpt-5-nano) caps.

Does not modify app/service code. Console output only.

Run (local):
  OPENAI_API_KEY=sk-... GEMINI_API_KEY=... python3 tools/check_openai_mock_v2_report.py
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.mock_v2_analysis import (
    GEMINI_REQUEST_TIMEOUT_MS,
    MOCK_V2_REPORT_MAX_OUTPUT_TOKENS,
    _parse_report_response,
    build_mock_v2_report_model_candidates,
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

# --- Synthetic 15-question mock_v2 sample (not real student data) ----------------

def _t(*parts: str) -> str:
    return " ".join(parts)


SAMPLE_QUESTIONS: List[Dict[str, Any]] = [
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
    {"question_index": 13, "question_number": 14, "opic_type": "Comparison", "combo": "Advanced", "step": "Comparison", "topic": "commute", "question_text": "Compare driving your own car with using public transportation for your daily commute."},
    {"question_index": 14, "question_number": 15, "opic_type": "News/Issue", "combo": "Advanced", "step": "News/Issue", "topic": "environment", "question_text": "What environmental issue concerns you most in your city, and what should people do about it?"},
]

SAMPLE_ANSWERS: List[Dict[str, Any]] = [
    {
        "question_index": 0, "question_number": 1, "opic_type": "Intro", "combo": "Intro", "topic": "intro",
        "question_text": SAMPLE_QUESTIONS[0]["question_text"],
        "transcript": _t(
            "My name is Minho and I work as a marketing coordinator at a small tech company in Seoul.",
            "I graduated from university about four years ago and I live with my wife in a quiet neighborhood.",
            "In my free time I enjoy hiking on weekends and trying new coffee shops around the city.",
            "I also like reading business books because they help me think about my career goals more clearly.",
            "Overall I would describe myself as curious, organized, and pretty outgoing when I meet new people.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 58.0, "wpm": 118.0,
    },
    {
        "question_index": 1, "question_number": 2, "opic_type": "Q1", "combo": "Combo1", "topic": "movies_tv",
        "question_text": SAMPLE_QUESTIONS[1]["question_text"],
        "transcript": _t(
            "These days I mostly watch Korean dramas and a few American series on streaming platforms.",
            "I especially enjoy character-driven stories because I like seeing how people change over time.",
            "My favorite show lately is a workplace drama that mixes humor with realistic office problems.",
            "I also rewatch classic films on weekends when I want something more thoughtful and slower paced.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 52.0, "wpm": 115.0,
    },
    {
        "question_index": 2, "question_number": 3, "opic_type": "Q2", "combo": "Combo1", "topic": "movies_tv",
        "question_text": SAMPLE_QUESTIONS[2]["question_text"],
        "transcript": _t(
            "I usually watch TV about three or four nights a week after dinner when I need to unwind.",
            "On weekdays I watch alone for thirty or forty minutes, but on Friday I often watch with my wife.",
            "We pick something light so we can talk about the plot while we eat snacks on the sofa.",
            "If we finish early we sometimes start another episode, but we try not to stay up too late.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 48.0, "wpm": 112.0,
    },
    {
        "question_index": 3, "question_number": 4, "opic_type": "Q3", "combo": "Combo1", "topic": "movies_tv",
        "question_text": SAMPLE_QUESTIONS[3]["question_text"],
        "transcript": _t(
            "The last movie I watched was a science-fiction film at a local cinema with two close friends.",
            "Before the movie we met at a noodle restaurant nearby and talked about our busy week at work.",
            "During the film I was impressed by the visual effects and the way the story handled time travel.",
            "Afterward we walked to a café and debated the ending for almost an hour because it was ambiguous.",
            "It was a fun night and reminded me why I prefer watching big movies on a large screen.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 62.0, "wpm": 120.0,
    },
    {
        "question_index": 4, "question_number": 5, "opic_type": "Q1", "combo": "Combo2", "topic": "park",
        "question_text": SAMPLE_QUESTIONS[4]["question_text"],
        "transcript": _t(
            "My favorite park is a riverside park about twenty minutes from my apartment by subway.",
            "It has wide walking paths, cherry trees, and a small pond where ducks gather in the spring.",
            "What makes it special is the view of the city skyline at sunset, which looks really peaceful.",
            "There are also outdoor fitness machines that older residents use every morning.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 50.0, "wpm": 116.0,
    },
    {
        "question_index": 5, "question_number": 6, "opic_type": "Q2", "combo": "Combo2", "topic": "park",
        "question_text": SAMPLE_QUESTIONS[5]["question_text"],
        "transcript": _t(
            "When I visit the park I usually walk briskly for thirty minutes to get light exercise.",
            "Sometimes I bring a book and read on a bench near the water if the weather is comfortable.",
            "On weekends I might jog slowly while listening to a podcast about current events.",
            "I also enjoy people-watching because families and cyclists create a lively atmosphere.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 46.0, "wpm": 114.0,
    },
    {
        "question_index": 6, "question_number": 7, "opic_type": "Q3", "combo": "Combo2", "topic": "park",
        "question_text": SAMPLE_QUESTIONS[6]["question_text"],
        "transcript": _t(
            "Last month I went to the park with my wife and her parents during a mild autumn afternoon.",
            "We packed sandwiches and thermoses of tea, then spread a blanket under a gingko tree.",
            "My father-in-law told stories about his childhood while we watched children fly kites nearby.",
            "Later we walked along the river and took photos because the yellow leaves looked beautiful.",
            "We stayed until the sun went down and then took a taxi home because we were tired but happy.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 60.0, "wpm": 119.0,
    },
    {
        "question_index": 7, "question_number": 8, "opic_type": "Q1", "combo": "Combo3", "topic": "music",
        "question_text": SAMPLE_QUESTIONS[7]["question_text"],
        "transcript": _t(
            "Recently I listen to a mix of indie pop and soft rock, especially when I am commuting.",
            "I like those genres because the melodies are catchy but the lyrics still feel meaningful.",
            "Some Korean indie bands have interesting arrangements that combine acoustic guitar with synth sounds.",
            "When I need focus at work I switch to instrumental playlists without vocals.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 47.0, "wpm": 113.0,
    },
    {
        "question_index": 8, "question_number": 9, "opic_type": "Q2", "combo": "Combo3", "topic": "music",
        "question_text": SAMPLE_QUESTIONS[8]["question_text"],
        "transcript": _t(
            "I mostly listen to music on the subway in the morning and while doing chores at home.",
            "I use noise-canceling earphones so I can hear details even in crowded trains.",
            "At home I play music on a small speaker in the kitchen when I cook dinner after work.",
            "I avoid listening too loudly because I worry about damaging my hearing over time.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 45.0, "wpm": 111.0,
    },
    {
        "question_index": 9, "question_number": 10, "opic_type": "Q3", "combo": "Combo3", "topic": "music",
        "question_text": SAMPLE_QUESTIONS[9]["question_text"],
        "transcript": _t(
            "One memorable concert was an outdoor jazz festival I attended two summers ago with college friends.",
            "We arrived early to get good seats near the stage and bought cold drinks from a food truck.",
            "The headline band played energetic sets that had the whole crowd clapping along.",
            "After the show we talked about starting a band ourselves, though we never actually did.",
            "The night ended with fireworks, and I still remember how warm the air felt.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 58.0, "wpm": 117.0,
    },
    {
        "question_index": 10, "question_number": 11, "opic_type": "Roleplay", "combo": "Roleplay", "topic": "hotel",
        "question_text": SAMPLE_QUESTIONS[10]["question_text"],
        "transcript": _t(
            "Hello, I have a reservation under the name Minho Park for two nights starting today.",
            "I would prefer a quiet room on a higher floor away from the elevator if possible.",
            "Could you tell me whether breakfast is included and what time the gym opens tomorrow?",
            "Also, is late checkout available on Sunday because my flight is in the evening?",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 44.0, "wpm": 110.0,
    },
    {
        "question_index": 11, "question_number": 12, "opic_type": "Roleplay", "combo": "Roleplay", "topic": "restaurant",
        "question_text": SAMPLE_QUESTIONS[11]["question_text"],
        "transcript": _t(
            "Excuse me, I ordered the grilled salmon, but this looks like a chicken dish instead.",
            "I am not upset, but I cannot eat chicken because of an allergy, so I need a replacement.",
            "Could you ask the kitchen to prepare the salmon again and let me know how long it will take?",
            "If there is a delay, may I have a simple salad while I wait so I am not hungry?",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 46.0, "wpm": 112.0,
    },
    {
        "question_index": 12, "question_number": 13, "opic_type": "Roleplay", "combo": "Roleplay", "topic": "travel",
        "question_text": SAMPLE_QUESTIONS[12]["question_text"],
        "transcript": _t(
            "Since you are planning your first solo trip, I suggest choosing a city with good public transit.",
            "Book accommodations near a subway line so you can save time and taxi fares.",
            "What dates are you considering, and do you have a rough budget for hotels and meals?",
            "If you share that information I can recommend neighborhoods that are safe and convenient.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 48.0, "wpm": 115.0,
    },
    {
        "question_index": 13, "question_number": 14, "opic_type": "Comparison", "combo": "Advanced", "topic": "commute",
        "question_text": SAMPLE_QUESTIONS[13]["question_text"],
        "transcript": _t(
            "Driving my own car is convenient because I can leave whenever I want and carry heavy bags easily.",
            "However, parking downtown is expensive and traffic jams make me stressed during rush hour.",
            "Public transportation is cheaper and better for the environment, and I can read on the train.",
            "On the other hand, trains are crowded in the morning and less flexible if I work late.",
            "Overall I use the subway on weekdays but drive when I visit my parents outside the city.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 55.0, "wpm": 118.0,
    },
    {
        "question_index": 14, "question_number": 15, "opic_type": "News/Issue", "combo": "Advanced", "topic": "environment",
        "question_text": SAMPLE_QUESTIONS[14]["question_text"],
        "transcript": _t(
            "Air quality is the environmental issue that worries me most because smog has worsened in recent years.",
            "On bad days I check fine dust levels before exercising outdoors with my running club.",
            "I think the city should expand bus lanes and subsidize electric vehicles to reduce emissions.",
            "Individuals can also help by using reusable containers and conserving energy at home.",
            "If everyone makes small changes, the air could improve for children and older residents.",
        ),
        "stt_status": "transcript_ready", "duration_seconds": 57.0, "wpm": 116.0,
    },
]

for row in SAMPLE_ANSWERS:
    row["student_answer"] = row["transcript"]


@dataclass
class MeasureResult:
    label: str
    skipped: bool = False
    skip_reason: str = ""
    elapsed_sec: float = 0.0
    finish_reason: str = ""
    output_truncated: bool = False
    parse_ok: bool = False
    parse_err: str = ""
    top_level_keys: int = 0
    q_feedback_len: int = 0
    q_feedback_complete: bool = False
    model_used: str = ""
    raw_err: str = ""
    parsed: Optional[Dict[str, Any]] = field(default=None, repr=False)


def _build_prompt() -> Tuple[str, Dict[str, Any]]:
    payload = build_mock_v2_report_payload(SAMPLE_ANSWERS, SAMPLE_QUESTIONS)
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    prompt = build_mock_v2_rubric_prompt() + "\n\nStudent data JSON:\n" + payload_json
    return prompt, payload


def _summarize_parsed(parsed: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(parsed, dict):
        return {}
    q_fb = parsed.get("question_feedback")
    q_len = len(q_fb) if isinstance(q_fb, list) else 0
    return {
        "overall_level": parsed.get("overall_level"),
        "summary_preview": str(parsed.get("summary") or "")[:120],
        "score_breakdown_keys": sorted((parsed.get("score_breakdown") or {}).keys())
        if isinstance(parsed.get("score_breakdown"), dict)
        else [],
        "question_feedback_len": q_len,
        "strengths_len": len(parsed.get("strengths") or [])
        if isinstance(parsed.get("strengths"), list)
        else 0,
        "weaknesses_len": len(parsed.get("weaknesses") or [])
        if isinstance(parsed.get("weaknesses"), list)
        else 0,
        "practice_mission_preview": str(parsed.get("practice_mission") or "")[:80],
    }


def _result_from_parse(
    *,
    label: str,
    elapsed: float,
    finish_reason: str,
    parsed: Optional[Dict[str, Any]],
    err: str,
    model_used: str,
) -> MeasureResult:
    truncated = (
        err == "output_truncated"
        or _is_truncated_finish_reason(finish_reason)
    )
    q_len = 0
    if isinstance(parsed, dict) and isinstance(parsed.get("question_feedback"), list):
        q_len = len(parsed["question_feedback"])
    return MeasureResult(
        label=label,
        elapsed_sec=round(elapsed, 2),
        finish_reason=finish_reason or "—",
        output_truncated=truncated,
        parse_ok=isinstance(parsed, dict),
        parse_err=err if not parsed else "",
        top_level_keys=len(parsed.keys()) if isinstance(parsed, dict) else 0,
        q_feedback_len=q_len,
        q_feedback_complete=(q_len == _EXPECTED_Q_FEEDBACK),
        model_used=model_used,
        raw_err=err,
        parsed=parsed,
    )


def _call_gemini_baseline(prompt: str) -> MeasureResult:
    label = "(a) Gemini baseline"
    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        return MeasureResult(label=label, skipped=True, skip_reason="GEMINI_API_KEY not set")

    models = build_mock_v2_report_model_candidates()
    if not models:
        return MeasureResult(label=label, skipped=True, skip_reason="no report models configured")

    model_name = models[0]
    t0 = time.perf_counter()
    parsed, err = invoke_gemini_report_text_json(
        api_key=api_key,
        prompt=prompt,
        model_name=model_name,
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
        elapsed=elapsed,
        finish_reason=finish_reason,
        parsed=parsed,
        err=err,
        model_used=model_name,
    )


def _call_openai_report(prompt: str, *, max_completion_tokens: int, label: str) -> MeasureResult:
    api_key = (get_openai_api_key() or "").strip()
    if not api_key:
        return MeasureResult(label=label, skipped=True, skip_reason="OPENAI_API_KEY not set")

    try:
        from openai import OpenAI
    except ImportError:
        return MeasureResult(label=label, skipped=True, skip_reason="openai package not installed")

    client = OpenAI(api_key=api_key)
    messages = [
        {"role": "system", "content": _OPENAI_JSON_SYSTEM},
        {"role": "user", "content": prompt},
    ]
    reasoning_effort = "minimal" if _openai_model_restricts_sampling(OPENAI_FALLBACK_MODEL) else None

    t0 = time.perf_counter()
    finish_reason = ""
    err = ""
    parsed: Optional[Dict[str, Any]] = None

    try:
        response = _openai_chat_completions_create(
            client,
            model=OPENAI_FALLBACK_MODEL,
            messages=messages,
            max_completion_tokens=max_completion_tokens,
            temperature=0.25,
            reasoning_effort=reasoning_effort,
        )
        raw_text, finish_reason = _openai_extract_choice_text(response)
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        return _result_from_parse(
            label=label,
            elapsed=elapsed,
            finish_reason="error",
            parsed=None,
            err=f"{type(exc).__name__}: {exc}",
            model_used=OPENAI_FALLBACK_MODEL,
        )

    elapsed = time.perf_counter() - t0

    if not raw_text:
        err = "output_truncated" if _is_truncated_finish_reason(finish_reason) else "empty_response"
        return _result_from_parse(
            label=label,
            elapsed=elapsed,
            finish_reason=finish_reason,
            parsed=None,
            err=err,
            model_used=OPENAI_FALLBACK_MODEL,
        )

    if _is_truncated_finish_reason(finish_reason):
        return _result_from_parse(
            label=label,
            elapsed=elapsed,
            finish_reason=finish_reason,
            parsed=None,
            err="output_truncated",
            model_used=OPENAI_FALLBACK_MODEL,
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
        elapsed=elapsed,
        finish_reason=finish_reason,
        parsed=parsed,
        err=err,
        model_used=OPENAI_FALLBACK_MODEL,
    )


def _print_table(results: List[MeasureResult]) -> None:
    headers = [
        "run",
        "skip",
        "elapsed_s",
        "model",
        "finish_reason",
        "truncated",
        "parse_ok",
        "top_keys",
        "q_fb_len",
        "q_fb_15",
    ]
    rows: List[List[str]] = []
    for r in results:
        rows.append(
            [
                r.label,
                r.skip_reason if r.skipped else "—",
                "—" if r.skipped else f"{r.elapsed_sec:.2f}",
                "—" if r.skipped else (r.model_used or "—"),
                "—" if r.skipped else r.finish_reason,
                "—" if r.skipped else ("yes" if r.output_truncated else "no"),
                "—" if r.skipped else ("yes" if r.parse_ok else "no"),
                "—" if r.skipped else str(r.top_level_keys),
                "—" if r.skipped else str(r.q_feedback_len),
                "—" if r.skipped else ("yes" if r.q_feedback_complete else "no"),
            ]
        )

    widths = [max(len(h), *(len(row[i]) for row in rows)) for i, h in enumerate(headers)]
    sep = " | "
    header_line = sep.join(h.ljust(widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(sep.join(row[i].ljust(widths[i]) for i in range(len(headers))))


def _print_summaries(results: List[MeasureResult]) -> None:
    for r in results:
        print(f"\n{'=' * 60}")
        print(r.label)
        print(f"{'=' * 60}")
        if r.skipped:
            print(f"SKIP: {r.skip_reason}")
            continue
        if r.raw_err and not r.parse_ok:
            print(f"error: {r.raw_err}")
        summary = _summarize_parsed(r.parsed)
        print(json.dumps(summary, ensure_ascii=False, indent=2))


def _print_recommendation(results: List[MeasureResult], prompt_chars: int) -> None:
    print(f"\n{'=' * 60}")
    print("Recommendation (diagnostic only)")
    print(f"{'=' * 60}")
    print(f"Prompt size: {prompt_chars} chars (~{prompt_chars // 4} tokens est.)")
    print(f"Gemini max_output_tokens baseline: {MOCK_V2_REPORT_MAX_OUTPUT_TOKENS}")

    by_label = {r.label: r for r in results}
    a = by_label.get("(a) Gemini baseline")
    b = by_label.get("(b) OpenAI gpt-5-nano cap=16384")
    c = by_label.get("(c) OpenAI gpt-5-nano cap=8192")

    openai_ok = [r for r in (b, c) if r and not r.skipped and r.parse_ok and r.q_feedback_complete]
    if openai_ok:
        best = min(openai_ok, key=lambda r: (r.output_truncated, r.elapsed_sec))
        cap_note = "16384" if "16384" in best.label else "8192"
        print(
            f"OpenAI cap: prefer max_completion_tokens={cap_note} "
            f"(parse_ok={best.parse_ok}, q_fb={best.q_feedback_len}, truncated={best.output_truncated})."
        )
        if c and not c.skipped and b and not b.skipped:
            if c.parse_ok and c.q_feedback_complete and not c.output_truncated:
                if b.output_truncated or not b.parse_ok:
                    print("8192 sufficient for this sample; 16384 not required.")
                elif c.elapsed_sec < b.elapsed_sec * 0.85:
                    print("8192 faster with same completeness — consider 8192 as lower bound.")
                else:
                    print("16384 safer if 8192 truncates or misses question_feedback items.")
    else:
        print("OpenAI: no successful full parse in this run — keep 16384 for mock_v2 until re-tested.")

    elapsed_vals = [r.elapsed_sec for r in results if not r.skipped and r.elapsed_sec > 0]
    if elapsed_vals:
        worst = max(elapsed_vals)
        # OpenAI primary + Gemini fallback headroom (mini mock uses 55s).
        suggested_wrapper = int(worst * 1.35 + 10)
        suggested_wrapper = max(70, min(suggested_wrapper, 120))
        print(
            f"Wrapper timeout: slowest single call {worst:.1f}s → "
            f"suggest mock_v2 wrapper ≥{suggested_wrapper}s if OpenAI-first + one Gemini fallback."
        )


def main() -> int:
    prompt, payload = _build_prompt()
    total_wc = int(payload.get("total_word_count") or 0)

    print("Mock V2 final report — Gemini vs OpenAI cap diagnostic (synthetic 15Q IH sample)")
    print(f"  questions={len(SAMPLE_ANSWERS)}  total_word_count={total_wc}")
    print(f"  prompt_chars={len(prompt)}  (~{len(prompt) // 4} tokens est.)")
    print(f"  gemini_key={'set' if get_gemini_api_key() else 'MISSING'}")
    print(f"  openai_key={'set' if get_openai_api_key() else 'MISSING'}")
    print()

    results = [
        _call_gemini_baseline(prompt),
        _call_openai_report(
            prompt,
            max_completion_tokens=16384,
            label="(b) OpenAI gpt-5-nano cap=16384",
        ),
        _call_openai_report(
            prompt,
            max_completion_tokens=8192,
            label="(c) OpenAI gpt-5-nano cap=8192",
        ),
    ]

    _print_table(results)
    _print_summaries(results)
    _print_recommendation(results, len(prompt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
