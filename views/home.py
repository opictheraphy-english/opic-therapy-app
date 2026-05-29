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

    # 1) Greeting
    _render_greeting(gid, um)

    # 2) Continue Study — the visual focus of the screen.
    snap = _detect_in_progress_snapshot(prog_disk, mx)
    if snap is not None:
        _render_resume_card(snap)
    else:
        _render_start_card(prog_disk, sett)

    # 3) Quick Action Cards
    _render_quick_actions()

    # 4) Simple Learning Stats
    _render_simple_stats(prog_disk, mx)


# ---------------------------------------------------------------------------
# 1) Greeting
# ---------------------------------------------------------------------------

def _render_greeting(gid: str, um: str) -> None:
    """Warm, single-line hello. Profile mode shown as a soft pill chip."""
    ss = st.session_state
    if ss.get("user_authenticated") and not ss.get("is_guest"):
        name = str(ss.get("user_name") or ss.get("user_email") or "회원").strip()
        meta_html = (
            f'<div class="gr-meta"><span class="gr-meta-dot"></span>👤 {html.escape(name)}</div>'
        )
    elif ss.get("is_guest") and gid:
        meta_html = (
            '<div class="gr-meta"><span class="gr-meta-dot"></span>게스트 모드</div>'
        )
    else:
        meta_html = ""
    st.markdown(
        f"""
        <section class="greeting" aria-label="환영 인사">
          <h1 class="gr-hello">안녕하세요 <span class="gr-wave" aria-hidden="true">👋</span></h1>
          <p class="gr-sub">오늘도 꾸준히 연습해볼까요?</p>
          {meta_html}
        </section>
        """,
        unsafe_allow_html=True,
    )


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

    st.markdown(
        f"""
        <section class="continue-card continue-card--resume" role="region"
                 aria-label="모의고사 이어하기">
          <div class="cc-row-top">
            <div class="cc-eyebrow">이어하기 가능</div>
            <div class="cc-time">{html.escape(last_label)}</div>
          </div>
          <div class="cc-title">Q{completed} <span class="cc-of">/ {total}</span>까지 학습했어요</div>
          {('<div class="cc-meta">' + topic_safe + '</div>') if topic_safe else ''}
          <div class="cc-progress" aria-hidden="true">
            <span class="cc-progress-fill" style="width:{progress_pct}%"></span>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("이어하기", type="primary", use_container_width=True, key="home_resume_continue"):
            navigate_to("MOCK", mock="TEST")
            st.rerun()
    with c2:
        if st.button("처음부터 다시", use_container_width=True, key="home_resume_reset"):
            navigate_to("MOCK", mock="SURVEY", reset=True)
            st.rerun()


def _render_start_card(
    prog_disk: Dict[str, Any],
    sett: Dict[str, Any],
) -> None:
    """Card shown when nothing is mid-exam.

    Returning users: one CTA to start mock practice (no past-report shortcut).
    New users: diagnostic start + pattern browse.
    """
    card = prog_disk.get("last_activity_card") if isinstance(prog_disk, dict) else None
    has_history = isinstance(card, dict) and bool(card.get("estimated_level"))
    diff = int(sett.get("difficulty", 5))

    if has_history:
        eyebrow = "오늘의 학습"
        title = "이어서 실력을 다져볼까요?"
        sub_bits = [
            f"최근 추정 <b>{html.escape(str(card.get('estimated_level')))}</b>",
            f"목표 난이도 <b>Lv.{diff}</b>",
        ]
        sub_html = " · ".join(sub_bits)
        primary_label = "모의고사 시작"
        primary_nav = ("MOCK", None, False)
        secondary_label = None
        secondary_nav = None
    else:
        eyebrow = "환영합니다"
        title = "5분이면 첫 진단을 끝낼 수 있어요"
        sub_html = (
            "먼저 가벼운 설문으로 난이도를 정해볼게요. "
            f"목표 난이도 <b>Lv.{diff}</b>"
        )
        primary_label = "진단 시작"
        primary_nav = ("MOCK", None, False)
        secondary_label = "패턴 둘러보기"
        secondary_nav = ("PATTERN", None, False)

    st.markdown(
        f"""
        <section class="continue-card continue-card--start" role="region"
                 aria-label="학습 시작">
          <div class="cc-row-top">
            <div class="cc-eyebrow">{html.escape(eyebrow)}</div>
          </div>
          <div class="cc-title">{html.escape(title)}</div>
          <div class="cc-meta">{sub_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if secondary_nav:
        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                primary_label,
                type="primary",
                use_container_width=True,
                key="home_start_primary",
            ):
                page, mock, reset = primary_nav
                navigate_to(page, mock=mock, reset=reset)
                st.rerun()
        with c2:
            if st.button(
                secondary_label or "",
                use_container_width=True,
                key="home_start_secondary",
            ):
                page, mock, reset = secondary_nav
                navigate_to(page, mock=mock, reset=reset)
                st.rerun()
    elif st.button(
        primary_label,
        type="primary",
        use_container_width=True,
        key="home_start_primary",
    ):
        page, mock, reset = primary_nav
        navigate_to(page, mock=mock, reset=reset)
        st.rerun()


# ---------------------------------------------------------------------------
# 3) Quick Action Cards
# ---------------------------------------------------------------------------

# Tiny inline SVGs — same stroke style as the bottom-nav icons so the home
# screen feels consistent with the dock.
_QA_ICONS: Dict[str, str] = {
    "wave": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M2 12h2"/><path d="M6 8v8"/>'
        '<path d="M10 4v16"/><path d="M14 8v8"/><path d="M18 5v14"/>'
        '<path d="M22 12h2"/></svg>'
    ),
    "file": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true">'
        '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
        '<polyline points="14 2 14 8 20 8"/>'
        '<line x1="16" y1="13" x2="8" y2="13"/>'
        '<line x1="16" y1="17" x2="8" y2="17"/></svg>'
    ),
    "play": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><rect width="18" height="18" x="3" y="3" rx="3"/>'
        '<path d="m10 8 6 4-6 4V8z"/></svg>'
    ),
    "chart": (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        'aria-hidden="true"><path d="M3 3v18h18"/>'
        '<rect x="7" y="13" width="3" height="5" rx="1"/>'
        '<rect x="12" y="9" width="3" height="9" rx="1"/>'
        '<rect x="17" y="5" width="3" height="13" rx="1"/></svg>'
    ),
}


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
    # 4th tuple field = per-card modifier class for icon colour (styles.py).
    items = (
        ("PATTERN", "wave", "오늘의 패턴", "한 줄 듣고 따라하기", "qa-card--pattern"),
        ("SCRIPTS", "file", "스크립트 연습", "답변 구조 익히기", "qa-card--scripts"),
        ("LECTURES", "play", "강의 보기", "출제 유형 강의", "qa-card--lectures"),
        ("SCRIPT_COACHING", "chart", "스크립트 첨삭", "내 답변 등급 진단받기", "qa-card--coaching"),
    )
    st.markdown('<div class="home-section-h">빠른 학습</div>', unsafe_allow_html=True)
    row_a = st.columns(2, gap="small")
    row_b = st.columns(2, gap="small")
    for col, (action, ico, title, sub, variant) in zip(row_a + row_b, items):
        with col:
            st.markdown(
                f'<div class="qa-card {variant}" aria-label="{html.escape(title)}">'
                f'<span class="qa-ico">{_QA_ICONS.get(ico, "")}</span>'
                f'<span class="qa-title">{html.escape(title)}</span>'
                f'<span class="qa-sub">{html.escape(sub)}</span>'
                "</div>",
                unsafe_allow_html=True,
            )
            if action == "SCRIPT_COACHING":
                if st.button(
                    f"{title} 열기",
                    key="qa_nav_script_coaching",
                    use_container_width=True,
                ):
                    _start_script_coaching_from_home()
            elif st.button(
                f"{title} 열기",
                key=f"qa_nav_{action}",
                use_container_width=True,
            ):
                navigate_to(action)
                st.rerun()


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
    if isinstance(prog_disk, dict):
        card = prog_disk.get("last_activity_card") or {}
        if isinstance(card, dict):
            if card.get("exam_finished"):
                completed_exams = 1
            last_at = card.get("activity_at")
        last_at = last_at or prog_disk.get("updated_at")

    last_label = human_time_ago(last_at) if last_at else "—"
    q_hint = "진행 중" if questions_done else "아직 시작 전"

    st.markdown(
        f"""
        <div class="home-section-h">학습 현황</div>
        <div class="stats-row">
          <div class="stat-chip">
            <div class="st-label">응시한 문항</div>
            <div class="st-value">{questions_done}</div>
            <div class="st-hint">{q_hint}</div>
          </div>
          <div class="stat-chip">
            <div class="st-label">완료한 모의고사</div>
            <div class="st-value">{completed_exams}</div>
            <div class="st-hint">전체 회차</div>
          </div>
          <div class="stat-chip">
            <div class="st-label">마지막 학습</div>
            <div class="st-value st-value--time">{html.escape(last_label)}</div>
            <div class="st-hint">로컬 기기 기준</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
