"""Per-browser session isolation via first-party cookies.

Why this exists
---------------
The app runs as a **single server process shared by every student** (Render).
``st.session_state`` is already isolated per browser connection, but a full page
reload (the bottom nav uses ``window.location.assign``) starts a *fresh* session
and wipes it. The previous fix persisted login identity to a single global disk
file (``app_session.json``); because that file is shared by all users, one
student's login leaked into every other student's session — a critical
cross-user identity/data bug.

The correct primitive for "this belongs to *this* browser" is a cookie:

* **Reads** are reliable and synchronous via ``st.context.cookies`` (the request
  carries the cookie header), so the server can identify the browser on the very
  first script run of a fresh session — no component round-trip needed.
* **Writes** go through a tiny ``components.html`` iframe that sets
  ``document.cookie`` on the top-level (same-origin) document. We only write when
  something actually changes (device id once per browser; login token at
  login/logout), so the invisible (height=0) helper iframe is rarely emitted.

Two cookies are used:
  * ``opic_did`` — a random per-browser device id used to key all server-side
    disk files so no two browsers ever share state.
  * ``opic_rt``  — the Supabase **refresh token** for a logged-in browser. The
    access token / identity are re-derived from it on each fresh session, so no
    identity is ever written to shared server disk.
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional
from urllib.parse import quote, unquote

import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

DEVICE_COOKIE = "opic_did"
REFRESH_COOKIE = "opic_rt"

_DEVICE_SS_KEY = "_device_id"
# Long-lived so navigation/return visits keep the same identity; the value is an
# opaque random id (device cookie) or a rotating refresh token (login cookie).
_DEVICE_MAX_AGE_DAYS = 365
_REFRESH_MAX_AGE_DAYS = 30


def _request_cookies() -> dict:
    try:
        cookies = st.context.cookies
        return dict(cookies) if cookies else {}
    except Exception:
        return {}


def read_cookie(name: str) -> Optional[str]:
    """Return the (URL-decoded) value of a request cookie, or ``None``."""
    raw = _request_cookies().get(name)
    if raw is None:
        return None
    try:
        return unquote(str(raw))
    except Exception:
        return str(raw)


def set_cookie(name: str, value: str, *, max_age_days: int = _DEVICE_MAX_AGE_DAYS) -> None:
    """Set a first-party cookie on the top-level document via a 0-height iframe.

    Uses ``window.parent.document.cookie`` (same-origin) so the cookie lands on
    the embedding page's origin rather than the component iframe. ``Secure`` is
    added automatically on https; ``SameSite=Lax`` keeps it sent on top-level
    navigations (which is exactly the full-reload nav case we need)."""
    enc = quote(str(value), safe="")
    max_age = int(max_age_days) * 24 * 60 * 60
    js = f"""
<script>
(function() {{
  try {{
    var doc = window.parent.document;
    var proto = window.parent.location.protocol;
    var secure = (proto === 'https:') ? '; Secure' : '';
    doc.cookie = "{name}={enc}; path=/; max-age={max_age}; SameSite=Lax" + secure;
  }} catch (e) {{
    try {{
      var secure2 = (location.protocol === 'https:') ? '; Secure' : '';
      document.cookie = "{name}={enc}; path=/; max-age={max_age}; SameSite=Lax" + secure2;
    }} catch (e2) {{}}
  }}
}})();
</script>
"""
    try:
        components.html(js, height=0, width=0)
    except Exception:
        logger.debug("set_cookie(%s) failed to inject", name)


def delete_cookie(name: str) -> None:
    """Expire a first-party cookie (login/logout)."""
    js = f"""
<script>
(function() {{
  try {{
    window.parent.document.cookie = "{name}=; path=/; max-age=0; SameSite=Lax";
  }} catch (e) {{
    try {{ document.cookie = "{name}=; path=/; max-age=0; SameSite=Lax"; }} catch (e2) {{}}
  }}
}})();
</script>
"""
    try:
        components.html(js, height=0, width=0)
    except Exception:
        logger.debug("delete_cookie(%s) failed to inject", name)


def get_or_create_device_id() -> str:
    """Return a stable per-browser device id, minting one on first contact.

    Cached in ``st.session_state`` so repeated reruns within a session never mint
    a second id before the freshly-set cookie has round-tripped. Brand-new
    browsers get a random id and the cookie is set; on the next request the
    cookie is read back. Cookie-blocked browsers fall back to a per-session id
    (state stays isolated, just not persisted across reloads)."""
    try:
        ss = st.session_state
    except Exception:
        ss = None

    if ss is not None:
        cached = ss.get(_DEVICE_SS_KEY)
        if cached:
            return str(cached)

    existing = read_cookie(DEVICE_COOKIE)
    if existing:
        if ss is not None:
            ss[_DEVICE_SS_KEY] = existing
        return existing

    new_id = uuid.uuid4().hex
    set_cookie(DEVICE_COOKIE, new_id, max_age_days=_DEVICE_MAX_AGE_DAYS)
    if ss is not None:
        ss[_DEVICE_SS_KEY] = new_id
    return new_id


def store_refresh_token(token: Optional[str]) -> None:
    """Persist (or clear) the login refresh token in this browser's cookie."""
    if token:
        set_cookie(REFRESH_COOKIE, str(token), max_age_days=_REFRESH_MAX_AGE_DAYS)
    else:
        delete_cookie(REFRESH_COOKIE)


def read_refresh_token() -> Optional[str]:
    return read_cookie(REFRESH_COOKIE)


def clear_refresh_token() -> None:
    delete_cookie(REFRESH_COOKIE)
