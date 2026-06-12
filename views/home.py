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

    st.markdown('<div class="home-screen" aria-hidden="true"></div>', unsafe_allow_html=True)

    # 1) Greeting
    _render_greeting(gid, um)

    # 2) Continue Study — the visual focus of the screen.
    from utils.v2_flow_persistence import get_v2_resume_offer

    v2_offer = get_v2_resume_offer(st.session_state, prog_disk)
    snap = None if v2_offer else _detect_in_progress_snapshot(prog_disk, mx)
    if v2_offer is not None:
        _render_v2_resume_card(v2_offer)
    elif snap is not None:
        _render_resume_card(snap)
    else:
        _render_start_card(prog_disk, sett)

    # 2.5) 내 학습 기록 진입점
    _render_history_entry()

    # 3) Quick Action Cards
    _render_quick_actions()

    # 4) Simple Learning Stats
    _render_simple_stats(prog_disk, mx)


# ---------------------------------------------------------------------------
# 1) Greeting
# ---------------------------------------------------------------------------

def _render_greeting(_gid: str, _um: str) -> None:
    """Warm hello — logged-in name or guest fallback."""
    ss = st.session_state
    if ss.get("user_authenticated") and not ss.get("is_guest"):
        raw_name = str(ss.get("user_name") or "").strip()
        if not raw_name:
            email = str(ss.get("user_email") or "").strip()
            raw_name = email.split("@")[0] if email else "회원"
        hello = f"{html.escape(raw_name)}님, 안녕하세요"
        sub = "오늘도 말하면서 고쳐볼까요?"
    else:
        hello = "안녕하세요"
        sub = "로그인하면 학습 기록이 저장돼요"
    st.markdown(
        f"""
        <section class="greeting" aria-label="환영 인사">
          <h1 class="gr-hello">{hello}</h1>
          <p class="gr-sub">{html.escape(sub)}</p>
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


def _render_v2_resume_card(offer: Dict[str, Any]) -> None:
    """Home hero when a V2 mini / mock exam is saved but not forced open."""
    flow = str(offer.get("flow") or "")
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
        desc = f"목표 난이도 Lv.{diff} · 모의고사나 주제별 연습으로 이어가요"
        primary_label = "연습 시작"
        primary_nav = ("MOCK", None, False)
        secondary_label = None
        secondary_nav = None
    else:
        desc = f"5분 진단으로 난이도를 맞춘 뒤 연습을 시작해요 · 목표 Lv.{diff}"
        primary_label = "진단 시작"
        primary_nav = ("MOCK", None, False)
        secondary_label = "패턴 둘러보기"
        secondary_nav = ("PATTERN", None, False)

    st.markdown(
        f"""
        <section class="continue-card continue-card--start" role="region"
                 aria-label="학습 시작">
          <div class="cc-row-top">
            <div class="cc-eyebrow">시작하기</div>
          </div>
          <div class="cc-title">오늘의 연습 시작하기</div>
          <div class="cc-desc">{html.escape(desc)}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="home-continue-actions-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
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
# 2.5) 내 학습 기록 진입점
# ---------------------------------------------------------------------------

def _render_history_entry() -> None:
    """Slim full-width entry into the saved-history view (login handled there)."""
    st.markdown(
        """
        <section class="continue-card continue-card--start" role="region"
                 aria-label="내 학습 기록" style="margin-top:10px;">
          <div class="cc-row-top">
            <div class="cc-eyebrow">내 기록</div>
          </div>
          <div class="cc-title">지난 학습 기록 보기</div>
          <div class="cc-meta">모의고사 · 주제별 연습 · 스크립트 첨삭 결과를 다시 확인해요</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    if st.button("학습 기록 열기", use_container_width=True, key="home_open_history"):
        navigate_to("HISTORY")
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
        ("SCRIPTS", "file", "스크립트", "스마트스토어에서 구매", "qa-card--scripts"),
        ("LECTURES", "play", "강의 보기", "출제 유형 강의", "qa-card--lectures"),
        ("SCRIPT_COACHING", "chart", "스크립트 첨삭", "내 답변 등급 진단받기", "qa-card--coaching"),
    )
    st.markdown('<div class="home-section-h home-section-h--quick">빠른 실행</div>', unsafe_allow_html=True)
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
