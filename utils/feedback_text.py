"""Normalize LLM markdown for premium feedback cards (render-only)."""

from __future__ import annotations

import html
import re
from typing import List, Optional, Tuple

_BRACKET_LABEL = re.compile(r"^\s*\[[A-Za-z0-9\-]+\]\s*", re.MULTILINE)
_HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_SCORE_TAIL = re.compile(
    r"^(?P<label>.+?)\s*(?:[·•|]\s*)?(?:평균\s*)?(?P<score>\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)
_EN_SNIPPET = re.compile(r"^[A-Za-z][A-Za-z\s,'\-]{12,}$")


def strip_bracket_labels(text: str) -> str:
    """Remove developer bracket labels like ``[A]``, ``[D-ii]``."""
    return _BRACKET_LABEL.sub("", str(text or "")).strip()


def normalize_feedback_md(text: str) -> str:
    """Strip dev labels and demote markdown headings to plain inline text."""
    raw = strip_bracket_labels(text)
    if not raw:
        return ""

    def _demote_heading(match: re.Match[str]) -> str:
        title = match.group(2).strip()
        return title

    out = _HEADING.sub(_demote_heading, raw)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _inline_md_to_html(segment: str) -> str:
    """Escape HTML then apply light inline markdown (bold only)."""
    escaped = html.escape(segment)

    def _bold(m: re.Match[str]) -> str:
        return f"<strong>{html.escape(m.group(1))}</strong>"

    return _BOLD.sub(_bold, escaped)


def normalize_feedback_md_html(text: str) -> str:
    """Return safe HTML: no h1–h6; headings become styled spans."""
    raw = strip_bracket_labels(text)
    if not raw:
        return ""

    parts: List[str] = []
    last = 0
    for match in _HEADING.finditer(raw):
        if match.start() > last:
            chunk = raw[last : match.start()].strip()
            if chunk:
                parts.append(_paragraphs_html(chunk))
        title = match.group(2).strip()
        if title:
            parts.append(
                f'<span class="eqfd-md-label">{html.escape(title)}</span>'
            )
        last = match.end()
    tail = raw[last:].strip()
    if tail:
        parts.append(_paragraphs_html(tail))
    if not parts:
        return _paragraphs_html(raw)
    return "".join(parts)


def _paragraphs_html(text: str) -> str:
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if not blocks:
        return _inline_md_to_html(text).replace("\n", "<br/>")
    return "".join(
        f'<p class="eqfd-md-p">{_inline_md_to_html(b).replace(chr(10), "<br/>")}</p>'
        for b in blocks
    )


def parse_weakness_bullet(text: str) -> Tuple[str, Optional[float], str]:
    """Split weakness bullet into label, optional score, and auxiliary English line."""
    line = str(text or "").strip()
    if not line:
        return "", None, ""

    m = _SCORE_TAIL.match(line)
    if m:
        label = m.group("label").strip().rstrip("·•|")
        try:
            score = float(m.group("score"))
        except (TypeError, ValueError):
            score = None
        return label, score, ""

    if _EN_SNIPPET.match(line):
        return "", None, line

    return line, None, ""


def split_improved_answer_and_mission(text: str) -> Tuple[str, List[str]]:
    """Separate model answer from embedded next-mission copy."""
    raw = normalize_feedback_md(text)
    if not raw:
        return "", []

    markers = (
        "다음 답변 미션",
        "바로 다음 연습",
        "다음 연습에",
    )
    answer = raw
    missions: List[str] = []
    for marker in markers:
        idx = raw.find(marker)
        if idx >= 0:
            answer = raw[:idx].strip()
            tail = raw[idx:].strip()
            for line in tail.splitlines():
                line = line.strip()
                if not line:
                    continue
                if any(line.startswith(m) for m in markers):
                    continue
                line = re.sub(r"^[\d]+[\.\)]\s*", "", line)
                line = re.sub(r"^[-•*]\s*", "", line)
                if line:
                    missions.append(line)
            break
    return answer, missions


def parse_prescription_sections(text: str) -> dict:
    """Parse Eric prescription into body, structure line, and connector chips."""
    raw = normalize_feedback_md(text)
    if not raw:
        return {"body": "", "structure": "", "connectors": []}

    body_lines: List[str] = []
    structure = ""
    connectors: List[str] = []

    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        lower = line.lower()
        if "순서" in line and "구조" in line:
            structure = line.split(":", 1)[-1].strip() if ":" in line else line
            continue
        if "연결어" in line:
            part = line.split(":", 1)[-1].strip() if ":" in line else line
            connectors = [
                c.strip()
                for c in re.split(r"[,，、]", part)
                if c.strip() and len(c.strip()) < 40
            ]
            continue
        if "개선 우선순위" in line:
            body_lines.append(line)
            continue
        if lower.startswith("recommend") or "추천 연결어" in line:
            part = line.split(":", 1)[-1].strip() if ":" in line else line
            connectors.extend(
                c.strip()
                for c in re.split(r"[,，、]", part)
                if c.strip() and len(c.strip()) < 40
            )
            continue
        body_lines.append(line)

    return {
        "body": "\n".join(body_lines).strip() or raw,
        "structure": structure,
        "connectors": connectors[:8],
    }
