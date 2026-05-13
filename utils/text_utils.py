"""Text helpers for coaching / overlap detection."""

from __future__ import annotations

import re
from typing import Set

PRECISION_MAP = {
    "good": "beneficial / high-quality / compelling",
    "like": "prefer / enjoy / appreciate",
    "table": "dining table / work desk / surface",
    "nice": "pleasant / impressive / polished",
    "happy": "satisfied / delighted / fulfilled",
}
DISCOURSE_MARKERS = [
    "First of all",
    "To begin with",
    "As it turned out",
    "In the end",
    "Looking back",
    "Furthermore",
    "Consequently",
]
STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "i",
    "you",
    "he",
    "she",
    "it",
    "we",
    "they",
    "to",
    "of",
    "in",
    "on",
    "for",
    "and",
    "but",
    "so",
    "this",
    "that",
    "with",
    "my",
    "your",
    "our",
}


def keywords(text: str) -> Set[str]:
    tokens = re.findall(r"[a-zA-Z']+", (text or "").lower())
    return {t for t in tokens if len(t) > 3 and t not in STOPWORDS}


def build_pronunciation_prescription(target_text: str, heard_text: str) -> str:
    target_words = re.findall(r"[a-zA-Z']+", (target_text or "").lower())
    heard_words = re.findall(r"[a-zA-Z']+", (heard_text or "").lower())
    if not target_words:
        return "타깃 문장이 비어 있어 발화 비교를 진행할 수 없습니다."
    if not heard_words:
        return "복원 텍스트가 비어 있습니다. 마이크 볼륨과 발화 길이를 늘려 다시 연습하세요."

    target_set = set(target_words)
    heard_set = set(heard_words)
    missing = [w for w in target_words if w not in heard_set]
    extra = [w for w in heard_words if w not in target_set]

    pronounce_hints = []
    for tw in target_words:
        if len(tw) < 5:
            continue
        for hw in heard_words:
            if len(hw) == len(tw) and hw[1:] == tw[1:] and hw[0] != tw[0]:
                pronounce_hints.append((tw, hw))
                break

    if pronounce_hints:
        t, h = pronounce_hints[0]
        return (
            f'"{t}"를 "{h}"처럼 들리게 발음했습니다. '
            "입술-혀 시작 위치를 먼저 고정하고 첫 소리를 또렷하게 내세요."
        )
    if missing:
        return (
            f'핵심 단어 "{missing[0]}"가 복원 텍스트에서 빠졌습니다. '
            "문장 첫 3단어를 천천히 분절해 말한 뒤 속도를 올리세요."
        )
    if extra:
        return (
            f'"{extra[0]}"처럼 타깃에 없는 소리가 섞였습니다. '
            "강세를 줄이고 문장 리듬을 일정하게 유지해 보세요."
        )
    return "발음 정확도와 억양 흐름이 안정적입니다. 문장 끝 억양만 조금 더 부드럽게 마무리해 보세요."
