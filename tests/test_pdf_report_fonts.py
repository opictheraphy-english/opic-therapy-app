"""Tests for PDF Korean font registration and rendering."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from services import pdf_report as pr


class PdfReportFontTests(unittest.TestCase):
    def setUp(self) -> None:
        pr._fonts_registered = False
        pr._font_regular_name = "Helvetica"
        pr._font_bold_name = "Helvetica-Bold"

    def test_font_paths_relative_to_module(self) -> None:
        regular, bold = pr._font_paths()
        self.assertTrue(regular.endswith(os.path.join("assets", "fonts", "NotoSansKR-Regular.ttf")))
        self.assertTrue(bold.endswith(os.path.join("assets", "fonts", "NotoSansKR-Bold.ttf")))
        self.assertTrue(os.path.isfile(regular))
        self.assertTrue(os.path.isfile(bold))

    def test_register_uses_noto_when_files_present(self) -> None:
        if not pr.pdf_export_available():
            self.skipTest("reportlab not installed")
        regular, bold = pr._register_pdf_fonts()
        self.assertEqual(regular, "NotoSansKR")
        self.assertEqual(bold, "NotoSansKR-Bold")
        regular2, bold2 = pr._register_pdf_fonts()
        self.assertEqual(regular2, regular)
        self.assertEqual(bold2, bold)

    def test_build_pdf_renders_korean_status_and_feedback(self) -> None:
        if not pr.pdf_export_available():
            self.skipTest("reportlab not installed")
        aggregates = {
            "overall_display": "IM2",
            "confidence": 88,
            "confidence_note": "대부분의 문항에서 충분한 음성이 인식되지 않아 정상적인 등급 산정이 어렵습니다.",
            "avg_wpm": 120,
            "avg_sentence_count": 8,
            "avg_semantic_density": 55,
            "strongest_topic": "Travel",
            "weakest_topic": "Work",
        }
        summary_rows = [
            {
                "Q": 1,
                "Topic": "여행",
                "Type": "Description",
                "Status": "분석 완료",
                "Est. Level": "IM2",
                "Fluency": 80,
                "Logic": 75,
                "Grammar": 70,
                "Overall": 78,
                "Feedback": "구체적 예시를 더 추가해 보세요.",
            }
        ]
        items = [
            {
                "q_id": 1,
                "topic": "여행",
                "type": "Description",
                "result": {
                    "transcript": "I went to Jeju last summer.",
                    "diagnosis_status": "ok",
                },
            }
        ]
        pdf_bytes = pr.build_exam_pdf(aggregates, summary_rows, items)
        self.assertIsNotNone(pdf_bytes)
        assert pdf_bytes is not None
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))
        self.assertGreater(len(pdf_bytes), 5000)

    def test_missing_font_falls_back_without_crash(self) -> None:
        if not pr.pdf_export_available():
            self.skipTest("reportlab not installed")
        pr._fonts_registered = False
        with patch.object(pr, "_font_paths", return_value=("/no/such/regular.ttf", "/no/such/bold.ttf")):
            regular, bold = pr._register_pdf_fonts()
        self.assertEqual(regular, "Helvetica")
        self.assertEqual(bold, "Helvetica-Bold")
        pdf_bytes = pr.build_exam_pdf({"overall_display": "IM2", "confidence": 80}, [], [])
        self.assertIsNotNone(pdf_bytes)


if __name__ == "__main__":
    unittest.main()
