"""Supabase client + Google OAuth helpers (login only; no data sync yet).

A single cached client is reused across reruns. We use the PKCE flow so the
OAuth redirect comes back to the app with a ``?code=`` query param that Python
can read via ``st.query_params`` (the implicit flow returns tokens in the URL
fragment, which server-side Python cannot see).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import streamlit as st

logger = logging.getLogger(__name__)


def _read_secret(name: str) -> str:
    try:
        val = st.secrets.get(name)
    except Exception:
        val = None
    return str(val or os.getenv(name) or "").strip()


def _normalize_supabase_url(raw: str) -> str:
    """Reduce SUPABASE_URL to the bare project origin (scheme://host).

    The supabase client expects just the project URL (e.g.
    ``https://abcd.supabase.co``) and appends ``/auth/v1`` and ``/rest/v1``
    itself. If the env value accidentally includes a path such as ``/rest/v1``,
    the OAuth authorize URL becomes ``…/rest/v1/auth/v1/authorize`` which the
    gateway routes to PostgREST and fails with PGRST125 ("Invalid path…").
    Stripping any path/query/fragment makes the client robust to that misconfig.
    """
    raw = (raw or "").strip()
    if not raw:
        return ""
    if "://" not in raw:
        raw = "https://" + raw
    from urllib.parse import urlsplit, urlunsplit

    parts = urlsplit(raw)
    scheme = parts.scheme or "https"
    netloc = parts.netloc or parts.path  # tolerate "abcd.supabase.co" w/o scheme
    return urlunsplit((scheme, netloc, "", "", "")).rstrip("/")


def get_supabase_credentials() -> tuple[str, str]:
    return _normalize_supabase_url(_read_secret("SUPABASE_URL")), _read_secret("SUPABASE_ANON_KEY")


def supabase_configured() -> bool:
    url, key = get_supabase_credentials()
    return bool(url and key)


@st.cache_resource(show_spinner=False)
def get_supabase_client():
    """Create (once) and reuse the Supabase client. Returns ``None`` if env is
    missing or the library fails to initialize."""
    url, key = get_supabase_credentials()
    if not url or not key:
        logger.warning("[SUPABASE] missing SUPABASE_URL / SUPABASE_ANON_KEY")
        return None
    try:
        from supabase import ClientOptions, create_client

        options = ClientOptions(flow_type="pkce")
        return create_client(url, key, options)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("[SUPABASE] client init failed: %s", exc)
        return None


def build_google_oauth_url(redirect_to: str) -> Optional[str]:
    """Build the Google OAuth URL (stores the PKCE verifier on the cached
    client). Call this at click time so the stored verifier matches the URL the
    browser navigates to."""
    client = get_supabase_client()
    if client is None:
        return None
    try:
        resp = client.auth.sign_in_with_oauth(
            {
                "provider": "google",
                "options": {"redirect_to": redirect_to},
            }
        )
        url = getattr(resp, "url", None)
        if not url:
            return None
        url = str(url)

        from urllib.parse import urlencode, urlsplit, urlunsplit

        base_url, anon_key = get_supabase_credentials()
        parts = urlsplit(url)

        # Self-heal a misrouted authorize URL. If the env/cached client produced a
        # path like ``/rest/v1/auth/v1/authorize`` (SUPABASE_URL carried a path),
        # the Kong gateway sends it to PostgREST and the browser gets PGRST125
        # ("Invalid path specified in request URL"). Force the host+path to the
        # correct GoTrue endpoint while keeping the PKCE query (provider, state,
        # redirect_to, code_challenge) so the verifier stored on the client still
        # matches.
        if not parts.path.startswith("/auth/v1/") and base_url:
            base_parts = urlsplit(base_url)
            parts = parts._replace(
                scheme=base_parts.scheme or parts.scheme or "https",
                netloc=base_parts.netloc or parts.netloc,
                path="/auth/v1/authorize",
            )
            url = urlunsplit(parts)

        # Log host+path only (never the apikey/state) so we can confirm the URL
        # targets /auth/v1/authorize and not a misrouted /rest/v1/... path.
        try:
            logger.info("[SUPABASE] oauth authorize host=%s path=%s", parts.netloc, parts.path)
        except Exception:
            pass

        # supabase-py omits the apikey from the /auth/v1/authorize URL. A browser
        # GET to that endpoint can't send an `apikey` header, so without it as a
        # query param the gateway rejects with "No API key found in request".
        if anon_key and "apikey=" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{urlencode({'apikey': anon_key})}"
        return url
    except Exception as exc:
        logger.exception("[SUPABASE] sign_in_with_oauth failed: %s", exc)
        return None


def exchange_code_for_user(code: str) -> Optional[Dict[str, Any]]:
    """Exchange the OAuth ``?code=`` for a session and return a small user dict
    (``id``, ``email``, ``name``) or ``None``.

    NOTE: this intentionally does NOT swallow exceptions — the caller
    (``handle_oauth_callback``) surfaces the real error to the UI/terminal so we
    can diagnose silent PKCE failures."""
    client = get_supabase_client()
    if client is None:
        raise RuntimeError("Supabase client is None (SUPABASE_URL/ANON_KEY missing?)")
    if not code:
        raise ValueError("empty auth code")

    resp = client.auth.exchange_code_for_session({"auth_code": code})

    user = getattr(resp, "user", None)
    if user is None:
        return None
    meta = getattr(user, "user_metadata", None) or {}
    email = getattr(user, "email", None) or meta.get("email") or ""
    name = (
        meta.get("full_name")
        or meta.get("name")
        or (email.split("@")[0] if email else "")
    )

    # Capture session tokens so authenticated PostgREST calls (history sync) can
    # use the user's JWT. expires_at is a unix epoch (seconds).
    session = getattr(resp, "session", None)
    access_token = getattr(session, "access_token", None) if session else None
    refresh_token = getattr(session, "refresh_token", None) if session else None
    expires_at = getattr(session, "expires_at", None) if session else None

    return {
        "id": getattr(user, "id", None),
        "email": email,
        "name": name,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
    }


def refresh_access_token(refresh_token: str) -> Optional[Dict[str, Any]]:
    """Exchange a refresh token for a fresh access token via GoTrue directly.

    Stateless on purpose: the cached Supabase client is shared across all users
    (``st.cache_resource``), so calling ``set_session`` on it could leak one
    user's session into another's request. We hit the token endpoint with httpx
    and return the new tokens for the caller to store in that user's session.
    Returns ``{access_token, refresh_token, expires_at}`` or ``None``.
    """
    if not refresh_token:
        return None
    base_url, anon_key = get_supabase_credentials()
    if not base_url or not anon_key:
        return None
    try:
        import httpx

        resp = httpx.post(
            f"{base_url}/auth/v1/token",
            params={"grant_type": "refresh_token"},
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            json={"refresh_token": refresh_token},
            timeout=10.0,
        )
    except Exception as exc:
        logger.warning("[SUPABASE] token refresh request failed: %s", exc)
        return None
    if resp.status_code != 200:
        logger.warning("[SUPABASE] token refresh http=%s", resp.status_code)
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    access = data.get("access_token")
    if not access:
        return None
    return {
        "access_token": access,
        "refresh_token": data.get("refresh_token") or refresh_token,
        "expires_at": data.get("expires_at"),
    }


def sign_out() -> None:
    client = get_supabase_client()
    if client is None:
        return
    try:
        client.auth.sign_out()
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("[SUPABASE] sign_out failed: %s", exc)
