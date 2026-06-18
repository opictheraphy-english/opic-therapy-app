"""Home — premium mobile learning dashboard.

Visual-only redesign (Step 2). Four sections, every section is a single,
cleanly bounded block of HTML so the screen feels app-like rather than
admin-y:

  1) Greeting           — warm hello, no marketing copy.
  2) Continue Study     — the screen's visual focus. Two states:
                            • resume an in-progress mock exam, or
                            • start a new mock exam from the hero card.
  3) Quick Actions      — 4 compact cards that fan out to the main tabs.
  4) Simple Stats       — 3 honest, derived numbers (no new tracking).

Routing uses ``navigate_to`` + ``st.button`` (same tab); query params stay in sync.
"""

from __future__ import annotations

import html
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import streamlit as st

from components.navigation import navigate_to
from utils.exam_state import (
    count_completed_exam_prefix,
    has_resumable_exam,
    reconcile_mock_exam_pointer,
)
from utils.local_profile import human_time_ago, load_user_progress
from utils.session_state import ensure_mock, ensure_settings, sync_settings_to_legacy


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_home() -> None:
    sync_settings_to_legacy(st.session_state)
    mx = ensure_mock(st.session_state)
    if mx.get("current_exam"):
        reconcile_mock_exam_pointer(mx)
    sett = ensure_settings(st.session_state)
    prog_disk = load_user_progress()

    gid = st.session_state.get("guest_id") or ""
    um = st.session_state.get("user_mode") or ""

    st.markdown('<div class="home-screen" aria-hidden="true"></div>', unsafe_allow_html=True)

    # 1) Greeting
    _render_greeting(gid, um, sett)

    # 2) Continue Study — the visual focus of the screen.
    from utils.v2_flow_persistence import get_v2_resume_offer

    v2_offer = get_v2_resume_offer(st.session_state, prog_disk)
    snap = None if v2_offer else _detect_in_progress_snapshot(prog_disk, mx)
    show_start_hero = v2_offer is None and snap is None
    if v2_offer is not None:
        _render_v2_resume_card(v2_offer)
    elif snap is not None:
        _render_resume_card(snap)

    _emit_home_card_grid_marker()
    if show_start_hero:
        _render_start_card(prog_disk, sett)

    # 2.5) 내 학습 기록 진입점
    _render_history_entry()

    # 3) Quick Action Cards
    _render_quick_actions()

    # 4) Simple Learning Stats
    _render_simple_stats(prog_disk, mx)


# ---------------------------------------------------------------------------
# 1) Greeting — design B
# ---------------------------------------------------------------------------

_GREETING_LINES = (
    "오늘의 처방, 한 문장이면 충분해요",
    "어색한 표현, 오늘 깔끔하게 교정해요",
    "막히던 문장도 오늘은 트일 거예요",
)

_KST_WEEKDAYS = ("월", "화", "수", "목", "금", "토", "일")

_GREETING_CALENDAR_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
    'aria-hidden="true"><path d="M4 7a2 2 0 0 1 2 -2h12a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-12a2 2 0 0 1 -2 -2l0 -12" />'
    '<path d="M16 3l0 4" /><path d="M8 3l0 4" /><path d="M4 11l16 0" /></svg>'
)


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
    """Return (hello line HTML-safe text, raw name for initials)."""
    if ss.get("user_authenticated") and not ss.get("is_guest"):
        raw_name = str(ss.get("user_name") or "").strip()
        if not raw_name:
            email = str(ss.get("user_email") or "").strip()
            raw_name = email.split("@")[0] if email else "회원"
        return raw_name, raw_name
    return "안녕하세요", ""


def _initials_from_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "O"
    for ch in name:
        if "\uac00" <= ch <= "\ud7a3":
            return ch
    parts = name.split()
    if len(parts) >= 2:
        a = parts[0][:1]
        b = parts[1][:1]
        if a and b:
            return f"{a}{b}".upper()
    if len(name) >= 2:
        return name[:2].upper()
    return name[:1].upper()


def _greeting_brand_line(ss: Any) -> str:
    if "greeting_line" not in ss:
        ss["greeting_line"] = random.choice(_GREETING_LINES)
    return str(ss["greeting_line"])


