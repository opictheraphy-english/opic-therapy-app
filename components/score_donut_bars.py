"""Score report: composite donut + semantic-colored axis bars (D layout)."""

from __future__ import annotations

import html
from typing import Any, Dict, Optional

from ui.design_tokens import BRAND_100, BRAND_500, TEXT_600, TEXT_900

_SCORE_COLOR_LOW = "#D85A30"
_SCORE_COLOR_MID = "#EF9F27"
_SCORE_COLOR_HIGH = BRAND_500
_TRACK_COLOR = BRAND_100
_DONUT_FILL = BRAND_500

_SCOPED_CSS = f"""
<style>
.sdb-card {{
  background: #fff;
  border: 0.5px solid rgba(15, 23, 42, 0.12);
  border-radius: 14px;
  padding: 16px;
  margin: 0 0 4px;
}}
.sdb-layout {{
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: 18px 20px;
}}
.sdb-donut-col {{
  flex: 0 0 92px;
  display: flex;
  justify-content: center;
}}
.sdb-bars-col {{
  flex: 1 1 200px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}}
@media (max-width: 520px) {{
  .sdb-donut-col {{
    flex: 0 0 100%;
  }}
  .sdb-bars-col {{
    flex: 0 0 100%;
  }}
}}
.sdb-donut-wrap {{
  position: relative;
  width: 92px;
  height: 92px;
}}
.sdb-donut-center {{
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}}
.sdb-donut-num {{
  font-size: 1.35rem;
  font-weight: 800;
  color: {TEXT_900};
  line-height: 1;
  letter-spacing: -0.02em;
}}
.sdb-donut-level {{
  font-size: 0.72rem;
  font-weight: 700;
  color: {TEXT_600};
  margin-top: 3px;
  letter-spacing: 0.02em;
}}
.sdb-bar-row {{
  display: grid;
  grid-template-columns: minmax(4.5rem, auto) 1fr auto;
  align-items: center;
  gap: 10px;
}}
.sdb-bar-label {{
  font-size: 0.82rem;
  font-weight: 600;
  color: {TEXT_900};
  white-space: nowrap;
}}
.sdb-bar-track {{
  height: 8px;
  background: {BRAND_100};
  border-radius: 999px;
  overflow: hidden;
}}
.sdb-bar-fill {{
  height: 100%;
  border-radius: 999px;
  min-width: 0;
  transition: width 0.2s ease;
}}
.sdb-bar-val {{
  font-size: 0.82rem;
  font-weight: 800;
  min-width: 1.75rem;
  text-align: right;
  font-variant-numeric: tabular-nums;
}}
</style>
"""


def _score_color(score: int) -> str:
    if score <= 44:
        return _SCORE_COLOR_LOW
    if score <= 64:
        return _SCORE_COLOR_MID
    return _SCORE_COLOR_HIGH


def _coerce_axis_score(value: Any) -> Optional[int]:
    if isinstance(value, dict):
        value = value.get("score")
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        return None


def _donut_svg(avg: int, *, size: int = 92) -> str:
    r = 36.0
    cx = cy = size / 2.0
    stroke = 8.0
    circumference = 2 * 3.141592653589793 * r
    pct = max(0, min(100, avg)) / 100.0
    dash = circumference * pct
    gap = max(0.0, circumference - dash)
    return (
        f'<svg class="sdb-donut-svg" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}" aria-hidden="true" role="presentation">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{_TRACK_COLOR}" '
        f'stroke-width="{stroke}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{_DONUT_FILL}" '
        f'stroke-width="{stroke}" stroke-dasharray="{dash:.2f} {gap:.2f}" '
        f'stroke-linecap="round" transform="rotate(-90 {cx} {cy})"/>'
        f"</svg>"
    )


def render_score_donut_bars_html(
    breakdown: dict,
    labels: dict[str, str],
    overall_level: str,
) -> str:
    """Return HTML for composite score donut + per-axis bars, or empty string if no data."""
    if not isinstance(breakdown, dict):
        breakdown = {}
    if not isinstance(labels, dict) or not labels:
        return ""

    level = str(overall_level or "").strip()
    has_breakdown = bool(breakdown) and any(key in breakdown for key in labels)
    if not has_breakdown and not level:
        return ""

    numeric_values: list[int] = []
    bar_rows: list[str] = []

    if has_breakdown:
        for key, label in labels.items():
            score = _coerce_axis_score(breakdown.get(key))
            if score is None:
                score = 0
            numeric_values.append(score)
            color = _score_color(score)
            bar_rows.append(
                f'<div class="sdb-bar-row">'
                f'<span class="sdb-bar-label">{html.escape(label)}</span>'
                f'<div class="sdb-bar-track">'
                f'<div class="sdb-bar-fill" style="width:{score}%;background:{color};"></div>'
                f"</div>"
                f'<span class="sdb-bar-val" style="color:{color};">{score}</span>'
                f"</div>"
            )

    avg: Optional[int] = None
    if numeric_values:
        avg = round(sum(numeric_values) / len(numeric_values))

    center_parts: list[str] = []
    if avg is not None:
        center_parts.append(f'<span class="sdb-donut-num">{avg}</span>')
    if level:
        center_parts.append(
            f'<span class="sdb-donut-level">{html.escape(level)}</span>'
        )
    center_html = "".join(center_parts)

    donut_html = ""
    if avg is not None or level:
        svg = _donut_svg(avg or 0) if avg is not None else _donut_svg(0)
        if avg is None:
            svg = (
                f'<svg class="sdb-donut-svg" width="92" height="92" '
                f'viewBox="0 0 92 92" aria-hidden="true" role="presentation">'
                f'<circle cx="46" cy="46" r="36" fill="none" stroke="{_TRACK_COLOR}" '
                f'stroke-width="8"/>'
                f"</svg>"
            )
        donut_html = (
            f'<div class="sdb-donut-col">'
            f'<div class="sdb-donut-wrap">{svg}'
            f'<div class="sdb-donut-center">{center_html}</div>'
            f"</div></div>"
        )

    bars_html = ""
    if bar_rows:
        bars_html = (
            f'<div class="sdb-bars-col">{"".join(bar_rows)}</div>'
        )

    if not donut_html and not bars_html:
        return ""

    return (
        f"{_SCOPED_CSS}"
        f'<section class="sdb-card" aria-label="점수 요약">'
        f'<div class="sdb-layout">{donut_html}{bars_html}</div>'
        f"</section>"
    )
