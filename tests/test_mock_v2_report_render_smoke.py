"""Smoke tests — mock_v2 final report render path (catch NameError / ImportError)."""

from __future__ import annotations

import importlib
import sys
import types
import unittest
from contextlib import contextmanager
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

# Report-chain modules that must import and execute without NameError.
_REPORT_MODULES = (
    "utils.feedback_text",
    "services.mock_v2_report_display",
    "services.mock_v2_pdf_report",
    "components.exam_question_feedback_detail",
    "components.mock_v2_final_report_ui",
    "views.new_final_report",
    "views.mock_v2",
)


class _FakeSessionState(dict):
    def __getattr__(self, key: str) -> Any:
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


def _sample_15q_bundle() -> tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    report = {
        "ok": True,
        "overall_level": "IM2",
        "summary": "전반적으로 질문에 맞게 답했지만 문법과 어휘 다양성을 보완하면 좋겠습니다.",
        "practice_mission": "이번 주에는 매일 5분씩 과거 경험을 두 문장 이상으로 말하는 연습을 해 보세요.",
        "strengths": ["주제에 맞게 답을 이어갔어요.", "발화 속도가 안정적이에요."],
        "weaknesses": ["문법 · 평균 55.0", "구체적 예시가 더 필요해요."],
        "question_feedback": [
            {
                "question_number": i,
                "status": "분석 완료",
                "feedback": f"Q{i} 피드백입니다.",
                "better_direction": f"Q{i}: because, so를 써 보세요.",
            }
            for i in range(1, 16)
        ],
    }
    answers: List[Dict[str, Any]] = []
    questions: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    for q in range(1, 16):
        no_resp = q == 7
        tx = "" if no_resp else (
            f"I usually enjoy my free time on weekends. For question {q}, "
            f"I like to spend time with friends and try new restaurants."
        )
        answers.append(
            {
                "question_index": q - 1,
                "question_number": q,
                "student_answer": tx,
                "word_count": 0 if no_resp else 18,
                "wpm": 0 if no_resp else 115.0,
                "stt_status": "no_speech" if no_resp else "transcript_ready",
            }
        )
        questions.append(
            {
                "question_index": q - 1,
                "question_number": q,
                "topic": "Self-Introduction" if q == 1 else "여가",
                "opic_type": "Intro" if q == 1 else "Q1",
                "question_text": f"Tell me about your experience related to topic {q}.",
            }
        )
        results.append(
            {
                "q_id": q,
                "question_index": q - 1,
                "topic": "Self-Introduction" if q == 1 else "여가",
                "type": "Intro" if q == 1 else "Q1",
                "question": f"Tell me about your experience related to topic {q}.",
                "result": {
                    "diagnosis_status": "no_speech" if no_resp else "ok",
                    "no_speech_detected": no_resp,
                    "transcript": tx,
                    "semantic_feedback": (
                        "응답이 충분하지 않았어요." if no_resp else f"Q{q} 피드백: 구체적 예시를 추가해 보세요."
                    ),
                    "prescription": (
                        "" if no_resp else f"Q{q}: 연결어 First of all, Moreover를 써 보세요."
                    ),
                    "estimated_level_display": "IM2",
                    "metrics": {"wpm": 115.0, "sentence_count": 4.0, "duration_seconds": 42.0},
                    "wpm": 115.0,
                },
            }
        )
    from services.exam_analytics import compute_exam_aggregates
    from services.new_final_report_data import merge_report_into_aggregates

    agg = merge_report_into_aggregates(compute_exam_aggregates(results), report)
    bundle = {"results": results, "analytics": agg, "report": report}
    stats = {"completed": 14, "no_speech": 1, "pending": 0, "answered": 15}
    return report, answers, questions, bundle, stats


@contextmanager
def _mock_streamlit():
    """Patch streamlit in views + components used by report render."""
    ss = _FakeSessionState({"target_level": "IH", "user_name": "테스트"})
    fake = types.SimpleNamespace(
        session_state=ss,
        markdown=MagicMock(),
        info=MagicMock(),
        caption=MagicMock(),
        button=MagicMock(return_value=False),
        download_button=MagicMock(),
        spinner=MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=None), __exit__=MagicMock(return_value=False))),
        rerun=MagicMock(),
        columns=MagicMock(return_value=[MagicMock(), MagicMock()]),
    )
    targets = (
        "views.new_final_report.st",
        "components.mock_v2_final_report_ui.st",
        "components.exam_question_feedback_detail.st",
    )
    patches = [patch(t, fake) for t in targets]
    for p in patches:
        p.start()
    try:
        yield fake
    finally:
        for p in reversed(patches):
            p.stop()


