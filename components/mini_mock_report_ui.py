"""5-minute mini mock diagnostic report UI."""

from __future__ import annotations

import html
from typing import Any, Dict, List

import streamlit as st

_MM_REPORT_SCOPED_CSS = """
<style>
.mm-report-wrap { margin: 0 0 8px; }
.mm-report-hero {
  background: linear-gradient(145deg, #f0faf8 0%, #ffffff 58%);
  border: 1px solid rgba(13, 148, 136, 0.18);
  border-radius: 18px;
  padding: 22px 20px 18px;
  margin-bottom: 18px;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.06);
}
.mm-report-badge {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #0f766e;
  background: rgba(20, 184, 166, 0.12);
  border: 1px solid rgba(20, 184, 166, 0.28);
  border-radius: 999px;
  padding: 4px 10px;
  margin-bottom: 10px;
}
.mm-report-title {
  font-size: 1.45rem;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: -0.03em;
  margin: 0 0 6px;
  line-height: 1.25;
}
.mm-report-sub {
  font-size: 0.92rem;
  color: #475569;
  line-height: 1.55;
  margin: 0;
}
.mm-report-section {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
  margin: 22px 0 12px;
  letter-spacing: -0.02em;
}
.mm-metric-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 6px;
}
@media (max-width: 720px) {
  .mm-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.mm-metric-card {
  background: #fff;
  border: 1px solid rgba(13, 148, 136, 0.14);
  border-radius: 14px;
  padding: 12px 10px;
  text-align: center;
  box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
}
.mm-metric-card--level {
  background: linear-gradient(160deg, #ecfdf5 0%, #fff 100%);
  border-color: rgba(5, 150, 105, 0.22);
}
.mm-metric-value {
  font-size: 1.28rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.2;
  letter-spacing: -0.02em;
}
.mm-metric-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: #64748b;
  margin-top: 4px;
  letter-spacing: 0.02em;
}
.mm-metric-hint {
  font-size: 0.68rem;
  color: #94a3b8;
  margin-top: 2px;
}
.mm-q-card {
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 14px;
  padding: 14px 14px 12px;
  margin-bottom: 12px;
}
.mm-q-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.mm-q-title {
  font-size: 0.88rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}
.mm-status-badge {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 999px;
  background: rgba(20, 184, 166, 0.12);
  color: #0f766e;
  border: 1px solid rgba(20, 184, 166, 0.25);
}
.mm-status-badge--pending {
  background: rgba(251, 191, 36, 0.15);
  color: #b45309;
  border-color: rgba(251, 191, 36, 0.35);
}
.mm-chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.mm-chip {
  font-size: 0.72rem;
  font-weight: 600;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 4px 10px;
}
.mm-q-transcript {
  font-size: 0.86rem;
  line-height: 1.55;
  color: #334155;
  background: #f8fafc;
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
}
.mm-q-feedback {
  font-size: 0.86rem;
  line-height: 1.5;
  color: #1e293b;
  margin: 0;
}
.mm-q-correction {
  font-size: 0.8rem;
  color: #475569;
  margin-top: 6px;
}
.mm-bullet-list {
  margin: 0;
  padding-left: 1.1rem;
  color: #334155;
  font-size: 0.88rem;
  line-height: 1.55;
}
.mm-bullet-list li { margin-bottom: 6px; }
</style>
"""


def _inject_mm_report_css() -> None:
    st.markdown(_MM_REPORT_SCOPED_CSS, unsafe_allow_html=True)


def _status_badge_class(status: str) -> str:
    if status == "분석 완료":
        return "mm-status-badge"
    return "mm-status-badge mm-status-badge--pending"


