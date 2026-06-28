"""Tests for script coaching analysis request guards."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from utils.analysis_request_guard import key_cooldown_until, key_in_flight
from views import script_coaching as sc


class ScriptCoachingGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.t0 = 1_700_000_000.0
        self.session: dict = {}

    def test_diagnose_button_in_flight_disabled(self) -> None:
        self.session[key_in_flight(sc._DIAGNOSE_GUARD_PREFIX)] = True
        self.session[f"{sc._DIAGNOSE_GUARD_PREFIX}_in_flight_at"] = self.t0
        with patch.object(sc.st, "session_state", self.session, create=True):
            with patch("views.script_coaching.time.time", return_value=self.t0):
                disabled, label = sc._diagnose_button_state()
        self.assertTrue(disabled)
        self.assertEqual(label, "진단 중…")

    def test_diagnose_register_failure_escalates_cooldown(self) -> None:
        with patch.object(sc.st, "session_state", self.session, create=True):
            with patch("views.script_coaching.time.time", return_value=self.t0):
                sc.guard_register_failure(
                    self.session,
                    sc._DIAGNOSE_GUARD_PREFIX,
                    sc._GUARD_ENTITY_ID,
                    "api_error",
                    base_cooldown=45,
                    step=15,
                    max_cooldown=90,
                )
                sc.guard_register_failure(
                    self.session,
                    sc._DIAGNOSE_GUARD_PREFIX,
                    sc._GUARD_ENTITY_ID,
                    "api_error",
                    base_cooldown=45,
                    step=15,
                    max_cooldown=90,
                )
        until = float(self.session[key_cooldown_until(sc._DIAGNOSE_GUARD_PREFIX)])
        self.assertEqual(int(until - self.t0), 60)

    @patch("services.script_coaching_diagnose_analysis.diagnose_script")
    def test_run_diagnose_guarded_clears_in_flight_on_success(
        self, diagnose_mock: MagicMock
    ) -> None:
        diagnose_mock.return_value = {"ok": True, "overall_level": "IM2", "word_count": 10}
        with patch.object(sc.st, "session_state", self.session, create=True):
            with patch.object(sc, "_merge_user_script_fields", side_effect=lambda r: r):
                with patch.object(sc.st, "rerun"):
                    sc._run_diagnose_guarded("Q?", "My script answer here.")
        self.assertNotIn(key_in_flight(sc._DIAGNOSE_GUARD_PREFIX), self.session)
        self.assertEqual(self.session[sc._KEY_STEP], "result")

    @patch("services.script_coaching_diagnose_analysis.diagnose_script")
    def test_run_diagnose_guarded_clears_in_flight_on_failure(
        self, diagnose_mock: MagicMock
    ) -> None:
        diagnose_mock.return_value = {
            "ok": False,
            "error_category": "api_error",
            "error_message": "fail",
        }
        with patch.object(sc.st, "session_state", self.session, create=True):
            with patch("views.script_coaching.time.time", return_value=self.t0):
                with patch.object(sc.st, "rerun"):
                    sc._run_diagnose_guarded("Q?", "My script answer here.")
        self.assertNotIn(key_in_flight(sc._DIAGNOSE_GUARD_PREFIX), self.session)
        self.assertIn(key_cooldown_until(sc._DIAGNOSE_GUARD_PREFIX), self.session)

    def test_upgrade_buttons_all_disabled_when_in_flight(self) -> None:
        self.session[key_in_flight(sc._UPGRADE_GUARD_PREFIX)] = True
        self.session[f"{sc._UPGRADE_GUARD_PREFIX}_in_flight_at"] = self.t0
        self.session[sc._KEY_UPGRADE_ACTIVE_BUTTON] = "script_coaching_upgrade_polish"
        with patch.object(sc.st, "session_state", self.session, create=True):
            with patch("views.script_coaching.time.time", return_value=self.t0):
                active_disabled, active_label = sc._upgrade_button_state(
                    "script_coaching_upgrade_polish",
                    "보완본 받기",
                )
                other_disabled, other_label = sc._upgrade_button_state(
                    "script_coaching_upgrade_one_step",
                    "한 단계 업그레이드 (IM2)",
                )
        self.assertTrue(active_disabled)
        self.assertEqual(active_label, "업그레이드 중…")
        self.assertTrue(other_disabled)

    @patch("services.script_coaching_upgrade_analysis.upgrade_script")
    def test_run_upgrade_clears_in_flight_in_finally(self, upgrade_mock: MagicMock) -> None:
        upgrade_mock.side_effect = RuntimeError("boom")
        with patch.object(sc.st, "session_state", self.session, create=True):
            with patch.object(sc.st, "rerun"):
                sc._run_upgrade("IM1", target_level="IM2", button_key="script_coaching_upgrade_one_step")
        self.assertNotIn(key_in_flight(sc._UPGRADE_GUARD_PREFIX), self.session)
        self.assertNotIn(sc._KEY_UPGRADE_ACTIVE_BUTTON, self.session)

    def test_reset_all_analysis_guards(self) -> None:
        self.session[key_in_flight(sc._DIAGNOSE_GUARD_PREFIX)] = True
        self.session[key_in_flight(sc._UPGRADE_GUARD_PREFIX)] = True
        with patch.object(sc.st, "session_state", self.session, create=True):
            sc._reset_all_analysis_guards()
        self.assertNotIn(key_in_flight(sc._DIAGNOSE_GUARD_PREFIX), self.session)
        self.assertNotIn(key_in_flight(sc._UPGRADE_GUARD_PREFIX), self.session)


if __name__ == "__main__":
    unittest.main()
