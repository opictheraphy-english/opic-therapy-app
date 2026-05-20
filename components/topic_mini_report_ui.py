"""Topic practice — saved confirmation, loading, and full AI report UI."""

from __future__ import annotations

import html
from typing import Any, Dict, List

import streamlit as st

from components.smart_feedback import render_alternative_expressions, render_grammar_corrections
from utils.daily_ai_usage import format_daily_ai_usage_label


def render_topic_answer_saved_card(*, q_idx: int, audio_len: int, is_last: bool) -> None:
    st.markdown(
        f"""
        <section class="continue-card continue-card--resume mx-landing-card" role="status">
          <div class="cc-eyebrow">저장 완료</div>
          <div class="cc-title">답변이 저장되었어요</div>
          <div class="cc-meta">좋아요. 지금은 흐름을 끊지 않고 다음 질문으로 넘어갈게요.<br/>
            3문항을 모두 끝낸 뒤 AI 풀 리포트를 받을 수 있어요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="mx-record-saved">녹음 저장됨 · {audio_len:,} bytes</p>',
        unsafe_allow_html=True,
    )
    if is_last:
        st.caption("세 번째 답변까지 저장되면 AI 풀 리포트를 받을 수 있어요.")


def render_topic_all_saved_card(topic_title: str) -> None:
    st.markdown(
        f"""
        <section class="continue-card continue-card--start mx-landing-card" role="region">
          <div class="cc-eyebrow">저장 완료</div>
          <div class="cc-title">3개 답변이 모두 저장되었어요</div>
          <div class="cc-meta">「{html.escape(topic_title)}」 주제로 말한 3개 답변을 안전하게 보관했어요.<br/>
            이제 AI가 3개 답변을 한 번에 분석해 주제별 풀 리포트를 만들어드릴게요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    usage_label = format_daily_ai_usage_label()
    if usage_label:
        st.markdown(
            f'<p class="mx-daily-usage">{html.escape(usage_label)}</p>',
            unsafe_allow_html=True,
        )


def render_topic_report_pending_retry_screen(
    *,
    saved_count: int = 3,
    is_quota: bool = False,
) -> None:
    if is_quota:
        _tp_pending_title = "AI 분석 요청이 잠시 많아요"
        _tp_pending_body = (
            "3개 답변은 모두 안전하게 저장되어 있습니다.<br/>"
            "현재 AI 분석 요청이 많아 리포트 생성이 잠시 지연되고 있어요.<br/>"
            "잠시 후 다시 분석을 눌러 주제별 리포트를 받아보세요."
        )
    else:
        _tp_pending_title = "AI 분석을 다시 시도해야 해요"
        _tp_pending_body = (
            "3개 답변은 모두 안전하게 저장되어 있습니다.<br/>"
            "현재 AI 분석 요청이 정상적으로 완료되지 않았어요.<br/>"
            "잠시 후 다시 분석을 눌러 풀 리포트를 받아보세요."
        )
    st.markdown(
        f"""
        <section class="recovery-card" role="alert" aria-live="polite">
          <div class="rv-eyebrow">AI 분석</div>
          <div class="rv-title">{html.escape(_tp_pending_title)}</div>
          <div class="rv-body">{_tp_pending_body}</div>
          <div class="rv-meta"><span>저장된 답변 {int(saved_count)}개</span></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_topic_mini_report(report: Dict[str, Any]) -> None:
    title = html.escape(str(report.get("topic_title") or "주제"))
    st.markdown(
        f"""
        <section class="mx-mode-intro" role="region" aria-label="주제별 풀 리포트">
          <h2 class="mx-mode-title">주제별 풀 리포트</h2>
          <p class="mx-mode-subtitle">방금 말한 3개 답변을 바탕으로 AI가 정리했어요.</p>
          <p class="tp-mini-topic">주제 · {title}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    restored = report.get("restored_transcripts") or []
    if restored:
        st.markdown("##### AI가 인식한 답변")
        for item in restored:
            if not isinstance(item, dict):
                continue
            lbl = html.escape(str(item.get("question_label") or "Q?"))
            tr = str(item.get("transcript") or "").strip()
            st.markdown(f"**{lbl}**")
            if tr:
                st.markdown(f'<p class="mx-tp-transcript">{html.escape(tr)}</p>', unsafe_allow_html=True)
            else:
                st.markdown(
                    '<p class="mx-tp-transcript mx-tp-transcript--empty">'
                    "응답이 충분하지 않았어요."
                    "</p>",
                    unsafe_allow_html=True,
                )

    flow = str(report.get("overall_flow_summary") or report.get("flow_summary") or "")
    st.markdown("##### 전체 흐름 총평")
    st.markdown(html.escape(flow))

    st.markdown("##### 가장 좋았던 점")
    for bullet in report.get("strengths") or []:
        st.markdown(f"- {html.escape(str(bullet))}")

    grammar = report.get("grammar_corrections") or []
    st.markdown("##### 바로 고치면 좋은 문법")
    render_grammar_corrections(
        "",
        hits=grammar,
        show_heading=False,
        empty_message="이번 세 답변에서 눈에 띄는 문법 슬립은 많지 않았어요.",
    )

    expressions = report.get("expression_upgrades") or []
    st.markdown("##### 표현 업그레이드")
    render_alternative_expressions(
        "",
        hits=expressions,
        show_heading=False,
        empty_message="표현을 한 단계 올릴 만한 포인트를 찾지 못했어요.",
    )

    structure_fb = report.get("structure_feedback")
    st.markdown("##### 답변 구조 피드백")
    if isinstance(structure_fb, dict):
        for g in structure_fb.get("good") or []:
            st.markdown(f"- 잘한 점: {html.escape(str(g))}")
        for m in structure_fb.get("missing") or []:
            st.markdown(f"- 보완: {html.escape(str(m))}")
        nxt = str(structure_fb.get("next") or "").strip()
        if nxt:
            st.markdown(f"- 다음: {html.escape(nxt)}")
    else:
        for mission in report.get("structure_missions") or []:
            st.markdown(f"- {html.escape(str(mission))}")

    st.markdown("##### 다시 말하기 추천 문장")
    improved = report.get("improved_sentences") or []
    if improved:
        for item in improved:
            if isinstance(item, dict):
                lbl = html.escape(str(item.get("question_label") or ""))
                sent = html.escape(str(item.get("sentence") or ""))
                if sent:
                    st.markdown(f"**{lbl}** {sent}")
    else:
        for i, sent in enumerate(report.get("retry_sentences") or [], start=1):
            st.markdown(f"{i}. {html.escape(str(sent))}")

    st.markdown("##### 다음 연습 미션")
    missions = report.get("missions") or report.get("structure_missions") or []
    for mission in missions:
        st.markdown(f"- {html.escape(str(mission))}")
