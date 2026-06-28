"""Tests for mini_mock_v2 analysis and STT-retry request guards."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from utils.analysis_request_guard import key_cooldown_until, key_in_flight
from views import mini_mock_v2 as mv


class MiniMockV2GuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.t0 = 1_700_000_000.0
        self.session: dict = {}

    def test_analysis_button_in_flight_disabled(self) -> None:
        self.session[key_in_flight(mv._ANALYSIS_GUARD_PREFIX)] = True
        self.session[f"{mv._ANALYSIS_GUARD_PREFIX}_in_flight_at"] = self.t0
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                disabled, label = mv._analysis_button_state()
        self.assertTrue(disabled)
        self.assertEqual(label, "리포트 생성 중…")

    def test_try_start_analysis_blocked_when_in_flight(self) -> None:
        self.session[key_in_flight(mv._ANALYSIS_GUARD_PREFIX)] = True
        self.session[f"{mv._ANALYSIS_GUARD_PREFIX}_in_flight_at"] = self.t0
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                with patch.object(mv, "_begin_v2_analysis") as begin_mock:
                    ok = mv._try_start_v2_analysis()
        self.assertFalse(ok)
        begin_mock.assert_not_called()
        self.assertNotIn(mv._KEY_ANALYSIS_ATTEMPT, self.session)

    @patch.object(mv, "_begin_v2_analysis")
    def test_try_start_analysis_sets_in_flight_before_attempt(
        self, begin_mock: MagicMock
    ) -> None:
        with patch.object(mv.st, "session_state", self.session, create=True):
            ok = mv._try_start_v2_analysis(retry=True)
        self.assertTrue(ok)
        begin_mock.assert_called_once_with(retry=True)
        self.assertTrue(self.session[key_in_flight(mv._ANALYSIS_GUARD_PREFIX)])

    @patch("services.mini_mock_v2_analysis.analyze_mini_mock_v2_answers")
    def test_maybe_run_clears_in_flight_on_success(self, analyze_mock: MagicMock) -> None:
        analyze_mock.return_value = {"ok": True, "overall_level": "IM2"}
        self.session[mv._KEY_ANALYSIS_ATTEMPT] = "abc123"
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch.object(mv, "_answers", return_value=[]):
                step = mv._maybe_run_v2_analysis()
        self.assertEqual(step, "report")
        self.assertNotIn(key_in_flight(mv._ANALYSIS_GUARD_PREFIX), self.session)

    @patch("services.mini_mock_v2_analysis.analyze_mini_mock_v2_answers")
    def test_maybe_run_clears_in_flight_on_failure(self, analyze_mock: MagicMock) -> None:
        analyze_mock.return_value = {"ok": False, "error_category": "api_error"}
        self.session[mv._KEY_ANALYSIS_ATTEMPT] = "abc123"
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                with patch.object(mv, "_answers", return_value=[]):
                    step = mv._maybe_run_v2_analysis()
        self.assertEqual(step, "pending")
        self.assertNotIn(key_in_flight(mv._ANALYSIS_GUARD_PREFIX), self.session)
        self.assertIn(key_cooldown_until(mv._ANALYSIS_GUARD_PREFIX), self.session)

    @patch("services.mini_mock_v2_analysis.analyze_mini_mock_v2_answers")
    def test_maybe_run_clears_in_flight_on_exception(self, analyze_mock: MagicMock) -> None:
        analyze_mock.side_effect = RuntimeError("boom")
        self.session[mv._KEY_ANALYSIS_ATTEMPT] = "abc123"
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                with patch.object(mv, "_answers", return_value=[]):
                    step = mv._maybe_run_v2_analysis()
        self.assertEqual(step, "pending")
        self.assertNotIn(key_in_flight(mv._ANALYSIS_GUARD_PREFIX), self.session)

    def test_analysis_dedup_still_runs_once_per_attempt(self) -> None:
        self.session[mv._KEY_ANALYSIS_ATTEMPT] = "dedup1"
        self.session[mv._KEY_ANALYSIS_STARTED_ATTEMPT] = "dedup1"
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch(
                "services.mini_mock_v2_analysis.analyze_mini_mock_v2_answers"
            ) as analyze_mock:
                step = mv._maybe_run_v2_analysis()
        analyze_mock.assert_not_called()
        self.assertEqual(step, "analyzing")

    def test_stt_retry_clears_in_flight_in_finally(self) -> None:
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch.object(
                mv,
                "_retry_mini_v2_stt_impl",
                return_value=(False, {"ok": False, "error_category": "api_error"}),
            ):
                with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                    mv._retry_mini_v2_stt(1)
        self.assertNotIn(key_in_flight(mv._STT_RETRY_GUARD_PREFIX), self.session)
        self.assertNotIn(mv._KEY_STT_RETRY_ACTIVE_QIDX, self.session)

    def test_reset_analysis_guards(self) -> None:
        self.session[key_in_flight(mv._ANALYSIS_GUARD_PREFIX)] = True
        self.session[key_in_flight(mv._STT_RETRY_GUARD_PREFIX)] = True
        with patch.object(mv.st, "session_state", self.session, create=True):
            mv._reset_mini_v2_analysis_guards()
        self.assertNotIn(key_in_flight(mv._ANALYSIS_GUARD_PREFIX), self.session)
        self.assertNotIn(key_in_flight(mv._STT_RETRY_GUARD_PREFIX), self.session)


if __name__ == "__main__":
    unittest.main()
