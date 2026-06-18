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
from utils.browser_session import (
    clear_refresh_token,
    read_refresh_token,
    store_refresh_token,
)
from utils.local_profile import complete_entry_guest, merge_app_session, persist_onboarding_completion

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
    # session and wipes session_state. Restore the login from this browser's
    # **own cookie** once per session so the user stays logged in across
    # navigation — WITHOUT ever reading identity from shared server disk (which
    # would leak one student's login into another's session).
    if not ss.get("_auth_restored"):
        _restore_auth_from_cookie(ss)
        ss["_auth_restored"] = True

    # Ensure this browser's login cookie matches the in-memory refresh token.
    # Critical for the post-OAuth path: handle_oauth_callback() does st.rerun()
    # right after login, which discards that run's component output — so a cookie
    # written during _set_authenticated() would never reach the browser. Writing
    # it here, on the subsequent rendering run, guarantees it lands.
    _sync_login_cookie(ss)

    # Returning guests (new browser session) flagged from disk user_mode so the
    # "게스트 모드" chip and any future guest gating stay consistent.
    if ss.get("user_mode") == "guest" and not ss.get("user_authenticated"):
        ss["is_guest"] = True


def _sync_login_cookie(ss: MutableMapping[str, Any]) -> None:
    """Align the browser ``opic_rt`` cookie with ``sb_refresh_token`` in session.

    We compare against the **incoming request** cookie (``read_refresh_token``),
    not a session-local "already wrote" flag. A ``st.rerun()`` that discards the
    set-cookie iframe therefore retries on the next run until the browser sends
    the cookie back on a full navigation/reload."""
    if not ss.get("user_authenticated"):
        return
    rt = ss.get("sb_refresh_token")
    if not rt:
        return
    rt_str = str(rt)
    cookie_rt = read_refresh_token()
    if cookie_rt == rt_str:
        return
    store_refresh_token(rt_str)
    logger.info("[AUTH] opic_rt cookie written (session→browser sync)")


def _restore_auth_from_cookie(ss: MutableMapping[str, Any]) -> None:
    """Rebuild the login from this browser's refresh-token cookie.

    The cookie holds only the Supabase refresh token (per-browser, never on
    shared disk). We exchange it for a fresh access token + the user identity,
    so two browsers can never see each other's account. A revoked/expired token
    simply leaves the session logged out and clears the stale cookie."""
    if ss.get("user_authenticated"):
        return
    rt = read_refresh_token()
    if not rt:
        logger.info("[AUTH] opic_rt missing on restore")
        return
    refreshed = refresh_access_token(str(rt))
    if not refreshed or not refreshed.get("id"):
        clear_refresh_token()
        ss["auth_session_expired_notice"] = True
        logger.warning("[AUTH] opic_rt restore failed (refresh rejected)")
        return
    ss["user_authenticated"] = True
    ss["is_guest"] = False
    ss["user_id"] = refreshed.get("id")
    ss["user_email"] = refreshed.get("email")
    ss["user_name"] = refreshed.get("name")
    ss["sb_access_token"] = refreshed.get("access_token")
    ss["sb_refresh_token"] = refreshed.get("refresh_token")
    ss["sb_token_expires_at"] = refreshed.get("expires_at")
    ss["entry_gate_completed"] = True
    ss["user_mode"] = "google"
    ss.setdefault("onboarding_completed", True)
    logger.info("[AUTH] opic_rt restore ok user_id=%s", refreshed.get("id"))
    _sync_login_cookie(ss)


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
    ss["entry_gate_completed"] = True
    ss["user_mode"] = "google"
    merge_app_session(
        {
            "entry_gate_completed": True,
            "user_mode": "google",
        }
    )
    persist_onboarding_completion(ss, skip_preferences=True)
    # The cookie itself is written by _sync_login_cookie() on the next (rendering)
    # run — this run is discarded by handle_oauth_callback()'s st.rerun().


def _store_refreshed_tokens(ss: MutableMapping[str, Any], tokens: dict) -> str:
    """Persist refreshed tokens to session + cookie; return the new access token.

    Tokens are kept in ``session_state`` (per-browser memory) and the refresh
    token in this browser's cookie. Nothing identity-related touches disk."""
    ss["sb_access_token"] = tokens.get("access_token")
    ss["sb_refresh_token"] = tokens.get("refresh_token")
    ss["sb_token_expires_at"] = tokens.get("expires_at")
    _sync_login_cookie(ss)
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
    try:
        code = st.query_params.get("code")
    except Exception:
        code = None
    if is_authenticated(ss):
        _clear_oauth_params()
        if code and not ss.get("onboarding_completed"):
            ss["entry_gate_completed"] = True
            merge_app_session({"entry_gate_completed": True, "user_mode": "google"})
            persist_onboarding_completion(ss, skip_preferences=True)
        return
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
    clear_refresh_token()
    logger.info("[AUTH] opic_rt cookie cleared (logout)")
    merge_app_session(
        {
            "entry_gate_completed": False,
            "user_mode": None,
        }
    )
    st.rerun()
