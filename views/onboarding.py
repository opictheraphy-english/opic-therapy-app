"""First-run entry + onboarding — single screen (Google login or guest)."""

from __future__ import annotations

import html
from typing import Any, MutableMapping

import streamlit as st

from services.supabase_client import supabase_configured
from utils.auth import google_login_url, is_authenticated, start_guest
from utils.local_profile import persist_onboarding_completion

_MIC_SVG = (
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>'
    '<path d="M19 10v2a7 7 0 0 1-14 0v-2"/>'
    '<line x1="12" y1="19" x2="12" y2="23"/>'
    '<line x1="8" y1="23" x2="16" y2="23"/>'
    "</svg>"
)
_SPARK_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 3l1.4 4.2L18 9l-4.6 1.8L12 15l-1.4-4.2L6 9l4.6-1.8L12 3z"/>'
    '<path d="M19 14l.7 2.1 2.1.7-2.1.7-.7 2.1-.7-2.1-2.1-.7 2.1-.7.7-2.1z"/>'
    "</svg>"
)
_REFRESH_SVG = (
    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/>'
    '<path d="M3 3v5h5"/>'
    '<path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"/>'
    '<path d="M16 16h5v5"/>'
    "</svg>"
)


def _finish_to_home(ss: MutableMapping[str, Any]) -> None:
    ss["entry_gate_completed"] = True
    persist_onboarding_completion(ss, skip_preferences=True)
    ss["page"] = "HOME"
    try:
        st.query_params.clear()
        st.query_params["nav"] = "HOME"
    except Exception:
        pass
    st.rerun()


def _finish_as_guest(ss: MutableMapping[str, Any]) -> None:
    start_guest(ss)
    persist_onboarding_completion(ss, skip_preferences=True)
    ss["page"] = "HOME"
    try:
        st.query_params.clear()
        st.query_params["nav"] = "HOME"
    except Exception:
        pass
    st.rerun()


def _step_card(num: str, icon_svg: str, label: str) -> str:
    return (
        f'<div class="onb-step-card">'
        f'<span class="onb-step-num">{html.escape(num)}</span>'
        f'<span class="onb-step-ico">{icon_svg}</span>'
        f'<span class="onb-step-title">{html.escape(label)}</span>'
        f"</div>"
    )


def _render_onboarding_card_html() -> str:
    return f"""
<section class="onb-wrap" aria-label="앱 소개">
  <div class="onb-card">
    <div class="onb-brand">
      <span class="onb-brand-icon">{_MIC_SVG}</span>
      <span class="onb-brand-text">오픽치료사 · AI 스피킹 코치</span>
    </div>
    <div class="onb-copy">
      <h1 class="onb-title-entry">외우지 말고,<br>말하면서 고쳐보세요</h1>
      <p class="onb-sub-hero">실전처럼 말하고, AI 피드백으로 문법·표현·흐름을 한 번에 점검해요.</p>
    </div>
    <div class="onb-steps" role="list" aria-label="연습 흐름">
      {_step_card("1", _MIC_SVG, "실전처럼 말하기")}
      {_step_card("2", _SPARK_SVG, "AI 피드백 받기")}
      {_step_card("3", _REFRESH_SVG, "다시 말하며 다듬기")}
    </div>
  </div>
</section>
"""


def render_onboarding() -> None:
    ss = st.session_state

    st.markdown('<div class="onb-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(_render_onboarding_card_html(), unsafe_allow_html=True)

    err = ss.pop("_auth_error", None)
    if err:
        st.error(err)

    login_url = ss.get("_google_oauth_url")
    if login_url is None and supabase_configured():
        login_url = google_login_url()
        ss["_google_oauth_url"] = login_url

    st.markdown('<div class="onb-cta-gap" aria-hidden="true"></div>', unsafe_allow_html=True)

    if is_authenticated(ss):
        if st.button(
            "바로 시작하기",
            type="primary",
            use_container_width=True,
            key="onb_continue_logged_in",
        ):
            _finish_to_home(ss)
    elif login_url:
        st.link_button(
            "구글로 시작하기",
            login_url,
            type="primary",
            use_container_width=True,
        )
    elif supabase_configured():
        st.warning(
            "로그인 링크를 만들지 못했어요. 잠시 후 다시 시도하거나 로그인 없이 둘러보기를 이용해 주세요."
        )
    else:
        st.info(
            "구글 로그인 설정(SUPABASE_URL · SUPABASE_ANON_KEY)이 아직 없어요. "
            "지금은 로그인 없이 둘러볼 수 있어요."
        )

    if st.button(
        "로그인 없이 둘러보기",
        use_container_width=True,
        key="onb_guest_start",
        type="secondary",
    ):
        _finish_as_guest(ss)

    st.markdown(
        '<p class="onb-footnote">로그인하면 학습 기록과 피드백이 저장돼요</p>',
        unsafe_allow_html=True,
    )


__all__ = ["render_onboarding"]