def _render_greeting(_gid: str, _um: str, sett: Dict[str, Any]) -> None:
    """Design B — avatar + date + hello + brand line + target level chip."""
    ss = st.session_state
    hello_text, raw_name = _resolve_greeting_name(ss)
    if raw_name:
        hello_html = f"{html.escape(raw_name)}님, 안녕하세요"
    else:
        hello_html = html.escape(hello_text)
    initials = html.escape(_initials_from_name(raw_name))
    date_label = html.escape(_format_kst_date_label())
    brand_line = html.escape(_greeting_brand_line(ss))
    target_level = int(sett.get("difficulty", 5) or 5)
    html_block = (
        f'<section class="greeting-card" role="region" aria-label="환영 인사">'
        f'<span class="greeting-avatar" aria-hidden="true">{initials}</span>'
        f'<div class="greeting-body">'
        f'<div class="greeting-date">'
        f'<span class="greeting-date-icon">{_GREETING_CALENDAR_SVG}</span>'
        f'<span class="greeting-date-text">{date_label}</span>'
        f"</div>"
        f'<div class="greeting-hello">{hello_html}</div>'
        f'<div class="greeting-brand">{brand_line}</div>'
        f"</div>"
        f'<span class="greeting-chip">목표 Lv.{target_level}</span>'
        f"</section>"
    )
    html_block = "".join(line.strip() for line in html_block.splitlines())
    st.markdown(html_block, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# 2) Continue Study Card
# ---------------------------------------------------------------------------

def _detect_in_progress_snapshot(
    prog_disk: Optional[Dict[str, Any]],
    mx: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Pick the freshest non-empty mid-exam state between in-memory + disk.

    Prefers the live ``mx`` because it represents the user's most recent
    action — disk is only flushed at the end of a rerun and may lag by
    one event during fast back-to-back navigation. Falls back to the
    on-disk ``mock_snapshot`` when ``mx`` has been freshly reset
    (e.g. brand-new Streamlit session before the eager disk-restore
    in ``app.py`` runs — though that path is also covered now). Returns
    ``None`` when there is nothing to resume.

    The "is this resumable?" check is delegated to
    :func:`utils.exam_state.has_resumable_exam` so home, mock view, and
    router never disagree on whether to surface the resume CTA.
    """
    if isinstance(mx, dict) and has_resumable_exam(mx):
        return {
            k: mx.get(k)
            for k in (
                "current_exam",
                "current_idx",
                "results",
                "exam_finished",
                "mock_page",
                "exam_started_at",
                "exam_last_seen_at",
            )
        }

    if isinstance(prog_disk, dict):
        snap = prog_disk.get("mock_snapshot")
        if isinstance(snap, dict) and has_resumable_exam(snap):
            return dict(snap)

    return None


def _render_v2_resume_card(offer: Dict[str, Any]) -> None:
    """Home hero when a V2 mini / mock / topic exam is saved but not forced open."""
    flow = str(offer.get("flow") or "")
    if flow == "topic_v2":
        label = "주제별 연습 이어서 풀기"
        desc_raw = str(offer.get("question_label") or "").strip()
        if not desc_raw:
            practice_label = str(offer.get("practice_label") or "").strip()
            current = int(offer.get("current_display") or 1)
            total = int(offer.get("total") or 0)
            desc_raw = (
                f"{practice_label} · {current}/{total}문항"
                if practice_label
                else f"{current}/{total}문항"
            )
        desc = html.escape(desc_raw)
        title_html = html.escape(label)
        st.markdown(
            f"""
        <section class="continue-card continue-card--resume" role="region"
                 aria-label="주제별 연습 이어하기">
          <div class="cc-row-top">
            <div class="cc-eyebrow">이어하기</div>
          </div>
          <div class="cc-title">{title_html}</div>
          <div class="cc-desc">{desc}</div>
        </section>
        """,
            unsafe_allow_html=True,
        )
    else:
        label = html.escape(str(offer.get("label") or "모의고사"))
        completed = int(offer.get("completed") or 0)
        total = int(offer.get("total") or 0)
        q_label = html.escape(str(offer.get("question_label") or ""))

        desc = q_label if q_label else "저장된 답변을 이어서 풀 수 있어요"
        st.markdown(
            f"""
        <section class="continue-card continue-card--resume" role="region"
                 aria-label="모의고사 이어하기">
          <div class="cc-row-top">
            <div class="cc-eyebrow">이어하기</div>
          </div>
          <div class="cc-title">{label} <span class="cc-muted-num">{completed}/{total}</span></div>
          <div class="cc-desc">{desc}</div>
        </section>
        """,
            unsafe_allow_html=True,
        )
    st.markdown('<div class="home-continue-actions-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    if st.button("이어서 풀기", type="primary", use_container_width=True, key=f"home_v2_resume_{flow}"):
        from utils.v2_flow_persistence import resume_v2_flow

        resume_v2_flow(st.session_state, flow=flow)
        if flow == "mini_mock_v2":
            navigate_to("MOCK", mock="MINI_MOCK")
        elif flow == "topic_v2":
            navigate_to("MOCK", mock="TOPIC_V2")
        else:
            navigate_to("MOCK", mock="PICK")
        st.rerun()


def _render_resume_card(snap: Dict[str, Any]) -> None:
    """Premium mint hero card — resume mid-exam."""
    exam = snap.get("current_exam") or []
    total = len(exam)
    completed = count_completed_exam_prefix(snap)
    idx_next = min(max(completed, 0), max(total - 1, 0)) if total else 0
    last_seen = snap.get("exam_last_seen_at") or snap.get("exam_started_at")
    last_label = human_time_ago(last_seen) if last_seen else "방금 전"

    topic = ""
    try:
        if exam and completed < total:
            topic = str(exam[idx_next].get("topic") or "")
        elif exam:
            topic = str(exam[-1].get("topic") or "")
    except Exception:
        topic = ""
    topic_safe = html.escape(topic) if topic else ""

    progress_pct = max(0, min(100, int(round((completed / total) * 100)))) if total else 0
    desc = topic_safe if topic_safe else "저장된 답변부터 이어서 풀 수 있어요"

    st.markdown(
        f"""
        <section class="continue-card continue-card--resume" role="region"
                 aria-label="모의고사 이어하기">
          <div class="cc-row-top">
            <div class="cc-eyebrow">이어하기</div>
            <div class="cc-time">{html.escape(last_label)}</div>
          </div>
          <div class="cc-title">실전 모의고사 <span class="cc-muted-num">{completed}/{total}</span></div>
          <div class="cc-desc">{desc}</div>
          <div class="cc-progress" aria-hidden="true">
            <span class="cc-progress-fill" style="width:{progress_pct}%"></span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="home-continue-actions-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("이어서 풀기", type="primary", use_container_width=True, key="home_resume_continue"):
            navigate_to("MOCK", mock="TEST")
            st.rerun()
    with c2:
        if st.button("새로 시작", use_container_width=True, key="home_resume_reset"):
            navigate_to("MOCK", mock="SURVEY", reset=True)
            st.rerun()


_HOME_CHEVRON_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="9 6 15 12 9 18"></polyline></svg>'
)

_HOME_CARD_ICONS: Dict[str, str] = {
    "player-play": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M7 4v16l13 -8z" /></svg>'
    ),
    "history": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M12 8l0 4l2 2" />'
        '<path d="M3.05 11a9 9 0 1 1 .5 4m-.5 5v-5h5" /></svg>'
    ),
    "wave-sine": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M3 12c2 -4 4 -4 6 0s4 4 6 0s4 -4 6 0s4 4 6 0" /></svg>'
    ),
    "shopping-bag": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M6.331 8h11.339a2 2 0 0 1 1.977 2.304l-1.255 8.152a3 3 0 0 1 -2.966 2.544h-6.852a3 3 0 0 1 -2.965 -2.544l-1.255 -8.152a2 2 0 0 1 1.977 -2.304" />'
        '<path d="M9 11v-5a3 3 0 0 1 6 0v5" /></svg>'
    ),
    "pencil-check": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M4 20h4l10.5 -10.5a2.828 2.828 0 1 0 -4 -4l-10.5 10.5v4" />'
        '<path d="M13.5 6.5l4 4" /><path d="M15 19l2 2l4 -4" /></svg>'
    ),
}


