"""Tests for premium Mock V2 PDF export."""

from __future__ import annotations

import unittest

from services import pdf_report as pr
from services.mock_v2_pdf_report import build_mock_v2_exam_pdf


def _sample_bundle() -> tuple:
    report = {
        "ok": True,
        "overall_level": "IM2",
        "summary": "전반적으로 질문에 맞게 답했지만 문법과 어휘 다양성을 보완하면 좋겠습니다.",
        "practice_mission": "이번 주에는 매일 5분씩 과거 경험을 두 문장 이상으로 말하는 연습을 해 보세요.",
        "strengths": ["주제에 맞게 답을 이어갔어요.", "발화 속도가 안정적이에요."],
        "weaknesses": ["구체적 예시가 더 필요해요.", "연결어 사용을 늘려 보세요."],
    }
    aggregates = {
        "overall_raw": "IM2",
        "overall_display": "IM2",
        "confidence": 82,
        "confidence_note": "대부분 문항에서 충분한 응답이 인식되었습니다.",
        "mock_v2_summary": report["summary"],
        "avg_wpm": 118,
        "rubric_averages": {
            "fluency": 70.4,
            "grammar": 67.0,
            "lexical": 72.0,
            "logic": 85.0,
        },
    }
    items = []
    for q in range(1, 16):
        no_resp = q == 7
        items.append(
            {
                "q_id": q,
                "question_index": q - 1,
                "topic": "Self-Introduction" if q == 1 else "해변",
                "type": "Intro" if q == 1 else "Q1",
                "question": f"Sample question text for Q{q}?",
                "result": {
                    "diagnosis_status": "no_speech" if no_resp else "ok",
                    "no_speech_detected": no_resp,
                    "transcript": "" if no_resp else f"This is my answer for question {q}.",
                    "semantic_feedback": (
                        "응답이 충분하지 않았어요." if no_resp else f"Q{q} 피드백: 구체적 예시를 추가해 보세요."
                    ),
                    "prescription": (
                        "" if no_resp else f"Q{q}: 연결어 because, so를 써 보세요."
                    ),
                    "estimated_level_display": "IM2",
                    "metrics": {"wpm": 115.0, "sentence_count": 4.0},
                },
            }
        )
    stats = {"completed": 14, "no_speech": 1, "pending": 0, "answered": 15}
    return aggregates, items, report, stats


class MockV2PdfReportTest(unittest.TestCase):
    def setUp(self) -> None:
        pr._fonts_registered = False

    def test_builds_multipage_pdf_with_korean(self) -> None:
        if not pr.pdf_export_available():
            self.skipTest("reportlab not installed")
        agg, items, report, stats = _sample_bundle()
        pdf_bytes = build_mock_v2_exam_pdf(
            agg,
            items,
            report,
            patient_label="테스트 학습자",
            target_level="IH",
            stats=stats,
        )
        self.assertIsNotNone(pdf_bytes)
        assert pdf_bytes is not None
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 20_000)
        self.assertLess(len(pdf_bytes), 10_000_000)

    def test_no_per_question_score_columns_in_content(self) -> None:
        if not pr.pdf_export_available():
            self.skipTest("reportlab not installed")
        agg, items, report, stats = _sample_bundle()
        pdf_bytes = build_mock_v2_exam_pdf(
            agg, items, report, stats=stats, target_level="IH"
        )
        assert pdf_bytes is not None
        # Heuristic: old template used "Fluency" column header; premium uses Korean sections
        self.assertNotIn(b"Fluency", pdf_bytes)
        self.assertIn(b"IM2", pdf_bytes)


if __name__ == "__main__":
    unittest.main()
