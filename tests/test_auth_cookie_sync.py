"""Auth cookie sync — opic_rt must retry until the browser round-trips it."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from utils.auth import _restore_auth_from_cookie, _sync_login_cookie, init_auth_state


class AuthCookieSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ss: dict = {}

    @patch("utils.auth.store_refresh_token")
    @patch("utils.auth.read_refresh_token", return_value=None)
    def test_sync_writes_when_cookie_missing(self, _read, store) -> None:
        self.ss.update(
            {
                "user_authenticated": True,
                "sb_refresh_token": "rt_session_abc",
                "_rt_cookie_value": "rt_session_abc",  # legacy flag must not block
            }
        )
        _sync_login_cookie(self.ss)
        store.assert_called_once_with("rt_session_abc")

    @patch("utils.auth.store_refresh_token")
    @patch("utils.auth.read_refresh_token", return_value="rt_session_abc")
    def test_sync_skips_when_cookie_matches(self, _read, store) -> None:
        self.ss.update(
            {
                "user_authenticated": True,
                "sb_refresh_token": "rt_session_abc",
            }
        )
        _sync_login_cookie(self.ss)
        store.assert_not_called()

    @patch("utils.auth.store_refresh_token")
    @patch("utils.auth.read_refresh_token", return_value="rt_old")
    def test_sync_writes_when_cookie_stale(self, _read, store) -> None:
        self.ss.update(
            {
                "user_authenticated": True,
                "sb_refresh_token": "rt_new",
            }
        )
        _sync_login_cookie(self.ss)
        store.assert_called_once_with("rt_new")

    @patch("utils.auth.store_refresh_token")
    @patch("utils.auth.read_refresh_token", return_value=None)
    def test_sync_noop_for_guest(self, _read, store) -> None:
        _sync_login_cookie(self.ss)
        store.assert_not_called()

    @patch("utils.auth._sync_login_cookie")
    @patch("utils.auth.refresh_access_token")
    @patch("utils.auth.read_refresh_token", return_value="rt_from_cookie")
    def test_restore_ok_then_syncs_cookie(self, _read, refresh, sync) -> None:
        refresh.return_value = {
            "id": "user-1",
            "email": "a@b.com",
            "name": "A",
            "access_token": "at",
            "refresh_token": "rt_rotated",
            "expires_at": 9999999999,
        }
        _restore_auth_from_cookie(self.ss)
        self.assertTrue(self.ss.get("user_authenticated"))
        self.assertEqual(self.ss.get("user_id"), "user-1")
        sync.assert_called_once_with(self.ss)

    @patch("utils.auth.clear_refresh_token")
    @patch("utils.auth.refresh_access_token", return_value=None)
    @patch("utils.auth.read_refresh_token", return_value="bad_rt")
    def test_restore_failed_clears_cookie(self, _read, _refresh, clear) -> None:
        _restore_auth_from_cookie(self.ss)
        self.assertFalse(self.ss.get("user_authenticated"))
        clear.assert_called_once()

    @patch("utils.auth._sync_login_cookie")
    @patch("utils.auth._restore_auth_from_cookie")
    def test_init_auth_calls_restore_once(self, restore, sync) -> None:
        init_auth_state(self.ss)
        restore.assert_called_once_with(self.ss)
        sync.assert_called_once_with(self.ss)
        self.assertTrue(self.ss.get("_auth_restored"))


if __name__ == "__main__":
    unittest.main()
