"""Mock V2 comprehensive final report — premium screen layout."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from components.mock_v2_final_report_ui import (
    _hero_note,
    _level_gap_chip,
    build_m2fr_diagnosis_html,
    build_m2fr_header_html,
    build_m2fr_hero_html,
    build_m2fr_session_summary_html,
    m2fr_screen_marker_html,
    render_m2fr_actions,
    render_m2fr_question_list,
    today_kst_label,
)
from services.exam_analytics import exam_results_summary_stats
from services.exam_analytics import compute_exam_aggregates
from services.mock_v2_pdf_report import build_mock_v2_exam_pdf
from services.new_final_report_data import (
    build_mock_v2_final_bundle,
    merge_report_into_aggregates,
)
from utils.home_stats import resolve_target_level

try:
    from services.pdf_report import pdf_export_available
except ImportError:

    def pdf_export_available() -> bool:
        return False

logger = logging.getLogger(__name__)

_KEY_BUNDLE = "mock_v2_new_final_bundle"
_KEY_SIG = "mock_v2_new_final_sig"
_KEY_PDF = "mock_v2_new_final_pdf_bytes"


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
            stats = exam_results_summary_stats(bundle.get("results") or [])
            patient = str(st.session_state.get("user_name") or "").strip()
            if not patient:
                patient = (
                    "OPIc Sample Report"
                    if st.session_state.get("_final_report_demo")
                    else "OPIc Mock V2 Report"
                )
            pdf_out = build_mock_v2_exam_pdf(
                bundle["analytics"],
                bundle["results"],
                bundle.get("report") or {},
                patient_label=patient,
                target_level=resolve_target_level(st.session_state),
                stats=stats,
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
    """Render Mock V2 AI report — premium layout (data pipeline unchanged)."""
    st.markdown(m2fr_screen_marker_html(), unsafe_allow_html=True)

    if is_demo or st.session_state.get("_final_report_demo"):
        st.markdown(
            '<div class="m2fr-demo">'
            "<b>샘플 리포트</b> · 데모 데이터로 만든 화면입니다. "
            "실제 모의고사를 완료하면 내 답변 기준 리포트가 생성됩니다."
            "</div>",
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

    overall_raw = str(agg.get("overall_raw") or agg.get("overall_display") or "—")
    conf = agg.get("confidence", 0)
    note = _hero_note(report, agg)
    answered_label = f"{int(stats.get('completed') or 0)}/15"
    gap_chip = _level_gap_chip(overall_raw, st.session_state)

    st.markdown(
        build_m2fr_header_html(
            date_label=today_kst_label(),
            exam_label="실전 모의고사",
            question_count=15,
        ),
        unsafe_allow_html=True,
    )
    st.markdown(
        build_m2fr_hero_html(
            overall_raw=overall_raw,
            confidence=conf,
            note=note,
            avg_wpm=agg.get("avg_wpm"),
            answered_label=answered_label,
            gap_chip=gap_chip,
        ),
        unsafe_allow_html=True,
    )

    rubric = agg.get("rubric_averages") or {}
    st.markdown(
        build_m2fr_diagnosis_html(rubric, overall_raw=overall_raw),
        unsafe_allow_html=True,
    )

    strengths = [
        str(s).strip()
        for s in (report.get("strengths") or [])
        if isinstance(report, dict) and str(s).strip()
    ]
    weaknesses = [
        str(w).strip()
        for w in (report.get("weaknesses") or [])
        if isinstance(report, dict) and str(w).strip()
    ]
    mission = str(report.get("practice_mission") or "").strip()
    summary_html = build_m2fr_session_summary_html(strengths, weaknesses, mission)
    if summary_html:
        st.markdown(summary_html, unsafe_allow_html=True)

    render_m2fr_question_list(results, stats, on_retry_stt=on_retry_stt)

    pdf_bytes = st.session_state.get(_KEY_PDF)
    pdf_ok = pdf_export_available()
    is_demo_run = is_demo or bool(st.session_state.get("_final_report_demo"))
    pdf_name = (
        "opic_final_report_sample.pdf" if is_demo_run else "opic_mock_v2_final_report.pdf"
    )
    render_m2fr_actions(
        pdf_bytes=pdf_bytes,
        pdf_ok=pdf_ok,
        pdf_name=pdf_name,
        on_restart=on_restart,
    )

    if on_portal and st.button(
        "학습하기로 돌아가기",
        key="mock_v2_nfr_go_portal",
        use_container_width=True,
    ):
        on_portal()

    if os.environ.get("DEBUG_REPORT_EXPORT") == "1":
        export_obj = {
            "generated_at": datetime.now().isoformat(),
            "exam_type": "mock_v2",
            "overall": agg,
            "mock_v2_report": report,
            "items": results,
        }
        st.download_button(
            "🧠 Raw Analysis 다운로드",
            data=json.dumps(export_obj, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name="mock_v2_analysis_result.json",
            mime="application/json",
            use_container_width=True,
            key="mock_v2_nfr_json_debug",
        )

    st.caption(f"{attempt_no}회 모의고사 · 종합 리포트")
