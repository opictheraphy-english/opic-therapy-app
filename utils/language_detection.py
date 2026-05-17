"""Lightweight transcript language checks (no external deps)."""

from __future__ import annotations

import re
from typing import Optional

# ``korean`` — clear Hangul in transcript
# ``possible_non_english`` — weak heuristic for other non-English scripts
LanguageMismatchKind = str


def detect_language_mismatch(text: str) -> Optional[LanguageMismatchKind]:
    """Return mismatch kind or None when text looks like English practice speech."""
    raw = (text or "").strip()
    if len(raw) < 3:
        return None

    hangul = re.findall(r"[가-힣]", raw)
    if len(hangul) >= 2:
        return "korean"

    en_words = re.findall(r"[a-zA-Z]{2,}", raw)
    if len(en_words) >= 2:
        return None

    non_ascii = sum(1 for c in raw if ord(c) > 127)
    if non_ascii >= max(3, int(len(raw) * 0.25)):
        return "possible_non_english"

    return None


def transcript_for_language_check(result: Optional[dict]) -> str:
    """Best-effort transcript text for language checks after Gemini returns."""
    if not isinstance(result, dict):
        return ""
    for key in (
        "transcript",
        "non_english_preview",
        "raw_transcript_rejected",
        "raw_transcription",
    ):
        chunk = (result.get(key) or "").strip()
        if chunk:
            return chunk
    return ""


def language_mismatch_title(kind: Optional[str]) -> str:
    if kind == "korean":
        return "영어로 답변해 주세요"
    if kind == "possible_non_english":
        return "답변 언어가 영어로 명확히 인식되지 않았어요"
    return "영어로 답변해 주세요"


def language_mismatch_body(kind: Optional[str]) -> str:
    if kind == "korean":
        return (
            "녹음은 정상적으로 저장되었지만, 답변이 영어가 아닌 언어로 인식되었어요. "
            "오픽 연습에서는 영어로 답변해야 AI 코칭을 받을 수 있어요."
        )
    if kind == "possible_non_english":
        return (
            "녹음은 저장되었지만, 답변이 영어로 명확히 인식되지 않았어요. "
            "오픽 연습에서는 영어로 답변해 주세요."
        )
    return (
        "녹음은 저장되었지만, 답변이 영어로 인식되지 않았어요. "
        "영어로 다시 답변해 주세요."
    )
