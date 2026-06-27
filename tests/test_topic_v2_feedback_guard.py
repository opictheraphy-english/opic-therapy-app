"""Tests for Topic V2 short-feedback guard helpers."""

from __future__ import annotations

import time
import unittest
from unittest.mock import MagicMock, patch

from views import topic_practice_v2 as tpv2


class TopicV2FeedbackGuardTests(unittest.TestCase):
    def test_clear_stale_feedback_in_flight_drops_old_flag(self) -> None:
        session = {
            tpv2._KEY_FB_IN_FLIGHT: True,
            tpv2._KEY_FB_IN_FLIGHT_AT: time.time() - (tpv2._FEEDBACK_IN_FLIGHT_STALE_SEC + 5),
        }
        with patch.object(tpv2.st, "session_state", session, create=True):
            tpv2._clear_stale_feedback_in_flight()
        self.assertNotIn(tpv2._KEY_FB_IN_FLIGHT, session)
        self.assertNotIn(tpv2._KEY_FB_IN_FLIGHT_AT, session)

    def test_clear_stale_feedback_in_flight_keeps_recent_flag(self) -> None:
        session = {
            tpv2._KEY_FB_IN_FLIGHT: True,
            tpv2._KEY_FB_IN_FLIGHT_AT: time.time(),
        }
        with patch.object(tpv2.st, "session_state", session, create=True):
            tpv2._clear_stale_feedback_in_flight()
        self.assertTrue(session.get(tpv2._KEY_FB_IN_FLIGHT))

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
