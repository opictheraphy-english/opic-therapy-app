#!/usr/bin/env python3
"""Synthesize MP3s for topic-practice and mock-exam question audio.

Generates one MP3 per question from:
  - TOPIC_PRACTICE_QUESTIONS q1–q4 (topic practice + mock bank seats)
  - ROLEPLAY_PRACTICE_SETS q6–q7–q8 (mock exam roleplay Q11–13)

  python generate_question_audio.py --metadata-only   # count jobs, no TTS
  python generate_question_audio.py                   # synthesize all missing
  python generate_question_audio.py --roleplay-only   # roleplay q6–q8 only
  python generate_question_audio.py --force           # re-make existing files
  python generate_question_audio.py --topics home cafe # limit topic q1–q4

Output: assets/question_audio/{question_id}.mp3  (e.g. home_q1_001.mp3)
Already-existing MP3s are skipped unless --force is given.
These MP3s are committed to git so they ship with the Render deploy.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Run from the repo root so the `data` package resolves. We also add ROOT
# to sys.path defensively, matching generate_pattern_audio.py's ROOT idiom.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AUDIO_DIR = ROOT / "assets" / "question_audio"

_SLOTS = ("q1", "q2", "q3", "q4")
_ROLEPLAY_SLOTS = ("q6", "q7", "q8")


def _all_topic_ids() -> list[str]:
    """Every topic_id present in the question bank (39 topics)."""
    from data.opic_question_bank_v2 import TOPIC_PRACTICE_QUESTIONS

    return sorted(TOPIC_PRACTICE_QUESTIONS.keys())


def _collect_topic_jobs(topic_ids: list[str]) -> list[tuple[str, str, str]]:
    """Return [(question_id, english_text, mp3_filename), ...] for topic q1–q4."""
    from data.opic_question_bank_v2 import TOPIC_PRACTICE_QUESTIONS

    jobs: list[tuple[str, str, str]] = []
    seen_ids: set[str] = set()
    for topic_id in topic_ids:
        bucket = TOPIC_PRACTICE_QUESTIONS.get(topic_id) or {}
        for slot in _SLOTS:
            for row in bucket.get(slot) or []:
                if not isinstance(row, dict):
                    continue
                qid = str(row.get("id") or "").strip()
                text = str(row.get("question_text") or "").strip()
                if not qid or not text:
                    print(f"  [skip] missing id/text in {topic_id}/{slot}")
                    continue
                if qid in seen_ids:
                    continue
                seen_ids.add(qid)
                jobs.append((qid, text, f"{qid}.mp3"))
    return jobs


def _collect_roleplay_jobs() -> list[tuple[str, str, str]]:
    """Return [(question_id, english_text, mp3_filename), ...] for roleplay q6–q8."""
    from data.opic_question_bank_v2 import ROLEPLAY_PRACTICE_SETS

    jobs: list[tuple[str, str, str]] = []
    seen_ids: set[str] = set()
    for ent in ROLEPLAY_PRACTICE_SETS:
        if not isinstance(ent, dict):
            continue
        qs = ent.get("questions") or {}
        for slot in _ROLEPLAY_SLOTS:
            row = qs.get(slot)
            if not isinstance(row, dict):
                continue
            qid = str(row.get("id") or "").strip()
            text = str(row.get("question_text") or "").strip()
            if not qid or not text:
                set_id = str(ent.get("set_id") or "?")
                print(f"  [skip] missing id/text in roleplay {set_id}/{slot}")
                continue
            if qid in seen_ids:
                continue
            seen_ids.add(qid)
            jobs.append((qid, text, f"{qid}.mp3"))
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Question MP3 asset builder")
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only count jobs; do not call TTS.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-synthesize even if the MP3 already exists.",
    )
    parser.add_argument(
        "--topics",
        nargs="+",
        default=None,
        metavar="TOPIC_ID",
        help="Limit to specific topic_ids for q1–q4. Default: all topics in the bank.",
    )
    parser.add_argument(
        "--roleplay-only",
        action="store_true",
        help="Synthesize only roleplay q6–q8 (42 questions).",
    )
    parser.add_argument(
        "--topics-only",
        action="store_true",
        help="Synthesize only topic bank q1–q4 (skip roleplay).",
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="Neural2 voice name (defaults to NEURAL2_EVA).",
    )
    parser.add_argument("--speaking-rate", type=float, default=0.95)
    parser.add_argument("--pitch", type=float, default=0.0)
    args = parser.parse_args()

    topic_ids = args.topics if args.topics else _all_topic_ids()
    jobs: list[tuple[str, str, str]] = []
    if not args.roleplay_only:
        jobs.extend(_collect_topic_jobs(topic_ids))
    if not args.topics_only:
        jobs.extend(_collect_roleplay_jobs())
    total = len(jobs)

    if args.metadata_only:
        topic_jobs = 0 if args.roleplay_only else len(_collect_topic_jobs(topic_ids))
        roleplay_jobs = 0 if args.topics_only else len(_collect_roleplay_jobs())
        print(
            f"[ok] topic_q1_q4_jobs={topic_jobs}, "
            f"roleplay_q6_q8_jobs={roleplay_jobs}, total={total}"
        )
        return 0

    if total == 0:
        print("[error] no question jobs collected - check the question bank.",
              file=sys.stderr)
        return 1

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # Imported lazily so --metadata-only needs no TTS credentials.
    from services.tts_service import NEURAL2_EVA, synthesize_tts_audio

    voice_name = args.voice or NEURAL2_EVA
    ok = 0
    skipped = 0
    err = 0

    for qid, text, filename in jobs:
        out = AUDIO_DIR / filename
        if out.is_file() and not args.force:
            skipped += 1
            print(f"[skip] {filename} (exists - use --force to redo)")
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
            print(f"[{ok}/{total}] {filename}")
        except Exception as e:  # noqa: BLE001 - report and continue
            err += 1
            print(f"[fail] {filename}: {e}", file=sys.stderr)

    print(f"[done] wrote {ok}, skipped {skipped}, errors {err} "
          f"-> {AUDIO_DIR}")
    return 0 if err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
