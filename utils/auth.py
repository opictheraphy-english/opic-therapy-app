"""Auth session-state glue for Supabase Google login + guest mode.

Login only — no learning-data sync yet. Session keys:
  - ``user_authenticated``: bool (guest = False)
  - ``user_id``: Supabase user id (guest = None)
  - ``user_email`` / ``user_name``: from the Google account
  - ``is_guest``: bool
"""

from __future__ import annotations

import logging
import time
from typing import Any, MutableMapping, Optional

import streamlit as st

from services.supabase_client import (
    build_google_oauth_url,
    exchange_code_for_user,
    refresh_access_token,
    sign_out,
    supabase_configured,
)
from utils.local_profile import complete_entry_guest, load_app_session, merge_app_session

logger = logging.getLogger(__name__)

_DEFAULTS = {
    "user_authenticated": False,
    "user_id": None,
    "user_email": None,
    "user_name": None,
    "is_guest": False,
}

# Supabase session tokens (for authenticated PostgREST history sync).
_TOKEN_KEYS = ("sb_access_token", "sb_refresh_token", "sb_token_expires_at")
# Refresh proactively when the access token is within this many seconds of expiry.
_TOKEN_REFRESH_LEEWAY_SEC = 60


def init_auth_state(ss: MutableMapping[str, Any]) -> None:
    for key, default in _DEFAULTS.items():
        ss.setdefault(key, default)

    # The bottom nav does a full page reload, which starts a fresh Streamlit
    # session and wipes session_state. Restore the login identity from disk once
    # per session so the user stays logged in across navigation. (Only the
    # profile is persisted here — Supabase token persistence comes with data
    # sync in a later step; no authenticated API calls happen yet.)
    if not ss.get("_auth_restored"):
        _restore_auth_from_disk(ss)
        ss["_auth_restored"] = True

    # Returning guests (new browser session) flagged from disk user_mode so the
    # "게스트 모드" chip and any future guest gating stay consistent.
    if ss.get("user_mode") == "guest" and not ss.get("user_authenticated"):
        ss["is_guest"] = True


def _restore_auth_from_disk(ss: MutableMapping[str, Any]) -> None:
    if ss.get("user_authenticated"):
        return
    disk = load_app_session()
    if disk.get("user_mode") == "google" and disk.get("user_id"):
        ss["user_authenticated"] = True
        ss["is_guest"] = False
        ss["user_id"] = disk.get("user_id")
        ss["user_email"] = disk.get("user_email")
        ss["user_name"] = disk.get("user_name")
        for key in _TOKEN_KEYS:
            ss[key] = disk.get(key)


def is_authenticated(ss: MutableMapping[str, Any]) -> bool:
    return bool(ss.get("user_authenticated"))


def is_guest(ss: MutableMapping[str, Any]) -> bool:
    return bool(ss.get("is_guest"))


def current_user_name(ss: MutableMapping[str, Any]) -> str:
    return str(ss.get("user_name") or ss.get("user_email") or "").strip()


def app_base_url() -> str:
    """Best-effort origin to use as the OAuth ``redirect_to`` — must match a
    Redirect URL registered in Supabase. Honors an explicit ``APP_BASE_URL``
    override, else derives from request headers, else localhost."""
    import os

    override = ""
    try:
        override = str(st.secrets.get("APP_BASE_URL") or "").strip()
    except Exception:
        override = ""
    override = override or str(os.getenv("APP_BASE_URL") or "").strip()
    if override:
        return override.rstrip("/")

    try:
        headers = st.context.headers or {}
        origin = headers.get("Origin") or headers.get("origin")
        if origin:
            return str(origin).rstrip("/")
        host = headers.get("Host") or headers.get("host")
        if host:
            scheme = "http" if str(host).startswith("localhost") else "https"
            return f"{scheme}://{host}"
    except Exception:
        pass
    return "http://localhost:8501"


def google_login_url() -> Optional[str]:
    if not supabase_configured():
        return None
    return build_google_oauth_url(app_base_url())


def _set_authenticated(ss: MutableMapping[str, Any], user: dict) -> None:
    ss["user_authenticated"] = True
    ss["is_guest"] = False
    ss["user_id"] = user.get("id")
    ss["user_email"] = user.get("email")
    ss["user_name"] = user.get("name")
    ss["sb_access_token"] = user.get("access_token")
    ss["sb_refresh_token"] = user.get("refresh_token")
    ss["sb_token_expires_at"] = user.get("expires_at")
    ss.pop("_google_oauth_url", None)
    # Pass the existing entry/onboarding gates so the normal app loads.
    ss["entry_gate_completed"] = True
    ss["user_mode"] = "google"
    if "onboarding_completed" not in ss:
        ss["onboarding_completed"] = False
    merge_app_session(
        {
            "entry_gate_completed": True,
            "user_mode": "google",
            "user_id": user.get("id"),
            "user_email": user.get("email"),
            "user_name": user.get("name"),
            "sb_access_token": user.get("access_token"),
            "sb_refresh_token": user.get("refresh_token"),
            "sb_token_expires_at": user.get("expires_at"),
        }
    )


