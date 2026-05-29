"""First-launch entry: Google login (Supabase OAuth) or Guest mode."""

from __future__ import annotations

import streamlit as st

from services.supabase_client import supabase_configured
from utils.auth import google_login_url, start_guest


def render_entry_gate() -> None:
    st.markdown(
        """
        <section class="home-hero" style="margin-top:1rem;">
          <div class="ds-hero-tag">OPIc Speech Therapy</div>
          <h1 class="ds-display">AI OPIc Speech Therapy</h1>
          <p class="ds-subtitle">실전형 AI 모의고사와 발화 정밀 분석 리포트로 OPIc을 준비하세요.
          구글로 로그인하면 학습 기록을 안전하게 이어갈 수 있어요.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    err = st.session_state.pop("_auth_error", None)
    if err:
        st.error(err)

    # Generate the OAuth URL once per session and reuse it. The PKCE verifier is
    # stored on the cached client when the URL is built, so regenerating on every
    # rerun could leave the rendered link pointing at a stale verifier.
    login_url = st.session_state.get("_google_oauth_url")
    if login_url is None and supabase_configured():
        login_url = google_login_url()
        st.session_state["_google_oauth_url"] = login_url

    if login_url:
        # A real anchor reliably navigates the top window to Google's consent
        # page; Supabase redirects back with ?code= (handled in app.py).
        st.link_button(
            "구글로 로그인",
            login_url,
            type="primary",
            use_container_width=True,
        )
    elif supabase_configured():
        st.warning(
            "로그인 링크를 만들지 못했어요. 잠시 후 다시 시도하거나 게스트로 시작해 주세요."
        )
    else:
        st.info(
            "구글 로그인 설정(SUPABASE_URL · SUPABASE_ANON_KEY)이 아직 없어요. "
            "지금은 게스트로 시작할 수 있어요."
        )

    if st.button(
        "게스트로 시작",
        use_container_width=True,
        key="entry_guest_start",
    ):
        start_guest(st.session_state)
        st.rerun()

    st.caption("게스트 모드에서도 학습 기록은 이 브라우저·기기에 저장됩니다.")
