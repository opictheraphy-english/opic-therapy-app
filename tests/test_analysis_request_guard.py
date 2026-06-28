"""Tests for utils.analysis_request_guard."""

from __future__ import annotations

import time
import unittest

from utils.analysis_request_guard import (
    DEFAULT_COOLDOWN_BASE_SEC,
    DEFAULT_COOLDOWN_MAX_SEC,
    DEFAULT_COOLDOWN_STEP_SEC,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_STALE_SEC,
    button_state,
    can_request,
    clear_guard,
    clear_stale_in_flight,
    cooldown_remaining,
    key_attempts,
    key_cooldown_until,
    key_in_flight,
    key_in_flight_at,
    key_user_notice,
    register_failure,
    reset_guard,
    set_in_flight,
)

_PREFIX = "topic_v2_feedback"
_LABELS = {
    "in_flight": "피드백 생성 중…",
    "cooldown": "피드백 다시 받기 ({remaining}초 후)",
    "maxed": "피드백 시도 한도 도달",
    "idle": "AI 짧은 피드백 받기",
}


class AnalysisRequestGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.t0 = 1_700_000_000.0
        self.ss: dict = {}

    def test_set_in_flight_set_and_clear(self) -> None:
        set_in_flight(self.ss, _PREFIX, True, now=self.t0)
        self.assertTrue(self.ss[key_in_flight(_PREFIX)])
        self.assertEqual(self.ss[key_in_flight_at(_PREFIX)], self.t0)

        set_in_flight(self.ss, _PREFIX, False)
        self.assertNotIn(key_in_flight(_PREFIX), self.ss)
        self.assertNotIn(key_in_flight_at(_PREFIX), self.ss)

    def test_clear_stale_in_flight_drops_old_flag(self) -> None:
        self.ss[key_in_flight(_PREFIX)] = True
        self.ss[key_in_flight_at(_PREFIX)] = self.t0 - DEFAULT_STALE_SEC - 1
        clear_stale_in_flight(self.ss, _PREFIX, now=self.t0)
        self.assertNotIn(key_in_flight(_PREFIX), self.ss)

    def test_clear_stale_in_flight_keeps_recent_flag(self) -> None:
        self.ss[key_in_flight(_PREFIX)] = True
        self.ss[key_in_flight_at(_PREFIX)] = self.t0
        clear_stale_in_flight(self.ss, _PREFIX, now=self.t0)
        self.assertTrue(self.ss[key_in_flight(_PREFIX)])

    def test_clear_stale_clears_when_timestamp_missing(self) -> None:
        self.ss[key_in_flight(_PREFIX)] = True
        clear_stale_in_flight(self.ss, _PREFIX, now=self.t0)
        self.assertNotIn(key_in_flight(_PREFIX), self.ss)

    def test_cooldown_escalates_and_caps_at_max(self) -> None:
        entity = "answer-1"
        expected = [
            DEFAULT_COOLDOWN_BASE_SEC,
            DEFAULT_COOLDOWN_BASE_SEC + DEFAULT_COOLDOWN_STEP_SEC,
            DEFAULT_COOLDOWN_BASE_SEC + 2 * DEFAULT_COOLDOWN_STEP_SEC,
            DEFAULT_COOLDOWN_MAX_SEC,
            DEFAULT_COOLDOWN_MAX_SEC,
        ]
        for i, exp_cd in enumerate(expected, start=1):
            n = register_failure(
                self.ss,
                _PREFIX,
                entity,
                "api_error",
                now=self.t0,
            )
            self.assertEqual(n, i)
            until = float(self.ss[key_cooldown_until(_PREFIX)])
            self.assertEqual(int(until - self.t0), exp_cd)

    def test_exempt_category_skips_cooldown(self) -> None:
        register_failure(self.ss, _PREFIX, "default", "api_key", now=self.t0)
        self.assertNotIn(key_cooldown_until(_PREFIX), self.ss)
        self.assertEqual(self.ss[key_attempts(_PREFIX)]["default"], 1)

    def test_max_attempts_blocks_can_request(self) -> None:
        entity = "answer-1"
        for _ in range(DEFAULT_MAX_ATTEMPTS):
            register_failure(self.ss, _PREFIX, entity, "api_key", now=self.t0)
        allowed, msg = can_request(
            self.ss,
            _PREFIX,
            entity,
            max_attempts=DEFAULT_MAX_ATTEMPTS,
            now=self.t0,
        )
        self.assertFalse(allowed)
        self.assertIsNotNone(msg)

    def test_can_request_blocks_in_flight_and_cooldown(self) -> None:
        set_in_flight(self.ss, _PREFIX, True, now=self.t0)
        allowed, msg = can_request(self.ss, _PREFIX, "default", now=self.t0)
        self.assertFalse(allowed)
        self.assertIn("처리 중", msg or "")

        set_in_flight(self.ss, _PREFIX, False)
        self.ss[key_cooldown_until(_PREFIX)] = self.t0 + 30
        allowed, msg = can_request(self.ss, _PREFIX, "default", now=self.t0)
        self.assertFalse(allowed)
        self.assertIn("30", msg or "")

    def test_default_entity_id_works(self) -> None:
        register_failure(self.ss, _PREFIX, "default", "api_error", now=self.t0)
        self.assertEqual(self.ss[key_attempts(_PREFIX)]["default"], 1)
        clear_guard(self.ss, _PREFIX, "default")
        self.assertEqual(self.ss[key_attempts(_PREFIX)], {})

    def test_button_state_label_branches(self) -> None:
        disabled, label = button_state(
            self.ss, _PREFIX, "e1", labels=_LABELS, now=self.t0
        )
        self.assertFalse(disabled)
        self.assertEqual(label, _LABELS["idle"])

        set_in_flight(self.ss, _PREFIX, True, now=self.t0)
        disabled, label = button_state(
            self.ss, _PREFIX, "e1", labels=_LABELS, now=self.t0
        )
        self.assertTrue(disabled)
        self.assertEqual(label, _LABELS["in_flight"])

        set_in_flight(self.ss, _PREFIX, False)
        self.ss[key_cooldown_until(_PREFIX)] = self.t0 + 12
        disabled, label = button_state(
            self.ss, _PREFIX, "e1", labels=_LABELS, now=self.t0
        )
        self.assertTrue(disabled)
        self.assertEqual(label, "피드백 다시 받기 (12초 후)")

        self.ss.pop(key_cooldown_until(_PREFIX), None)
        for _ in range(DEFAULT_MAX_ATTEMPTS):
            register_failure(self.ss, _PREFIX, "e1", "api_key", now=self.t0)
        disabled, label = button_state(
            self.ss,
            _PREFIX,
            "e1",
            labels=_LABELS,
            max_attempts=DEFAULT_MAX_ATTEMPTS,
            now=self.t0,
        )
        self.assertTrue(disabled)
        self.assertEqual(label, _LABELS["maxed"])

    def test_button_state_cooldown_callable_label(self) -> None:
        labels = dict(_LABELS)
        labels["cooldown"] = lambda rem: f"wait {rem}s"
        self.ss[key_cooldown_until(_PREFIX)] = self.t0 + 7
        disabled, label = button_state(
            self.ss, _PREFIX, "e1", labels=labels, now=self.t0
        )
        self.assertTrue(disabled)
        self.assertEqual(label, "wait 7s")

    def test_clear_guard_clears_cooldown_and_notice(self) -> None:
        self.ss[key_cooldown_until(_PREFIX)] = self.t0 + 60
        self.ss[key_user_notice(_PREFIX)] = "blocked"
        register_failure(self.ss, _PREFIX, "e1", "api_error", now=self.t0)
        clear_guard(self.ss, _PREFIX, "e1")
        self.assertNotIn(key_cooldown_until(_PREFIX), self.ss)
        self.assertNotIn(key_user_notice(_PREFIX), self.ss)
        self.assertNotIn("e1", self.ss[key_attempts(_PREFIX)])

    def test_reset_guard_clears_all_prefix_keys(self) -> None:
        set_in_flight(self.ss, _PREFIX, True, now=self.t0)
        self.ss[key_cooldown_until(_PREFIX)] = self.t0 + 90
        self.ss[key_user_notice(_PREFIX)] = "notice"
        self.ss[key_attempts(_PREFIX)] = {"e1": 2}
        reset_guard(self.ss, _PREFIX)
        self.assertNotIn(key_in_flight(_PREFIX), self.ss)
        self.assertNotIn(key_in_flight_at(_PREFIX), self.ss)
        self.assertNotIn(key_cooldown_until(_PREFIX), self.ss)
        self.assertNotIn(key_user_notice(_PREFIX), self.ss)
        self.assertEqual(self.ss[key_attempts(_PREFIX)], {})

    def test_cooldown_remaining(self) -> None:
        self.assertEqual(cooldown_remaining(self.ss, _PREFIX, now=self.t0), 0)
        self.ss[key_cooldown_until(_PREFIX)] = self.t0 + 25.7
        self.assertEqual(cooldown_remaining(self.ss, _PREFIX, now=self.t0), 25)


if __name__ == "__main__":
    unittest.main()
