"""Home — dashboard + today's goals.

Four blocks top to bottom:
  1) Greeting header (compact, no card)
  2) Dark hero progress card — real stats when logged in
  3) Today's goals card
  4) Bottom shortcuts (history · pattern · scripts) in one unified card
"""

from __future__ import annotations

import html
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, List, Optional, Tuple

import streamlit as st

from components.navigation import navigate_to
from utils.home_stats import LEVEL_ORDER, get_cached_home_stats

# ---------------------------------------------------------------------------
# Goals placeholders (completion wiring is a later step)
# ---------------------------------------------------------------------------

_GOALS_DONE = 1
_GOALS_TOTAL = 3

_GREETING_SUBLINES = (
    "한 문장부터.",
    "막히던 문장, 오늘 트여요.",
    "어제보다 한 계단 위로.",
)

_KST_WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")

_FLAME_SVG = (
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 3c1 3 3 4.5 3 7.5a3 3 0 1 1 -6 0c0 -1.5 .5 -2.5 1.5 -4.5" />'
    '<path d="M12 21a6 6 0 0 0 6 -6c0 -4 -3 -6 -3 -10a6 6 0 0 0 -6 0c0 4 -3 6 -3 10a6 6 0 0 0 6 6" />'
    "</svg>"
)

_CHECK_SVG = (
    '<svg viewBox="0 0 12 12" width="11" height="11" fill="none" '
    'stroke="#ffffff" stroke-width="2" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true">'
    '<path d="M2.5 6l2.5 2.5 4.5 -5" />'
    "</svg>"
)

_SHORTCUT_ICONS = {
    "history": (
        '<svg viewBox="0 0 24 24" width="19" height="19" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12 8v4l2 2" /><path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5" />'
        "</svg>"
    ),
    "pattern": (
        '<svg viewBox="0 0 24 24" width="19" height="19" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M3 12c2 -4 4 -4 6 0s4 4 6 0s4 -4 6 0s4 4 6 0" />'
        "</svg>"
    ),
    "scripts": (
        '<svg viewBox="0 0 24 24" width="19" height="19" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M6 6h15l-1.5 9h-12z" />'
        '<path d="M6 6l-.8 -3h-2.2v15" />'
        "</svg>"
    ),
}

# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def render_home() -> None:
    st.markdown('<div class="home-screen" aria-hidden="true"></div>', unsafe_allow_html=True)
    _render_greeting_header()
    _render_progress_card()
    _render_todays_goals_card()
    _render_bottom_shortcuts()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _normalize_html(html_block: str) -> str:
    return "".join(line.strip() for line in html_block.splitlines())


def _kst_now() -> datetime:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Seoul"))
    except Exception:
        return datetime.now(timezone(timedelta(hours=9)))


def _format_kst_date_label() -> str:
    now = _kst_now()
    return f"{now.month}월 {now.day}일 {_KST_WEEKDAYS[now.weekday()]}"


def _resolve_display_name(ss: Any) -> str:
    if ss.get("user_authenticated") and not ss.get("is_guest"):
        raw_name = str(ss.get("user_name") or "").strip()
        if not raw_name:
            email = str(ss.get("user_email") or "").strip()
            raw_name = email.split("@")[0] if email else ""
        return raw_name
    return ""


def _greeting_primary_line(ss: Any) -> str:
    name = _resolve_display_name(ss)
    if name:
        return f"{name}님, 오늘도"
    return "안녕하세요,"


def _session_greeting_subline(ss: Any) -> str:
    if "home_greeting_subline" not in ss:
        ss["home_greeting_subline"] = random.choice(_GREETING_SUBLINES)
    return str(ss["home_greeting_subline"])


def _is_logged_in_user(ss: Any) -> bool:
    return bool(ss.get("user_authenticated")) and not ss.get("is_guest")


def _target_pill_label(stats: dict) -> str:
    estimated = stats.get("estimated_level")
    target = str(stats.get("target_level") or "IH")
    gap = int(stats.get("level_gap") or 0)
    if not estimated:
        return "등급 측정 중"
    if gap <= 0:
        return f"{target} 달성"
    if gap == 1:
        return f"{target}까지 한 계단"
    if gap == 2:
        return f"{target}까지 두 계단"
    return f"{target}까지 {gap}계단"


