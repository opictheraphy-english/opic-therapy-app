"""Unit tests for content-word counting (speech-rate metrics)."""

import unittest

from services.speech_rate_scoring import count_content_words
from services.topic_practice_v2_analysis import (
    _coerce_answer_level,
    _normalize_success,
    _stringify_result,
)


class TestCountContentWords(unittest.TestCase):
    def test_fillers_and_stutter_repeats_excluded(self):
        text = "uh um I think I think movies are are fun"
        self.assertEqual(count_content_words(text), 5)

    def test_discourse_markers_preserved(self):
        text = "well you know I like movies so actually it is fun"
        self.assertEqual(count_content_words(text), 11)

    def test_like_preserved_not_treated_as_filler(self):
        text = "I like like action movies"
        # adjacent duplicate "like" collapses to one; discourse "like" kept when not repeated
        self.assertEqual(count_content_words(text), 4)

    def test_separated_repeats_not_collapsed(self):
        text = "I think movies are fun and I think again"
        self.assertEqual(count_content_words(text), 9)

    def test_punctuation_stripped_for_fillers(self):
        text = "Uh, um... I think."
        self.assertEqual(count_content_words(text), 2)


class TestTopicV2FeedbackSummary(unittest.TestCase):
    def test_normalize_success_does_not_append_speech_band(self):
        parsed = {
            "summary": "문법과 어휘가 자연스럽습니다.",
            "strength": "좋아요.",
            "correction_focus": "괜찮습니다.",
            "better_expression": "ok",
            "upgrade_sample": "Sample.",
            "keyword_drill": ["because"],
            "practice_mission": "연습하세요.",
        }
        result = _normalize_success(parsed)
        summary = result.get("summary") or ""
        self.assertNotIn("추정", summary)
        self.assertNotIn("밴드", summary)
        self.assertEqual(summary, "문법과 어휘가 자연스럽습니다.")

    def test_normalize_success_coerces_answer_level(self):
        parsed = {
            "answer_level": "im2",
            "summary": "문법과 어휘가 자연스럽습니다.",
            "strength": "좋아요.",
            "correction_focus": "괜찮습니다.",
            "better_expression": "ok",
            "upgrade_sample": "Sample.",
            "keyword_drill": ["because"],
            "practice_mission": "연습하세요.",
        }
        result = _normalize_success(parsed)
        self.assertEqual(result.get("answer_level"), "IM2")

    def test_coerce_answer_level_rejects_invalid(self):
        self.assertEqual(_coerce_answer_level("IH"), "IH")
        self.assertEqual(_coerce_answer_level("  al "), "AL")
        self.assertEqual(_coerce_answer_level("IM4"), "")
        self.assertEqual(_coerce_answer_level(""), "")

    def test_stringify_result_includes_answer_level(self):
        out = _stringify_result({"ok": True, "answer_level": "NH", "summary": "ok"})
        self.assertEqual(out.get("answer_level"), "NH")
        fail = _stringify_result({"ok": False, "answer_level": "bogus"})
        self.assertEqual(fail.get("answer_level"), "")


if __name__ == "__main__":
    unittest.main()
