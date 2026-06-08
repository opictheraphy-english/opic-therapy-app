"""App settings."""

from __future__ import annotations

import streamlit as st

from utils.auth import current_user_name, is_authenticated, logout
from utils.local_profile import reset_onboarding_for_rerun


def _render_account_section() -> None:
    ss = st.session_state
    if is_authenticated(ss):
        name = current_user_name(ss) or "회원"
        email = str(ss.get("user_email") or "")
        st.markdown(
            f"""
            <div class="glass-card-quiet" style="margin-bottom:12px;">
              <p style="margin:0 0 4px 0;font-weight:700;color:#0f172a;">환영합니다, {name}님</p>
              <p class="ds-muted" style="margin:0;">{email}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("로그아웃", use_container_width=True, key="settings_logout"):
            logout(ss)
    else:
        st.markdown(
            """
            <div class="glass-card-quiet" style="margin-bottom:12px;">
              <p style="margin:0 0 4px 0;font-weight:700;color:#0f172a;">게스트 모드로 이용 중</p>
              <p class="ds-muted" style="margin:0;">구글로 로그인하면 학습 기록을 계정에 안전하게 이어갈 수 있어요.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("로그인하기", use_container_width=True, key="settings_login"):
            logout(ss)


def render_step_header(step_title: str) -> None:
    st.markdown(
        f"""
        <div class="glass-card" style="border-left:4px solid #0D9488;">
          <div style="font-size:13px;color:#0f766e;font-weight:600;">{step_title}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_settings() -> None:
    render_step_header("Step 6. 환경 설정")
    st.markdown('<p class="ds-h2">환경 설정</p>', unsafe_allow_html=True)

    _render_account_section()

    st.divider()
    st.markdown('<p class="ds-muted" style="margin-top:8px;">앱을 처음 쓰는 분께 안내 화면을 다시 보여 드립니다.</p>', unsafe_allow_html=True)
    if st.button("온보딩 다시 보기", use_container_width=True, key="settings_reset_onboarding"):
        reset_onboarding_for_rerun(st.session_state)
        st.rerun()
