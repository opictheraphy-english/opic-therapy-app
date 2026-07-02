"""
Shared AI-feedback screen HTML (topic practice; mini/real mock later).

Uses the ``.tq-screen-marker`` scope in ``ui/styles.py`` — same card tone as
the answer-saved screen (``tq-saved-*``), with an emphasized summary variant
(``tq-feedback-*``). Streamlit widgets stay in views; only chrome is HTML here.
"""

from __future__ import annotations

import html
from typing import Tuple

import streamlit as st

_ACCENT_NAMES: Tuple[str, ...] = (
    "teal",
    "blue",
    "purple",
    "pink",
    "amber",
    "coral",
)

_SPARK_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true">'
    '<path d="M12 3l1.8 4.6L18 9.4l-4.2 1.8L12 16l-1.8-4.8L6 9.4l4.2-1.8z" />'
    '<path d="M18 14l.9 2.3L21 17.2l-2.1.9L18 20l-.9-1.9L15 17.2l2.1-.9z" />'
    "</svg>"
)


def _svg(*paths: str) -> str:
    inner = "".join(paths)
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{inner}</svg>'
    )


_FB_ICONS = {
    "circle-check": _svg(
        '<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />',
        '<path d="M9 12l2 2l4 -4" />',
    ),
    "target": _svg(
        '<path d="M12 12m-1 0a1 1 0 1 0 2 0a1 1 0 1 0 -2 0" />',
        '<path d="M12 12m-5 0a5 5 0 1 0 10 0a5 5 0 1 0 -10 0" />',
        '<path d="M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0 -18 0" />',
    ),
    "edit": _svg(
        '<path d="M7 7h-1a2 2 0 0 0 -2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2 -2v-1" />',
        '<path d="M20.385 6.585a2.1 2.1 0 0 0 -2.97 -2.97l-8.415 8.385v3h3l8.385 -8.415z" />',
        '<path d="M16 5l3 3" />',
    ),
    "message-up": _svg(
        '<path d="M3 20l1.3 -3.9a9 8 0 1 1 3.4 2.9l-4.7 1" />',
        '<path d="M12 14v-4" />',
        '<path d="M10 12l2 -2l2 2" />',
    ),
    "key": _svg(
        '<path d="M16.555 3.843l3.602 3.602a2.877 2.877 0 0 1 0 4.069l-2.643 2.643a2.877 2.877 0 0 1 -4.069 0l-.301 -.301l-6.558 6.558a2 2 0 0 1 -1.239 .578l-.175 .008h-1.575a1 1 0 0 1 -.993 -.883l-.007 -.117v-1.575a2 2 0 0 1 .467 -1.284l.119 -.13l.414 -.414h2v-2h2v-2l2.144 -2.144l-.301 -.301a2.877 2.877 0 0 1 0 -4.069l2.643 -2.643a2.877 2.877 0 0 1 4.069 0z" />',
        '<path d="M15 9h.01" />',
    ),
    "flag": _svg(
        '<path d="M5 5a5 5 0 0 1 7 0a5 5 0 0 0 7 0v9a5 5 0 0 1 -7 0a5 5 0 0 0 -7 0v-9z" />',
        '<path d="M5 21v-7" />',
    ),
}


def _normalize_accent(accent: str) -> str:
    key = str(accent or "teal").strip().lower()
    if key not in _ACCENT_NAMES:
        return "teal"
    return key


def build_feedback_label_html(*, accent: str = "teal") -> str:
    """Small "AI 짧은 피드백" label row (icon box + text) + ``.tq-screen-marker``.

    Plant the screen marker here (once per feedback screen) when the header
    above did not already include it.
    """
    accent_key = html.escape(_normalize_accent(accent))
    return (
        '<div class="tq-feedback-label-row">'
        f'<span class="tq-feedback-label-ico tq-feedback-label-ico--{accent_key}">'
        f"{_SPARK_SVG}"
        f"</span>"
        f'<span class="tq-feedback-label-text">AI 짧은 피드백</span>'
        f"</div>"
    )


