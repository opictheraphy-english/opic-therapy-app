#!/usr/bin/env python3
"""Smoke-test view render entrypoints for NameError / import failures."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import types
import traceback
from contextlib import contextmanager
from typing import Any, Callable, List, Tuple
from unittest.mock import MagicMock, patch


def _install_streamlit_mock() -> None:
    class _SessionState(dict):
        def __getattr__(self, key: str) -> Any:
            try:
                return self[key]
            except KeyError as exc:
                raise AttributeError(key) from exc

        def __setattr__(self, key: str, value: Any) -> None:
            self[key] = value

    st = types.ModuleType("streamlit")
    st.session_state = _SessionState(
        {
            "page": "HOME",
            "user_authenticated": True,
            "is_guest": False,
            "splash_seen_this_session": True,
            "history_selected_id": "test-record-1",
            "history_filter": "all",
            "history_sort": "newest",
            "history_period": "all",
            "mock_mode": None,
            "mock_page": None,
            "practice_portal_selected": False,
            "topic_v2_step": "select_topic",
            "difficulty": 5,
            "pattern_active_tab": "all",
        }
    )

    @contextmanager
    def _col_ctx():
        yield MagicMock()

    def _columns(spec, **kwargs):
        n = spec if isinstance(spec, int) else len(spec)
        return [_col_ctx() for _ in range(n)]

    @contextmanager
    def _container_ctx(**kwargs):
        yield MagicMock()

    class _TabCtx:
        def __enter__(self):
            return MagicMock()

        def __exit__(self, *args):
            return False

    def _tabs(*labels):
        if len(labels) == 1 and isinstance(labels[0], (list, tuple)):
            labels = labels[0]
        return tuple(_TabCtx() for _ in labels)

    st.markdown = MagicMock()
    st.title = MagicMock()
    st.subheader = MagicMock()
    st.header = MagicMock()
    st.button = MagicMock(return_value=False)
    st.rerun = MagicMock()
    st.stop = MagicMock()
    st.caption = MagicMock()
    st.divider = MagicMock()
    st.columns = _columns
    st.container = _container_ctx
    st.expander = lambda *a, **k: _col_ctx()
    st.tabs = _tabs
    st.write = MagicMock()
    st.error = MagicMock()
    st.warning = MagicMock()
    st.info = MagicMock()
    st.success = MagicMock()
    st.cache_data = lambda **k: (lambda f: f)
    st.cache_resource = lambda **k: (lambda f: f)
    st.query_params = {}
    st.text_input = MagicMock(return_value="")
    st.selectbox = MagicMock(return_value="all")
    st.radio = MagicMock(return_value="newest")
    st.multiselect = MagicMock(return_value=[])
    st.select_slider = MagicMock(return_value=0)
    st.slider = MagicMock(return_value=0)
    st.checkbox = MagicMock(return_value=False)

    components = types.ModuleType("streamlit.components")
    components.v1 = types.ModuleType("streamlit.components.v1")
    components.v1.html = MagicMock()
    components.v1.declare_component = MagicMock(return_value=MagicMock())
    st.components = components

    sys.modules["streamlit"] = st
    sys.modules["streamlit.components"] = components
    sys.modules["streamlit.components.v1"] = components.v1


MOCK_RECORD = {
    "id": "test-record-1",
    "practice_type": "mock_exam",
    "subtype": "mock_v2",
    "title": "실전 모의고사",
    "overall_level": "IM2",
    "content": {
        "score_breakdown": {
            "response_amount": 72,
            "relevance": 68,
            "structure": 70,
            "grammar": 65,
            "vocabulary": 71,
            "fluency": 69,
        },
        "summary": "Test summary",
    },
}

TOPIC_RECORD = {
    **MOCK_RECORD,
    "practice_type": "topic_practice",
    "subtype": "topic_v2",
    "title": "주제별 연습",
    "content": {
        **MOCK_RECORD["content"],
        "questions": [{"question": "Tell me about travel", "transcript": "I like travel"}],
        "short_feedback": {"ok": True, "summary": "Good"},
    },
}

SCRIPT_RECORD = {
    **MOCK_RECORD,
    "practice_type": "script_coaching",
    "subtype": "script_coaching",
    "title": "스크립트 첨삭",
    "content": {
        "original_script": "Hello world",
        "upgraded_script": "Hello, world!",
        "summary": "Add punctuation",
    },
}


def _run(label: str, fn: Callable[[], None]) -> Tuple[str, str, str]:
    try:
        fn()
        return label, "OK", ""
    except Exception as exc:
        return label, "FAIL", f"{type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}"


def main() -> int:
    _install_streamlit_mock()
    import streamlit as st

    results: List[Tuple[str, str, str]] = []

    from views.history import _render_detail, _render_score_breakdown, render_history

    results.append(
        _run(
            "history/_render_score_breakdown(mock)",
            lambda: _render_score_breakdown(
                MOCK_RECORD["content"]["score_breakdown"],
                overall_level="IM2",
                practice_type="mock_exam",
                subtype="mock_v2",
            ),
        )
    )

    with patch("views.history.is_authenticated", return_value=True), patch(
        "views.history.list_history", return_value=[MOCK_RECORD]
    ), patch("views.history.get_history_record", return_value=MOCK_RECORD):
        results.append(_run("history/render_history(list)", lambda: render_history()))

    for name, rec in [
        ("history/detail_mock", MOCK_RECORD),
        ("history/detail_topic", TOPIC_RECORD),
        ("history/detail_script", SCRIPT_RECORD),
    ]:
        with patch("views.history.get_history_record", return_value=rec):
            results.append(_run(name, lambda r=rec: _render_detail(str(r["id"]))))

    from views.home import render_home

    results.append(_run("home/render_home", render_home))

    from views.mock_exam import render_learning_portal, mock_session

    mx = mock_session()
    results.append(_run("learn/render_learning_portal", lambda: render_learning_portal(mx)))

    from views.mock_v2 import render_mock_v2
    from views.mini_mock_v2 import render_mini_mock_v2

    st.session_state["mock_mode"] = "mock_v2"
    st.session_state["mock_v2_step"] = "survey"
    results.append(_run("mock_v2/render_mock_v2(survey)", render_mock_v2))

    st.session_state["mock_mode"] = "mini_mock"
    st.session_state["mini_v2_step"] = "saved"
    st.session_state["mini_v2_index"] = 0
    st.session_state["mini_v2_answers"] = [{"transcript": "test answer"}]
    st.session_state["mini_mock_v2_active"] = True
    results.append(_run("mini_mock_v2/render_mini_mock_v2(saved)", render_mini_mock_v2))

    from views.topic_practice_v2 import (
        _render_feedback_ui,
        _render_saved_normal,
        build_topic_practice_header_html,
        render_topic_practice_v2,
    )

    results.append(
        _run(
            "topic_v2/header_html",
            lambda: build_topic_practice_header_html("travel", 0, include_screen_marker=True),
        )
    )

    st.session_state.update(
        {
            "topic_v2_step": "saved",
            "topic_v2_topic": "travel",
            "topic_v2_q_index": 0,
            "topic_v2_questions": [{"en": "Q", "ko": "질문", "opic_type": "description"}],
            "topic_v2_session_topic": "travel",
            "topic_v2_answers": [{"transcript": "I like travel", "stt_status": "ok"}],
        }
    )
    results.append(_run("topic_v2/render_saved", render_topic_practice_v2))

    st.session_state["topic_v2_step"] = "feedback"
    st.session_state["topic_v2_feedback"] = {
        "ok": True,
        "summary": "Nice",
        "strength": "Clear",
        "correction_focus": "Grammar",
        "answer_level": "IM2",
        "better_expression": "Better",
        "upgrade_sample": "Upgraded",
        "practice_mission": "Practice more",
        "keyword_drill": ["because"],
    }
    results.append(_run("topic_v2/render_feedback", render_topic_practice_v2))

    st.session_state["topic_v2_step"] = "question"

    from views.patterns import render_patterns
    from views.settings_page import render_settings
    from views.scripts import render_scripts
    from views.lectures import render_lectures

    results.append(_run("patterns/render_patterns", render_patterns))
    results.append(_run("settings/render_settings", render_settings))
    results.append(_run("scripts/render_scripts", render_scripts))
    results.append(_run("lectures/render_lectures", render_lectures))

    from components.score_donut_bars import render_score_donut_bars_html

    results.append(
        _run(
            "components/render_score_donut_bars_html",
            lambda: render_score_donut_bars_html(
                MOCK_RECORD["content"]["score_breakdown"],
                {"response_amount": "답변량", "relevance": "적합도"},
                "IM2",
            ),
        )
    )

    print("SMOKE RENDER RESULTS")
    print("=" * 60)
    fails = 0
    for label, status, err in results:
        print(f"{label}: {status}")
        if status == "FAIL":
            fails += 1
            print(err)
    print("=" * 60)
    print(f"TOTAL {len(results)} | OK {len(results)-fails} | FAIL {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
