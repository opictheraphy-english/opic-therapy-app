"""Home — dashboard + today's goals.

Four blocks top to bottom:
  1) Greeting header (compact, no card)
  2) Progress card (donut + weekly mini chart) — real stats when logged in
  3) Today's goals card
  4) Bottom shortcuts (history · pattern · scripts)
"""

from __future__ import annotations

import html
import math
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, List, Optional

import streamlit as st

from components.navigation import navigate_to
from utils.home_stats import get_cached_home_stats

# ---------------------------------------------------------------------------
# Goals placeholders (completion wiring is a later step)
# ---------------------------------------------------------------------------

_GOALS_DONE = 1
_GOALS_TOTAL = 3

_BRAND_LINES = (
    "오늘의 처방, 한 문장이면 충분해요",
    "어색한 표현, 오늘 깔끔하게 교정해요",
    "막히던 문장도 오늘은 트일 거예요",
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

_TARGET_SVG = (
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" '
    'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
    'aria-hidden="true">'
    '<circle cx="12" cy="12" r="9" />'
    '<circle cx="12" cy="12" r="4" />'
    '<path d="M12 3v2" /><path d="M12 19v2" />'
    '<path d="M3 12h2" /><path d="M19 12h2" />'
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
        '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M12 8v4l2 2" /><path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5" />'
        "</svg>"
    ),
    "pattern": (
        '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
        'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round" aria-hidden="true">'
        '<path d="M3 12c2 -4 4 -4 6 0s4 4 6 0s4 -4 6 0s4 4 6 0" />'
        "</svg>"
    ),
    "scripts": (
        '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" '
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


def _resolve_greeting_name(ss: Any) -> tuple[str, str]:
    """Return (hello line text, raw name for initials)."""
    if ss.get("user_authenticated") and not ss.get("is_guest"):
        raw_name = str(ss.get("user_name") or "").strip()
        if not raw_name:
            email = str(ss.get("user_email") or "").strip()
            raw_name = email.split("@")[0] if email else ""
        if raw_name:
            return f"안녕하세요, {raw_name}님", raw_name
    return "안녕하세요!", ""


def _single_initial(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "O"
    for ch in name:
        if "\uac00" <= ch <= "\ud7a3":
            return ch
    return name[0].upper()


def _session_brand_line(ss: Any) -> str:
    if "home_brand_line" not in ss:
        ss["home_brand_line"] = random.choice(_BRAND_LINES)
    return str(ss["home_brand_line"])


def _is_logged_in_user(ss: Any) -> bool:
    return bool(ss.get("user_authenticated")) and not ss.get("is_guest")


def _streak_label(streak_days: int) -> str:
    if streak_days <= 0:
        return "오늘 시작해볼까요?"
    return f"{streak_days}일 연속"


def _donut_svg(
    *,
    measuring: bool,
    level: str = "",
    target: str = "",
    ring_fill_pct: int = 0,
    subtitle: str = "",
    size: int = 84,
) -> str:
    r = 36
    cx = cy = size // 2
    circ = 2 * math.pi * r
    filled = circ * max(0, min(100, ring_fill_pct)) / 100.0
    gap = circ - filled
    if measuring:
        center_text = "측정 중"
        sub_text = subtitle or "답변이 쌓이면 등급이 표시돼요"
        aria = "등급 측정 중"
    else:
        center_text = level
        sub_text = subtitle
        aria = f"{level} 추정 등급"
    return (
        f'<svg class="home-progress-donut" width="{size}" height="{size}" '
        f'viewBox="0 0 {size} {size}" role="img" aria-label="{html.escape(aria)}">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#e8f2ec" stroke-width="8" />'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#1d9e75" stroke-width="8" '
        f'stroke-linecap="round" stroke-dasharray="{filled:.2f} {gap:.2f}" '
        f'transform="rotate(-90 {cx} {cy})" />'
        f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" dominant-baseline="middle" '
        f'fill="#0f6e56" font-size="{"13" if measuring else "15"}" font-weight="600">'
        f"{html.escape(center_text)}</text>"
        f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" dominant-baseline="middle" '
        f'fill="#888780" font-size="9.5" font-weight="400">{html.escape(sub_text)}</text>'
        f"</svg>"
    )


def _week_bars_html(heights_pct: tuple[int, ...]) -> str:
    bars: List[str] = []
    for i, h in enumerate(heights_pct):
        tone = "home-week-bar--recent" if i == len(heights_pct) - 1 else ""
        empty = " home-week-bar--empty" if int(h) <= 8 else ""
        bars.append(
            f'<span class="home-week-bar {tone}{empty}" style="height:{int(h)}%" aria-hidden="true"></span>'
        )
    return f'<div class="home-week-bars" aria-hidden="true">{"".join(bars)}</div>'


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


def _render_goal_row_with_button(
    title: str,
    subtitle: str,
    *,
    button_key: str,
    button_label: str,
    on_click: Callable[[], None],
) -> None:
    """Visible action button on the right — no transparent overlay."""
    st.markdown('<div class="home-goals-interactive-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    row_col, btn_col = st.columns([5.4, 1.3], gap="small")
    with row_col:
        st.markdown(_normalize_html(_goal_row_pending_body(title, subtitle)), unsafe_allow_html=True)
    with btn_col:
        if st.button(button_label, key=button_key, use_container_width=True):
            _run_home_nav(on_click)


def _render_shortcut_with_button(
    col,
    *,
    variant: str,
    label: str,
    icon_key: str,
    button_key: str,
    button_label: str,
    on_click: Callable[[], None],
) -> None:
    with col:
        st.markdown(_normalize_html(_shortcut_card_html(variant, label, icon_key)), unsafe_allow_html=True)
        if st.button(button_label, key=button_key, use_container_width=True):
            _run_home_nav(on_click)


# ---------------------------------------------------------------------------
# Block 1 — Greeting header
# ---------------------------------------------------------------------------


def _render_greeting_header() -> None:
    ss = st.session_state
    hello_text, raw_name = _resolve_greeting_name(ss)
    initials = html.escape(_single_initial(raw_name))
    date_label = html.escape(_format_kst_date_label())
    hello_html = html.escape(hello_text)

    streak_html = ""
    if _is_logged_in_user(ss):
        stats = get_cached_home_stats(ss)
        streak_days = int((stats or {}).get("streak_days") or 0)
        streak_label = html.escape(_streak_label(streak_days))
        streak_html = (
            f'<span class="home-dash-streak" aria-label="{streak_label}">'
            f'<span class="home-dash-streak-ico">{_FLAME_SVG}</span>'
            f"<span>{streak_label}</span></span>"
        )

    html_block = (
        f'<header class="home-dash-header" role="banner">'
        f'<div class="home-dash-header-left">'
        f'<span class="home-dash-avatar" aria-hidden="true">{initials}</span>'
        f'<div class="home-dash-header-text">'
        f'<div class="home-dash-hello">{hello_html}</div>'
        f'<div class="home-dash-date">{date_label}</div>'
        f"</div></div>"
        f"{streak_html}"
        f"</header>"
    )
    st.markdown(_normalize_html(html_block), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Block 2 — Progress card
# ---------------------------------------------------------------------------


def _render_guest_stats_prompt() -> None:
    st.markdown(
        _normalize_html(
            '<section class="home-progress-card home-progress-card--guest" role="region" '
            'aria-label="학습 통계">'
            '<p class="home-guest-stats-line">로그인하면 학습 통계가 쌓여요</p>'
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
                '<section class="home-progress-card home-progress-card--loading" role="region" '
                'aria-label="학습 진행">'
                '<p class="home-guest-stats-line">통계를 불러오지 못했어요. 잠시 후 다시 확인해 주세요.</p>'
                "</section>"
            ),
            unsafe_allow_html=True,
        )
        return

    estimated = stats.get("estimated_level")
    target = str(stats.get("target_level") or "IH")
    measuring = not estimated
    if measuring:
        donut = _donut_svg(measuring=True, ring_fill_pct=0, subtitle="답변이 쌓이면 등급이 표시돼요")
    else:
        gap = int(stats.get("level_gap") or 0)
        if gap <= 0:
            sub = f"→ {target} 달성"
        elif gap == 1:
            sub = f"→ {target} 한 계단"
        elif gap == 2:
            sub = f"→ {target} 두 계단"
        else:
            sub = f"→ {target} {gap}계단"
        donut = _donut_svg(
            measuring=False,
            level=str(estimated),
            target=target,
            ring_fill_pct=int(stats.get("ring_fill_pct") or 0),
            subtitle=sub,
        )

    week_bars = _week_bars_html(tuple(stats.get("week_bar_heights_pct") or (8,) * 7))
    tagline = html.escape(str(stats.get("progress_tagline") or ""))
    week_n = int(stats.get("week_answers") or 0)
    total_n = int(stats.get("total_answers") or 0)
    stats_line = html.escape(f"이번 주 {week_n}문항 · 총 {total_n}답변")
    html_block = (
        f'<section class="home-progress-card" role="region" aria-label="학습 진행">'
        f'<div class="home-progress-card-inner">'
        f'<div class="home-progress-donut-wrap">{donut}</div>'
        f'<div class="home-progress-meta">'
        f'<div class="home-progress-tagline">{tagline}</div>'
        f"{week_bars}"
        f'<div class="home-progress-stats">{stats_line}</div>'
        f"</div></div></section>"
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
    brand = html.escape(_session_brand_line(st.session_state))
    head = (
        f'<div class="home-goals-head">'
        f'<span class="home-goals-head-left">'
        f'<span class="home-goals-target-ico">{_TARGET_SVG}</span>'
        f"<span>오늘의 목표</span></span>"
        f'<span class="home-goals-head-count">{_GOALS_DONE} / {_GOALS_TOTAL} 완료</span>'
        f"</div>"
    )
    st.markdown(_normalize_html(head), unsafe_allow_html=True)
    st.markdown(
        _normalize_html(_goal_row_done("오늘의 표현 1개 암기")),
        unsafe_allow_html=True,
    )
    _render_goal_row_with_button(
        "주제별 연습 3문항",
        "약 10분",
        button_key="home_goal_topic",
        button_label="시작 →",
        on_click=_start_topic_v2_from_home,
    )
    _render_goal_row_with_button(
        "스크립트 첨삭 1회",
        "약 5분",
        button_key="home_goal_script",
        button_label="시작 →",
        on_click=_start_script_coaching_from_home,
    )
    foot = f'<div class="home-goals-strip">{brand}</div>'
    st.markdown(_normalize_html(foot), unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Block 4 — Bottom shortcuts
# ---------------------------------------------------------------------------


def _shortcut_card_html(variant: str, label: str, icon_key: str) -> str:
    return (
        f'<div class="home-shortcut-card home-shortcut-card--{html.escape(variant)}" role="region" '
        f'aria-label="{html.escape(label)}">'
        f'<span class="home-shortcut-ico">{_SHORTCUT_ICONS[icon_key]}</span>'
        f'<span class="home-shortcut-label">{html.escape(label)}</span>'
        f"</div>"
    )


def _render_bottom_shortcuts() -> None:
    items = (
        ("history", "학습 기록", "history", "home_shortcut_history", _nav_history_from_home),
        ("pattern", "오늘의 패턴", "pattern", "home_shortcut_pattern", _nav_pattern_from_home),
        ("scripts", "스크립트", "scripts", "home_shortcut_scripts", _nav_scripts_store_from_home),
    )
    st.markdown('<div class="home-shortcuts-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    cols = st.columns(3, gap="small")
    for col, (variant, label, icon_key, button_key, on_click) in zip(cols, items):
        _render_shortcut_with_button(
            col,
            variant=variant,
            label=label,
            icon_key=icon_key,
            button_key=button_key,
            button_label="보기 →",
            on_click=on_click,
        )
