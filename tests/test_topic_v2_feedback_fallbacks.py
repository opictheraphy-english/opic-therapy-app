"""Tests for Topic V2 feedback empty-field fallbacks."""

from __future__ import annotations

import unittest

from components.exam_feedback_screen import (
    build_feedback_keyword_chips_html,
    build_feedback_summary_html,
)
from services.topic_practice_v2_analysis import (
    TOPIC_V2_KEYWORD_DRILL_EMPTY_MESSAGE,
    _FALLBACK_UPGRADE_SAMPLE,
    _apply_ok_field_fallbacks,
    _coerce_answer_level,
    _extract_answer_level_token_from_text,
    _fallback_keyword_drill_from_topic,
    _fallback_upgrade_sample_from_answer,
    _normalize_success,
)


class TopicV2FeedbackFallbackTests(unittest.TestCase):
    def test_upgrade_sample_from_transcript_preserves_short_answer(self) -> None:
        from services.topic_practice_v2_analysis import _upgrade_sample_from_transcript

        transcript = (
            "I like to go to the cafe. I like coffee very much. "
            "I go there every week. I read books there."
        )
        sample = _upgrade_sample_from_transcript(transcript)
        self.assertEqual(sample.count("."), 4)
        self.assertIn("enjoy", sample.lower())

    def test_apply_ok_field_fallbacks_upgrade_sample_from_transcript(self) -> None:
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
        answer = {
            "topic": "unknown_topic_xyz",
            "transcript": "I like to go to the cafe. I like coffee very much.",
        }
        _apply_ok_field_fallbacks(norm, answer)
        self.assertNotEqual(norm["upgrade_sample"], _FALLBACK_UPGRADE_SAMPLE)
        self.assertIn("enjoy", norm["upgrade_sample"].lower())

    def test_fallback_upgrade_sample_uses_correction_arrow_pairs(self) -> None:
        norm = _normalize_success(
            {
                "summary": "ok",
                "strength": "ok",
                "correction_focus": (
                    '"what kind of songs you are interested" → "what kinds of songs you are interested in"'
                ),
                "better_expression": "ok",
                "upgrade_sample": "",
                "keyword_drill": ["because"],
                "practice_mission": "ok",
            }
        )
        answer = {
            "transcript": "I like what kind of songs you are interested when I study.",
        }
        sample = _fallback_upgrade_sample_from_answer(answer, norm)
        self.assertIn("interested in", sample.lower())
        self.assertNotEqual(sample, _FALLBACK_UPGRADE_SAMPLE)

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

    def test_coerce_answer_level_aliases(self) -> None:
        self.assertEqual(_coerce_answer_level("im2"), "IM2")
        self.assertEqual(_coerce_answer_level("IM 2"), "IM2")
        self.assertEqual(_coerce_answer_level(" AL "), "AL")
        self.assertEqual(_coerce_answer_level("IM"), "IM2")
        self.assertEqual(_coerce_answer_level("Intermediate Mid"), "IM2")
        self.assertEqual(_coerce_answer_level("intermediate high"), "IH")
        self.assertEqual(_coerce_answer_level("IM4"), "")

    def test_extract_level_from_summary_text(self) -> None:
        self.assertEqual(
            _extract_answer_level_token_from_text("전반적으로 IM3 수준의 답변입니다."),
            "IM3",
        )
        self.assertEqual(
            _extract_answer_level_token_from_text("Shows IM level connected speech."),
            "IM2",
        )

    def test_apply_ok_field_fallbacks_recovers_level_from_summary(self) -> None:
        norm = _normalize_success(
            {
                "answer_level": "",
                "summary": "문장 연결이 좋고 IM2에 가깝습니다.",
                "strength": "ok",
                "correction_focus": "ok",
                "better_expression": "ok",
                "upgrade_sample": "Sample.",
                "keyword_drill": ["because"],
                "practice_mission": "ok",
            }
        )
        _apply_ok_field_fallbacks(norm, {})
        self.assertEqual(norm["answer_level"], "IM2")
        self.assertFalse(norm.get("answer_level_missing"))

    def test_apply_ok_field_fallbacks_marks_missing_when_no_level(self) -> None:
        norm = _normalize_success(
            {
                "answer_level": "",
                "summary": "문법과 흐름이 자연스럽습니다.",
                "strength": "ok",
                "correction_focus": "ok",
                "better_expression": "ok",
                "upgrade_sample": "Sample.",
                "keyword_drill": ["because"],
                "practice_mission": "ok",
            }
        )
        _apply_ok_field_fallbacks(norm, {})
        self.assertEqual(norm["answer_level"], "")
        self.assertTrue(norm.get("answer_level_missing"))

    def test_summary_html_shows_missing_level_hint(self) -> None:
        html = build_feedback_summary_html(
            "요약입니다.",
            answer_level="",
            answer_level_missing=True,
        )
        self.assertIn("등급 미표시", html)
        self.assertIn("재요청 시 표시될 수 있어요", html)


if __name__ == "__main__":
    unittest.main()
