"""Tests for IM exam builder (levels 3–4)."""

from __future__ import annotations

import random
import unittest

from services.mock_v2_question_selector import _build_mock_v2_exam_im, build_mock_v2_exam

_SURVEY = {
    "leisure": ["영화 보기", "공원 가기"],
    "interests": ["음악 감상하기", "요리하기"],
    "sports": ["농구", "조깅"],
    "travel": ["국내 여행"],
}

_SURVEY_SPARSE = {
    "leisure": ["영화 보기"],
    "interests": ["요리하기"],
    "sports": [],
    "travel": [],
}


class MockV2ExamImTest(unittest.TestCase):
    def _exam_topics(self, exam: list) -> list[str]:
        return [
            str(q.get("topic_id") or "")
            for q in exam
            if q.get("question_number") in (2, 3, 4, 5, 6, 7, 8, 9, 10, 14)
        ]

    def test_level_3_and_4_same_structure(self) -> None:
        random.seed(7)
        exam3 = _build_mock_v2_exam_im(_SURVEY, difficulty=3)
        random.seed(7)
        exam4 = _build_mock_v2_exam_im(_SURVEY, difficulty=4)
        self.assertEqual(
            [(q["question_number"], q["opic_type"], q.get("bank_slot")) for q in exam3],
            [(q["question_number"], q["opic_type"], q.get("bank_slot")) for q in exam4],
        )

    def test_im_exam_structure_seeds(self) -> None:
        for lev in (3, 4):
            for seed in (0, 1, 42):
                random.seed(seed)
                exam = build_mock_v2_exam(_SURVEY, difficulty=lev)
                self.assertEqual(len(exam), 15, f"lev={lev} seed={seed}")

                q14 = exam[13]
                q15 = exam[14]
                self.assertEqual(q14["question_number"], 14)
                self.assertEqual(q14["bank_slot"], "q1")
                self.assertEqual(q14["opic_type"], "Q1")
                self.assertEqual(q14["combo"], "Advanced")

                self.assertEqual(q15["question_number"], 15)
                self.assertEqual(q15["opic_type"], "Q5")
                self.assertEqual(q15["step"], "질문하기 (Ask the Interviewer)")
                self.assertEqual(q15["combo"], "Advanced")
                self.assertTrue(q15.get("topic_id"))
                self.assertTrue(q15.get("question_text"))

                combo_topics = [
                    exam[i]["topic_id"]
                    for i in (1, 4, 7, 13)
                ]
                self.assertEqual(len(set(combo_topics)), 4, f"t1–t4 unique lev={lev} seed={seed}")

                self.assertEqual(exam[6]["bank_slot"] in ("q3", "q4"), True)
                self.assertEqual(exam[8]["bank_slot"], "q3")
                self.assertEqual(exam[9]["bank_slot"], "q4")

    def test_sparse_survey_still_builds(self) -> None:
        for lev in (3, 4):
            for seed in range(10):
                random.seed(seed)
                exam = build_mock_v2_exam(_SURVEY_SPARSE, difficulty=lev)
                self.assertEqual(len(exam), 15)
                self.assertEqual(exam[13]["opic_type"], "Q1")
                self.assertEqual(exam[14]["opic_type"], "Q5")


if __name__ == "__main__":
    unittest.main()
