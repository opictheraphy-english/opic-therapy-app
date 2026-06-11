"""Onboarding Google OAuth uses same-tab redirect, not st.link_button."""

from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

from views.onboarding import (
    _emit_pending_oauth_redirect,
    _same_tab_redirect_script,
    render_onboarding,
)


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
    def test_emit_redirect_pops_and_emits(self, mock_render) -> None:
        ss = {"_oauth_redirect_url": "https://oauth.example/start"}
        _emit_pending_oauth_redirect(ss)
        mock_render.assert_called_once_with("https://oauth.example/start")
        self.assertNotIn("_oauth_redirect_url", ss)

    @patch("views.onboarding._render_same_tab_oauth_redirect")
    def test_no_pending_redirect_is_noop(self, mock_render) -> None:
        ss: dict = {}
        _emit_pending_oauth_redirect(ss)
        mock_render.assert_not_called()

    def test_render_onboarding_never_returns_early_before_ctas(self) -> None:
        src = inspect.getsource(render_onboarding)
        self.assertNotIn("link_button", src)
        self.assertNotIn("return\n", src.replace(" ", ""))
        # CTAs must render before redirect emit
        self.assertLess(src.index("onb_guest_start"), src.index("_emit_pending_oauth_redirect"))
        self.assertLess(src.index("onb_google_start"), src.index("_emit_pending_oauth_redirect"))

    def test_oauth_url_failure_flag_does_not_block_guest_button(self) -> None:
        src = inspect.getsource(render_onboarding)
        self.assertIn("_oauth_login_failed", src)
        self.assertLess(src.index("_oauth_login_failed"), src.index("onb_guest_start"))


if __name__ == "__main__":
    unittest.main()
