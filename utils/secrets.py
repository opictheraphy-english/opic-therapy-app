"""API keys from Streamlit secrets / environment."""

from __future__ import annotations

import os

import streamlit as st


def get_gemini_api_key() -> str | None:
    try:
        secret_key = st.secrets.get("GEMINI_API_KEY")
    except Exception:
        secret_key = None
    return secret_key or os.getenv("GEMINI_API_KEY")


def get_openai_api_key() -> str | None:
    try:
        secret_key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        secret_key = None
    return secret_key or os.getenv("OPENAI_API_KEY")
