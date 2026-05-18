"""Post-exam comprehensive report — cache-only; no Gemini calls."""

from __future__ import annotations

import html
import json
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components.collapsible_section import render_collapsible_section
from components.coaching_experience import render_structured_coaching_report
from services.exam_analytics import (
    compute_exam_aggregates,
    detect_risk_flags,
    exam_results_summary_stats,
    result_display_status,
    summary_rows_for_table,
)
from utils.exam_state import reset_exam_state, start_new_mock_attempt
from utils.local_profile import sync_user_progress
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

from services.tts_service import clear_mock_question_tts_keys

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


def _ensure_analytics(mx: Dict[str, Any]) -> Dict[str, Any]:
    results: List[Dict[str, Any]] = mx.get("results") or []
    sig = (len(results), tuple(r.get("q_id") for r in results))
    if mx.get("_analytics_sig") == sig and mx.get("analytics_cache"):
        return mx["analytics_cache"]
    with st.spinner("에릭 노 AI가 전체 시험을 종합 분석 중입니다…"):
        agg = compute_exam_aggregates(results)
        mx["analytics_cache"] = agg
        mx["overall_estimated_level"] = agg.get("overall_display")
        mx["_analytics_sig"] = sig
        mx["final_report_generated"] = True
        mx["downloadable_report_bytes"] = None
        if pdf_export_available():
            try:
                pdf_out = build_exam_pdf(
                    agg,
                    summary_rows_for_table(results),
                    results,
                )
                if pdf_out:
                    mx["downloadable_report_bytes"] = pdf_out
            except Exception:
                mx["downloadable_report_bytes"] = None
    return mx["analytics_cache"]


