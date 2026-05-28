from __future__ import annotations

import streamlit as st

from ui.styles import inject_global_styles

st.set_page_config(layout="wide")
inject_global_styles()

mode = st.query_params.get("mode", "topic_hub")
if isinstance(mode, list):
    mode = mode[0] if mode else "topic_hub"

if mode == "topic_hub":
    from views.topic_practice_v2 import _KEY_ROLEPLAY_EXPAND, _render_select_topic

    st.session_state[_KEY_ROLEPLAY_EXPAND] = True
    _render_select_topic()
elif mode == "home":
    from views.home import render_home

    render_home()
elif mode == "mock_portal":
    from utils.session_state import ensure_mock
    from views.mock_exam import render_learning_portal

    mx = ensure_mock(st.session_state)
    st.session_state["practice_portal_selected"] = True
    mx["mock_page"] = "PICK"
    render_learning_portal(mx)
elif mode == "script_coaching":
    from utils.session_state import ensure_mock
    from views.script_coaching import render_script_coaching

    ensure_mock(st.session_state)
    st.session_state["mock_mode"] = "script_coaching"
    st.session_state["practice_portal_selected"] = True
    render_script_coaching()
