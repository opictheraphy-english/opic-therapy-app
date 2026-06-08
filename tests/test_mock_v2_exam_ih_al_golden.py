"""Golden tests: IH/AL exam builder (_build_mock_v2_exam_ih_al) must stay stable across refactors."""

from __future__ import annotations

import json
import random
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
