"""
Namespaced Streamlit session state for mock exam + settings.
Migrates legacy flat keys once into ``st.session_state["mock"]`` / ``["settings"]``.
"""

from __future__ import annotations

from typing import Any, Dict, MutableMapping

import streamlit as st

from config.pattern_config import PATTERN_BANK

_DEFAULT_MOCK: Dict[str, Any] = {
    "mock_page": "SURVEY",
    "exam": [],
    "current_exam": [],
    "survey_results": {},
    "current_idx": 0,
    "results": [],
    "last_result": None,
    "recordings": {},
    "exam_listen_nonce": None,
    "question_play_counts": {},
    "analysis_status": "",
    "analysis_done": False,
    "analysis_error_msg": "",
    "analysis_result": None,
    "audio_bytes": None,
    "preview_transcript": None,
    "exam_finished": False,
    "final_report_generated": False,
    "overall_estimated_level": None,
    "analytics_cache": None,
    "downloadable_report_bytes": None,
}

_DEFAULT_SETTINGS: Dict[str, Any] = {
    "difficulty": 5,
    "voice_choice": "Eva",
}

_LEGACY_MOCK_KEYS = frozenset(_DEFAULT_MOCK.keys())


def ensure_mock(ss: MutableMapping[str, Any]) -> Dict[str, Any]:
    """Return the mock-exam namespace dict (creates + one-time migration)."""
    if "mock" not in ss:
        ss["mock"] = {}
    m: Dict[str, Any] = ss["mock"]
    if not ss.get("_mock_ns_ready"):
        for k, default in _DEFAULT_MOCK.items():
            if k not in m:
                m[k] = ss.get(k, default)
        ss["_mock_ns_ready"] = True
    else:
        for k, default in _DEFAULT_MOCK.items():
            m.setdefault(k, default)
    return m


def ensure_settings(ss: MutableMapping[str, Any]) -> Dict[str, Any]:
    if "settings" not in ss:
        ss["settings"] = {}
    s: Dict[str, Any] = ss["settings"]
    if not ss.get("_settings_ns_ready"):
        for k, default in _DEFAULT_SETTINGS.items():
            if k not in s:
                s[k] = ss.get(k, default)
        ss["_settings_ns_ready"] = True
    else:
        for k, default in _DEFAULT_SETTINGS.items():
            s.setdefault(k, default)
    return s


def sync_settings_to_legacy(ss: MutableMapping[str, Any]) -> None:
    """Keep legacy top-level keys used by widgets / older snippets."""
    s = ensure_settings(ss)
    ss["difficulty"] = s.get("difficulty", 5)
    ss["voice_choice"] = s.get("voice_choice", "Eva")


def mock_session() -> Dict[str, Any]:
    return ensure_mock(st.session_state)


def settings_session() -> Dict[str, Any]:
    return ensure_settings(st.session_state)


def ensure_pattern(ss: MutableMapping[str, Any]) -> Dict[str, Any]:
    """Pattern drill + description cards namespace."""
    if "pattern" not in ss:
        ss["pattern"] = {}
    p: Dict[str, Any] = ss["pattern"]
    if not ss.get("_pattern_ns_ready"):
        legacy = ss.get("pattern_data") if isinstance(ss.get("pattern_data"), dict) else {}
        for k, v in legacy.items():
            p.setdefault(k, v)
        ss["_pattern_ns_ready"] = True
    defaults = {
        "patterns": PATTERN_BANK,
        "selected_step": "Step 1. 외과적 스캔 (공간/외관)",
        "active_pattern": None,
        "last_transcript": "",
        "last_mastery": 0,
        "recording_active": False,
        "selected_description_sentence_key": None,
        "desc_tts_pending": None,
    }
    for k, v in defaults.items():
        p.setdefault(k, v)
    # Legacy key (unused by new pattern UI); master data loads via pattern_ui_mapping.
    p["description_patterns"] = []
    return p
