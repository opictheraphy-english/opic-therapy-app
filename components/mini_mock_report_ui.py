"""5-minute mini mock diagnostic report UI."""

from __future__ import annotations

import html
from typing import Any, Dict, List

import streamlit as st


def render_mini_mock_report(report: Dict[str, Any]) -> None:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    answered = int(summary.get("answered_count") or report.get("answered_count") or 0)
    completed = int(summary.get("completed_count") or 0)
    pending = int(summary.get("pending_count") or 0)
    unclear = int(summary.get("unclear_count") or 0)
    non_english = int(summary.get("non_english_count") or 0)
    total = int(summary.get("total_count") or 3)

    st.markdown(
        """
        <section class="mx-mode-intro" role="region" aria-label="미니 진단 리포트">
          <h2 class="mx-mode-title">5분 진단 미니 리포트</h2>
          <p class="mx-mode-subtitle">묘사, 경험, 롤플레이 3개 답변을 바탕으로 현재 답변 습관을 빠르게 진단했어요.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if report.get("has_pending"):
        st.markdown(
            """
            <section class="recovery-card" role="alert" aria-live="polite">
              <div class="rv-eyebrow">AI 분석</div>
              <div class="rv-title">일부 문항은 AI 분석이 지연되고 있어요</div>
              <div class="rv-body">분석 완료된 문항을 기준으로 먼저 리포트를 보여드릴게요.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    level = html.escape(str(report.get("estimated_level") or "").strip())
    level_note = html.escape(str(report.get("estimated_level_note") or "").strip())
    level_line = level if level else "—"
    if level_note:
        level_line = f"{level_line}<br/><span class='cc-meta'>{level_note}</span>"

    st.markdown(
        f"""
        <section class="continue-card continue-card--start mx-landing-card" role="region"
                 aria-label="진단 요약">
          <div class="cc-eyebrow">진단 요약</div>
          <div class="cc-title">답변 {answered} / {total}</div>
          <div class="cc-meta">분석 완료 {completed} · 분석 대기 {pending} · 불명확 {unclear} · 영어 필요 {non_english}</div>
          <p class="mx-rh-eyebrow" style="margin-top:12px;">추정 레벨</p>
          <div class="mx-rh-title">{level_line}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### 문항별 결과")
    per_q: List[Dict[str, Any]] = report.get("per_question") or []
    for item in per_q:
        if not isinstance(item, dict):
            continue
        qn = int(item.get("question_index") or 0) + 1
        label = html.escape(str(item.get("question_label") or ""))
        status = html.escape(str(item.get("status") or "—"))
        st.markdown(
            f'<p class="mx-rh-eyebrow">Q{qn} · {label}</p>'
            f'<p><strong>{status}</strong></p>',
            unsafe_allow_html=True,
        )
        tx = str(item.get("transcript_preview") or "").strip()
        if tx:
            st.markdown(
                f'<div class="mx-rh-transcript">{html.escape(tx)}</div>',
                unsafe_allow_html=True,
            )
        elif status == "AI 분석 대기 중":
            st.caption("AI 분석 대기 중")
        elif status == "영어 답변 필요":
            st.caption("영어 답변 필요")
        elif status == "말소리 인식 불명확":
            st.caption("말소리 인식 불명확")
        fb = str(item.get("short_feedback") or "").strip()
        if fb and status == "분석 완료":
            st.markdown(html.escape(fb))
        corr = str(item.get("key_correction") or "").strip()
        if corr and status == "분석 완료":
            st.markdown(f"**핵심 교정:** {html.escape(corr)}")

    st.markdown("##### 현재 강점")
    for bullet in report.get("strengths") or []:
        st.markdown(f"- {html.escape(str(bullet))}")

    st.markdown("##### 바로 고치면 좋은 점")
    fix_now = report.get("fix_now") or []
    if fix_now:
        for bullet in fix_now:
            st.markdown(f"- {html.escape(str(bullet))}")
    else:
        st.caption("분석이 완료된 문항이 더 있으면 구체적인 교정 포인트가 표시돼요.")

    st.markdown("##### 다음 연습 미션")
    for mission in report.get("missions") or []:
        st.markdown(f"- {html.escape(str(mission))}")

    st.markdown("##### 추천 학습 경로")


def render_mini_mock_report_download(
    report: Dict[str, Any],
    results: list[dict],
) -> None:
    from services.feedback.mini_mock_report import build_mini_mock_report_markdown

    markdown = build_mini_mock_report_markdown(report, results)
    st.download_button(
        label="리포트 다운로드",
        data=markdown,
        file_name="opic_mini_diagnostic_report.md",
        mime="text/markdown",
        key="mm_report_download_md",
        use_container_width=True,
    )


def render_mini_mock_report_actions(*, on_retry_pending: bool = False) -> None:
    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "주제별 답변 연습으로",
            type="primary",
            use_container_width=True,
            key="mm_report_goto_topic",
        ):
            from utils.session_state import mock_session

            st.session_state["mock_mode"] = "topic_practice"
            st.session_state["practice_portal_selected"] = True
            st.session_state["topic_practice_step"] = "select_topic"
            st.session_state["selected_topic_id"] = None
            st.session_state["topic_practice_question_index"] = 0
            st.session_state["mini_mock_completed"] = False
            st.session_state["mock_page"] = "TOPIC"
            mx = mock_session()
            mx["mock_mode"] = "topic_practice"
            mx["mock_page"] = "TOPIC"
            st.rerun()
    with c2:
        if st.button(
            "실전 모의고사 도전",
            use_container_width=True,
            key="mm_report_goto_real",
        ):
            from utils.session_state import mock_session

            st.session_state["mock_mode"] = "real_mock"
            st.session_state["practice_portal_selected"] = True
            st.session_state["mini_mock_completed"] = False
            st.session_state["mock_page"] = "SURVEY"
            mx = mock_session()
            mx["mock_mode"] = "real_mock"
            mx["mock_page"] = "SURVEY"
            st.rerun()

    if on_retry_pending:
        if st.button(
            "분석 대기 문항 다시 시도",
            use_container_width=True,
            key="mm_report_retry_pending",
        ):
            st.session_state["_mm_retry_pending"] = True
            st.rerun()