def build_feedback_summary_html(
    summary: str,
    *,
    accent: str = "teal",
    answer_level: str = "",
    answer_level_missing: bool = False,
) -> str:
    """Emphasized one-line summary card (accent-tinted background + border)."""
    accent_key = html.escape(_normalize_accent(accent))
    text = html.escape(str(summary or "").strip())
    level = html.escape(str(answer_level or "").strip())
    pill = ""
    scope = ""
    if level:
        pill = f'<span class="tq-feedback-summary-level-pill">{level}</span>'
        scope = '<p class="tq-feedback-summary-scope">이 답변 기준</p>'
    elif answer_level_missing:
        from services.topic_practice_v2_analysis import ANSWER_LEVEL_MISSING_LABEL

        hint = html.escape(ANSWER_LEVEL_MISSING_LABEL)
        pill = (
            f'<span class="tq-feedback-summary-level-pill '
            f'tq-feedback-summary-level-pill--missing">{hint}</span>'
        )
        scope = '<p class="tq-feedback-summary-scope">재요청 시 표시될 수 있어요</p>'
    return (
        f'<div class="tq-feedback-summary tq-feedback-summary--{accent_key}" '
        f'role="region" aria-label="한 줄 총평">'
        f'<div class="tq-feedback-summary-head">'
        f'<span class="tq-feedback-summary-label">한 줄 총평</span>'
        f"{pill}"
        f"</div>"
        f"{scope}"
        f'<p class="tq-feedback-summary-text">{text}</p>'
        f"</div>"
    )


def build_feedback_section_card_html(
    label: str,
    body: str,
    *,
    accent: str = "teal",
    icon: str = "circle-check",
    filled: bool = False,
) -> str:
    """One feedback section card (icon + label + body). ``filled`` tints the bg."""
    accent_key = html.escape(_normalize_accent(accent))
    svg = _FB_ICONS.get(icon, _FB_ICONS["circle-check"])
    filled_cls = " tq-feedback-section--filled" if filled else ""
    text = html.escape(str(body or "").strip())
    return (
        f'<div class="tq-feedback-section tq-feedback-section--{accent_key}{filled_cls}" '
        f'role="region" aria-label="{html.escape(label)}">'
        f'<div class="tq-feedback-section-head">'
        f'<span class="tq-feedback-section-ico tq-feedback-section-ico--{accent_key}">'
        f"{svg}</span>"
        f'<span class="tq-feedback-section-label">{html.escape(label)}</span>'
        f"</div>"
        f'<p class="tq-feedback-section-body">{text}</p>'
        f"</div>"
    )


def build_feedback_keyword_chips_html(
    keywords,
    *,
    accent: str = "teal",
    empty_message: str = "",
) -> str:
    """Filled card with pill chips for ``keyword_drill`` (hint if empty)."""
    accent_key = html.escape(_normalize_accent(accent))
    svg = _FB_ICONS["key"]
    clean = [str(w or "").strip() for w in (keywords or []) if str(w or "").strip()]
    if clean:
        chips = "".join(
            f'<span class="tq-feedback-chip tq-feedback-chip--{accent_key}">'
            f"{html.escape(w)}</span>"
            for w in clean
        )
        body = f'<div class="tq-feedback-chips">{chips}</div>'
    else:
        hint = str(empty_message or "").strip()
        if hint:
            body = f'<p class="tq-feedback-section-body">{html.escape(hint)}</p>'
        else:
            body = '<p class="tq-feedback-section-body">—</p>'
    return (
        f'<div class="tq-feedback-section tq-feedback-section--{accent_key} '
        f'tq-feedback-section--filled" role="region" aria-label="다시 말하기 키워드">'
        f'<div class="tq-feedback-section-head">'
        f'<span class="tq-feedback-section-ico tq-feedback-section-ico--{accent_key}">'
        f"{svg}</span>"
        f'<span class="tq-feedback-section-label">다시 말하기 키워드</span>'
        f"</div>"
        f"{body}"
        f"</div>"
    )


def render_feedback_label(*, accent: str = "teal") -> None:
    st.markdown(build_feedback_label_html(accent=accent), unsafe_allow_html=True)


def render_feedback_section_card(
    label: str,
    body: str,
    *,
    accent: str = "teal",
    icon: str = "circle-check",
    filled: bool = False,
) -> None:
    st.markdown(
        build_feedback_section_card_html(
            label, body, accent=accent, icon=icon, filled=filled
        ),
        unsafe_allow_html=True,
    )


def render_feedback_keyword_chips(
    keywords,
    *,
    accent: str = "teal",
    empty_message: str = "",
) -> None:
    st.markdown(
        build_feedback_keyword_chips_html(
            keywords,
            accent=accent,
            empty_message=empty_message,
        ),
        unsafe_allow_html=True,
    )


