"""One session splash before Home — not persisted, not onboarding."""

from __future__ import annotations

import streamlit as st


def render_splash_screen() -> None:
    """Premium mobile-style splash; pair with app.py two-phase rerun + sleep."""
    st.markdown(
        '<div class="splash-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<section class="splash-root" aria-label="앱 시작">
  <div class="splash-card">
    <p class="splash-brand">오픽치료사</p>
    <p class="splash-sub">AI 오픽 말하기 코치</p>
    <p class="splash-line">오늘도 한 문장씩,<br/>더 자연스럽게 말해볼까요?</p>
    <p class="splash-loading">학습 환경을 준비하고 있어요...</p>
    <div class="splash-dots" aria-hidden="true">
      <span></span><span></span><span></span>
    </div>
  </div>
</section>
        """,
        unsafe_allow_html=True,
    )


__all__ = ["render_splash_screen"]
