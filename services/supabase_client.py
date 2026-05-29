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


def get_supabase_credentials() -> tuple[str, str]:
    return _read_secret("SUPABASE_URL"), _read_secret("SUPABASE_ANON_KEY")


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
        # supabase-py omits the apikey from the /auth/v1/authorize URL. A browser
        # GET to that endpoint can't send an `apikey` header, so without it as a
        # query param the gateway rejects with "No API key found in request".
        _, anon_key = get_supabase_credentials()
        if anon_key and "apikey=" not in url:
            from urllib.parse import urlencode

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
    return {
        "id": getattr(user, "id", None),
        "email": email,
        "name": name,
    }


def sign_out() -> None:
    client = get_supabase_client()
    if client is None:
        return
    try:
        client.auth.sign_out()
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("[SUPABASE] sign_out failed: %s", exc)
