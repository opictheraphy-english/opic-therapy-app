"""Tests for Topic V2 feedback empty-field fallbacks."""

from __future__ import annotations

import unittest

from components.exam_feedback_screen import build_feedback_keyword_chips_html
from services.topic_practice_v2_analysis import (
    TOPIC_V2_KEYWORD_DRILL_EMPTY_MESSAGE,
    _FALLBACK_UPGRADE_SAMPLE,
    _apply_ok_field_fallbacks,
    _fallback_keyword_drill_from_topic,
    _normalize_success,
)


class TopicV2FeedbackFallbackTests(unittest.TestCase):
    def test_apply_ok_field_fallbacks_upgrade_sample(self) -> None:
        norm = _normalize_success(
            {
                "summary": "ok",
                "strength": "ok",
                "correction_focus": "ok",
                "better_expression": "ok",
                "upgrade_sample": "",
                "keyword_drill": ["because"],
                "practice_mission": "ok",
            }
        )
        _apply_ok_field_fallbacks(norm, {"topic": "unknown_topic_xyz"})
        self.assertEqual(norm["upgrade_sample"], _FALLBACK_UPGRADE_SAMPLE)

    def test_apply_ok_field_fallbacks_preserves_nonempty_upgrade(self) -> None:
        norm = _normalize_success(
            {
                "summary": "ok",
                "strength": "ok",
                "correction_focus": "ok",
                "better_expression": "ok",
                "upgrade_sample": "I usually go there on weekends.",
                "keyword_drill": ["because"],
                "practice_mission": "ok",
            }
        )
        _apply_ok_field_fallbacks(norm, {})
        self.assertEqual(norm["upgrade_sample"], "I usually go there on weekends.")

    def test_fallback_keyword_drill_from_topic_cafe(self) -> None:
        drills = _fallback_keyword_drill_from_topic({"topic": "cafe"})
        self.assertGreaterEqual(len(drills), 2)
        self.assertLessEqual(len(drills), 3)

    def test_apply_ok_field_fallbacks_uses_topic_pool_when_drill_empty(self) -> None:
        norm = _normalize_success(
            {
                "summary": "ok",
                "strength": "ok",
                "correction_focus": "ok",
                "better_expression": "ok",
                "upgrade_sample": "Sample line.",
                "keyword_drill": [],
                "practice_mission": "ok",
            }
        )
        _apply_ok_field_fallbacks(norm, {"topic": "cafe"})
        self.assertGreaterEqual(len(norm["keyword_drill"]), 2)

    def test_keyword_chips_empty_shows_hint_not_dash(self) -> None:
        html = build_feedback_keyword_chips_html(
            [],
            empty_message=TOPIC_V2_KEYWORD_DRILL_EMPTY_MESSAGE,
        )
        self.assertIn(TOPIC_V2_KEYWORD_DRILL_EMPTY_MESSAGE, html)
        self.assertNotIn(">—<", html)

    def test_keyword_chips_nonempty_unchanged(self) -> None:
        html = build_feedback_keyword_chips_html(
            ["because", "actually"],
            empty_message=TOPIC_V2_KEYWORD_DRILL_EMPTY_MESSAGE,
        )
        self.assertIn("because", html)
        self.assertIn("actually", html)
        self.assertNotIn(TOPIC_V2_KEYWORD_DRILL_EMPTY_MESSAGE, html)


if __name__ == "__main__":
    unittest.main()
