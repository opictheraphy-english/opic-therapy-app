"""Landing page — premium clinical hero + status + features."""

from __future__ import annotations

import html

import streamlit as st

from utils.local_profile import human_time_ago, load_user_progress
from utils.recent_patterns import recent_lines_for_home
from utils.session_state import ensure_mock, ensure_settings, sync_settings_to_legacy


def render_home() -> None:
    sync_settings_to_legacy(st.session_state)
    mx = ensure_mock(st.session_state)
    sett = ensure_settings(st.session_state)
    prog_disk = load_user_progress()

    agg = mx.get("analytics_cache") or {}
    level_display = agg.get("overall_display") or mx.get("overall_estimated_level") or "—"
    n_done = len(mx.get("results") or [])
    diff = int(sett.get("difficulty", 5))
    exam_done = bool(mx.get("exam_finished"))

    gid = st.session_state.get("guest_id") or ""
    um = st.session_state.get("user_mode")
    um_label = "게스트"
    if um == "login_placeholder":
        um_label = "클라우드 연동 예정"
    profile_hint = (
        f'<p style="font-size:0.75rem;color:#94a3b8;margin:10px 0 0 0;">로컬 프로필 · {html.escape(gid)} · {um_label}</p>'
        if gid
        else ""
    )
    st.markdown(
        f"""
        <section class="home-hero">
          <div class="ds-hero-tag">OPIc Speech Therapy</div>
          <h1 class="ds-display">AI OPIc Speech Therapy</h1>
          <p class="ds-subtitle">프리미엄 발화 분석과 재활 훈련을 한 화면에서. 의료 AI 다큐멘터리 수준의 진단 경험을 목표로 합니다.</p>
          {profile_hint}
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ds-section-title">오늘의 진단 상태</div>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="home-metrics">
          <div class="metric-tile">
            <div class="metric-label">예상 레벨</div>
            <div class="metric-value">{html.escape(str(level_display))}</div>
            <div class="metric-hint">종합 리포트 기준 추정</div>
          </div>
          <div class="metric-tile">
            <div class="metric-label">진행 문항</div>
            <div class="metric-value">{n_done} / 15</div>
            <div class="metric-hint">{"세션 완료" if exam_done else "모의고사 진행 중"}</div>
          </div>
          <div class="metric-tile">
            <div class="metric-label">목표 난이도</div>
            <div class="metric-value">Lv.{diff}</div>
            <div class="metric-hint">설정에서 변경 가능</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    recent_lines = recent_lines_for_home()
    if recent_lines:
        st.markdown('<div class="ds-section-title">최근 들은 패턴</div>', unsafe_allow_html=True)
        inner = ""
        for ln in recent_lines[:10]:
            inner += f'<div class="recent-row" style="font-size:0.9rem;">🔊 {html.escape(ln)}</div>'
        st.markdown(f'<div class="recent-list">{inner}</div>', unsafe_allow_html=True)

    st.markdown('<div class="ds-section-title">핵심 기능</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="feature-grid">
        """
        + _feature_link(
            "?nav=MOCK",
            "정밀 진단",
            "실전형 모의고사와 문항별 발화 분석 리포트.",
        )
        + _feature_link(
            "?nav=PATTERN",
            "패턴 쉐도잉",
            "한 줄 듣기 · 빠른 반복 청취 (패턴 페이지).",
        )
        + _feature_link(
            "?nav=SCRIPTS",
            "개인 처방",
            "등급·문항 기반 스크립트 훈련 (점진 공개).",
        )
        + """
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="ds-section-title">최근 학습 기록</div>', unsafe_allow_html=True)
    card = prog_disk.get("last_activity_card") if isinstance(prog_disk, dict) else None
    if isinstance(card, dict) and card.get("estimated_level"):
        lvl = html.escape(str(card.get("estimated_level") or "—"))
        top = html.escape(str(card.get("topic") or "—"))
        ago = html.escape(human_time_ago(card.get("activity_at")))
        label = html.escape(str(card.get("label") or "최근 모의고사"))
        st.markdown(
            f"""
            <div class="glass-card-quiet" style="margin-bottom:14px;">
              <div style="font-size:0.7rem;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;color:#64748b;">{label}</div>
              <div style="display:flex;flex-wrap:wrap;gap:12px 24px;align-items:baseline;margin-top:10px;">
                <span style="font-size:1.5rem;font-weight:800;color:#0f172a;">{lvl}</span>
                <span style="font-size:0.95rem;color:#475569;">{top}</span>
                <span style="font-size:0.85rem;color:#94a3b8;">{ago}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    rows = mx.get("results") or []
    if rows:
        tail = rows[-5:]
        inner = ""
        for item in reversed(tail):
            qid = item.get("q_id", "—")
            topic = html.escape(str(item.get("topic") or "Topic"))
            inner += f'<div class="recent-row">Q{html.escape(str(qid))} · {topic}</div>'
        st.markdown(f'<div class="recent-list">{inner}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="recent-list"><div class="recent-empty">모의고사를 시작하면 문항 기록이 여기에 쌓입니다. 기록은 이 기기에 저장됩니다.</div></div>',
            unsafe_allow_html=True,
        )


def _feature_link(href: str, title: str, body: str) -> str:
    return f"""
        <a href="{html.escape(href, quote=True)}" style="text-decoration:none;color:inherit;display:block;">
          <div class="feature-tile">
            <div class="ft-title">{html.escape(title)}</div>
            <div class="ft-body">{html.escape(body)}</div>
          </div>
        </a>
    """
