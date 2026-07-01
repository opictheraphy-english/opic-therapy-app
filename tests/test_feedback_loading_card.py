"""Tests for feedback loading card helpers."""

from __future__ import annotations

import unittest

from components.feedback_loading_card import (
    _FLAT_TARGET_EXPRESSIONS,
    _flatten_target_expressions,
    _normalize_html_one_line,
    _pick_sample_expressions,
    render_feedback_loading_card,
)


class FeedbackLoadingCardTests(unittest.TestCase):
    def test_flatten_dedupes_by_expr(self) -> None:
        flat = _flatten_target_expressions()
        self.assertGreater(len(flat), 100)
        exprs = [item["expr"] for item in flat]
        self.assertEqual(len(exprs), len(set(exprs)))
        self.assertTrue(all("expr" in item and "ko" in item for item in flat))

    def test_module_cache_matches_helper(self) -> None:
        self.assertEqual(len(_FLAT_TARGET_EXPRESSIONS), len(_flatten_target_expressions()))

    def test_pick_sample_size(self) -> None:
        sample = _pick_sample_expressions()
        self.assertGreaterEqual(len(sample), 5)
        self.assertLessEqual(len(sample), 8)

    def test_build_html_one_line(self) -> None:
        from components.feedback_loading_card import _build_card_html

        block = _build_card_html(
            card_id="test-card",
            message='AI "분석" 중',
            expressions=[{"expr": "cozy", "ko": "아늑한"}],
        )
        line = _normalize_html_one_line(block)
        self.assertNotIn("\n", line)
        self.assertIn("오늘의 표현", line)
        self.assertIn("setInterval", line)
        self.assertIn("cozy", line)

    def test_render_calls_markdown(self) -> None:
        import streamlit as st
        from unittest.mock import patch

        with patch.object(st, "markdown") as md_mock:
            render_feedback_loading_card(message="테스트")
        md_mock.assert_called_once()
        html_arg = md_mock.call_args[0][0]
        self.assertIn("opic-fb-loading", html_arg)
        self.assertIn("unsafe_allow_html", md_mock.call_args[1])


if __name__ == "__main__":
    unittest.main()
