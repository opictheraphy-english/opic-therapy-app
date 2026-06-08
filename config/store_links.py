"""External shop links."""

from __future__ import annotations

import os

# Render / .env 에서 SMART_STORE_URL 로 덮어쓸 수 있음 (예: https://smartstore.naver.com/your_store)
_DEFAULT_SMART_STORE_URL = "https://smartstore.naver.com/opictherapist"


def smart_store_url() -> str:
    return (os.getenv("SMART_STORE_URL") or _DEFAULT_SMART_STORE_URL).strip()
