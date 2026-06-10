#!/usr/bin/env python3
"""Synthesize MP3s for Mock V2 extras (intro + IH/AL Q14–Q15).

Jobs:
  - mock_v2_intro.mp3  (Q1 self-introduction)
  - {set_id}_comparison.mp3 / {set_id}_news_issue.mp3  (ADVANCED_SET_POOL)

Output: assets/question_audio/{audio_id}.mp3
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AUDIO_DIR = ROOT / "assets" / "question_audio"


def _collect_jobs() -> list[tuple[str, str, str]]:
    from services.mock_exam.mock_exam_test_set_generator import ADVANCED_SET_POOL
    from services.mock_v2_question_selector import _INTRO_TEXT
    from utils.question_audio_assets import MOCK_V2_INTRO_AUDIO_ID

    jobs: list[tuple[str, str, str]] = [
        (MOCK_V2_INTRO_AUDIO_ID, _INTRO_TEXT, f"{MOCK_V2_INTRO_AUDIO_ID}.mp3"),
    ]
    for entry in ADVANCED_SET_POOL:
        if not isinstance(entry, dict):
            continue
        set_id = str(entry.get("set_id") or "").strip()
        if not set_id:
            continue
        for kind in ("comparison", "news_issue"):
            block = entry.get(kind)
            if not isinstance(block, dict):
                continue
            text = str(block.get("question") or "").strip()
            if not text:
                continue
            audio_id = f"{set_id}_{kind}"
            jobs.append((audio_id, text, f"{audio_id}.mp3"))
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Advanced Q14/Q15 MP3 builder")
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-synthesize even if the MP3 already exists.",
    )
    parser.add_argument("--voice", default=None)
    parser.add_argument("--speaking-rate", type=float, default=0.95)
    parser.add_argument("--pitch", type=float, default=0.0)
    args = parser.parse_args()

    jobs = _collect_jobs()
    total = len(jobs)

    if args.metadata_only:
        print(f"[ok] advanced_audio_jobs={total}")
        return 0

    if total == 0:
        print("[error] no advanced jobs collected", file=sys.stderr)
        return 1

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    from services.tts_service import NEURAL2_EVA, synthesize_tts_audio

    voice_name = args.voice or NEURAL2_EVA
    ok = 0
    skipped = 0
    err = 0

    for audio_id, text, filename in jobs:
        out = AUDIO_DIR / filename
        if out.is_file() and not args.force:
            skipped += 1
            continue
        try:
            payload = synthesize_tts_audio(
                text,
                voice_name=voice_name,
                speaking_rate=args.speaking_rate,
                pitch=args.pitch,
            )
            blob = payload.get("audio_bytes") or b""
            if not blob:
                raise RuntimeError("empty audio bytes")
            out.write_bytes(blob)
            ok += 1
            print(f"[{ok}/{total - skipped}] {filename}")
        except Exception as e:  # noqa: BLE001
            err += 1
            print(f"[fail] {filename}: {e}", file=sys.stderr)

    print(f"[done] wrote {ok}, skipped {skipped}, errors {err} -> {AUDIO_DIR}")
    return 0 if err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
