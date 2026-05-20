"""Safe developer diagnostics — logger only, never print/stderr (Streamlit-safe)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def safe_debug_log(prefix: str, message: str) -> None:
    """Log dev-only diagnostics; must never crash the app on broken pipes."""
    try:
        logger.debug("[%s] %s", prefix, message)
    except Exception:
        pass
