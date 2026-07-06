"""Tests for LLM feedback markdown normalization."""

from __future__ import annotations

import unittest

from utils.feedback_text import (
    normalize_feedback_md,
    normalize_feedback_md_html,
    parse_prescription_sections,
    parse_weakness_bullet,
    split_improved_answer_and_mission,
    strip_bracket_labels,
)


class FeedbackTextTest(unittest.TestCase):
    def test_strip_bracket_labels(self) -> None:
        self.assertEqual(
            strip_bracket_labels("[A] 질문 내용"),
            "질문 내용",
        )
        self.assertEqual(
            strip_bracket_labels("[D-ii] 코칭 피드백"),
            "코칭 피드백",
        )

    def test_normalize_demotes_headings(self) -> None:
        raw = "## 답변의 방향은 좋았어\n\n본문 설명"
        out = normalize_feedback_md(raw)
        self.assertNotIn("#", out)
        self.assertIn("답변의 방향은 좋았어", out)
        self.assertIn("본문 설명", out)

    def test_normalize_html_no_h_tags(self) -> None:
        html_out = normalize_feedback_md_html("### 큰 제목\n\n- bullet")
        self.assertNotIn("<h1", html_out.lower())
        self.assertNotIn("<h2", html_out.lower())
        self.assertIn("eqfd-md-label", html_out)

    def test_parse_weakness_score(self) -> None:
        label, score, aux = parse_weakness_bullet("문법 · 평균 55.0")
        self.assertEqual(label, "문법")
        self.assertEqual(score, 55.0)
        self.assertEqual(aux, "")

    def test_split_mission_from_model_answer(self) -> None:
        text = (
            "I usually wake up early.\n\n"
            "다음 답변 미션\n"
            "1. because를 한 번 써 보세요\n"
            "2. 구체적 시간을 넣어 보세요"
        )
        answer, missions = split_improved_answer_and_mission(text)
        self.assertIn("wake up early", answer)
        self.assertEqual(len(missions), 2)

    def test_parse_prescription_connectors(self) -> None:
        parsed = parse_prescription_sections(
            "담화 연결을 강화하세요.\n연결어 예시: First of all, Moreover, In addition"
        )
        self.assertTrue(parsed["body"])
        self.assertIn("First of all", parsed["connectors"])


if __name__ == "__main__":
    unittest.main()