def render_final_report(mx: Dict[str, Any]) -> None:
    st.markdown(_REPORT_CSS, unsafe_allow_html=True)

    if mx.get("_final_report_demo"):
        st.info(
            "**데모 모드** — 가짜 15문항 데이터로 UI를 보여줍니다. "
            "실제 시험을 끝까지 보면 본인 녹음·분석 결과로 대체됩니다."
        )

    if mx.pop("_show_exam_celebration", False):
        st.balloons()

    agg = _ensure_analytics(mx)
    results: List[Dict[str, Any]] = mx.get("results") or []
    stats = exam_results_summary_stats(results)

    if stats["pending"] > 0:
        st.info(
            "일부 문항은 AI 분석 대기 중입니다. "
            "분석이 완료된 문항 기준으로 리포트를 먼저 보여드릴게요."
        )

    # --- Hero ---
    st.markdown(
        f"""
<div class="final-hero">
  <div style="font-size:1.35rem;margin-bottom:0.35rem;">🎉 축하합니다!</div>
  <div class="sub">모든 AI 언어 정밀 진단을 완료했습니다.<br/>
  이제 에릭 노 강사의 전체 발화 분석 리포트를 확인하세요.</div>
  <div class="sub" style="margin-top:1rem;">ERIC NO · OPIc Precision Lab</div>
  <h1>최종 종합 진단 리포트</h1>
  <p class="sub">Clinical-grade speaking analytics · Premium coaching insight</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    ov = agg.get("overall_display", "NH")
    conf = agg.get("confidence", 0)
    note = agg.get("confidence_note", "")

    st.markdown(
        f"""
<div class="section-card" style="text-align:center;">
  <div style="font-size:0.85rem;color:#64748b;letter-spacing:0.12em;font-weight:700;">OVERALL PREDICTED OPIC LEVEL</div>
  <div class="final-level">{ov} <span style="font-size:1.25rem;color:#64748b;font-weight:600;">(Estimated)</span></div>
  <div class="final-confidence">Confidence · {conf}%</div>
  <p class="final-note">{note}</p>
</div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class="section-card">
  <div style="font-size:0.85rem;color:#64748b;font-weight:700;letter-spacing:0.08em;">전체 요약</div>
  <p style="margin:0.5rem 0 0;line-height:1.55;color:#334155;">
    답변 저장 <b>{stats["answered"]}</b>문항 · 분석 완료 <b>{stats["completed"]}</b> · 분석 대기 <b>{stats["pending"]}</b>
  </p>
  <p style="margin:0.35rem 0 0;color:#64748b;font-size:0.92rem;">
    예상 레벨 <b>{html.escape(str(ov))}</b> · 신뢰도 {conf}%
  </p>
</div>
        """,
        unsafe_allow_html=True,
    )

    combined_tx = " ".join(
        (str((r.get("result") or {}).get("transcript") or "")).strip()
        for r in results
        if isinstance(r, dict)
        and result_display_status(r.get("result") or {}) == "분석 완료"
        and is_real_speech_transcript(str((r.get("result") or {}).get("transcript") or ""))
    ).strip()
    if combined_tx:
        from services.feedback.coach_copy import collect_transcript_strengths
        from services.feedback.missions import build_next_missions
        from services.feedback.structure_feedback import build_structure_feedback

        strengths = collect_transcript_strengths(combined_tx)[:3]
        structure = build_structure_feedback(combined_tx, "")
        missions = build_next_missions(combined_tx, structure)[:3]
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.subheader("강점")
        for s in strengths or ["질문 주제에 맞게 답을 이어갔어요."]:
            st.markdown(f"- {html.escape(s)}")
        st.subheader("주요 개선 포인트")
        rb = agg.get("rubric_averages") or {}
        st.markdown(
            f"- 문법 · 평균 {rb.get('grammar', '—')} · 표현·어휘 {rb.get('lexical', '—')}"
        )
        st.markdown(
            f"- 구조 · 논리 {rb.get('logic', '—')} · 유창성 {rb.get('fluency', '—')}"
        )
        st.markdown(f"- 전달 · {html.escape(str(agg.get('filler_trend') or '리듬과 쉼을 점검해 보세요.'))}")
        st.subheader("추천 미션")
        for m in missions or [
            "각 답변 마지막에 Overall, I'd say... 로 마무리해 보세요.",
            "이유를 말한 뒤 To be more specific,... 으로 예시를 하나 붙여 보세요.",
            "문장 사이에 짧은 쉼을 넣어 또렷하게 말해 보세요.",
        ]:
            st.markdown(f"- {html.escape(str(m))}")
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    att = int(mx.get("attempt_no") or 1)
    st.caption(f"{att}회 모의고사 · 종합 리포트")
    b_new, b_home, b_refresh = st.columns([1.2, 1, 0.9])
    with b_new:
        if st.button("새 모의고사 시작하기", type="primary", use_container_width=True, key="mx_final_new_attempt"):
            if start_new_mock_attempt(mx, st.session_state):
                clear_mock_question_tts_keys()
                sync_user_progress(st.session_state)
                try:
                    st.query_params.clear()
                    st.query_params["nav"] = "MOCK"
                    st.query_params["mock"] = "TEST"
                except Exception:
                    pass
                st.rerun()
            else:
                st.error("설문 데이터가 없거나 종료된 시험이 아니면 새 시험을 시작할 수 없습니다.")
    with b_home:
        if st.button("홈으로 가기", use_container_width=True, key="mx_final_go_home"):
            reset_exam_state(mx, st.session_state)
            st.session_state.page = "HOME"
            st.query_params.clear()
            st.query_params["nav"] = "HOME"
            st.rerun()
    with b_refresh:
        if st.button("리포트 다시 보기", use_container_width=True, key="mx_final_refresh"):
            st.rerun()
    st.divider()

    # --- Section B: table ---
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

    # --- Dashboard ---
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

    # --- Section C: expanders ---
    st.subheader("문항별 상세 복기")
    for row in sorted(results, key=lambda x: int(x.get("q_id") or 0)):
        qid = row.get("q_id")
        topic = row.get("topic") or ""
        typ = row.get("type") or ""
        res = row.get("result") or {}
        label = clean_visible_label(f"Q{qid} · {topic} · {typ}", f"Q{qid}")

        def _final_row_body(r: Dict[str, Any] = row, q: Any = qid) -> None:
            res = r.get("result") or {}
            st.markdown("##### [A] 질문 내용")
            st.write(r.get("question") or "—")

            st.markdown("##### [B] 나의 답변 (Transcript)")
            tx_raw = (res.get("transcript") or "").strip()
            tx_is_real = False
            _pending = (
                res.get("diagnosis_status") == "analysis_pending"
                or str(res.get("analysis_status") or "").lower() == "pending"
            )
            if _pending:
                st.markdown(
                    '<div class="mono-tx" style="opacity:.9;">'
                    "<b>AI 분석 대기 중</b><br/>"
                    "이 문항의 답변은 저장되었지만, 분석이 아직 완료되지 않았습니다."
                    "</div>",
                    unsafe_allow_html=True,
                )
                if st.button("AI 분석 다시 시도", key=f"final_retry_analysis_q{q}"):
                    from views.mock_exam import retry_stored_answer_analysis

                    retry_stored_answer_analysis(mx, int(q))
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
                        f'<div class="mono-tx">{tx_raw}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    # Trust-gate rejection: render the empty-state copy instead
                    # of any potentially fabricated text. Never display "(없음)"
                    # next to a content area — users read that as "the system
                    # erased my speech".
                    st.markdown(
                        f'<div class="mono-tx" style="opacity:.85;">'
                        f'🎤 {NO_SPEECH_EMPTY_TEXT}'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown("##### [C] 에이바(Ava)의 상세 피드백")
            if _pending:
                st.info("AI 분석이 완료되면 이 영역에 상세 피드백이 표시됩니다.")
            else:
                st.info(res.get("semantic_feedback") or res.get("summary_speech_rehab") or "—")
            sem = res.get("semantic_dimensions") or {}
            chips = []
            for k in ("narrative_depth", "discourse_continuity", "elaboration_quality", "spontaneity_score", "naturalness"):
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

            # [D-ii] Rule-based grammar fix + alternative-expression cards.
            # Same component the per-question report card uses, kept here so
            # the final report stays the single source of truth for review.
            # Only run when the trust gate has accepted the transcript so we
            # never "fix grammar" on hallucinated text.
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
            order = [("fluency", "Fluency"), ("grammar", "Grammar"), ("lexical", "Lexical"), ("logic", "Logic")]
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
                for r in risks:
                    st.warning(r)
            else:
                st.success("특이 위험 패턴이 감지되지 않았습니다.")

        render_collapsible_section(
            label,
            f"final_q{qid}",
            _final_row_body,
            css_scope="mx-col",
        )

    # --- Downloads ---
    st.divider()
    dc1, dc2, dc3 = st.columns(3)
    pdf_bytes = mx.get("downloadable_report_bytes")
    pdf_ok = pdf_export_available()
    if pdf_ok and pdf_bytes:
        fn = f"opic_therapy_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        dc1.download_button(
            "📄 PDF로 저장하기",
            data=pdf_bytes,
            file_name=fn,
            mime="application/pdf",
            use_container_width=True,
        )
    elif pdf_ok and not pdf_bytes:
        dc1.caption("📄 PDF 생성에 실패했습니다. 잠시 후 페이지를 새로고침하거나 로그를 확인하세요.")
    else:
        dc1.caption(
            "📄 PDF 저장은 **`pip install reportlab pillow`** 설치 후 사용할 수 있습니다. "
            "(선택 기능 · 나머지 리포트는 그대로 이용 가능)"
        )

    export_obj = {
        "generated_at": datetime.now().isoformat(),
        "overall": agg,
        "items": results,
    }
    dc2.download_button(
        "🧠 Raw Analysis 다운로드",
        data=json.dumps(export_obj, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="analysis_result.json",
        mime="application/json",
        use_container_width=True,
    )

    dc3.button("🔗 결과 공유하기", disabled=True, use_container_width=True)
    dc3.caption("추후: 공유 링크 · 클라우드 저장 · 강사 검수 연동 예정")
