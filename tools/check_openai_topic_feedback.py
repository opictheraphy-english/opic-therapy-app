#!/usr/bin/env python3
"""One-off diagnostic: Gemini vs OpenAI topic feedback JSON shape + UI safety.

Does not modify app/service/UI code. Console output only.

Run (local):
  export GEMINI_API_KEY=...
  export OPENAI_API_KEY=...   # optional; (b) skipped if missing
  python tools/check_openai_topic_feedback.py
  python tools/check_openai_topic_feedback.py --sample real_ih
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from services.evaluation.eval_config import build_topic_feedback_model_candidates
from services.gemini_json_client import (
    OPENAI_FALLBACK_MAX_COMPLETION_TOKENS,
    OPENAI_FALLBACK_MODEL,
    invoke_openai_text_json,
    run_gemini_json_model_chain,
)
from services.topic_practice_v2_analysis import (
    GEMINI_REQUEST_TIMEOUT_MS,
    _build_prompt,
)
from tools.check_openai_mock_v2_report import _real_ih_q14_san_diego_transcript
from utils.secrets import get_gemini_api_key, get_openai_api_key

# --- Synthetic sample (not real student data) --------------------------------

SAMPLE_ANSWER: Dict[str, Any] = {
    "topic": "cafe",
    "opic_type": "description",
    "en": "Tell me about a café or coffee shop you like to visit.",
    "ko": "자주 가는 카페나 커피숍에 대해 말해 보세요.",
    "duration_seconds": 52.0,
    "transcript": (
        "Well, I usually go to a small café near my office about twice a week. "
        "I like the quiet atmosphere because it helps me focus when I read or plan my day. "
        "My favorite drink is a latte, and sometimes I order a blueberry muffin if I am hungry. "
        "I often sit by the window so I can people-watch while I sip my coffee. "
        "On weekends, I might meet a friend there and we chat for an hour or so."
    ),
}

REAL_IH_COMPARISON_ANSWER: Dict[str, Any] = {
    "topic": "neighborhood",
    "opic_type": "comparison",
    "en": "Tell me about your neighborhood when you were younger and how it is different now.",
    "ko": "어릴 때 살던 동네와 지금의 차이에 대해 말해 보세요.",
    "duration_seconds": 110.0,
    "transcript": _real_ih_q14_san_diego_transcript(),
}

_ACCEPTABLE_REAL_IH_LEVELS = frozenset({"IM3", "IH", "AL"})

# LLM output keys (rubric v7) consumed by topic feedback UI after _normalize_success.
# Source: services/topic_practice_v2_rubric.py output schema;
#         views/topic_practice_v2._render_feedback_ui (.get keys).
UI_MODEL_KEYS: Tuple[str, ...] = (
    "answer_level",
    "summary",
    "strength",
    "correction_focus",
    "better_expression",
    "upgrade_sample",
    "keyword_drill",
    "practice_mission",
)

# Expected value types for UI-safe rendering (topic practice standard mode).
UI_KEY_TYPES: Dict[str, type | tuple[type, ...]] = {
    "answer_level": str,
    "summary": str,
    "strength": str,
    "correction_focus": str,
    "better_expression": str,
    "upgrade_sample": str,
    "keyword_drill": list,
    "practice_mission": str,
}


def _transcript_from_answer(answer: Dict[str, Any]) -> str:
    for key in ("transcript", "student_answer", "stt_transcript", "raw_transcript"):
        val = str(answer.get(key) or "").strip()
        if val:
            return val
    return ""


def _call_gemini_chain(prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
    api_key = (get_gemini_api_key() or "").strip()
    if not api_key:
        return None, "missing_gemini_api_key"
    models = build_topic_feedback_model_candidates()
    return run_gemini_json_model_chain(
        api_key=api_key,
        prompt=prompt,
        models=models,
        temperature=0.2,
        max_output_tokens=1024,
        timeout_ms=GEMINI_REQUEST_TIMEOUT_MS,
        log_tag="TOPIC_V2_FEEDBACK",
    )


def _call_openai_direct(prompt: str) -> Tuple[Optional[Dict[str, Any]], str]:
    if not (get_openai_api_key() or "").strip():
        return None, "skip"
    return invoke_openai_text_json(
        prompt=prompt,
        model=OPENAI_FALLBACK_MODEL,
        log_tag="TOPIC_V2_FEEDBACK",
        max_output_tokens=OPENAI_FALLBACK_MAX_COMPLETION_TOKENS,
        temperature=0.2,
    )


def _type_label(val: Any) -> str:
    if val is None:
        return "null"
    if isinstance(val, bool):
        return "bool"
    if isinstance(val, list):
        if not val:
            return "list[empty]"
        inner = {_type_label(x) for x in val[:3]}
        return f"list[{','.join(sorted(inner))}]"
    if isinstance(val, dict):
        return f"dict(keys={sorted(val.keys())})"
    return type(val).__name__


def _compare_dicts(
    left: Dict[str, Any],
    right: Dict[str, Any],
    *,
    left_name: str,
    right_name: str,
) -> None:
    left_keys = set(left.keys())
    right_keys = set(right.keys())
    only_left = sorted(left_keys - right_keys)
    only_right = sorted(right_keys - left_keys)
    shared = sorted(left_keys & right_keys)

    print(f"\n=== Key diff ({left_name} vs {right_name}) ===")
    print(f"  {left_name} only: {only_left or '(none)'}")
    print(f"  {right_name} only: {only_right or '(none)'}")
    print(f"  shared top-level: {shared or '(none)'}")

    print("\n=== Nested structure (one level) ===")
    nested_left = {k: v for k, v in left.items() if isinstance(v, dict)}
    nested_right = {k: v for k, v in right.items() if isinstance(v, dict)}
    if not nested_left and not nested_right:
        print("  (no nested dict values at top level)")
    for key in sorted(set(nested_left) | set(nested_right)):
        lk = set(nested_left.get(key, {}).keys())
        rk = set(nested_right.get(key, {}).keys())
        print(
            f"  {key!r}: {left_name}_only={sorted(lk - rk) or '(none)'} "
            f"{right_name}_only={sorted(rk - lk) or '(none)'} "
            f"shared={sorted(lk & rk) or '(none)'}"
        )

    print("\n=== Value type mismatches (shared keys) ===")
    mismatches: List[str] = []
    for key in shared:
        lt = _type_label(left[key])
        rt = _type_label(right[key])
        if lt != rt:
            mismatches.append(f"  {key!r}: {left_name}={lt}  {right_name}={rt}")
    if mismatches:
        print("\n".join(mismatches))
    else:
        print("  (none)")


def _check_ui_keys(label: str, data: Optional[Dict[str, Any]]) -> None:
    print(f"\n=== UI required keys — {label} ===")
    if not isinstance(data, dict):
        print("  (no dict to check)")
        return
    for key in UI_MODEL_KEYS:
        present = key in data and data.get(key) not in (None, "")
        if key == "keyword_drill":
            present = key in data and isinstance(data.get(key), list)
        mark = "✓" if present else "✗"
        extra = ""
        if key in data:
            extra = f"  type={_type_label(data[key])}"
        print(f"  {mark} {key}{extra}")


def _print_json_block(title: str, data: Optional[Dict[str, Any]], err: str) -> None:
    print(f"\n{'=' * 60}")
    print(title)
    print(f"{'=' * 60}")
    if err:
        print(f"error/skip token: {err}")
    if data is None:
        print("(no parsed dict)")
        return
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> int:
    parser = argparse.ArgumentParser(description="Topic feedback JSON diagnostic")
    parser.add_argument(
        "--sample",
        choices=("cafe", "real_ih"),
        default="cafe",
        help="cafe=default UI sample; real_ih=San Diego comparison IH calibration",
    )
    args = parser.parse_args()
    answer = REAL_IH_COMPARISON_ANSWER if args.sample == "real_ih" else SAMPLE_ANSWER

    transcript = _transcript_from_answer(answer)
    prompt = _build_prompt(answer, transcript)

    print(f"Topic feedback JSON shape check (sample={args.sample})")
    print(f"  topic={answer['topic']!r}  words≈{len(transcript.split())}  duration={answer.get('duration_seconds')}")
    print(f"  gemini_key={'set' if get_gemini_api_key() else 'MISSING'}")
    print(f"  openai_key={'set' if get_openai_api_key() else 'MISSING'}")

    gemini_dict, gemini_err = _call_gemini_chain(prompt)
    _print_json_block("(a) Gemini chain — run_gemini_json_model_chain", gemini_dict, gemini_err)

    if not (get_openai_api_key() or "").strip():
        print(f"\n{'=' * 60}")
        print(f"(b) OpenAI direct — invoke_openai_text_json model={OPENAI_FALLBACK_MODEL}")
        print(f"{'=' * 60}")
        print("skip (OPENAI_API_KEY not set)")
        openai_dict, openai_err = None, "skip"
    else:
        openai_dict, openai_err = _call_openai_direct(prompt)
        _print_json_block(
            f"(b) OpenAI direct — invoke_openai_text_json model={OPENAI_FALLBACK_MODEL}",
            openai_dict,
            openai_err if openai_err == "skip" else (openai_err if not openai_dict else ""),
        )

    if isinstance(gemini_dict, dict) and isinstance(openai_dict, dict):
        _compare_dicts(gemini_dict, openai_dict, left_name="Gemini", right_name="GPT")
    else:
        print("\n=== Key diff skipped (need both parsed dicts) ===")

    _check_ui_keys("Gemini", gemini_dict)
    _check_ui_keys("GPT", openai_dict)

    if args.sample == "real_ih":
        for label, data in (("Gemini", gemini_dict), ("GPT", openai_dict)):
            if not isinstance(data, dict):
                continue
            level = str(data.get("answer_level") or "").strip().upper()
            ok = level in _ACCEPTABLE_REAL_IH_LEVELS
            mark = "PASS" if ok else "FAIL"
            print(f"\n[calibration gate] real_ih {label}: {mark} — answer_level={level or '—'} (want IM3/IH/AL)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
