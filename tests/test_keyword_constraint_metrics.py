"""Unit tests for keyword constraint transcript metrics."""

from __future__ import annotations

import unittest

from services.keyword_constraint_metrics import compute_keyword_constraint_metrics


class KeywordConstraintMetricsTest(unittest.TestCase):
    def test_targets_detected_case_insensitive(self) -> None:
        transcript = (
            "My favorite park is within walking distance. "
            "I usually head to it on weekends."
        )
        out = compute_keyword_constraint_metrics(
            transcript,
            ["within walking distance", "head to", "hooked on"],
            [],
        )
        by_expr = {row["expr"]: row for row in out["targets"]}
        self.assertTrue(by_expr["within walking distance"]["used"])
        self.assertEqual(by_expr["within walking distance"]["count"], 1)
        self.assertTrue(by_expr["head to"]["used"])
        self.assertFalse(by_expr["hooked on"]["used"])
        self.assertEqual(out["target_used_count"], 2)
        self.assertEqual(out["target_total"], 3)

    def test_banned_word_boundary_avoids_false_positives(self) -> None:
        transcript = "I am alike to hiking but I like parks and I like trees."
        out = compute_keyword_constraint_metrics(
            transcript,
            [],
            ["like", "many"],
        )
        like_row = next(r for r in out["banned"] if r["expr"] == "like")
        many_row = next(r for r in out["banned"] if r["expr"] == "many")
        self.assertTrue(like_row["hit"])
        self.assertEqual(like_row["count"], 2)
        self.assertFalse(many_row["hit"])
        self.assertEqual(out["banned_hit_count"], 1)

    def test_banned_multi_word_substring(self) -> None:
        transcript = "I feel very happy when I visit the park."
        out = compute_keyword_constraint_metrics(
            transcript,
            [],
            ["very happy"],
        )
        row = out["banned"][0]
        self.assertTrue(row["hit"])
        self.assertEqual(row["count"], 1)

    def test_many_not_matching_inside_other_words(self) -> None:
        transcript = "There are manysomething issues but not many parks."
        out = compute_keyword_constraint_metrics(transcript, [], ["many"])
        row = out["banned"][0]
        self.assertTrue(row["hit"])
        self.assertEqual(row["count"], 1)

    def test_targets_with_ko_dict_structure(self) -> None:
        transcript = "I'm really into gripping movies and I binge-watch them."
        targets = [
            {"expr": "into", "ko": "~에 빠진"},
            {"expr": "gripping", "ko": "몰입하게 하는"},
            {"expr": "binge-watch", "ko": "몰아보다"},
        ]
        out = compute_keyword_constraint_metrics(transcript, targets, [])
        self.assertEqual(out["target_used_count"], 3)
        by_expr = {row["expr"]: row for row in out["targets"]}
        self.assertEqual(by_expr["into"]["ko"], "~에 빠진")
        self.assertTrue(by_expr["gripping"]["used"])
        self.assertTrue(by_expr["binge-watch"]["used"])


if __name__ == "__main__":
    unittest.main()