def _level_ladder_html(estimated_level: Optional[str]) -> str:
    current_idx = (
        LEVEL_ORDER.index(str(estimated_level))
        if estimated_level and str(estimated_level) in LEVEL_ORDER
        else -1
    )
    segments: List[str] = []
    for i, _lv in enumerate(LEVEL_ORDER):
        if current_idx < 0:
            cls = "home-ladder-seg--future"
        elif i < current_idx:
            cls = "home-ladder-seg--past"
        elif i == current_idx:
            cls = "home-ladder-seg--current"
        else:
            cls = "home-ladder-seg--future"
        segments.append(f'<span class="home-ladder-seg {cls}" aria-hidden="true"></span>')
    current_label = html.escape(str(estimated_level or "—"))
    return (
        f'<div class="home-ladder" role="img" aria-label="레벨 계단">'
        f'<div class="home-ladder-track">{"".join(segments)}</div>'
        f'<div class="home-ladder-labels">'
        f'<span class="home-ladder-end">NL</span>'
        f'<span class="home-ladder-current">{current_label}</span>'
        f'<span class="home-ladder-end">AL</span>'
        f"</div></div>"
    )


def _week_bar_tone(index: int, total: int) -> str:
    if total <= 1:
        return "home-hero-week-bar--mid"
    ratio = index / (total - 1)
    if ratio >= 0.85:
        return "home-hero-week-bar--bright"
    if ratio >= 0.55:
        return "home-hero-week-bar--recent"
    if ratio >= 0.25:
        return "home-hero-week-bar--mid"
    return "home-hero-week-bar--past"


def _week_bars_dark_html(daily_counts: Tuple[int, ...]) -> str:
    counts = daily_counts or (0,) * 7
    if len(counts) < 7:
        counts = tuple(list(counts) + [0] * (7 - len(counts)))
    peak = max(counts) if counts else 0
    bars: List[str] = []
    for i, n in enumerate(counts[:7]):
        if peak <= 0:
            height = 8
        else:
            height = max(8, min(26, round(8 + 18 * n / peak)))
        tone = _week_bar_tone(i, 7)
        bars.append(
            f'<span class="home-hero-week-bar {tone}" style="height:{height}px" aria-hidden="true"></span>'
        )
    return f'<div class="home-hero-week-bars" aria-hidden="true">{"".join(bars)}</div>'


def _nav_history_from_home() -> None:
    navigate_to("HISTORY")


def _nav_pattern_from_home() -> None:
    navigate_to("PATTERN")


def _nav_scripts_store_from_home() -> None:
    navigate_to("SCRIPTS")


def _start_topic_v2_from_home() -> None:
    navigate_to("MOCK", mock="TOPIC_V2")


def _start_script_coaching_from_home() -> None:
    from views.mock_exam import _clear_reset_practice_query_param, _sync_portal_mode_to_mx
    from views.script_coaching import clear_script_coaching_session
    from utils.session_state import ensure_mock

    clear_script_coaching_session()
    mx = ensure_mock(st.session_state)
    st.session_state["mock_mode"] = "script_coaching"
    st.session_state["practice_portal_selected"] = True
    st.session_state["page"] = "MOCK"
    _sync_portal_mode_to_mx(mx, "script_coaching")
    _clear_reset_practice_query_param()


def _run_home_nav(on_click: Callable[[], None], *, rerun_after: bool = True) -> None:
    on_click()
    if rerun_after:
        st.rerun()


_CARD_CHEVRON = "›"


def _goal_row_pending_body(title: str, subtitle: str) -> str:
    title_safe = html.escape(title)
    sub_safe = html.escape(subtitle)
    return (
        f'<div class="home-goals-row home-goals-row--pending">'
        f'<span class="home-goals-check home-goals-check--open" aria-hidden="true"></span>'
        f'<div class="home-goals-row-text">'
        f'<div class="home-goals-title">{title_safe}</div>'
        f'<div class="home-goals-sub">{sub_safe}</div>'
        f"</div></div>"
    )


