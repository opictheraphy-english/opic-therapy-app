"""First-run onboarding: positioning, goal, level, then home or mock (UI only)."""

from __future__ import annotations

import html
from typing import Any, MutableMapping

import streamlit as st

from utils.local_profile import persist_onboarding_completion

_TARGET_OPTIONS: tuple[tuple[str, str], ...] = (
    ("IM", "IM"),
    ("IH", "IH"),
    ("AL", "AL"),
)

_TARGET_COPY: dict[str, tuple[str, str]] = {
    "IM": ("IM", "기본 답변을 안정적으로 말하고 싶어요."),
    "IH": ("IH", "자연스럽고 길게 말하는 연습이 필요해요."),
    "AL": ("AL", "논리적이고 풍부한 답변을 만들고 싶어요."),
}

_CURRENT_OPTIONS: tuple[tuple[str, str], ...] = (
    ("beginner", "아직 말이 잘 안 나와요"),
    ("short", "짧은 문장은 가능해요"),
    ("minute", "1분 정도는 말할 수 있어요"),
    ("advanced", "IH 이상을 목표로 연습 중이에요"),
)

_CURRENT_COPY: dict[str, tuple[str, str]] = {
    "beginner": ("아직 말이 잘 안 나와요", "단어는 아는데 문장이 바로 안 나와요."),
    "short": ("짧은 문장은 가능해요", "짧게는 말하지만 답변이 금방 끝나요."),
    "minute": ("1분 정도는 말할 수 있어요", "어느 정도 말하지만 흐름이 자주 끊겨요."),
    "advanced": ("IH 이상을 목표로 연습 중이에요", "표현력과 논리성을 더 올리고 싶어요."),
}


def _progress_html(step: int) -> str:
    pct = int((step / 4) * 100)
    dots = []
    for i in range(1, 5):
        cls = "onb-dot onb-dot--on" if i <= step else "onb-dot"
        dots.append(f'<span class="{cls}" aria-hidden="true"></span>')
    return (
        '<header class="onb-progress" aria-label="온보딩 진행">'
        f'<span class="onb-progress-label">Step {step} / 4</span>'
        f'<div class="onb-progress-track" role="progressbar" aria-valuenow="{pct}" '
        f'aria-valuemin="0" aria-valuemax="100">'
        f'<span class="onb-progress-fill" style="width:{pct}%;"></span></div>'
        f'<div class="onb-progress-dots">{"".join(dots)}</div>'
        "</header>"
    )


def _shell_open(step: int) -> None:
    st.markdown('<div class="onb-marker" aria-hidden="true"></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="onb-shell" data-onb-step="{step}">', unsafe_allow_html=True)
    st.markdown(_progress_html(step), unsafe_allow_html=True)


def _shell_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def _head_block(title: str, subtitle: str) -> str:
    return (
        '<section class="onb-head-card">'
        f'<h2 class="onb-h2">{html.escape(title)}</h2>'
        f'<p class="onb-muted">{html.escape(subtitle)}</p>'
        "</section>"
    )


def _choice_card_html(title: str, body: str, *, selected: bool, badge: str | None = None) -> str:
    state = " onb-pick-card--selected" if selected else ""
    mark = '<span class="onb-pick-check" aria-hidden="true">✓</span>' if selected else '<span class="onb-pick-check onb-pick-check--empty" aria-hidden="true"></span>'
    badge_html = (
        f'<span class="onb-pick-badge">{html.escape(badge)}</span>' if badge else ""
    )
    return (
        f'<article class="onb-pick-card{state}" aria-pressed="{"true" if selected else "false"}">'
        f"{mark}{badge_html}"
        f'<p class="onb-pick-title">{html.escape(title)}</p>'
        f'<p class="onb-pick-body">{html.escape(body)}</p>'
        "</article>"
    )


def _skip_to_home(ss: MutableMapping[str, Any]) -> None:
    persist_onboarding_completion(ss, skip_preferences=True)
    ss["page"] = "HOME"
    try:
        st.query_params.clear()
        st.query_params["nav"] = "HOME"
    except Exception:
        pass
    st.rerun()


