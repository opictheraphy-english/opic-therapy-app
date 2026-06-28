"""Tests for mock_v2 report and STT-retry analysis request guards."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from utils.analysis_request_guard import key_attempts, key_cooldown_until, key_in_flight
from utils.recording_blob_memory import trim_mock_v2_widget_state
from views import mock_v2 as mv


class MockV2GuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.t0 = 1_700_000_000.0
        self.session: dict = {}

    def test_report_button_in_flight_disabled(self) -> None:
        self.session[key_in_flight(mv._REPORT_GUARD_PREFIX)] = True
        self.session[f"{mv._REPORT_GUARD_PREFIX}_in_flight_at"] = self.t0
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                disabled, label = mv._report_button_state()
        self.assertTrue(disabled)
        self.assertEqual(label, "리포트 생성 중…")

    def test_report_register_failure_escalates_cooldown(self) -> None:
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                mv.guard_register_failure(
                    self.session,
                    mv._REPORT_GUARD_PREFIX,
                    mv._REPORT_ENTITY_ID,
                    "timeout",
                    base_cooldown=mv._REPORT_COOLDOWN_BASE,
                    step=mv._REPORT_COOLDOWN_STEP,
                    max_cooldown=mv._REPORT_COOLDOWN_MAX,
                )
                mv.guard_register_failure(
                    self.session,
                    mv._REPORT_GUARD_PREFIX,
                    mv._REPORT_ENTITY_ID,
                    "api_error",
                    base_cooldown=mv._REPORT_COOLDOWN_BASE,
                    step=mv._REPORT_COOLDOWN_STEP,
                    max_cooldown=mv._REPORT_COOLDOWN_MAX,
                )
        until = float(self.session[key_cooldown_until(mv._REPORT_GUARD_PREFIX)])
        self.assertEqual(int(until - self.t0), 60)

    @patch("services.mock_v2_analysis.analyze_mock_v2_answers")
    def test_run_report_clears_in_flight_on_success(
        self, analyze_mock: MagicMock
    ) -> None:
        analyze_mock.return_value = {"ok": True, "overall_level": "IM2"}
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch.object(mv, "_answers_list", return_value=[]):
                with patch.object(mv, "_questions_list", return_value=[]):
                    with patch.object(mv.st, "rerun"):
                        mv._run_mock_v2_report_generation()
        self.assertNotIn(key_in_flight(mv._REPORT_GUARD_PREFIX), self.session)
        self.assertEqual(self.session[mv._KEY_STEP], "report")

    @patch("services.mock_v2_analysis.analyze_mock_v2_answers")
    def test_run_report_clears_in_flight_on_failure(
        self, analyze_mock: MagicMock
    ) -> None:
        analyze_mock.return_value = {
            "ok": False,
            "error_category": "timeout",
        }
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                with patch.object(mv, "_answers_list", return_value=[]):
                    with patch.object(mv, "_questions_list", return_value=[]):
                        with patch.object(mv.st, "rerun"):
                            mv._run_mock_v2_report_generation()
        self.assertNotIn(key_in_flight(mv._REPORT_GUARD_PREFIX), self.session)
        self.assertIn(key_cooldown_until(mv._REPORT_GUARD_PREFIX), self.session)

    @patch("services.mock_v2_analysis.analyze_mock_v2_answers")
    def test_run_report_clears_in_flight_on_exception(
        self, analyze_mock: MagicMock
    ) -> None:
        analyze_mock.side_effect = RuntimeError("boom")
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                with patch.object(mv, "_answers_list", return_value=[]):
                    with patch.object(mv, "_questions_list", return_value=[]):
                        with patch.object(mv.st, "rerun"):
                            mv._run_mock_v2_report_generation()
        self.assertNotIn(key_in_flight(mv._REPORT_GUARD_PREFIX), self.session)

    def test_stt_retry_attempt_max_per_question_independent(self) -> None:
        q1 = "q-001"
        q2 = "q-002"
        with patch.object(mv.st, "session_state", self.session, create=True):
            for _ in range(mv._STT_RETRY_MAX_ATTEMPTS):
                mv.guard_register_failure(
                    self.session,
                    mv._STT_RETRY_GUARD_PREFIX,
                    q1,
                    "api_key",
                    base_cooldown=mv._STT_RETRY_COOLDOWN_BASE,
                    step=mv._STT_RETRY_COOLDOWN_STEP,
                    max_cooldown=mv._STT_RETRY_COOLDOWN_MAX,
                )
            disabled_q1, label_q1 = mv._stt_retry_button_state(q1)
            disabled_q2, label_q2 = mv._stt_retry_button_state(q2)
        self.assertTrue(disabled_q1)
        self.assertEqual(label_q1, "잠시 후 다시 시도")
        self.assertFalse(disabled_q2)
        self.assertEqual(label_q2, mv._STT_RETRY_IDLE_LABEL)

    def test_stt_retry_cooldown_blocks_all_buttons(self) -> None:
        q1 = "q-001"
        q2 = "q-002"
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                mv.guard_register_failure(
                    self.session,
                    mv._STT_RETRY_GUARD_PREFIX,
                    q1,
                    "api_error",
                    base_cooldown=mv._STT_RETRY_COOLDOWN_BASE,
                    step=mv._STT_RETRY_COOLDOWN_STEP,
                    max_cooldown=mv._STT_RETRY_COOLDOWN_MAX,
                )
                disabled_q1, label_q1 = mv._stt_retry_button_state(q1)
                disabled_q2, label_q2 = mv._stt_retry_button_state(q2)
        self.assertTrue(disabled_q1)
        self.assertIn("초", label_q1)
        self.assertTrue(disabled_q2)
        self.assertIn("초", label_q2)

    def test_stt_retry_active_question_shows_in_flight_label(self) -> None:
        qid = "q-003"
        self.session[key_in_flight(mv._STT_RETRY_GUARD_PREFIX)] = True
        self.session[f"{mv._STT_RETRY_GUARD_PREFIX}_in_flight_at"] = self.t0
        self.session[mv._KEY_STT_RETRY_ACTIVE_QID] = qid
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                active_disabled, active_label = mv._stt_retry_button_state(qid)
                other_disabled, other_label = mv._stt_retry_button_state("q-other")
        self.assertTrue(active_disabled)
        self.assertEqual(active_label, "인식 중…")
        self.assertTrue(other_disabled)
        self.assertEqual(other_label, mv._STT_RETRY_IDLE_LABEL)

    @patch.object(mv, "_retry_mock_v2_stt_impl")
    def test_stt_retry_clears_in_flight_in_finally(
        self, impl_mock: MagicMock
    ) -> None:
        impl_mock.return_value = (False, {"ok": False, "error_category": "api_error"})
        row = {"question_id": "q-004", "answer_id": "a1"}
        with patch.object(mv.st, "session_state", self.session, create=True):
            with patch.object(mv, "_answer_for_index", return_value=row):
                with patch.object(mv, "_current_question", return_value=None):
                    with patch.object(mv, "_questions_list", return_value=[]):
                        with patch("utils.analysis_request_guard.time.time", return_value=self.t0):
                            mv._retry_mock_v2_stt(0)
        self.assertNotIn(key_in_flight(mv._STT_RETRY_GUARD_PREFIX), self.session)
        self.assertNotIn(mv._KEY_STT_RETRY_ACTIVE_QID, self.session)

    def test_reset_analysis_guards_clears_both_prefixes(self) -> None:
        self.session[key_in_flight(mv._REPORT_GUARD_PREFIX)] = True
        self.session[key_in_flight(mv._STT_RETRY_GUARD_PREFIX)] = True
        self.session[mv._KEY_STT_RETRY_ACTIVE_QID] = "q-x"
        with patch.object(mv.st, "session_state", self.session, create=True):
            mv._reset_mock_v2_analysis_guards()
        self.assertNotIn(key_in_flight(mv._REPORT_GUARD_PREFIX), self.session)
        self.assertNotIn(key_in_flight(mv._STT_RETRY_GUARD_PREFIX), self.session)
        self.assertNotIn(mv._KEY_STT_RETRY_ACTIVE_QID, self.session)

    def test_trim_mock_v2_widget_state_preserves_guard_keys(self) -> None:
        self.session[key_in_flight(mv._REPORT_GUARD_PREFIX)] = True
        self.session[key_in_flight(mv._STT_RETRY_GUARD_PREFIX)] = True
        self.session[key_attempts(mv._REPORT_GUARD_PREFIX)] = {"default": 1}
        self.session[key_attempts(mv._STT_RETRY_GUARD_PREFIX)] = {"q-1": 2}
        self.session["mock_v2_mic_old_q_output"] = {"bytes": b"x"}
        questions = [{"id": "q-current", "question_index": 14}]
        trim_mock_v2_widget_state(
            self.session,
            questions=questions,
            current_index=14,
        )
        self.assertIn(key_in_flight(mv._REPORT_GUARD_PREFIX), self.session)
        self.assertIn(key_in_flight(mv._STT_RETRY_GUARD_PREFIX), self.session)
        self.assertIn(key_attempts(mv._REPORT_GUARD_PREFIX), self.session)
        self.assertIn(key_attempts(mv._STT_RETRY_GUARD_PREFIX), self.session)


if __name__ == "__main__":
    unittest.main()
