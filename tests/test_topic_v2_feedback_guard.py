"""Tests for Topic V2 short-feedback guard helpers (via analysis_request_guard)."""

from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

from views import topic_practice_v2 as tpv2


class TopicV2FeedbackGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.t0 = 1_700_000_000.0
        self.session: dict = {}

    def test_clear_stale_feedback_in_flight_drops_old_flag(self) -> None:
        self.session[tpv2._KEY_FB_IN_FLIGHT] = True
        self.session[tpv2._KEY_FB_IN_FLIGHT_AT] = (
            self.t0 - tpv2._FEEDBACK_IN_FLIGHT_STALE_SEC - 5
        )
        with patch.object(tpv2.st, "session_state", self.session, create=True):
            with patch("views.topic_practice_v2.time.time", return_value=self.t0):
                tpv2._clear_stale_feedback_in_flight()
        self.assertNotIn(tpv2._KEY_FB_IN_FLIGHT, self.session)
        self.assertNotIn(tpv2._KEY_FB_IN_FLIGHT_AT, self.session)

    def test_clear_stale_feedback_in_flight_keeps_recent_flag(self) -> None:
        self.session[tpv2._KEY_FB_IN_FLIGHT] = True
        self.session[tpv2._KEY_FB_IN_FLIGHT_AT] = self.t0
        with patch.object(tpv2.st, "session_state", self.session, create=True):
            with patch("views.topic_practice_v2.time.time", return_value=self.t0):
                tpv2._clear_stale_feedback_in_flight()
        self.assertTrue(self.session.get(tpv2._KEY_FB_IN_FLIGHT))

    def test_register_failure_escalates_cooldown(self) -> None:
        with patch.object(tpv2.st, "session_state", self.session, create=True):
            with patch("views.topic_practice_v2.time.time", return_value=self.t0):
                tpv2._register_feedback_failure("api_error", "aid-1")
                tpv2._register_feedback_failure("api_error", "aid-1")
        until = float(self.session[tpv2._KEY_FB_COOLDOWN_UNTIL])
        self.assertEqual(int(until - self.t0), 60)
        self.assertEqual(self.session[tpv2._KEY_FB_ATTEMPTS]["aid-1"], 2)

    def test_can_request_blocks_after_max_attempts(self) -> None:
        self.session[tpv2._KEY_FB_ATTEMPTS] = {"aid-1": 4}
        with patch.object(tpv2.st, "session_state", self.session, create=True):
            allowed, msg = tpv2._can_request_topic_v2_feedback("aid-1")
        self.assertFalse(allowed)
        self.assertIn("시도 횟수", msg)

    def test_reset_guard_clears_prefix_keys(self) -> None:
        self.session[tpv2._KEY_FB_IN_FLIGHT] = True
        self.session[tpv2._KEY_FB_IN_FLIGHT_AT] = self.t0
        self.session[tpv2._KEY_FB_COOLDOWN_UNTIL] = self.t0 + 90
        self.session[tpv2._KEY_FB_ATTEMPTS] = {"aid-1": 2}
        with patch.object(tpv2.st, "session_state", self.session, create=True):
            tpv2._reset_feedback_guard_for_question()
        self.assertNotIn(tpv2._KEY_FB_IN_FLIGHT, self.session)
        self.assertEqual(self.session[tpv2._KEY_FB_ATTEMPTS], {})

    def test_button_state_in_flight_label(self) -> None:
        self.session[tpv2._KEY_FB_IN_FLIGHT] = True
        self.session[tpv2._KEY_FB_IN_FLIGHT_AT] = self.t0
        with patch.object(tpv2.st, "session_state", self.session, create=True):
            with patch("views.topic_practice_v2.time.time", return_value=self.t0):
                disabled, label = tpv2._feedback_request_button_state("aid-1")
        self.assertTrue(disabled)
        self.assertEqual(label, "피드백 생성 중…")

    @patch("views.topic_practice_v2._TOPIC_V2_FEEDBACK_WRAPPER_TIMEOUT_SEC", 0.01)
    @patch("services.topic_practice_v2_analysis.analyze_topic_practice_v2_answer")
    def test_invoke_feedback_analysis_times_out(self, analyze_mock: MagicMock) -> None:
        def _slow(_row: dict) -> dict:
            time.sleep(0.2)
            return {"ok": True, "summary": "late"}

        analyze_mock.side_effect = _slow
        with patch.object(tpv2, "_is_keyword_constraint_mode", return_value=False):
            result = tpv2._invoke_topic_v2_feedback_analysis({"transcript": "hello world test"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["error_category"], "timeout")


if __name__ == "__main__":
    unittest.main()