def _finish_to_home(ss: MutableMapping[str, Any], target: str | None, current_key: str | None) -> None:
    persist_onboarding_completion(
        ss,
        target_level=target,
        current_level_label=current_key,
        skip_preferences=False,
    )
    ss["page"] = "HOME"
    try:
        st.query_params.clear()
        st.query_params["nav"] = "HOME"
    except Exception:
        pass
    st.rerun()


def _finish_to_mock(ss: MutableMapping[str, Any], target: str | None, current_key: str | None) -> None:
    persist_onboarding_completion(
        ss,
        target_level=target,
        current_level_label=current_key,
        skip_preferences=False,
    )
    ss["page"] = "MOCK"
    try:
        st.query_params.clear()
        st.query_params["nav"] = "MOCK"
        st.query_params["mock"] = "SURVEY"
    except Exception:
        pass
    st.rerun()


def _finish_to_pattern(ss: MutableMapping[str, Any], target: str | None, current_key: str | None) -> None:
    persist_onboarding_completion(
        ss,
        target_level=target,
        current_level_label=current_key,
        skip_preferences=False,
    )
    ss["page"] = "PATTERN"
    try:
        st.query_params.clear()
        st.query_params["nav"] = "PATTERN"
    except Exception:
        pass
    st.rerun()


def _recommendation_bullets(target: str | None, current_key: str | None) -> list[str]:
    t = (target or "IH").upper()
    c = current_key or "short"
    base = [
        "패턴 3개 익히기",
        "짧은 답변 1개 말하기",
        "AI 피드백으로 다시 말하기",
    ]
    if c == "beginner":
        return [
            "패턴 2개로 연결어 입에 붙이기",
            "인사 + 한 문장만 말해 보기",
            "모의고사 1문항으로 AI 피드백 받기",
        ]
    if c == "minute":
        return [
            "패턴으로 도입–전개–마무리 틀 잡기",
            f"목표 {t}에 맞는 질문 하나 45초 답하기",
            "AI 코칭 카드로 표현 한 줄만 고쳐 보기",
        ]
    if c == "advanced":
        return [
            "논리 연결어로 답을 촘촘하게 만들기",
            "모의고사 연속 문항으로 리듬 유지",
            "AI 피드백 중 한 가지만 골라 반복",
        ]
    return base