def _render_metric_grid(report: Dict[str, Any]) -> None:
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    agg = report.get("aggregate_metrics") if isinstance(
        report.get("aggregate_metrics"), dict
    ) else {}
    total = int(summary.get("total_count") or report.get("total_count") or 3)
    completed = int(
        summary.get("completed_count") or report.get("completed_count") or 0
    )
    level = html.escape(str(report.get("estimated_level") or "").strip() or "—")
    level_note = html.escape(str(report.get("estimated_level_note") or "").strip())
    note_html = (
        f'<p class="mm-metric-hint">{level_note}</p>' if level_note else ""
    )

    cards = [
        (
            "level",
            level,
            "추정 레벨",
            "",
            True,
        ),
        (
            "wpm",
            html.escape(str(agg.get("avg_wpm_display") or "—")),
            "평균 WPM",
            "말하기 속도",
            False,
        ),
        (
            "words",
            html.escape(str(agg.get("avg_word_count_display") or "—")),
            "평균 단어 수",
            "답변 길이",
            False,
        ),
        (
            "filler",
            html.escape(str(agg.get("total_filler_display") or "—")),
            "필러 사용",
            "um / uh / well 등",
            False,
        ),
        (
            "done",
            html.escape(f"{completed} / {total}"),
            "분석 완료",
            "3문항 기준",
            False,
        ),
    ]
    cells = []
    for _key, value, label, hint, is_level in cards:
        cls = "mm-metric-card mm-metric-card--level" if is_level else "mm-metric-card"
        hint_html = f'<div class="mm-metric-hint">{hint}</div>' if hint else ""
        cells.append(
            f'<div class="{cls}">'
            f'<div class="mm-metric-value">{value}</div>'
            f'<div class="mm-metric-label">{html.escape(label)}</div>'
            f"{hint_html}"
            f"</div>"
        )
    st.markdown(
        f'<div class="mm-metric-grid">{"".join(cells)}</div>',
        unsafe_allow_html=True,
    )
    if note_html:
        st.markdown(note_html, unsafe_allow_html=True)


def _render_question_card(item: Dict[str, Any]) -> None:
    qn = int(item.get("question_index") or 0) + 1
    label = html.escape(str(item.get("question_label") or ""))
    status = str(item.get("status") or "—")
    status_cls = _status_badge_class(status)
    chips = [
        ("WPM", item.get("wpm_display", "—")),
        ("단어", item.get("word_count_display", "—")),
        ("문장", item.get("sentence_count_display", "—")),
        ("필러", item.get("filler_display", "—")),
        ("점수", item.get("score_display", "—")),
    ]
    chip_html = "".join(
        f'<span class="mm-chip">{html.escape(name)} {html.escape(str(val))}</span>'
        for name, val in chips
    )
    tx = str(item.get("transcript_display") or item.get("transcript_preview") or "").strip()
    stt_status = str(item.get("stt_status") or "").lower()
    transcript_html = ""
    if tx:
        transcript_html = (
            '<p class="mm-q-transcript-label">AI가 인식한 답변</p>'
            f'<div class="mm-q-transcript">{html.escape(tx)}</div>'
        )
    elif stt_status == "insufficient_response" or status == "응답 부족":
        transcript_html = (
            '<p class="mm-q-transcript-label">AI가 인식한 답변</p>'
            '<p class="mm-q-transcript mm-q-transcript--empty">응답이 충분하지 않았어요.</p>'
        )
    fb = str(item.get("short_feedback") or "").strip()
    feedback_html = ""
    if fb and status == "분석 완료":
        feedback_html = f'<p class="mm-q-feedback">{html.escape(fb)}</p>'
    corr = str(item.get("key_correction") or "").strip()
    correction_html = ""
    if corr and status == "분석 완료":
        correction_html = (
            f'<p class="mm-q-correction"><strong>핵심 교정:</strong> '
            f"{html.escape(corr)}</p>"
        )

    st.markdown(
        f"""
        <article class="mm-q-card">
          <div class="mm-q-head">
            <p class="mm-q-title">Q{qn} · {label}</p>
            <span class="{status_cls}">{html.escape(status)}</span>
          </div>
          <div class="mm-chip-row">{chip_html}</div>
          {transcript_html}
          {feedback_html}
          {correction_html}
        </article>
        """,
        unsafe_allow_html=True,
    )
    if not tx and status in ("분석 대기", "AI 분석 대기 중"):
        st.caption("분석 대기")
    elif not tx and status == "영어 답변 필요":
        st.caption("영어 답변 필요")
    elif not tx and status == "말소리 인식 불명확":
        st.caption("말소리 인식 불명확")


