"""Mock V2 comprehensive final report — legacy final-report layout and evaluation axes."""

from __future__ import annotations

import html
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.collapsible_section import render_collapsible_section
from components.coaching_experience import render_structured_coaching_report
from components.topbar import render_top_bar
from services.exam_analytics import (
    detect_risk_flags,
    exam_results_summary_stats,
    result_display_status,
    result_is_no_speech_row,
    summary_rows_for_table,
)
from services.exam_analytics import compute_exam_aggregates
from services.new_final_report_data import (
    _MOCK_BREAKDOWN_KEYS,
    build_mock_v2_final_bundle,
    merge_report_into_aggregates,
)
from utils.streamlit_ui import clean_visible_label
from utils.text_utils import (
    DISCOURSE_MARKERS,
    NO_SPEECH_EMPTY_TEXT,
    is_real_speech_transcript,
)

try:
    from services.pdf_report import build_exam_pdf, pdf_export_available
except ImportError:

    def pdf_export_available() -> bool:
        return False

    def build_exam_pdf(*_a, **_kw):  # type: ignore[misc]
        return None

logger = logging.getLogger(__name__)

_KEY_BUNDLE = "mock_v2_new_final_bundle"
_KEY_SIG = "mock_v2_new_final_sig"
_KEY_PDF = "mock_v2_new_final_pdf_bytes"

_REPORT_CSS = """
<style>
.final-hero {
  text-align: center;
  padding: 2rem 1rem 1.5rem;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  margin-bottom: 1.25rem;
}
.final-hero h1 {
  font-size: 2.15rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 0.35rem 0;
  letter-spacing: -0.02em;
}
.final-hero .sub {
  color: #475569;
  font-size: 1rem;
}
.final-level {
  font-size: 2.6rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0.5rem 0 0.25rem;
}
.final-confidence {
  color: #0f766e;
  font-weight: 600;
  font-size: 1.05rem;
}
.final-note {
  color: #334155;
  max-width: 720px;
  margin: 0.75rem auto 0;
  line-height: 1.55;
}
.section-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 1.25rem 1.35rem;
  margin-bottom: 1.1rem;
  box-shadow: 0 8px 24px rgba(15,23,42,0.05);
}
.mono-tx {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 0.88rem;
  background: #0f172a08;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: anywhere;
}
</style>
"""

_MOCK_SCORE_LABELS = {
    "response_amount": "답변량",
    "relevance": "질문 적합도",
    "structure": "답변 구조",
    "grammar": "문법",
    "vocabulary": "어휘",
    "naturalness": "자연스러움",
}


def _bundle_signature(
    report: Dict[str, Any],
    answers: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
) -> tuple:
    aid = tuple(
        sorted(
            (int(a.get("question_index", -1)), str(a.get("answer_id") or ""))
            for a in answers
            if isinstance(a, dict)
        )
    )
    return (
        bool(report.get("ok")),
        str(report.get("overall_level") or ""),
        str(report.get("summary") or "")[:80],
        len(answers),
        len(questions),
        aid,
    )


def _results_signature(
    report: Dict[str, Any],
    results: List[Dict[str, Any]],
) -> tuple:
    qids = tuple(int(r.get("q_id") or 0) for r in results if isinstance(r, dict))
    return (
        bool(report.get("ok")),
        str(report.get("overall_level") or ""),
        len(results),
        qids,
    )


def _cache_bundle(sig: tuple, bundle: Dict[str, Any]) -> Dict[str, Any]:
    pdf_bytes = None
    if pdf_export_available():
        try:
            pdf_out = build_exam_pdf(
                bundle["analytics"],
                summary_rows_for_table(bundle["results"]),
                bundle["results"],
                patient_label=(
                    "OPIc Sample Report"
                    if st.session_state.get("_final_report_demo")
                    else "OPIc Mock V2 Report"
                ),
            )
            if pdf_out:
                pdf_bytes = pdf_out
        except Exception:
            logger.exception("[NEW_FINAL_REPORT] pdf_build_failed")
    st.session_state[_KEY_SIG] = sig
    st.session_state[_KEY_BUNDLE] = bundle
    st.session_state[_KEY_PDF] = pdf_bytes
    return bundle