def _store_refreshed_tokens(ss: MutableMapping[str, Any], tokens: dict) -> str:
    """Persist refreshed tokens to session + disk; return the new access token."""
    ss["sb_access_token"] = tokens.get("access_token")
    ss["sb_refresh_token"] = tokens.get("refresh_token")
    ss["sb_token_expires_at"] = tokens.get("expires_at")
    merge_app_session(
        {
            "sb_access_token": tokens.get("access_token"),
            "sb_refresh_token": tokens.get("refresh_token"),
            "sb_token_expires_at": tokens.get("expires_at"),
        }
    )
    return str(tokens.get("access_token") or "")


def get_valid_access_token(ss: MutableMapping[str, Any]) -> Optional[str]:
    """Return a usable Supabase access token, refreshing proactively if it is
    expired or within the leeway window. Returns ``None`` for guests/logged-out
    users or when refresh fails and no token is available."""
    token = ss.get("sb_access_token")
    expires_at = ss.get("sb_token_expires_at")
    refresh = ss.get("sb_refresh_token")

    needs_refresh = False
    try:
        if expires_at is not None and int(expires_at) <= int(time.time()) + _TOKEN_REFRESH_LEEWAY_SEC:
            needs_refresh = True
    except (TypeError, ValueError):
        needs_refresh = False

    if token and not needs_refresh:
        return str(token)
    if not refresh:
        return str(token) if token else None

    refreshed = refresh_access_token(str(refresh))
    if not refreshed:
        # Could not refresh; hand back the existing token (the caller may still
        # retry / handle a 401) rather than hard-failing here.
        return str(token) if token else None
    return _store_refreshed_tokens(ss, refreshed) or (str(token) if token else None)


def force_refresh_access_token(ss: MutableMapping[str, Any]) -> Optional[str]:
    """Force a token refresh regardless of expiry (used after a 401). Returns the
    new access token, or ``None`` if there is no refresh token or refresh fails."""
    refresh = ss.get("sb_refresh_token")
    if not refresh:
        return None
    refreshed = refresh_access_token(str(refresh))
    if not refreshed:
        return None
    return _store_refreshed_tokens(ss, refreshed) or None


def handle_oauth_callback(ss: MutableMapping[str, Any]) -> None:
    """If the browser came back from Google with ``?code=``, exchange it for a
    session, store the user, and clear the param. Runs early in ``app.py``."""
    if is_authenticated(ss):
        _clear_oauth_params()
        return
    try:
        code = st.query_params.get("code")
    except Exception:
        code = None
    if not code:
        return

    try:
        user = exchange_code_for_user(str(code))
    except Exception:
        logger.exception("[AUTH] oauth code exchange raised")
        ss["_auth_error"] = "구글 로그인 처리 중 오류가 났어요. 다시 시도해 주세요."
        _clear_oauth_params()
        ss.pop("_google_oauth_url", None)
        return

    _clear_oauth_params()
    if user and user.get("id"):
        _set_authenticated(ss, user)
        logger.info("[AUTH] google login ok user_id=%s", user.get("id"))
        st.rerun()
    else:
        ss["_auth_error"] = "구글 로그인에 실패했어요. 다시 시도해 주세요."
        ss.pop("_google_oauth_url", None)
        logger.warning("[AUTH] oauth code exchange returned no user")


def _clear_oauth_params() -> None:
    for key in ("code", "state"):
        try:
            if key in st.query_params:
                del st.query_params[key]
        except Exception:
            pass


def start_guest(ss: MutableMapping[str, Any]) -> None:
    ss["is_guest"] = True
    ss["user_authenticated"] = False
    ss["user_id"] = None
    ss["user_email"] = None
    ss["user_name"] = None
    complete_entry_guest(ss)


def logout(ss: MutableMapping[str, Any]) -> None:
    """Sign out of Supabase, clear auth state, and return to the login screen."""
    try:
        sign_out()
    except Exception:
        pass
    for key in _DEFAULTS:
        ss[key] = _DEFAULTS[key]
    for key in _TOKEN_KEYS:
        ss[key] = None
    ss["entry_gate_completed"] = False
    ss["user_mode"] = None
    ss.pop("_login_info_open", None)
    ss.pop("_google_oauth_url", None)
    ss["_auth_restored"] = True  # don't re-restore the just-cleared identity
    merge_app_session(
        {
            "entry_gate_completed": False,
            "user_mode": None,
            "user_id": None,
            "user_email": None,
            "user_name": None,
            "sb_access_token": None,
            "sb_refresh_token": None,
            "sb_token_expires_at": None,
        }
    )
    st.rerun()