def _normalize_home_card_html(html_block: str) -> str:
    return "".join(line.strip() for line in html_block.splitlines())


def _emit_home_card_grid_marker() -> None:
    st.markdown(
        '<div class="home-card-grid-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )


def _render_home_design_a_card(
    *,
    variant: str,
    aria_label: str,
    title: str,
    sub: str,
    icon: str,
    compact: bool = False,
) -> None:
    """Home design-A card (transparent overlay tap target follows in st.button)."""
    icon_svg = _HOME_CARD_ICONS.get(icon, "")
    compact_cls = " mx-portal-card--compact" if compact else ""
    html_block = (
        f'<div class="mx-portal-card mx-portal-card--{html.escape(variant)}{compact_cls}" role="region" '
        f'aria-label="{html.escape(aria_label)}">'
        f'<span class="mx-portal-card-accent" aria-hidden="true"></span>'
        f'<span class="mx-portal-card-ico">{icon_svg}</span>'
        f'<div class="mx-portal-card-body">'
        f'<div class="mx-portal-card-title-row">'
        f'<span class="mx-portal-card-title">{html.escape(title)}</span>'
        f"</div>"
        f'<span class="mx-portal-card-sub">{html.escape(sub)}</span>'
        f"</div>"
        f'<span class="mx-portal-card-chevron" aria-hidden="true">{_HOME_CHEVRON_SVG}</span>'
        f"</div>"
    )
    st.markdown(_normalize_home_card_html(html_block), unsafe_allow_html=True)


def _render_home_overlay_card_in_col(
    col,
    *,
    variant: str,
    aria_label: str,
    title: str,
    sub: str,
    icon: str,
    button_label: str,
    button_key: str,
    on_click,
    compact: bool = False,
    rerun_after: bool = True,
) -> None:
    """Design-A card + transparent overlay button in one column (portal pattern)."""
    with col:
        _render_home_design_a_card(
            variant=variant,
            aria_label=aria_label,
            title=title,
            sub=sub,
            icon=icon,
            compact=compact,
        )
        if st.button(button_label, use_container_width=True, key=button_key):
            on_click()
            if rerun_after:
                st.rerun()


def _render_home_overlay_card(
    *,
    variant: str,
    aria_label: str,
    title: str,
    sub: str,
    icon: str,
    button_label: str,
    button_key: str,
    on_click,
    compact: bool = False,
    rerun_after: bool = True,
) -> None:
    """Full-width design-A card + overlay (single column)."""
    col, = st.columns(1)
    _render_home_overlay_card_in_col(
        col,
        variant=variant,
        aria_label=aria_label,
        title=title,
        sub=sub,
        icon=icon,
        button_label=button_label,
        button_key=button_key,
        on_click=on_click,
        compact=compact,
        rerun_after=rerun_after,
    )


def _render_start_card(
    prog_disk: Dict[str, Any],
    sett: Dict[str, Any],
) -> None:
    """Card shown when nothing is mid-exam."""
    card = prog_disk.get("last_activity_card") if isinstance(prog_disk, dict) else None
    has_history = isinstance(card, dict) and bool(card.get("estimated_level"))
    diff = int(sett.get("difficulty", 5))

    if has_history:
        desc = f"목표 난이도 Lv.{diff} · 모의고사나 주제별 연습으로 이어가요"
    else:
        desc = f"5분 진단으로 난이도를 맞춘 뒤 연습을 시작해요 · 목표 Lv.{diff}"

    _render_home_overlay_card(
        variant="home-start",
        aria_label="학습 시작",
        title="오늘의 연습 시작하기",
        sub=desc,
        icon="player-play",
        button_label="오늘의 연습 시작하기",
        button_key="home_start_primary",
        on_click=lambda: navigate_to("MOCK"),
    )


# ---------------------------------------------------------------------------
# 2.5) 내 학습 기록 진입점
# ---------------------------------------------------------------------------

def _render_history_entry() -> None:
    """Slim full-width entry into the saved-history view (login handled there)."""
    _render_home_overlay_card(
        variant="home-history",
        aria_label="내 학습 기록",
        title="지난 학습 기록 보기",
        sub="모의고사 · 주제별 · 첨삭 결과 다시 보기",
        icon="history",
        button_label="지난 학습 기록 보기",
        button_key="home_open_history",
        on_click=lambda: navigate_to("HISTORY"),
    )


# ---------------------------------------------------------------------------
# 3) Quick Action Cards
# ---------------------------------------------------------------------------


def _start_script_coaching_from_home() -> None:
    """Home quick action → MOCK tab, script_coaching mode (skip learning portal)."""
    from views.mock_exam import _clear_reset_practice_query_param, _sync_portal_mode_to_mx
    from views.script_coaching import clear_script_coaching_session

    clear_script_coaching_session()
    mx = ensure_mock(st.session_state)
    st.session_state["mock_mode"] = "script_coaching"
    st.session_state["practice_portal_selected"] = True
    st.session_state["page"] = "MOCK"
    _sync_portal_mode_to_mx(mx, "script_coaching")
    _clear_reset_practice_query_param()
    st.rerun()


def _render_quick_actions() -> None:
    items = (
        ("home-quick-pattern", "wave-sine", "오늘의 패턴", "한 줄 듣고 따라하기", "qa_nav_PATTERN", lambda: navigate_to("PATTERN"), True),
        ("home-quick-scripts", "shopping-bag", "스크립트", "스마트스토어에서 구매", "qa_nav_SCRIPTS", lambda: navigate_to("SCRIPTS"), True),
        ("home-quick-lectures", "player-play", "강의 보기", "출제 유형 강의", "qa_nav_LECTURES", lambda: navigate_to("LECTURES"), True),
        ("home-quick-coaching", "pencil-check", "스크립트 첨삭", "내 답변 등급 진단받기", "qa_nav_script_coaching", _start_script_coaching_from_home, False),
    )
    st.markdown('<div class="home-section-h home-section-h--quick">빠른 실행</div>', unsafe_allow_html=True)
    row_a = st.columns(2, gap="small")
    row_b = st.columns(2, gap="small")
    for col, (variant, icon, title, sub, button_key, on_click, rerun_after) in zip(
        row_a + row_b, items
    ):
        _render_home_overlay_card_in_col(
            col,
            variant=variant,
            aria_label=title,
            title=title,
            sub=sub,
            icon=icon,
            button_label=title,
            button_key=button_key,
            on_click=on_click,
            compact=True,
            rerun_after=rerun_after,
        )


# ---------------------------------------------------------------------------
# 4) Simple Learning Stats
# ---------------------------------------------------------------------------

def _render_simple_stats(prog_disk: Dict[str, Any], mx: Dict[str, Any]) -> None:
    """Three honest, derived numbers. No new tracking introduced."""
    results = mx.get("results") or []
    questions_done = (
        count_completed_exam_prefix(mx)
        if isinstance(mx, dict) and mx.get("current_exam")
        else len(results)
    )

    completed_exams = 0
    last_at: Optional[str] = None
    estimated_level = ""
    if isinstance(prog_disk, dict):
        card = prog_disk.get("last_activity_card") or {}
        if isinstance(card, dict):
            if card.get("exam_finished"):
                completed_exams = 1
            last_at = card.get("activity_at")
            estimated_level = str(card.get("estimated_level") or "").strip()
        last_at = last_at or prog_disk.get("updated_at")

    last_label = human_time_ago(last_at) if last_at else "—"
    level_cls = "st-value st-value--level" if estimated_level else "st-value"
    level_value = html.escape(estimated_level) if estimated_level else "—"
    q_value = str(questions_done) if questions_done > 0 else "—"
    exam_value = str(completed_exams) if completed_exams > 0 else "—"

    st.markdown(
        f"""
        <div class="home-section-h home-section-h--stats">학습 통계</div>
        <div class="stats-row">
          <div class="stat-chip">
            <div class="st-label">추정 등급</div>
            <div class="{level_cls}">{level_value}</div>
          </div>
          <div class="stat-chip">
            <div class="st-label">응시한 문항</div>
            <div class="st-value">{q_value}</div>
          </div>
          <div class="stat-chip">
            <div class="st-label">마지막 학습</div>
            <div class="st-value st-value--time">{html.escape(last_label)}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
