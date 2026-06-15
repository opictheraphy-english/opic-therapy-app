"""Keyword constraint practice — deterministic transcript metrics (no AI)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence


def _coerce_expr_list(items: Any) -> List[str]:
    if not isinstance(items, (list, tuple)):
        return []
    out: List[str] = []
    for raw in items:
        s = str(raw or "").strip()
        if s:
            out.append(s)
    return out


def _coerce_target_items(items: Any) -> List[Dict[str, str]]:
    """Normalize targets: dicts with expr/ko, or legacy plain strings."""
    if not isinstance(items, (list, tuple)):
        return []
    out: List[Dict[str, str]] = []
    for raw in items:
        if isinstance(raw, dict):
            expr = str(raw.get("expr") or "").strip()
            if not expr:
                continue
            out.append({"expr": expr, "ko": str(raw.get("ko") or "").strip()})
        else:
            expr = str(raw or "").strip()
            if expr:
                out.append({"expr": expr, "ko": ""})
    return out


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip().lower())


def _is_multi_word(expr: str) -> bool:
    return bool(re.search(r"\s", str(expr or "").strip()))


def _count_substring_occurrences(text: str, phrase: str) -> int:
    norm_text = _normalize_whitespace(text)
    norm_phrase = _normalize_whitespace(phrase)
    if not norm_phrase:
        return 0
    count = 0
    start = 0
    while True:
        idx = norm_text.find(norm_phrase, start)
        if idx == -1:
            break
        count += 1
        start = idx + max(1, len(norm_phrase))
    return count


def _count_word_boundary_occurrences(text: str, word: str) -> int:
    token = str(word or "").strip().lower()
    if not token:
        return 0
    pattern = r"\b" + re.escape(token) + r"\b"
    return len(re.findall(pattern, str(text or "").lower()))


def _count_expression(text: str, expr: str, *, use_word_boundary_for_single: bool) -> int:
    if _is_multi_word(expr):
        return _count_substring_occurrences(text, expr)
    if use_word_boundary_for_single:
        return _count_word_boundary_occurrences(text, expr)
    return _count_substring_occurrences(text, expr)


def compute_keyword_constraint_metrics(
    transcript: str,
    target_expressions: Sequence[Any],
    banned_expressions: Sequence[str],
) -> Dict[str, Any]:
    """Match target/banned expressions in a transcript (case-insensitive).

    Multi-word phrases use normalized substring matching.
    Single-word banned expressions use word boundaries to avoid false positives
    (e.g. ``like`` in ``alike``).
    """
    text = str(transcript or "")
    targets_in = _coerce_target_items(target_expressions)
    banned_in = _coerce_expr_list(banned_expressions)

    targets: List[Dict[str, Any]] = []
    target_used_count = 0
    for item in targets_in:
        expr = item["expr"]
        ko = item.get("ko") or ""
        count = _count_expression(text, expr, use_word_boundary_for_single=True)
        used = count > 0
        if used:
            target_used_count += 1
        targets.append({"expr": expr, "ko": ko, "used": used, "count": count})

    banned: List[Dict[str, Any]] = []
    banned_hit_count = 0
    for expr in banned_in:
        count = _count_expression(text, expr, use_word_boundary_for_single=True)
        hit = count > 0
        if hit:
            banned_hit_count += 1
        banned.append({"expr": expr, "hit": hit, "count": count})

    return {
        "targets": targets,
        "banned": banned,
        "target_used_count": target_used_count,
        "target_total": len(targets_in),
        "banned_hit_count": banned_hit_count,
    }