def _render_bullet_section(title: str, bullets: List[str], *, empty_caption: str = "") -> None:
    st.markdown(f'<p class="mm-report-section">{html.escape(title)}</p>', unsafe_allow_html=True)
    if bullets:
        items = "".join(
            f"<li>{html.escape(str(b))}</li>" for b in bullets if str(b).strip()
        )
        st.markdown(f'<ul class="mm-bullet-list">{items}</ul>', unsafe_allow_html=True)
    elif empty_caption:
        st.caption(empty_caption)


def _render_dev_metrics_debug(report: Dict[str, Any]) -> None:
    from utils.mini_mock_state import mini_mock_rows_sorted, row_result

    rows = mini_mock_rows_sorted()
    per_q = {
        int(p.get("question_index") or 0): p
        for p in (report.get("per_question") or [])
        if isinstance(p, dict)
    }

    with st.expander("Mini report raw metrics debug", expanded=False):
        for row in rows:
            q_idx = int(row.get("question_index") or 0)
            res = row_result(row)
            metrics = res.get("metrics") if isinstance(res.get("metrics"), dict) else {}
            pq = per_q.get(q_idx, {})
            st.markdown(f"**Q{q_idx + 1}** `{row.get('question_id', '')}`")
            st.json(
                {
                    "result_keys": sorted(res.keys()) if isinstance(res, dict) else [],
                    "metrics_keys": sorted(metrics.keys()),
                    "estimated_level": res.get("estimated_level"),
                    "estimated_level_display": res.get("estimated_level_display"),
                    "final_grade_score": res.get("final_grade_score"),
                    "display_wpm": pq.get("wpm_display"),
                    "display_word_count": pq.get("word_count_display"),
                    "top_level_wpm": res.get("wpm"),
                    "nested_metrics_wpm": metrics.get("wpm"),
                }
            )


def render_mini_mock_report(report: Dict[str, Any]) -> None:
    _inject_mm_report_css()
    st.markdown('<div class="mm-report-wrap">', unsafe_allow_html=True)

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

    st.markdown(
        """
        <section class="mm-report-hero" aria-label="미니 진단 리포트">
          <span class="mm-report-badge">Quick Diagnostic</span>
          <h2 class="mm-report-title">5분 진단 미니 리포트</h2>
          <p class="mm-report-sub">묘사 · 경험 · 롤플레이 3개 답변으로 현재 오픽 답변 습관을 빠르게 진단했어요.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<p class="mm-report-section">진단 요약</p>', unsafe_allow_html=True)
    _render_metric_grid(report)

    st.markdown('<p class="mm-report-section">핵심 지표</p>', unsafe_allow_html=True)
    summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
    answered = int(summary.get("answered_count") or report.get("answered_count") or 0)
    pending = int(summary.get("pending_count") or 0)
    unclear = int(summary.get("unclear_count") or 0)
    non_english = int(summary.get("non_english_count") or 0)
    total = int(summary.get("total_count") or 3)
    st.caption(
        f"답변 {answered}/{total} · 분석 대기 {pending} · "
        f"불명확 {unclear} · 영어 필요 {non_english}"
    )

    st.markdown('<p class="mm-report-section">문항별 결과</p>', unsafe_allow_html=True)
    per_q: List[Dict[str, Any]] = report.get("per_question") or []
    for item in per_q:
        if isinstance(item, dict):
            _render_question_card(item)

    _render_bullet_section("현재 강점", report.get("strengths") or [])
    _render_bullet_section(
        "바로 고치면 좋은 점",
        report.get("fix_now") or [],
        empty_caption="분석이 완료된 문항이 더 있으면 구체적인 교정 포인트가 표시돼요.",
    )
    _render_bullet_section("다음 연습 미션", report.get("missions") or [])

    learning = report.get("learning_path") or []
    _render_bullet_section(
        "추천 학습 경로",
        learning if learning else ["실전 모의고사 15문항으로 전체 답변 체력을 점검해 보세요."],
    )

    st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("show_dev_debug"):
        _render_dev_metrics_debug(report)


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