_GOAL_ROW_CONTAINER_KEYS = {
    "home_goal_topic": "goal_row_topic",
    "home_goal_script": "goal_row_script",
}


def _render_goal_row_with_button(
    title: str,
    subtitle: str,
    *,
    button_key: str,
    on_click: Callable[[], None],
) -> None:
    """List-style goal row: check + text and quiet chevron in one keyed row container."""
    container_key = _GOAL_ROW_CONTAINER_KEYS[button_key]
    with st.container(key=container_key, gap=None):
        row_col, btn_col = st.columns([8, 2], gap="small")
        with row_col:
            st.markdown(_normalize_html(_goal_row_pending_body(title, subtitle)), unsafe_allow_html=True)
        with btn_col:
            if st.button(_CARD_CHEVRON, key=button_key, use_container_width=False):
                _run_home_nav(on_click)


def _shortcut_slot_html(variant: str, label: str, icon_key: str) -> str:
    return (
        f'<div class="home-shortcut-slot home-shortcut-slot--{html.escape(variant)}" role="group" '
        f'aria-label="{html.escape(label)}">'
        f'<span class="home-shortcut-ico">{_SHORTCUT_ICONS[icon_key]}</span>'
        f'<span class="home-shortcut-label">{html.escape(label)}</span>'
        f"</div>"
    )


# ---------------------------------------------------------------------------
# Block 1 — Greeting header
# ---------------------------------------------------------------------------


