"""Regression tests for mock_v2 final-report fixes (dedup, levels, per-item scores)."""

from __future__ import annotations

import random
import unittest

from services.mock_v2_question_selector import build_mock_v2_exam
from services.new_final_report_data import build_mock_v2_final_bundle, merge_report_into_aggregates
from services.exam_analytics import compute_exam_aggregates, strongest_weakest_topic

_SURVEY = {
    "leisure": ["영화 보기", "공원 가기"],
    "interests": ["음악 감상하기", "요리하기"],
    "sports": ["농구", "조깅"],
    "travel": ["국내 여행"],
}

_SAMPLE_REPORT = {
    "ok": True,
    "overall_level": "IM2",
    "summary": "Session summary text.",
    "score_breakdown": {
        "response_amount": 72,
        "relevance": 70,
        "structure": 85,
        "grammar": 67,
        "vocabulary": 72,
        "naturalness": 70,
    },
    "question_feedback": [
        {
            "question_number": 1,
            "status": "분석 완료",
            "feedback": "Intro feedback A.",
            "better_direction": "Add detail.",
        },
        {
            "question_number": 2,
            "status": "분석 완료",
            "feedback": "Q2 feedback B.",
            "better_direction": "Use connectors.",
        },
    ],
}


class MockV2FinalReportFixesTest(unittest.TestCase):
    def test_im_combo3_q9_q10_distinct_text(self) -> None:
        """IM Combo3 uses fixed q3+q4; distinct bank rows must not repeat the same sentence."""
        for seed in range(40):
            random.seed(seed)
            exam = build_mock_v2_exam(_SURVEY, difficulty=3)
            q9, q10 = exam[8], exam[9]
            self.assertNotEqual(
                q9.get("question_text"),
                q10.get("question_text"),
                f"q9/q10 duplicate text seed={seed}",
            )
            self.assertNotEqual(
                q9.get("source_id"),
                q10.get("source_id"),
                f"q9/q10 duplicate source_id seed={seed}",
            )

    def test_no_duplicate_source_id_when_avoidable(self) -> None:
        for lev in (3, 4, 5, 6):
            for seed in range(25):
                random.seed(seed)
                exam = build_mock_v2_exam(_SURVEY, difficulty=lev)
                ids = [
                    str(q.get("source_id"))
                    for q in exam
                    if q.get("source_id")
                ]
                if len(ids) != len(set(ids)):
                    texts = [
                        " ".join(str(q.get("question_text") or "").split()).strip().lower()
                        for q in exam
                        if q.get("question_text")
                    ]
                    self.assertEqual(
                        len(texts),
                        len(set(texts)),
                        f"duplicate source_id should imply duplicate text lev={lev} seed={seed}",
                    )

    def test_per_item_rows_omit_session_rubric_stamp(self) -> None:
        answers = [
            {
                "question_index": 0,
                "question_number": 1,
                "student_answer": "I am a student who likes music and travel.",
                "word_count": 10,
                "wpm": 110.0,
                "stt_status": "transcript_ready",
            },
            {
                "question_index": 1,
                "question_number": 2,
                "student_answer": "My favorite movie is about friendship and hope.",
                "word_count": 9,
                "wpm": 105.0,
                "stt_status": "transcript_ready",
            },
        ]
        questions = [
            {"question_index": 0, "question_number": 1, "topic": "Self-Introduction", "opic_type": "Intro"},
            {"question_index": 1, "question_number": 2, "topic": "Movies", "opic_type": "Q1"},
        ]
        bundle = build_mock_v2_final_bundle(answers, questions, _SAMPLE_REPORT)
        for row in bundle["results"]:
            res = row.get("result") or {}
            self.assertNotIn("rubric_scores", res)
            self.assertNotIn("final_grade_score", res)
            self.assertNotIn("semantic_dimensions", res)
            self.assertEqual(res.get("estimated_level_display"), "IM2")

        agg = bundle["analytics"]
        self.assertEqual(agg.get("overall_display"), "IM2")
        self.assertEqual(agg.get("overall_raw"), "IM2")
        rubric = agg.get("rubric_averages") or {}
        self.assertTrue(rubric.get("fluency", 0) > 0)

    def test_strongest_weakest_without_per_item_scores(self) -> None:
        items = [
            {"topic": "Self-Introduction", "result": {"is_gradable": True, "estimated_level": "IM2"}},
            {"topic": "Movies", "result": {"is_gradable": True, "estimated_level": "IM2"}},
        ]
        strong, weak = strongest_weakest_topic(items)
        self.assertEqual(strong, "—")
        self.assertEqual(weak, "—")
        agg = compute_exam_aggregates(items)
        agg = merge_report_into_aggregates(agg, _SAMPLE_REPORT)
        self.assertEqual(agg.get("strongest_topic"), "—")
        self.assertEqual(agg.get("weakest_topic"), "—")


if __name__ == "__main__":
    unittest.main()
