"""Tests for random mini mock V2 question assembly from opic_question_bank_v2."""

from __future__ import annotations

import unittest

from services.mock_v2_question_selector import build_mini_mock_v2_questions


class MiniMockV2QuestionSelectorTests(unittest.TestCase):
    def test_three_question_structure(self) -> None:
        exam = build_mini_mock_v2_questions()
        self.assertEqual(len(exam), 3)
        self.assertEqual([q["question_index"] for q in exam], [0, 1, 2])
        self.assertEqual(exam[0]["type"], "description")
        self.assertEqual(exam[0]["type_label"], "묘사")
        self.assertEqual(exam[0]["bank_slot"], "q1")
        self.assertEqual(exam[1]["type"], "memorable_experience")
        self.assertEqual(exam[1]["type_label"], "기억에 남는 경험")
        self.assertEqual(exam[1]["bank_slot"], "q4")
        self.assertEqual(exam[2]["type"], "roleplay")
        self.assertEqual(exam[2]["type_label"], "롤플레이")
        self.assertEqual(exam[2]["bank_slot"], "q7")
        for q in exam:
            self.assertTrue(str(q.get("question_en") or "").strip())
            self.assertTrue(str(q.get("question_id") or "").strip())

    def test_five_runs_produce_variety(self) -> None:
        signatures: set[str] = set()
        for _ in range(5):
            exam = build_mini_mock_v2_questions()
            sig = "|".join(
                str(q.get("source_id") or q.get("question_id") or "")
                for q in exam
            )
            signatures.add(sig)
        self.assertGreater(
            len(signatures),
            1,
            "expected at least 2 distinct 3-question sets in 5 random draws",
        )

    def test_q1_and_q2_topics_often_differ(self) -> None:
        different = 0
        for _ in range(10):
            exam = build_mini_mock_v2_questions()
            if exam[0].get("topic_id") != exam[1].get("topic_id"):
                different += 1
        self.assertGreaterEqual(different, 5)


if __name__ == "__main__":
    unittest.main()
