"""Sample scripts placeholder page."""

from __future__ import annotations

import streamlit as st


def render_step_header(step_title: str) -> None:
    st.markdown(
        f"""
        <div class="glass-card" style="border-left:4px solid #0D9488;">
          <div style="font-size:13px;color:#0f766e;font-weight:600;">{step_title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_scripts() -> None:
    render_step_header("Step 4. 처방 스크립트 훈련")
    st.markdown(
        '<div class="glass-card-quiet"><p class="ds-h2" style="margin:0;">샘플 스크립트</p>'
        '<p class="ds-muted">등급별 처방 스크립트가 순차적으로 제공됩니다.</p></div>',
        unsafe_allow_html=True,
    )
