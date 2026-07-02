"""Persist & fetch a logged-in user's learning history via Supabase PostgREST.

Step 2 of the "past records" feature: the storage plumbing only. The three save
hooks (mock exam / topic practice / script coaching) and the history UI come in
later steps — nothing here is wired into the report flow yet.

Design notes:
- We call PostgREST directly with httpx using the user's JWT as a Bearer token.
  We deliberately do NOT mutate the shared cached Supabase client
  (``st.cache_resource``), which is shared across all users and would leak
  sessions between them.
- ``user_id`` is never sent in the insert body: the ``practice_history`` table
  defaults it to ``auth.uid()`` from the JWT, and RLS enforces ownership.
- Append-only: every save is a new INSERT (no update/upsert), so re-taking the
  same exam keeps a full history ordered by ``created_at``.
- All functions fail soft (return ``None`` / ``[]`` and log) so a sync hiccup
  never blocks the learning flow.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import streamlit as st

from services.supabase_client import get_supabase_credentials

logger = logging.getLogger(__name__)

_TABLE = "practice_history"
_REQUEST_TIMEOUT_SEC = 10.0

# Columns returned for the history list view (omit heavy ``content`` for speed).
_LIST_SELECT = "id,practice_type,subtype,title,overall_level,score,created_at"

VALID_PRACTICE_TYPES = ("mock_exam", "topic_practice", "script_coaching")


def _access_token() -> Optional[str]:
    from utils.auth import get_valid_access_token

    return get_valid_access_token(st.session_state)


def _force_refresh_token() -> Optional[str]:
    from utils.auth import force_refresh_access_token

    return force_refresh_access_token(st.session_state)


def _headers(access_token: str, anon_key: str, *, write: bool = False) -> Dict[str, str]:
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }
    if write:
        headers["Content-Type"] = "application/json"
        headers["Prefer"] = "return=representation"
    return headers


def _request(
    method: str,
    *,
    params: Optional[Dict[str, str]] = None,
    json_body: Optional[Any] = None,
    write: bool = False,
):
    """Perform one PostgREST call with a single 401 token-refresh retry.

    Returns the httpx ``Response`` on a 2xx, else ``None``.
    """
    base_url, anon_key = get_supabase_credentials()
    if not base_url or not anon_key:
        logger.info("[HISTORY] supabase not configured")
        return None

    token = _access_token()
    if not token:
        logger.info("[HISTORY] no access token (guest or logged out) — skip")
        return None

    try:
        import httpx
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("[HISTORY] httpx unavailable: %s", exc)
        return None

    url = f"{base_url}/rest/v1/{_TABLE}"

    def _do(tok: str):
        return httpx.request(
            method,
            url,
            params=params,
            json=json_body,
            headers=_headers(tok, anon_key, write=write),
            timeout=_REQUEST_TIMEOUT_SEC,
        )

    try:
        resp = _do(token)
        if resp.status_code == 401:
            new_token = _force_refresh_token()
            if new_token:
                resp = _do(new_token)
        if resp.status_code >= 400:
            logger.warning(
                "[HISTORY] %s %s -> %s %s",
                method,
                _TABLE,
                resp.status_code,
                (resp.text or "")[:200],
            )
            return None
        return resp
    except Exception as exc:
        logger.warning("[HISTORY] request failed: %s", exc)
        return None


def save_history_record(
    *,
    practice_type: str,
    content: Dict[str, Any],
    subtype: Optional[str] = None,
    title: Optional[str] = None,
    overall_level: Optional[str] = None,
    score: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """INSERT one learning-history record for the current user (append-only).

    Returns the saved row dict, or ``None`` if not logged in / on failure.
    """
    if practice_type not in VALID_PRACTICE_TYPES:
        logger.warning("[HISTORY] invalid practice_type=%s", practice_type)
        return None

    body: Dict[str, Any] = {
        "practice_type": practice_type,
        "subtype": subtype,
        "title": title,
        "overall_level": overall_level,
        "score": score,
        "content": content or {},
    }
    resp = _request("POST", json_body=body, write=True)
    if resp is None:
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


def list_history(
    *,
    practice_type: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Return the current user's history rows (newest first), without ``content``.

    Returns ``[]`` for guests/logged-out users or on failure.
    """
    params: Dict[str, str] = {
        "select": _LIST_SELECT,
        "order": "created_at.desc",
        "limit": str(max(1, int(limit))),
    }
    if practice_type:
        params["practice_type"] = f"eq.{practice_type}"
    resp = _request("GET", params=params)
    if resp is None:
        return []
    try:
        data = resp.json()
    except Exception:
        return []
    return data if isinstance(data, list) else []


def list_history_stats_rows(
    *,
    page_size: int = 200,
    max_rows: int = 5000,
) -> Optional[List[Dict[str, Any]]]:
    """Return lightweight rows for home-dashboard stats (includes ``content``).

    Paginates until ``max_rows`` or no more data. Returns ``None`` on auth /
    network failure (distinct from an empty list).
    """
    rows: List[Dict[str, Any]] = []
    offset = 0
    page_size = max(1, int(page_size))
    max_rows = max(1, int(max_rows))
    while len(rows) < max_rows:
        limit = min(page_size, max_rows - len(rows))
        params: Dict[str, str] = {
            "select": "created_at,practice_type,subtype,overall_level,content",
            "order": "created_at.desc",
            "limit": str(limit),
            "offset": str(offset),
        }
        resp = _request("GET", params=params)
        if resp is None:
            return None if not rows else rows
        try:
            batch = resp.json()
        except Exception:
            return None if not rows else rows
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        if len(batch) < limit:
            break
        offset += len(batch)
    return rows


def get_history_record(record_id: str) -> Optional[Dict[str, Any]]:
    """Return a single history row (including ``content``) owned by the user."""
    if not record_id:
        return None
    params = {"id": f"eq.{record_id}", "select": "*", "limit": "1"}
    resp = _request("GET", params=params)
    if resp is None:
        return None
    try:
        data = resp.json()
    except Exception:
        return None
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None
