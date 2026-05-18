"""Final report preview card — display only, no API calls."""

from __future__ import annotations

import html
from typing import Any, Dict, List

import streamlit as st


def render_final_report_preview_card(preview: Dict[str, Any]) -> None:
    """Mint preview card for real-mock completion screen."""
    total = int(preview.get("total_count") or 15)
    answered = int(preview.get("answered_count") or 0)
    completed = int(preview.get("completed_count") or 0)
    pending = int(preview.get("pending_count") or 0)
    unclear = int(preview.get("unclear_count") or 0)
    non_english = int(preview.get("non_english_count") or 0)
    insights: List[str] = list(preview.get("preview_insights") or [])

    rows_html = (
        f'<li><span class="mx-frp-label">답변 완료</span>'
        f'<span class="mx-frp-val">{answered}/{total}</span></li>'
        f'<li><span class="mx-frp-label">AI 분석 완료</span>'
        f'<span class="mx-frp-val">{completed}/{total}</span></li>'
        f'<li><span class="mx-frp-label">분석 대기</span>'
        f'<span class="mx-frp-val">{pending}개</span></li>'
        f'<li><span class="mx-frp-label">음성 확인 필요</span>'
        f'<span class="mx-frp-val">{unclear}개</span></li>'
        f'<li><span class="mx-frp-label">영어 답변 필요</span>'
        f'<span class="mx-frp-val">{non_english}개</span></li>'
    )

    if insights:
        insight_items = "".join(
            f'<li>{html.escape(str(line))}</li>' for line in insights[:3]
        )
        insights_block = f"""
          <p class="mx-frp-insights-title">미리 보는 코칭 포인트</p>
          <ol class="mx-frp-insights">{insight_items}</ol>
        """
    else:
        insights_block = """
          <p class="mx-frp-insights-note">아직 분석이 충분히 완료되지 않았어요.<br/>
            그래도 저장된 답변 기준으로 최종 리포트를 먼저 확인할 수 있어요.</p>
        """

    pending_note = ""
    if pending > 0:
        pending_note = (
            '<p class="mx-frp-pending">일부 문항은 AI 분석 대기 중입니다. '
            "분석이 완료된 답변을 기준으로 리포트를 먼저 보여드릴게요.</p>"
        )

    st.markdown(
        f"""
        <section class="mx-fr-preview" role="region" aria-label="최종 리포트 미리보기">
          <p class="mx-frp-eyebrow">최종 리포트 미리보기</p>
          <ul class="mx-frp-stats">{rows_html}</ul>
          {pending_note}
          {insights_block}
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_real_mock_progress_chip(
    *,
    current_q: int,
    total_q: int,
    answered_count: int,
    completed_count: int,
) -> None:
    """Compact in-exam progress strip (real mock only)."""
    st.markdown(
        f"""
        <section class="mx-fr-progress" role="status" aria-label="실전 모의고사 진행률">
          <p class="mx-fr-progress-title">실전 모의고사 진행률</p>
          <p class="mx-fr-progress-line">Q{int(current_q)} / {int(total_q)}</p>
          <p class="mx-fr-progress-meta">답변 저장 {int(answered_count)}개 · AI 분석 완료 {int(completed_count)}개</p>
        </section>
        """,
        unsafe_allow_html=True,
    )