def render_feedback_summary(
    summary: str,
    *,
    accent: str = "teal",
    answer_level: str = "",
    answer_level_missing: bool = False,
) -> None:
    st.markdown(
        build_feedback_summary_html(
            summary,
            accent=accent,
            answer_level=answer_level,
            answer_level_missing=answer_level_missing,
        ),
        unsafe_allow_html=True,
    )


def build_keyword_constraint_feedback_label_html() -> str:
    return (
        '<div class="tq-feedback-label-row">'
        f'<span class="tq-feedback-label-ico tq-feedback-label-ico--teal">'
        f"{_SPARK_SVG}"
        f"</span>"
        f'<span class="tq-feedback-label-text">키워드 표현 피드백</span>'
        f"</div>"
    )


def build_keyword_constraint_checklist_html(fb: dict) -> str:
    """Checklist for target/banned/pattern results (separate from keyword_drill chips)."""
    targets = fb.get("targets") if isinstance(fb.get("targets"), list) else []
    banned = fb.get("banned") if isinstance(fb.get("banned"), list) else []
    target_used = int(fb.get("target_used_count") or 0)
    target_total = int(fb.get("target_total") or len(targets))
    banned_hit_count = int(fb.get("banned_hit_count") or 0)
    patterns_used = bool(fb.get("patterns_used"))
    pattern_quote = html.escape(str(fb.get("pattern_quote") or "").strip())

    target_rows: list[str] = []
    for row in targets:
        if not isinstance(row, dict):
            continue
        expr = html.escape(str(row.get("expr") or "").strip())
        ko = html.escape(str(row.get("ko") or "").strip())
        ko_html = (
            f'<span class="tq-kc-result-ko">{ko}</span>' if ko else ""
        )
        used = bool(row.get("used"))
        if used:
            mark = "✓"
            cls = "tq-kc-result-row--ok"
            meta = f"{int(row.get('count') or 1)}회"
        else:
            mark = "—"
            cls = "tq-kc-result-row--miss"
            meta = "미사용"
        target_rows.append(
            f'<li class="tq-kc-result-row {cls}">'
            f'<span class="tq-kc-result-mark">{mark}</span>'
            f'<span class="tq-kc-result-expr">{expr}{ko_html}</span>'
            f'<span class="tq-kc-result-meta">{meta}</span>'
            f"</li>"
        )
    target_list = (
        f'<ul class="tq-kc-result-list">{"".join(target_rows)}</ul>'
        if target_rows
        else '<p class="tq-kc-result-empty">—</p>'
    )

    banned_rows: list[str] = []
    for row in banned:
        if not isinstance(row, dict) or not row.get("hit"):
            continue
        expr = html.escape(str(row.get("expr") or "").strip())
        count = int(row.get("count") or 0)
        banned_rows.append(
            f'<li class="tq-kc-result-row tq-kc-result-row--warn">'
            f'<span class="tq-kc-result-mark">⚠</span>'
            f'<span class="tq-kc-result-expr">{expr}</span>'
            f'<span class="tq-kc-result-meta">{count}회</span>'
            f"</li>"
        )
    if banned_rows:
        banned_section = f'<ul class="tq-kc-result-list">{"".join(banned_rows)}</ul>'
    else:
        banned_section = '<p class="tq-kc-result-clear">금지 표현 안 씀 ✓</p>'

    if patterns_used:
        pattern_mark = "✓"
        pattern_cls = "tq-kc-result-row--pattern-ok"
        pattern_meta = "사용"
    else:
        pattern_mark = "—"
        pattern_cls = "tq-kc-result-row--miss"
        pattern_meta = "안 씀"
    pattern_quote_block = ""
    if patterns_used and pattern_quote:
        pattern_quote_block = (
            f'<p class="tq-kc-result-quote">“{pattern_quote}”</p>'
        )

    naturalness = html.escape(str(fb.get("naturalness_note") or "").strip())
    naturalness_block = ""
    if naturalness:
        naturalness_block = (
            f'<p class="tq-kc-result-note">{naturalness}</p>'
        )

    return (
        '<div class="tq-kc-result-panel" role="region" aria-label="키워드 표현 체크리스트">'
        '<div class="tq-kc-result-block tq-kc-result-block--target">'
        '<div class="tq-kc-result-head">'
        '<span class="tq-kc-result-title">목표 표현</span>'
        f'<span class="tq-kc-result-score">{target_used}/{target_total} 사용</span>'
        "</div>"
        f"{target_list}"
        "</div>"
        '<div class="tq-kc-result-block tq-kc-result-block--banned">'
        '<div class="tq-kc-result-head">'
        '<span class="tq-kc-result-title">금지 표현</span>'
        f'<span class="tq-kc-result-score">{banned_hit_count}건 위반</span>'
        "</div>"
        f"{banned_section}"
        "</div>"
        '<div class="tq-kc-result-block tq-kc-result-block--pattern">'
        '<div class="tq-kc-result-head">'
        '<span class="tq-kc-result-title">확장 패턴</span>'
        f'<span class="tq-kc-result-score">{pattern_meta}</span>'
        "</div>"
        f'<div class="tq-kc-result-row {pattern_cls}">'
        f'<span class="tq-kc-result-mark">{pattern_mark}</span>'
        f'<span class="tq-kc-result-expr">AI 판정</span>'
        "</div>"
        f"{pattern_quote_block}"
        f"{naturalness_block}"
        "</div>"
        "</div>"
        "<style>"
        ".tq-kc-result-panel{display:flex;flex-direction:column;gap:10px;margin:0 0 14px 0;}"
        ".tq-kc-result-block{border-radius:12px;padding:12px 14px;border:0.5px solid transparent;}"
        ".tq-kc-result-block--target{background:#ecfdf5;border-color:#99f6e4;}"
        ".tq-kc-result-block--banned{background:#fff7ed;border-color:#fdba74;}"
        ".tq-kc-result-block--pattern{background:#f5f3ff;border-color:#c4b5fd;}"
        ".tq-kc-result-head{display:flex;justify-content:space-between;align-items:center;"
        "gap:8px;margin:0 0 8px 0;}"
        ".tq-kc-result-title{font-size:12px;font-weight:700;color:#334155;}"
        ".tq-kc-result-block--target .tq-kc-result-title{color:#0f766e;}"
        ".tq-kc-result-block--banned .tq-kc-result-title{color:#c2410c;}"
        ".tq-kc-result-block--pattern .tq-kc-result-title{color:#5b21b6;}"
        ".tq-kc-result-score{font-size:12px;font-weight:600;color:#64748b;}"
        ".tq-kc-result-list{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:6px;}"
        ".tq-kc-result-row{display:flex;align-items:center;gap:8px;font-size:13px;}"
        ".tq-kc-result-mark{width:18px;font-weight:700;flex-shrink:0;}"
        ".tq-kc-result-expr{flex:1;font-weight:600;color:#0f172a;}"
        ".tq-kc-result-ko{margin-left:6px;font-size:12px;font-weight:500;color:#94a3b8;}"
        ".tq-kc-result-meta{font-size:12px;color:#64748b;}"
        ".tq-kc-result-row--ok .tq-kc-result-mark{color:#0f766e;}"
        ".tq-kc-result-row--miss .tq-kc-result-mark{color:#94a3b8;}"
        ".tq-kc-result-row--warn .tq-kc-result-mark{color:#c2410c;}"
        ".tq-kc-result-row--pattern-ok .tq-kc-result-mark{color:#5b21b6;}"
        ".tq-kc-result-clear{margin:0;font-size:13px;font-weight:600;color:#0f766e;}"
        ".tq-kc-result-empty,.tq-kc-result-note,.tq-kc-result-quote{margin:6px 0 0 0;"
        "font-size:13px;color:#475569;}"
        ".tq-kc-result-quote{font-style:italic;color:#5b21b6;}"
        "</style>"
    )


def render_keyword_constraint_feedback(fb: dict, *, accent: str = "teal") -> None:
    """Keyword-constraint result screen (checklist + summary/coaching cards)."""
    summary = str(fb.get("summary") or "").strip() or "키워드 표현 결과를 확인해 보세요."
    coaching = str(fb.get("coaching") or "").strip() or "목표 표현을 자연스럽게 녹여 다시 말해 보세요."

    st.markdown(build_keyword_constraint_feedback_label_html(), unsafe_allow_html=True)
    render_feedback_summary(summary, accent=accent)
    st.markdown(build_keyword_constraint_checklist_html(fb), unsafe_allow_html=True)
    render_feedback_section_card(
        "코칭 한 줄",
        coaching,
        accent="amber",
        icon="flag",
        filled=True,
    )
