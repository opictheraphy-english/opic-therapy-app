"""Onboarding Google OAuth uses same-tab redirect, not st.link_button."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from views.onboarding import _maybe_render_pending_oauth_redirect, _same_tab_redirect_script


class OnboardingOAuthRedirectTests(unittest.TestCase):
    def test_redirect_script_uses_top_location_not_blank(self) -> None:
        script = _same_tab_redirect_script("https://example.supabase.co/auth/v1/authorize?x=1")
        self.assertIn("window.top.location.href", script)
        self.assertNotIn("_blank", script)
        self.assertIn("https://example.supabase.co/auth/v1/authorize?x=1", script)

    def test_redirect_script_escapes_quotes(self) -> None:
        script = _same_tab_redirect_script('https://ex.com/?q="a"')
        self.assertIn("\\\"a\\\"", script)

    @patch("views.onboarding._render_same_tab_oauth_redirect")
    def test_pending_redirect_pops_and_emits(self, mock_render) -> None:
        ss = {"_oauth_redirect_url": "https://oauth.example/start"}
        self.assertTrue(_maybe_render_pending_oauth_redirect(ss))
        mock_render.assert_called_once_with("https://oauth.example/start")
        self.assertNotIn("_oauth_redirect_url", ss)

    def test_no_pending_redirect_is_noop(self) -> None:
        ss: dict = {}
        self.assertFalse(_maybe_render_pending_oauth_redirect(ss))

    def test_onboarding_has_no_link_button(self) -> None:
        import inspect

        from views import onboarding

        src = inspect.getsource(onboarding.render_onboarding)
        self.assertNotIn("link_button", src)
        self.assertIn("onb_google_start", src)
        self.assertIn("_oauth_redirect_url", src)


if __name__ == "__main__":
    unittest.main()
