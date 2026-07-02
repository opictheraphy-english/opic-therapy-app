"""Home dashboard stats aggregation."""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from utils.home_stats import (
    _answer_count_for_row,
    _compute_streak_days,
    _mode_level,
    get_home_stats,
    progress_tagline,
    ring_fill_pct,
)
from views.topic_practice_v2 import _aggregate_topic_v2_overall_level


class TopicV2LevelAggregateTests(unittest.TestCase):
    def test_mode_with_tie_picks_higher(self) -> None:
        results = [
            {"short_feedback": {"answer_level": "IM2"}},
            {"short_feedback": {"answer_level": "IM3"}},
            {"short_feedback": {"answer_level": "IM2"}},
            {"short_feedback": {"answer_level": "IM3"}},
        ]
        self.assertEqual(_aggregate_topic_v2_overall_level(results), "IM3")

    def test_no_valid_levels_returns_none(self) -> None:
        self.assertIsNone(_aggregate_topic_v2_overall_level([{"short_feedback": {}}]))


class AnswerCountTests(unittest.TestCase):
    def test_topic_practice_uses_answers_count(self) -> None:
        row = {
            "practice_type": "topic_practice",
            "content": {"answers_count": 2, "results": [{}, {}, {}]},
        }
        self.assertEqual(_answer_count_for_row(row), 2)

    def test_mock_exam_defaults_to_15(self) -> None:
        row = {"practice_type": "mock_exam", "content": {}}
        self.assertEqual(_answer_count_for_row(row), 15)

    def test_script_is_one(self) -> None:
        row = {"practice_type": "script_coaching", "content": {}}
        self.assertEqual(_answer_count_for_row(row), 1)


class StreakTests(unittest.TestCase):
    def test_streak_continues_from_yesterday_if_no_today(self) -> None:
        today = date(2026, 6, 4)
        dates = [today - timedelta(days=1), today - timedelta(days=2)]
        self.assertEqual(_compute_streak_days(dates, today=today), 2)

    def test_streak_zero_if_gap(self) -> None:
        today = date(2026, 6, 4)
        dates = [today - timedelta(days=3)]
        self.assertEqual(_compute_streak_days(dates, today=today), 0)


class LevelDisplayTests(unittest.TestCase):
    def test_gap_tagline(self) -> None:
        self.assertIn("두 계단", progress_tagline("IM2", "IH"))
        self.assertIn("목표 달성", progress_tagline("IH", "IH"))

    def test_ring_fill(self) -> None:
        self.assertGreater(ring_fill_pct("IM2", "IH"), 0)
        self.assertEqual(ring_fill_pct("IH", "IH"), 100)

    def test_mode_needs_three_samples(self) -> None:
        self.assertEqual(_mode_level(["IM2", "IM2"]), "IM2")


class GetHomeStatsGuestTests(unittest.TestCase):
    def test_none_without_user(self) -> None:
        self.assertIsNone(get_home_stats(None))


if __name__ == "__main__":
    unittest.main()