class MockV2ReportRenderSmokeTest(unittest.TestCase):
    def test_report_chain_modules_import(self) -> None:
        for name in _REPORT_MODULES:
            mod = importlib.import_module(name)
            self.assertIsNotNone(mod, name)

    def test_html_builders_no_name_error(self) -> None:
        from components.mock_v2_final_report_ui import (
            _level_gap_chip,
            build_m2fr_diagnosis_html,
            build_m2fr_header_html,
            build_m2fr_hero_html,
            build_m2fr_qrow_header_html,
            build_m2fr_session_summary_html,
            today_kst_label,
        )

        report, _answers, _questions, bundle, _stats = _sample_15q_bundle()
        agg = bundle["analytics"]
        ss = _FakeSessionState({"target_level": "IH"})

        self.assertTrue(build_m2fr_header_html(date_label=today_kst_label()))
        gap = _level_gap_chip(str(agg.get("overall_raw") or "IM2"), ss)
        self.assertTrue(gap)
        self.assertTrue(
            build_m2fr_hero_html(
                overall_raw="IM2",
                confidence=82,
                note=str(report.get("summary") or ""),
                avg_wpm=118,
                answered_label="14/15",
                gap_chip=gap,
            )
        )
        self.assertIn("영역별 진단", build_m2fr_diagnosis_html(agg.get("rubric_averages") or {}, overall_raw="IM2"))
        summary = build_m2fr_session_summary_html(
            list(report.get("strengths") or []),
            list(report.get("weaknesses") or []),
            str(report.get("practice_mission") or ""),
        )
        self.assertIn("m2fr-session-summary", summary)
        for row in bundle["results"]:
            html_out = build_m2fr_qrow_header_html(row, is_open=False)
            self.assertIn(f"Q{row['q_id']}", html_out)

    def test_question_feedback_detail_all_row_types(self) -> None:
        from components.exam_question_feedback_detail import render_exam_question_feedback_detail

        _report, _answers, _questions, bundle, _stats = _sample_15q_bundle()
        with _mock_streamlit():
            for row in bundle["results"]:
                render_exam_question_feedback_detail(
                    row,
                    key_prefix=f"smoke_q{row['q_id']}",
                    show_type_pill=True,
                    show_coaching=True,
                )

    def test_render_new_final_report_full_path(self) -> None:
        from views import new_final_report as nfr

        report, answers, questions, bundle, stats = _sample_15q_bundle()
        with _mock_streamlit() as fake_st:
            with patch.object(nfr, "_ensure_bundle", return_value=bundle):
                with patch.object(nfr, "pdf_export_available", return_value=False):
                    nfr.render_new_final_report(
                        report,
                        answers,
                        questions,
                        attempt_no=1,
                        is_demo=False,
                        on_restart=lambda: None,
                        on_portal=lambda: None,
                    )
        self.assertGreater(fake_st.markdown.call_count, 5)

    def test_render_question_list_and_expand(self) -> None:
        from components.mock_v2_final_report_ui import render_m2fr_question_list

        _report, _answers, _questions, bundle, stats = _sample_15q_bundle()
        with _mock_streamlit() as fake_st:
            # Simulate user opening Q1
            fake_st.session_state["m2fr_open_m2fr_q_1"] = True
            render_m2fr_question_list(bundle["results"], stats)
        self.assertGreater(fake_st.markdown.call_count, 3)

    def test_pdf_builder_smoke(self) -> None:
        from services import pdf_report as pr
        from services.mock_v2_pdf_report import build_mock_v2_exam_pdf

        if not pr.pdf_export_available():
            self.skipTest("reportlab not installed")
        report, _answers, _questions, bundle, stats = _sample_15q_bundle()
        pdf = build_mock_v2_exam_pdf(
            bundle["analytics"],
            bundle["results"],
            report,
            patient_label="테스트",
            target_level="IH",
            stats=stats,
        )
        self.assertIsNotNone(pdf)
        assert pdf is not None
        self.assertTrue(pdf.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