def _ensure_bundle(
    report: Dict[str, Any],
    answers: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
) -> Dict[str, Any]:
    sig = _bundle_signature(report, answers, questions)
    cached = st.session_state.get(_KEY_BUNDLE)
    if st.session_state.get(_KEY_SIG) == sig and isinstance(cached, dict):
        return cached

    with st.spinner("에릭 노 AI가 전체 시험을 종합 분석 중입니다…"):
        bundle = build_mock_v2_final_bundle(answers, questions, report)
        return _cache_bundle(sig, bundle)


def _ensure_bundle_from_results(
    report: Dict[str, Any],
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    sig = _results_signature(report, results)
    cached = st.session_state.get(_KEY_BUNDLE)
    if st.session_state.get(_KEY_SIG) == sig and isinstance(cached, dict):
        return cached

    with st.spinner("에릭 노 AI가 전체 시험을 종합 분석 중입니다…"):
        items = [r for r in results if isinstance(r, dict)]
        agg = compute_exam_aggregates(items)
        agg = merge_report_into_aggregates(agg, report)
        bundle = {"results": items, "analytics": agg, "report": report}
        return _cache_bundle(sig, bundle)


def render_new_final_report(
    report: Dict[str, Any],
    answers: List[Dict[str, Any]],
    questions: List[Dict[str, Any]],
    *,
    legacy_results: Optional[List[Dict[str, Any]]] = None,
    attempt_no: int = 1,
    is_demo: bool = False,
    on_restart: Optional[Callable[[], None]] = None,
    on_portal: Optional[Callable[[], None]] = None,
    on_retry_stt: Optional[Callable[[int], bool]] = None,
) -> None:
    """
    Render Mock V2 AI report using the legacy final-report layout (hero, matrix,
    dashboard, per-question expanders, PDF/JSON export).
    """
    st.markdown(_REPORT_CSS, unsafe_allow_html=True)
    render_top_bar("리포트", back_href="?nav=MOCK", eyebrow="실전 모의고사")

    if is_demo or st.session_state.get("_final_report_demo"):
        st.markdown(
            """
            <section class="continue-card continue-card--resume mx-landing-card" role="status"
                     aria-label="샘플 리포트 안내">
              <div class="cc-eyebrow">샘플</div>
              <div class="cc-title">샘플 리포트입니다</div>
              <div class="cc-meta">이 화면은 데모 데이터로 만든 리포트입니다.<br/>
                실제 모의고사를 완료하면 내 답변 기준의 최종 리포트가 생성됩니다.</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    if legacy_results is not None:
        bundle = _ensure_bundle_from_results(report, legacy_results)
    else:
        bundle = _ensure_bundle(report, answers, questions)
    agg = bundle.get("analytics") or {}
    results: List[Dict[str, Any]] = bundle.get("results") or []
    stats = exam_results_summary_stats(results)

    if stats.get("pending", 0) > 0:
        st.info(
            "일부 문항은 AI 분석 대기 중입니다. "
            "분석이 완료된 문항 기준으로 리포트를 먼저 보여드릴게요."
        )
    elif stats.get("no_speech", 0) > 0 and stats.get("completed", 0) == 0:
        st.info(
            "대부분의 문항에서 충분한 음성이 인식되지 않아 정상적인 등급 산정이 어렵습니다. "
            "실제 시험에서는 매우 낮은 평가로 이어질 수 있습니다."
        )

    st.markdown(
        """
<div class="final-hero">
  <div style="font-size:1.35rem;margin-bottom:0.35rem;">🎉 축하합니다!</div>
  <div class="sub">실전 모의고사 15문항 AI 진단을 완료했습니다.<br/>
  이제 에릭 노 강사의 전체 발화 분석 리포트를 확인하세요.</div>
  <div class="sub" style="margin-top:1rem;">ERIC NO · OPIc Precision Lab</div>
  <h1>최종 종합 진단 리포트</h1>
  <p class="sub">Clinical-grade speaking analytics · Premium coaching insight</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    ov = agg.get("overall_display") or "측정 불가 · 응답 부족"
    conf = agg.get("confidence", 0)
    note = str(agg.get("confidence_note") or "")
    mock_summary = str(agg.get("mock_v2_summary") or report.get("summary") or "").strip()
    if mock_summary and mock_summary not in note:
        note = f"{mock_summary}\n\n{note}".strip() if note else mock_summary

    st.markdown(
        f"""
<div class="section-card" style="text-align:center;">
  <div style="font-size:0.85rem;color:#64748b;letter-spacing:0.12em;font-weight:700;">OVERALL PREDICTED OPIC LEVEL</div>
  <div class="final-level">{html.escape(str(ov))} <span style="font-size:1.25rem;color:#64748b;font-weight:600;">(Estimated)</span></div>
  <div class="final-confidence">Confidence · {conf}%</div>
  <p class="final-note">{html.escape(note)}</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="section-card">
  <div style="font-size:0.85rem;color:#64748b;font-weight:700;letter-spacing:0.08em;">전체 요약</div>
  <p style="margin:0.5rem 0 0;line-height:1.55;color:#334155;">
    답변 저장 <b>{stats["answered"]}</b>문항 · 분석 완료 <b>{stats["completed"]}</b> · 분석 대기 <b>{stats.get("pending", 0)}</b> · 응답 부족 <b>{stats.get("no_speech", 0)}</b>
  </p>
  <p style="margin:0.35rem 0 0;color:#64748b;font-size:0.92rem;">
    예상 레벨 <b>{html.escape(str(ov))}</b> · 신뢰도 {conf}%
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    strengths = report.get("strengths") if isinstance(report.get("strengths"), list) else []
    weaknesses = report.get("weaknesses") if isinstance(report.get("weaknesses"), list) else []
    mission = str(report.get("practice_mission") or "").strip()

    combined_tx = " ".join(
        (str((r.get("result") or {}).get("transcript") or "")).strip()
        for r in results
        if isinstance(r, dict)
        and result_display_status(r.get("result") or {}) == "분석 완료"
        and is_real_speech_transcript(str((r.get("result") or {}).get("transcript") or ""))
    ).strip()

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("강점")
    if strengths:
        for s in strengths:
            text = str(s).strip()
            if text:
                st.markdown(f"- {html.escape(text)}")
    elif combined_tx:
        from services.feedback.coach_copy import collect_transcript_strengths

        for s in collect_transcript_strengths(combined_tx)[:3] or [
            "질문 주제에 맞게 답을 이어갔어요."
        ]:
            st.markdown(f"- {html.escape(s)}")
    else:
        st.markdown("- 질문 주제에 맞게 답을 이어갔어요.")

    st.subheader("주요 개선 포인트")
    if weaknesses:
        for w in weaknesses:
            text = str(w).strip()
            if text:
                st.markdown(f"- {html.escape(text)}")
    rb = agg.get("rubric_averages") or {}
    st.markdown(
        f"- 문법 · 평균 {rb.get('grammar', '—')} · 표현·어휘 {rb.get('lexical', '—')}"
    )
    st.markdown(
        f"- 구조 · 논리 {rb.get('logic', '—')} · 유창성 {rb.get('fluency', '—')}"
    )
    st.markdown(
        f"- 전달 · {html.escape(str(agg.get('filler_trend') or '리듬과 쉼을 점검해 보세요.'))}"
    )

    st.subheader("추천 미션")
    if mission:
        st.info(mission)
    elif combined_tx:
        from services.feedback.missions import build_next_missions
        from services.feedback.structure_feedback import build_structure_feedback

        structure = build_structure_feedback(combined_tx, "")
        missions = build_next_missions(combined_tx, structure)[:3]
        for m in missions or [
            "각 답변 마지막에 Overall, I'd say... 로 마무리해 보세요.",
            "이유를 말한 뒤 To be more specific,... 으로 예시를 하나 붙여 보세요.",
            "문장 사이에 짧은 쉼을 넣어 또렷하게 말해 보세요.",
        ]:
            st.markdown(f"- {html.escape(str(m))}")
    else:
        st.markdown(
            "- 최소 3문항 이상 영어로 20~30초 이상 답변한 뒤, 다시 리포트를 받아 보세요."
        )
    st.markdown("</div>", unsafe_allow_html=True)

    speech_m = report.get("speech_rate_metrics")
    if isinstance(speech_m, dict) and speech_m.get("words_normalized_90s") is not None:
        st.markdown(
            f"""
<div class="section-card">
  <div style="font-size:0.85rem;color:#64748b;font-weight:700;">발화 속도 (90초 기준)</div>
  <p style="margin:0.5rem 0 0;color:#334155;">
    환산 단어 수 <b>{speech_m.get("words_normalized_90s")}</b>어 ·
    추정 밴드 <b>{html.escape(str(speech_m.get("speech_rate_level") or "—"))}</b> ·
    WPM <b>{speech_m.get("average_wpm") or "—"}</b>
  </p>
  <p style="margin:0.35rem 0 0;color:#64748b;font-size:0.9rem;">
    {html.escape(str(speech_m.get("scoring_note") or ""))}
  </p>
</div>
            """,
            unsafe_allow_html=True,
        )

    breakdown = report.get("score_breakdown")
    if isinstance(breakdown, dict) and breakdown:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("실전 모의고사 6축 점수 (AI 종합)")
        cols = st.columns(3)
        for i, key in enumerate(_MOCK_BREAKDOWN_KEYS):
            label = _MOCK_SCORE_LABELS.get(key, key)
            try:
                val = int(breakdown.get(key) or 0)
            except (TypeError, ValueError):
                val = 0
            with cols[i % 3]:
                st.progress(max(0, min(100, val)) / 100.0)
                st.caption(f"{label}: {val}/100")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.caption(f"{attempt_no}회 모의고사 · 종합 리포트")
    b_new, b_portal, b_refresh = st.columns([1.2, 1, 0.9])
    with b_new:
        if st.button(
            "새 모의고사 시작",
            type="primary",
            use_container_width=True,
            key="mock_v2_nfr_new_attempt",
        ):
            if on_restart:
                on_restart()
    with b_portal:
        if st.button(
            "학습하기로 돌아가기",
            use_container_width=True,
            key="mock_v2_nfr_go_portal",
        ):
            if on_portal:
                on_portal()
    with b_refresh:
        if st.button("리포트 다시 보기", use_container_width=True, key="mock_v2_nfr_refresh"):
            st.session_state.pop(_KEY_SIG, None)
            st.session_state.pop(_KEY_BUNDLE, None)
            st.session_state.pop(_KEY_PDF, None)
            st.rerun()
    st.divider()

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("문항 요약 · Summary Matrix")
    rows = summary_rows_for_table(results)
    if rows:
        df = pd.DataFrame(rows)

        def _heat(v):
            try:
                x = float(v)
            except (TypeError, ValueError):
                return ""
            if x >= 70:
                return "background-color: #ccfbf1; color: #0f766e; font-weight: 600"
            if x < 45:
                return "background-color: #ffe4e6; color: #9f1239"
            return ""

        try:
            styler = df.style.map(
                _heat,
                subset=[
                    c
                    for c in df.columns
                    if c not in ("Q", "Topic", "Type", "Status", "Feedback", "Est. Level")
                ],
            )
            st.dataframe(styler, use_container_width=True, hide_index=True)
        except Exception:
            st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("표시할 결과가 없습니다.")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.subheader("Speech Analytics Dashboard")
    c1, c2 = st.columns(2)
    with c1:
        st.metric("평균 WPM", agg.get("avg_wpm", "—"))
        st.metric("평균 발화 유닛 수", agg.get("avg_sentence_count", "—"))
        st.metric("평균 Semantic Density", agg.get("avg_semantic_density", "—"))
    with c2:
        st.metric("강한 주제", agg.get("strongest_topic", "—"))
        st.metric("보완 주제", agg.get("weakest_topic", "—"))
        st.caption(agg.get("filler_trend", ""))

    rd = agg.get("radar_dimensions") or {}
    if rd:
        cats = list(rd.keys())
        vals = list(rd.values())
        fig_r = go.Figure(
            data=go.Scatterpolar(
                r=vals + [vals[0]],
                theta=cats + [cats[0]],
                fill="toself",
                fillcolor="rgba(20, 184, 166, 0.25)",
                line=dict(color="#14b8a6"),
            )
        )
        fig_r.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
            showlegend=False,
            margin=dict(t=30, b=30),
            height=420,
        )
        st.plotly_chart(fig_r, use_container_width=True)

    rb = agg.get("rubric_averages") or {}
    if rb:
        fig_b = go.Figure(
            go.Bar(
                x=list(rb.keys()),
                y=list(rb.values()),
                marker_color="#0f172a",
                text=list(rb.values()),
                textposition="outside",
            )
        )
        fig_b.update_layout(height=360, margin=dict(t=40, b=40), yaxis_range=[0, 100])
        st.plotly_chart(fig_b, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.subheader("문항별 상세 복기")
    for row in sorted(results, key=lambda x: int(x.get("q_id") or 0)):
        qid = row.get("q_id")
        topic = row.get("topic") or ""
        typ = row.get("type") or ""
        label = clean_visible_label(f"Q{qid} · {topic} · {typ}", f"Q{qid}")

        def _final_row_body(r: Dict[str, Any] = row, q: Any = qid) -> None:
            res = r.get("result") or {}
            st.markdown("##### [A] 질문 내용")
            st.write(r.get("question") or "—")

            st.markdown("##### [B] AI가 인식한 답변")
            tx_raw = (res.get("transcript") or "").strip()
            tx_is_real = False
            _no_speech = result_is_no_speech_row(res)
            _pending = (
                not _no_speech
                and (
                    res.get("diagnosis_status") == "analysis_pending"
                    or str(res.get("analysis_status") or "").lower() == "pending"
                )
            )
            if _no_speech:
                st.markdown(
                    '<div class="mono-tx" style="opacity:.9;">'
                    "<b>응답이 충분하지 않았어요</b><br/>"
                    "이 문항은 말소리가 충분히 인식되지 않아 문법, 표현, 구조 피드백을 제공하기 어렵습니다.<br/>"
                    "다시 연습할 때는 최소 20~30초 이상 영어로 답변해 주세요."
                    "</div>",
                    unsafe_allow_html=True,
                )
            elif _pending:
                st.markdown(
                    '<div class="mono-tx" style="opacity:.9;">'
                    "<b>음성 인식 대기/실패</b><br/>"
                    "이 문항의 답변은 저장되었지만, 텍스트 인식이 완료되지 않았습니다."
                    "</div>",
                    unsafe_allow_html=True,
                )
                if on_retry_stt and st.button(
                    "음성 인식 다시 시도",
                    key=f"mock_v2_nfr_retry_stt_q{q}",
                ):
                    try:
                        q_idx = int(r.get("question_index", int(q) - 1))
                    except (TypeError, ValueError):
                        q_idx = max(0, int(r.get("q_id") or 1) - 1)
                    if on_retry_stt(q_idx):
                        st.session_state.pop(_KEY_SIG, None)
                        st.session_state.pop(_KEY_BUNDLE, None)
                        st.rerun()
            else:
                tx_no_speech = bool(res.get("no_speech_detected")) or (
                    res.get("diagnosis_status") == "no_speech"
                )
                tx_is_real = (
                    bool(tx_raw)
                    and not tx_no_speech
                    and is_real_speech_transcript(tx_raw)
                )
                if tx_is_real:
                    st.markdown(
                        f'<div class="mono-tx">{html.escape(tx_raw)}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div class="mono-tx" style="opacity:.85;">'
                        f"🎤 {NO_SPEECH_EMPTY_TEXT}"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

            st.markdown("##### [C] 에이바(Ava)의 상세 피드백")
            if _no_speech:
                st.info(res.get("summary_speech_rehab") or "응답이 충분하지 않았어요.")
            elif _pending:
                st.info("음성 인식이 완료되면 이 영역에 상세 피드백이 표시됩니다.")
            else:
                st.info(res.get("semantic_feedback") or res.get("summary_speech_rehab") or "—")
            sem = res.get("semantic_dimensions") or {}
            chips = []
            for k in (
                "narrative_depth",
                "discourse_continuity",
                "elaboration_quality",
                "spontaneity_score",
                "naturalness",
            ):
                v = sem.get(k)
                if isinstance(v, (int, float)):
                    chips.append(f"**{k}**: {v:.0f}")
            if chips:
                st.caption(" · ".join(chips))

            st.markdown("##### [D] 에릭 노의 처방전")
            st.write(res.get("prescription") or "—")
            st.caption(
                "개선 우선순위: 담화 연결 → 구체적 디테일 → 시제 안정성 · 추천 연결어 예시: "
                + ", ".join(DISCOURSE_MARKERS[:5])
            )

            if tx_is_real:
                st.markdown("##### [D-ii] 코칭 피드백 (문법 · 표현 · 구조)")
                render_structured_coaching_report(
                    res,
                    tx_raw,
                    int(q or 0),
                    show_hero=True,
                    question_text=str(r.get("question") or ""),
                )

            st.markdown("##### [E] 세부 점수")
            rs = res.get("rubric_scores") or {}
            cols = st.columns(4)
            order = [
                ("fluency", "Fluency"),
                ("grammar", "Grammar"),
                ("lexical", "Lexical"),
                ("logic", "Logic"),
            ]
            for i, (key, title) in enumerate(order):
                v = rs.get(key, 0)
                try:
                    vv = float(v) / 100.0
                except (TypeError, ValueError):
                    vv = 0.0
                cols[i % 4].progress(min(1.0, max(0.0, vv)), text=f"{title}: {v}")

            sem2 = res.get("semantic_dimensions") or {}
            for label_k, name in (
                ("narrative_depth", "Narrative depth"),
                ("semantic_density", "Semantic density"),
                ("naturalness", "Naturalness"),
                ("tense_stability", "Tense stability"),
            ):
                v = sem2.get(label_k)
                if isinstance(v, (int, float)):
                    st.progress(min(1.0, float(v) / 100.0), text=f"{name}: {v:.0f}")

            st.markdown("##### [F] 위험 요소 감지")
            risks = detect_risk_flags(res)
            if risks:
                for risk in risks:
                    st.warning(risk)
            else:
                st.success("특이 위험 패턴이 감지되지 않았습니다.")

        render_collapsible_section(
            label,
            f"mock_v2_nfr_q{qid}",
            _final_row_body,
            css_scope="mx-col",
        )

    st.divider()
    dc1, dc2, dc3 = st.columns(3)
    pdf_bytes = st.session_state.get(_KEY_PDF)
    pdf_ok = pdf_export_available()
    is_demo = is_demo or bool(st.session_state.get("_final_report_demo"))
    pdf_name = (
        "opic_final_report_sample.pdf" if is_demo else "opic_mock_v2_final_report.pdf"
    )
    if pdf_ok and pdf_bytes:
        dc1.download_button(
            "PDF 리포트 다운로드",
            data=pdf_bytes,
            file_name=pdf_name,
            mime="application/pdf",
            use_container_width=True,
        )
    elif pdf_ok and not pdf_bytes:
        dc1.caption("PDF 생성에 실패했습니다. 잠시 후 「리포트 다시 보기」를 눌러 주세요.")
    else:
        dc1.caption(
            "PDF 생성 기능을 사용할 수 없어요. 화면 리포트를 먼저 확인해 주세요."
        )

    export_obj = {
        "generated_at": datetime.now().isoformat(),
        "exam_type": "mock_v2",
        "overall": agg,
        "mock_v2_report": report,
        "items": results,
    }
    dc2.download_button(
        "🧠 Raw Analysis 다운로드",
        data=json.dumps(export_obj, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="mock_v2_analysis_result.json",
        mime="application/json",
        use_container_width=True,
    )

    dc3.button("🔗 결과 공유하기", disabled=True, use_container_width=True)
    dc3.caption("추후: 공유 링크 · 클라우드 저장 · 강사 검수 연동 예정")
