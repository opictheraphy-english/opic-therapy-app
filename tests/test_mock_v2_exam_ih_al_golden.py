"""Golden tests: IH/AL exam builder (_build_mock_v2_exam_ih_al) must stay stable across refactors."""

from __future__ import annotations

import json
import random
import unittest
from pathlib import Path

from services.mock_exam.mock_exam_test_set_generator import ADVANCED_SET_POOL
from services.mock_v2_question_selector import _build_mock_v2_exam_ih_al, build_mock_v2_exam

_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "mock_v2_exam_ih_al_golden.json"

_SURVEY = {
    "leisure": ["영화 보기", "공원 가기"],
    "interests": ["음악 감상하기", "요리하기"],
    "sports": ["농구", "조깅"],
    "travel": ["국내 여행"],
}


def _serialize_exam(exam: list) -> list:
    return [
        {
            "question_number": q["question_number"],
            "opic_type": q["opic_type"],
            "combo": q["combo"],
            "step": q["step"],
            "topic_id": q.get("topic_id"),
            "bank_slot": q.get("bank_slot"),
            "source_id": q.get("source_id"),
            "question_text": q["question_text"],
        }
        for q in exam
    ]


class MockV2ExamIhAlGoldenTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with _FIXTURE_PATH.open(encoding="utf-8") as f:
            cls.golden = json.load(f)

    def test_router_delegates_to_ih_al_builder(self) -> None:
        random.seed(0)
        via_router = build_mock_v2_exam(_SURVEY, difficulty=5)
        random.seed(0)
        via_builder = _build_mock_v2_exam_ih_al(_SURVEY, difficulty=5)
        self.assertEqual(via_router, via_builder)

    def test_golden_level_5_and_6_seeds_0_to_19(self) -> None:
        mismatches: list[str] = []
        for lev in (5, 6):
            for seed in range(20):
                key = f"lev{lev}_seed{seed}"
                random.seed(seed)
                exam = _build_mock_v2_exam_ih_al(_SURVEY, difficulty=lev)
                actual = _serialize_exam(exam)
                expected = self.golden[key]
                if actual != expected:
                    mismatches.append(key)
        self.assertEqual(mismatches, [], f"Golden mismatch keys: {mismatches}")

    def test_advanced_set_pool_has_20_sets(self) -> None:
        self.assertEqual(len(ADVANCED_SET_POOL), 20)
        ids = [entry["set_id"] for entry in ADVANCED_SET_POOL]
        self.assertEqual(len(set(ids)), 20)
        for entry in ADVANCED_SET_POOL:
            self.assertIn("comparison", entry)
            self.assertIn("news_issue", entry)
            self.assertTrue(entry["comparison"].get("question"))
            self.assertTrue(entry["news_issue"].get("question"))

    def test_q14_q15_same_topic_set(self) -> None:
        for lev in (5, 6):
            for seed in range(20):
                random.seed(seed)
                exam = _build_mock_v2_exam_ih_al(_SURVEY, difficulty=lev)
                q14, q15 = exam[13], exam[14]
                self.assertEqual(q14["topic"], q15["topic"], f"lev={lev} seed={seed}")
                self.assertEqual(q14["opic_type"], "Comparison")
                self.assertEqual(q15["opic_type"], "News/Issue")
                self.assertEqual(q14["step"], "Comparison")
                self.assertEqual(q15["step"], "News/Issue")

    def test_q1_13_slot_structure_unchanged(self) -> None:
        """Bank/roleplay seats (Q1–13) must keep the IH/AL matrix; only Q14–15 content changed."""
        for lev in (5, 6):
            for seed in range(20):
                random.seed(seed)
                exam = _build_mock_v2_exam_ih_al(_SURVEY, difficulty=lev)
                self.assertEqual(len(exam), 15)

                self.assertEqual(exam[0]["opic_type"], "Intro")
                self.assertEqual(exam[0]["combo"], "Intro")

                self.assertEqual([q["bank_slot"] for q in exam[1:4]], ["q1", "q2", "q3"])
                self.assertTrue(all(q["combo"] == "Combo1" for q in exam[1:4]))

                self.assertEqual(exam[4]["bank_slot"], "q1")
                self.assertEqual(exam[5]["bank_slot"], "q3")
                self.assertIn(exam[6]["bank_slot"], ("q2", "q3", "q4"))
                self.assertTrue(all(q["combo"] == "Combo2" for q in exam[4:7]))

                self.assertEqual(exam[7]["bank_slot"], "q1")
                self.assertIn(exam[8]["bank_slot"], ("q2", "q3", "q4"))
                self.assertIn(exam[9]["bank_slot"], ("q3", "q4"))
                self.assertTrue(all(q["combo"] == "Combo3" for q in exam[7:10]))

                self.assertEqual([q["bank_slot"] for q in exam[10:13]], ["q6", "q7", "q8"])
                self.assertTrue(all(q["combo"] == "Roleplay" for q in exam[10:13]))


if __name__ == "__main__":
    unittest.main()
