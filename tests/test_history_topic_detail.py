"""History detail helpers for topic practice records."""

from __future__ import annotations

import unittest

from views.history import (
    _format_correction_focus_html,
    _is_topic_practice_record,
    _opic_header_label,
    _question_text_from_item,
    _resolve_short_feedback,
    _short_feedback_keywords,
    _short_feedback_text,
    _truncate_preview,
)


class HistoryTopicDetailTest(unittest.TestCase):
    def test_is_topic_practice_record(self) -> None:
        self.assertTrue(
            _is_topic_practice_record("topic_practice", {"report_source": "other"})
        )
        self.assertTrue(
            _is_topic_practice_record("mock_exam", {"report_source": "topic_practice_v2"})
        )
        self.assertFalse(_is_topic_practice_record("mock_exam", {"report_source": "mock_v2"}))

    def test_truncate_preview_uses_ellipsis(self) -> None:
        text = "Tell me about a well-known company in your country"
        out = _truncate_preview(text, 40)
        self.assertTrue(out.endswith("…"))
        self.assertLess(len(out), len(text))

    def test_question_text_prefers_full_question_field(self) -> None:
        item = {
            "question": "Full question text here",
            "topic": "Truncated topic",
        }
        self.assertEqual(_question_text_from_item(item), "Full question text here")

    def test_resolve_short_feedback_from_dict(self) -> None:
        fb = {
            "ok": True,
            "summary": "Nice flow",
            "strength": "Clear opener",
            "keyword_drill": ["because", "for example"],
        }
        resolved = _resolve_short_feedback({"short_feedback": fb})
        self.assertIsNotNone(resolved)
        assert resolved is not None
        self.assertEqual(resolved["summary"], "Nice flow")
        self.assertEqual(_short_feedback_text(resolved, "strength"), "Clear opener")
        self.assertEqual(_short_feedback_keywords(resolved), ["because", "for example"])

    def test_resolve_short_feedback_legacy_string(self) -> None:
        resolved = _resolve_short_feedback({"feedback": "Legacy one-line feedback"})
        self.assertEqual(resolved, {"summary": "Legacy one-line feedback"})

    def test_resolve_short_feedback_missing(self) -> None:
        self.assertIsNone(_resolve_short_feedback({"transcript": "hello"}))
        self.assertIsNone(
            _resolve_short_feedback({"short_feedback": {"ok": False, "summary": "x"}})
        )

    def test_opic_header_label(self) -> None:
        self.assertEqual(_opic_header_label("Q1", 1), "Q1 · 묘사")
        self.assertEqual(_opic_header_label("Q3", 3), "Q3 · 경험")

    def test_correction_focus_quote_arrow(self) -> None:
        html_out = _format_correction_focus_html(
            '"what kind of songs you are interested" → 전치사가 빠졌으니 "interested in"으로.'
        )
        self.assertIn("hist-correction-orig", html_out)
        self.assertIn("hist-correction-fix", html_out)
        self.assertIn("what kind of songs you are interested", html_out)

    def test_correction_focus_plain_text(self) -> None:
        html_out = _format_correction_focus_html("다음에는 이유를 한 문장 더 추가해 보세요.")
        self.assertIn("hist-card-body", html_out)
        self.assertNotIn("hist-correction-orig", html_out)


if __name__ == "__main__":
    unittest.main()
