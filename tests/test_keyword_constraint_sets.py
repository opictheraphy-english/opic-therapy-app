"""Keyword constraint set data helpers."""

from __future__ import annotations

import unittest

from data.keyword_constraint_sets import (
    KEYWORD_CONSTRAINT_CATEGORY_ORDER,
    PATTERN_POOLS,
    get_keyword_constraint_category,
    get_keyword_constraint_practice_set,
    list_keyword_constraint_sets,
    list_keyword_constraint_sets_by_category,
)


class KeywordConstraintSetsTest(unittest.TestCase):
    def test_list_sets_count(self) -> None:
        sets = list_keyword_constraint_sets()
        self.assertEqual(len(sets), 49)
        self.assertTrue(all(s.get("category") for s in sets))

    def test_category_groups_cover_all_sets(self) -> None:
        groups = list_keyword_constraint_sets_by_category()
        self.assertEqual([g["category"] for g in groups], list(KEYWORD_CONSTRAINT_CATEGORY_ORDER))
        grouped_ids = [s["set_id"] for g in groups for s in g["sets"]]
        all_ids = [s["set_id"] for s in list_keyword_constraint_sets()]
        self.assertEqual(len(grouped_ids), 49)
        self.assertEqual(set(grouped_ids), set(all_ids))

    def test_family_home_in_daily_category(self) -> None:
        self.assertEqual(get_keyword_constraint_category("family_home"), "일상")
        daily = next(g for g in list_keyword_constraint_sets_by_category() if g["category"] == "일상")
        daily_ids = [s["set_id"] for s in daily["sets"]]
        self.assertIn("family_home", daily_ids)
        self.assertEqual(daily_ids.index("family_home"), daily_ids.index("home") + 1)

    def test_cafe_five_combo_rows(self) -> None:
        rows = get_keyword_constraint_practice_set("cafe")
        self.assertEqual(len(rows), 5)
        self.assertEqual(
            [r["combo"] for r in rows],
            ["description", "routine", "experience", "detail_experience", "roleplay"],
        )

    def test_all_sets_have_five_combos_with_ko_targets(self) -> None:
        for entry in list_keyword_constraint_sets():
            sid = entry["set_id"]
            rows = get_keyword_constraint_practice_set(sid)
            self.assertEqual(len(rows), 5, msg=sid)
            for row in rows:
                targets = row["target_expressions"]
                self.assertEqual(len(targets), 4, msg=sid)
                self.assertEqual(len(row["patterns"]), 2, msg=sid)
                for t in targets:
                    self.assertIsInstance(t, dict, msg=sid)
                    self.assertTrue(t.get("expr"), msg=sid)
                    self.assertTrue(t.get("ko"), msg=sid)
                if sid == "cafe":
                    self.assertGreaterEqual(len(row["banned_expressions"]), 3, msg=sid)
                else:
                    self.assertEqual(len(row["banned_expressions"]), 3, msg=sid)

    def test_family_home_practice_row(self) -> None:
        row = get_keyword_constraint_practice_set("family_home")[0]
        self.assertEqual(row["target_expressions"][0]["expr"], "close-knit")
        self.assertEqual(row["target_expressions"][0]["ko"], "끈끈한")

    def test_patterns_assigned_from_pool_by_set_index(self) -> None:
        cafe_desc = get_keyword_constraint_practice_set("cafe")[0]["patterns"]
        home_desc = get_keyword_constraint_practice_set("home")[0]["patterns"]
        pool = PATTERN_POOLS["description"]
        self.assertEqual(cafe_desc, [pool[0], pool[1]])
        self.assertEqual(home_desc, [pool[2], pool[3]])


if __name__ == "__main__":
    unittest.main()
