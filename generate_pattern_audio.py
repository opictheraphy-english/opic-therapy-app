#!/usr/bin/env python3
"""
Synthesize MP3s from master_patterns.json.

각 예문(examples[])마다 audio_file 이름으로 저장(병합 스키마).
레거시 단일 example 행도 지원.

  python generate_pattern_audio.py --metadata-only
  python generate_pattern_audio.py
  python generate_pattern_audio.py --force   # re-make existing files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MASTER_JSON = ROOT / "data" / "patterns" / "master_patterns.json"
AUDIO_DIR = ROOT / "assets" / "pattern_audio"


def _example_jobs(rec: dict, rec_index: int) -> list[tuple[str, str]]:
    """Return list of (english_text, audio_filename)."""
    jobs: list[tuple[str, str]] = []
    if isinstance(rec.get("examples"), list):
        for j, ex in enumerate(rec["examples"]):
            if not isinstance(ex, dict):
                continue
            en = (ex.get("en") or "").strip()
            if not en:
                continue
            af = (ex.get("audio_file") or "").strip()
            if not af:
                af = f"pattern_{rec_index:04d}_{j}.mp3"
            jobs.append((en, af))
        if jobs:
            return jobs
    ex = rec.get("example") if isinstance(rec.get("example"), dict) else {}
    en = (ex.get("en") or "").strip()
    if en:
        jobs.append((en, f"pattern_{rec_index:04d}.mp3"))
    return jobs


def main() -> int:
    parser = argparse.ArgumentParser(description="Pattern MP3 asset builder")
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

    if not MASTER_JSON.is_file():
        print(f"Missing {MASTER_JSON}", file=sys.stderr)
        return 1

    raw = json.loads(MASTER_JSON.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print("[error] master_patterns.json must be a JSON array", file=sys.stderr)
        return 1

    n_patterns = len(raw)
    jobs: list[tuple[str, str]] = []
    for i, rec in enumerate(raw, start=1):
        if isinstance(rec, dict):
            jobs.extend(_example_jobs(rec, i))

    total_mp3 = len(jobs)

    if args.metadata_only:
        print(f"[ok] patterns={n_patterns}, example_audio_jobs={total_mp3}")
        return 0

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    from services.tts_service import NEURAL2_EVA, synthesize_tts_audio

    voice_name = args.voice or NEURAL2_EVA
    ok = 0
    skipped = 0
    err = 0
    for en, af in jobs:
        out = AUDIO_DIR / af
        if out.is_file() and not args.force:
            skipped += 1
            continue
        try:
            payload = synthesize_tts_audio(
                en,
                voice_name=voice_name,
                speaking_rate=args.speaking_rate,
                pitch=args.pitch,
            )
            blob = payload.get("audio_bytes") or b""
            if not blob:
                raise RuntimeError("empty audio bytes")
            out.write_bytes(blob)
            ok += 1
            print(f"[{ok}/{total_mp3}] {af}")
        except Exception as e:
            err += 1
            print(f"[fail] {af}: {e}", file=sys.stderr)

    print(
        f"[done] wrote {ok}, skipped {skipped}, errors {err} -> {AUDIO_DIR}"
    )
    return 0 if err == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
