"""First-launch entry: Guest (default) vs login placeholder (no real OAuth)."""

from __future__ import annotations

import streamlit as st

from utils.local_profile import complete_entry_guest, complete_entry_login_placeholder


def render_entry_gate() -> None:
    st.markdown(
        """
        <section class="home-hero" style="margin-top:1rem;">
          <div class="ds-hero-tag">OPIc Speech Therapy</div>
          <h1 class="ds-display">AI OPIc Speech Therapy</h1>
          <p class="ds-subtitle">실전형 AI 모의고사와 발화 정밀 분석 리포트를 제공합니다. 회원가입 없이 바로 시작할 수 있습니다.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)
    with c1:
        if st.button(
            "게스트로 바로 시작하기",
            type="primary",
            use_container_width=True,
            key="entry_guest_primary",
        ):
            complete_entry_guest(st.session_state)
            st.rerun()
    with c2:
        if st.button(
            "로그인하고 학습 기록 저장하기",
            use_container_width=True,
            key="entry_login_secondary",
        ):
            st.session_state["_login_info_open"] = True
            st.rerun()

    if st.session_state.get("_login_info_open"):
        st.markdown(
            """
            <div class="glass-card-quiet" style="margin-top:12px;">
              <p style="margin:0 0 8px 0;font-weight:700;color:#0f172a;">클라우드 로그인 준비 중</p>
              <p class="ds-muted" style="margin:0;">Google 로그인 및 계정 간 학습 기록 동기화는 추후 지원 예정입니다.
              지금은 이 기기에 로컬로 진행 상황이 저장됩니다.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button(
                "게스트로 시작 (로컬 저장)",
                type="primary",
                use_container_width=True,
                key="entry_from_login_guest",
            ):
                st.session_state.pop("_login_info_open", None)
                complete_entry_guest(st.session_state)
                st.rerun()
        with b2:
            if st.button(
                "알겠습니다 · 동일하게 시작",
                use_container_width=True,
                key="entry_login_placeholder_continue",
            ):
                st.session_state.pop("_login_info_open", None)
                complete_entry_login_placeholder(st.session_state)
                st.rerun()

    st.caption("게스트 모드에서도 학습 기록은 이 브라우저·기기에 저장됩니다.")
