"""Unit tests for final report completion hero metrics."""

import unittest

from components.final_report_hero import (
    collect_hero_display_metrics,
    render_final_report_completion_hero_html,
)


class TestCollectHeroDisplayMetrics(unittest.TestCase):
    def test_results_nonempty_uses_results_count(self):
        results = [{"result": {"word_count": 12}}, {"result": {"word_count": 8}}]
        answers = [{"word_count": 99, "duration_seconds": 30.0}]
        metrics = collect_hero_display_metrics(results, answers)
        self.assertEqual(metrics["answered"], 2)
        self.assertEqual(metrics["total_words"], 20)
        self.assertAlmostEqual(metrics["total_duration"], 30.0)

    def test_empty_results_falls_back_to_valid_answers(self):
        answers = [
            {"status": "saved", "word_count": 10, "duration_seconds": 20.0},
            {"status": "saved", "word_count": 15, "duration_seconds": 25.5},
            {"status": "recording_failed", "word_count": 0},
        ]
        metrics = collect_hero_display_metrics([], answers)
        self.assertEqual(metrics["answered"], 2)
        self.assertEqual(metrics["total_words"], 25)
        self.assertAlmostEqual(metrics["total_duration"], 45.5)

    def test_empty_results_counts_transcript_without_saved_status(self):
        answers = [{"transcript": "hello world", "word_count": 2}]
        metrics = collect_hero_display_metrics([], answers)
        self.assertEqual(metrics["answered"], 1)
        self.assertEqual(metrics["total_words"], 2)

    def test_no_valid_data_returns_zeros_and_none(self):
        metrics = collect_hero_display_metrics([], [])
        self.assertEqual(metrics["answered"], 0)
        self.assertIsNone(metrics["total_words"])
        self.assertIsNone(metrics["total_duration"])


class TestRenderFinalReportCompletionHeroHtml(unittest.TestCase):
    def test_three_question_title_and_celebration_scene(self):
        html_out = render_final_report_completion_hero_html(
            answered_count=3,
            overall_display="IM2",
            pending_count=0,
            total_words=42,
            total_duration=95.0,
            note="Good job.",
            eyebrow="5분 진단 완료",
        )
        self.assertIn("3문항을 끝까지 해냈어요!", html_out)
        self.assertIn("5분 진단 완료", html_out)
        self.assertIn("mx-fr-hero", html_out)
        self.assertIn('viewBox="0 0 240 120"', html_out)
        self.assertIn("IM2", html_out)
        self.assertIn("42", html_out)
        self.assertIn("1분 35초", html_out)

    def test_pending_grade_hides_pill(self):
        html_out = render_final_report_completion_hero_html(
            answered_count=3,
            overall_display="분석 대기",
            pending_count=0,
            total_words=10,
        )
        self.assertNotIn("mx-fr-hero-grade", html_out)

    def test_default_eyebrow_unchanged_for_real_mock(self):
        html_out = render_final_report_completion_hero_html(
            answered_count=15,
            overall_display="IH",
            pending_count=0,
        )
        self.assertIn("오늘의 진료 완료", html_out)
        self.assertIn("15문항을 끝까지 해냈어요!", html_out)


if __name__ == "__main__":
    unittest.main()