def _render_greeting_header() -> None:
    ss = st.session_state
    date_label = html.escape(_format_kst_date_label())
    primary = html.escape(_greeting_primary_line(ss))
    subline = html.escape(_session_greeting_subline(ss))

    streak_html = ""
    if _is_logged_in_user(ss):
        stats = get_cached_home_stats(ss)
        streak_days = int((stats or {}).get("streak_days") or 0)
        if streak_days > 0:
            streak_label = html.escape(f"{streak_days}일")
            streak_html = (
                f'<span class="home-dash-streak" aria-label="{streak_label} 연속">'
                f'<span class="home-dash-streak-ico">{_FLAME_SVG}</span>'
                f"<span>{streak_label}</span></span>"
            )

    html_block = (
        f'<header class="home-dash-header" role="banner">'
        f'<div class="home-dash-header-left">'
        f'<div class="home-dash-header-text">'
        f'<div class="home-dash-date">{date_label}</div>'
        f'<div class="home-dash-hello">'
        f"<span>{primary}</span>"
        f'<span class="home-dash-hello-sub">{subline}</span>'
        f"</div></div></div>"
        f"{streak_html}"
        f"</header>"
    )
    st.markdown(_normalize_html(html_block), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Block 2 — Dark hero progress card
# ---------------------------------------------------------------------------


def _render_guest_stats_prompt() -> None:
    st.markdown(
        _normalize_html(
            '<section class="home-hero-card home-hero-card--guest" role="region" '
            'aria-label="학습 통계">'
            '<p class="home-hero-guest-line">로그인하면 학습 통계가 쌓여요</p>'
            "</section>"
        ),
        unsafe_allow_html=True,
    )
    if st.button("로그인하러 가기", type="primary", use_container_width=True, key="home_go_login"):
        navigate_to("SETTINGS")
        st.rerun()


def _render_progress_card() -> None:
    ss = st.session_state
    if not _is_logged_in_user(ss):
        _render_guest_stats_prompt()
        return

    stats: Optional[dict] = get_cached_home_stats(ss)
    if not stats:
        st.markdown(
            _normalize_html(
                '<section class="home-hero-card home-hero-card--guest" role="region" '
                'aria-label="학습 진행">'
                '<p class="home-hero-guest-line">통계를 불러오지 못했어요. 잠시 후 다시 확인해 주세요.</p>'
                "</section>"
            ),
            unsafe_allow_html=True,
        )
        return

    estimated = stats.get("estimated_level")
    measuring = not estimated
    level_text = "측정 중" if measuring else html.escape(str(estimated))
    level_cls = "home-hero-level home-hero-level--measuring" if measuring else "home-hero-level"
    pill = html.escape(_target_pill_label(stats))
    ladder = _level_ladder_html(str(estimated) if estimated else None)
    week_bars = _week_bars_dark_html(tuple(stats.get("week_daily_counts") or (0,) * 7))
    week_n = int(stats.get("week_answers") or 0)
    total_n = int(stats.get("total_answers") or 0)

    html_block = (
        f'<section class="home-hero-card" role="region" aria-label="학습 진행">'
        f'<div class="home-hero-top">'
        f'<div class="home-hero-level-col">'
        f'<div class="home-hero-eyebrow">현재 레벨</div>'
        f'<div class="{level_cls}">{level_text}</div>'
        f"</div>"
        f'<div class="home-hero-pill-col">'
        f'<div class="home-hero-pill">{pill}</div>'
        f'<div class="home-hero-pill-sub">최근 10개 답변 기준</div>'
        f"</div></div>"
        f"{ladder}"
        f'<div class="home-hero-stats-row">'
        f'<div class="home-hero-stats-left">'
        f'<div class="home-hero-stats-eyebrow">이번 주</div>'
        f'<div class="home-hero-stats-main">'
        f'<span class="home-hero-stats-week">{week_n}문항</span>'
        f'<span class="home-hero-stats-total"> · 총 {total_n}답변</span>'
        f"</div></div>"
        f"{week_bars}"
        f"</div></section>"
    )
    st.markdown(_normalize_html(html_block), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Block 3 — Today's goals
# ---------------------------------------------------------------------------


def _goal_row_done(title: str) -> str:
    title_safe = html.escape(title)
    return (
        f'<div class="home-goals-row home-goals-row--done">'
        f'<span class="home-goals-check home-goals-check--done" aria-hidden="true">{_CHECK_SVG}</span>'
        f'<div class="home-goals-row-text">'
        f'<div class="home-goals-title home-goals-title--done">{title_safe}</div>'
        f"</div></div>"
    )


def _render_todays_goals_card() -> None:
    head = (
        f'<div class="home-goals-section-head">'
        f'<span class="home-goals-section-title">오늘의 목표</span>'
        f'<span class="home-goals-section-count">'
        f'<span class="home-goals-section-done">{_GOALS_DONE}</span>'
        f'<span class="home-goals-section-total"> / {_GOALS_TOTAL}</span>'
        f"</span></div>"
    )
    st.markdown(_normalize_html(head), unsafe_allow_html=True)
    with st.container(key="home_goals_card"):
        st.markdown(
            _normalize_html(_goal_row_done("오늘의 표현 1개 암기")),
            unsafe_allow_html=True,
        )
        st.markdown('<div class="home-goals-interactive-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
        _render_goal_row_with_button(
            "주제별 연습 3문항",
            "약 10분 · 매일 추천",
            button_key="home_goal_topic",
            on_click=_start_topic_v2_from_home,
        )
        _render_goal_row_with_button(
            "스크립트 첨삭 1회",
            "약 5분 · 오늘 추천",
            button_key="home_goal_script",
            on_click=_start_script_coaching_from_home,
        )


# ---------------------------------------------------------------------------
# Block 4 — Bottom shortcuts (unified card)
# ---------------------------------------------------------------------------


def _render_bottom_shortcuts() -> None:
    items = (
        ("history", "학습 기록", "history", "home_shortcut_history", _nav_history_from_home),
        ("pattern", "오늘의 패턴", "pattern", "home_shortcut_pattern", _nav_pattern_from_home),
        ("scripts", "스크립트", "scripts", "home_shortcut_scripts", _nav_scripts_store_from_home),
    )
    st.markdown('<div class="home-shortcuts-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    with st.container(key="home_shortcuts_unified"):
        cols = st.columns(3, gap="small")
        for col, (variant, label, icon_key, button_key, on_click) in zip(cols, items):
            with col:
                st.markdown(_normalize_html(_shortcut_slot_html(variant, label, icon_key)), unsafe_allow_html=True)
                if st.button(_CARD_CHEVRON, key=button_key, use_container_width=False):
                    _run_home_nav(on_click)