def render_onboarding() -> None:
    ss = st.session_state
    ss.setdefault("onboarding_step", 1)
    step = int(ss.get("onboarding_step") or 1)
    step = max(1, min(4, step))

    _shell_open(step)

    if step == 1:
        st.markdown(
            """
<section class="onb-hero-premium">
  <div class="onb-badge">AI OPIc Speaking Coach</div>
  <h1 class="onb-title-xl">오픽 답변,<br/>외우지 말고<br/>말하면서 고쳐보세요.</h1>
  <p class="onb-sub-hero">
    실전처럼 말하고,<br/>
    AI 피드백으로 문법·표현·흐름을<br/>
    한 번에 점검할 수 있어요.
  </p>
  <div class="onb-mini-mock" aria-label="연습 미리보기">
    <div class="onb-mini-head">
      <span class="onb-mini-tag">오늘의 연습 예시</span>
    </div>
    <p class="onb-mini-q">Tell me about your home.</p>
    <div class="onb-mini-flow">
      <span class="onb-mini-chip onb-mini-chip--rec">녹음하기</span>
      <span class="onb-mini-arrow" aria-hidden="true">→</span>
      <span class="onb-mini-chip onb-mini-chip--ai">AI 분석</span>
      <span class="onb-mini-arrow" aria-hidden="true">→</span>
      <span class="onb-mini-chip">다시 말하기</span>
    </div>
  </div>
</section>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="onb-actions onb-actions--hero">', unsafe_allow_html=True)
        if st.button("시작하기", type="primary", use_container_width=True, key="onb_start"):
            ss["onboarding_step"] = 2
            st.rerun()
        if st.button("건너뛰기", use_container_width=True, key="onb_skip_bottom"):
            _skip_to_home(ss)
        st.markdown("</div>", unsafe_allow_html=True)
        _shell_close()
        return

    if step == 2:
        ss.setdefault("_onb_target", "IH")
        st.markdown(
            _head_block(
                "목표 등급을 골라 주세요",
                "코칭 톤에만 반영돼요. 로그인은 필요 없습니다.",
            ),
            unsafe_allow_html=True,
        )
        st.markdown('<div class="onb-choice-list">', unsafe_allow_html=True)
        for code, _short in _TARGET_OPTIONS:
            title, body = _TARGET_COPY[code]
            sel = ss.get("_onb_target") == code
            st.markdown(
                _choice_card_html(title, body, selected=sel, badge=title),
                unsafe_allow_html=True,
            )
            if st.button(
                "선택" if not sel else "선택됨",
                type="primary" if sel else "secondary",
                use_container_width=True,
                key=f"onb_tgt_{code}",
            ):
                ss["_onb_target"] = code
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="onb-actions onb-actions--split">', unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("이전", key="onb_back_2", use_container_width=True):
                ss["onboarding_step"] = 1
                st.rerun()
        with bc2:
            if st.button("다음", type="primary", use_container_width=True, key="onb_next_2"):
                ss["onboarding_step"] = 3
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        _shell_close()
        return

    if step == 3:
        ss.setdefault("_onb_current", "short")
        st.markdown(
            _head_block(
                "지금 말하기는 어느 쪽에 가깝나요?",
                "가장 가까운 한 가지만 선택해 주세요.",
            ),
            unsafe_allow_html=True,
        )
        st.markdown('<div class="onb-choice-list">', unsafe_allow_html=True)
        for code, _label in _CURRENT_OPTIONS:
            title, sub = _CURRENT_COPY[code]
            sel = ss.get("_onb_current") == code
            st.markdown(
                _choice_card_html(title, sub, selected=sel),
                unsafe_allow_html=True,
            )
            if st.button(
                "선택" if not sel else "선택됨",
                type="primary" if sel else "secondary",
                use_container_width=True,
                key=f"onb_cur_{code}",
            ):
                ss["_onb_current"] = code
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="onb-actions onb-actions--split">', unsafe_allow_html=True)
        bc1, bc2 = st.columns(2)
        with bc1:
            if st.button("이전", key="onb_back_3", use_container_width=True):
                ss["onboarding_step"] = 2
                st.rerun()
        with bc2:
            if st.button("다음", type="primary", use_container_width=True, key="onb_next_3"):
                ss["onboarding_step"] = 4
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        _shell_close()
        return

    target = str(ss.get("_onb_target") or "IH")
    current_key = str(ss.get("_onb_current") or "short")
    bullets = _recommendation_bullets(target, current_key)
    blist = "".join(f"<li>{html.escape(b)}</li>" for b in bullets)
    st.markdown(
        f"""
        <section class="onb-head-card onb-head-card--plan">
          <h2 class="onb-h2">오늘은 이렇게 시작해볼까요?</h2>
          <p class="onb-muted">처음부터 완벽하게 말할 필요는 없어요.<br/>
            짧게 말하고, 피드백 받고, 다시 말하는 과정이 실력입니다.</p>
        </section>
        <section class="onb-plan-card" aria-label="추천 루트">
          <p class="onb-plan-eyebrow">추천 루트</p>
          <ol class="onb-plan-list">{blist}</ol>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="onb-actions onb-actions--stack">', unsafe_allow_html=True)
    if st.button("이전", key="onb_back_4", use_container_width=True):
        ss["onboarding_step"] = 3
        st.rerun()

    if st.button("모의고사 1문항 시작하기", type="primary", use_container_width=True, key="onb_mock"):
        _finish_to_mock(ss, target, current_key)

    if st.button("패턴 먼저 보기", type="secondary", use_container_width=True, key="onb_pattern"):
        _finish_to_pattern(ss, target, current_key)

    if st.button("홈에서 둘러보기", type="secondary", use_container_width=True, key="onb_home"):
        _finish_to_home(ss, target, current_key)
    st.markdown("</div>", unsafe_allow_html=True)

    st.caption("설정에서 「온보딩 다시 보기」를 켜면 이 안내를 다시 볼 수 있어요.")
    _shell_close()


__all__ = ["render_onboarding"]
