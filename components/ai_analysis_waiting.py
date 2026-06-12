"""Polished waiting UI while Gemini analysis runs (display only)."""

from __future__ import annotations

import html
import random
import time
from typing import Any, Optional

import streamlit as st

from config.waiting_tips import WAITING_TIPS, WaitingTip
from components.brand_character import render_character_svg

# Local UI testing only — never enable in production.
DEBUG_SLOW_ANALYSIS_UI_DELAY_SEC = 1.5


def debug_slow_analysis_enabled() -> bool:
    """Optional hold so the waiting card stays visible after analysis (default off)."""
    return bool(st.session_state.get("debug_slow_analysis_ui"))


def finish_analysis_waiting_ui(
    wait_slot: Any,
    session_id: str,
    *,
    final_stage_label: str = "거의 다 됐어요…",
) -> None:
    """Clear waiting UI; debug mode keeps it on screen briefly before feedback."""
    if debug_slow_analysis_enabled():
        with wait_slot.container():
            render_ai_analysis_waiting(session_id, stage_label=final_stage_label)
        time.sleep(DEBUG_SLOW_ANALYSIS_UI_DELAY_SEC)
    wait_slot.empty()


def reset_waiting_tip_session() -> None:
    """Clear tip binding so the next analysis picks a fresh tip."""
    st.session_state.pop("current_waiting_tip", None)
    st.session_state.pop("waiting_tip_session_id", None)


def ensure_waiting_tip(session_id: str) -> WaitingTip:
    """Pick one tip per analysis session; stable across reruns in the same run."""
    sid = (session_id or "").strip() or "default"
    if st.session_state.get("waiting_tip_session_id") != sid:
        st.session_state["waiting_tip_session_id"] = sid
        st.session_state["current_waiting_tip"] = random.choice(WAITING_TIPS)
    tip = st.session_state.get("current_waiting_tip")
    if not isinstance(tip, dict) or not tip.get("pattern"):
        tip = random.choice(WAITING_TIPS)
        st.session_state["current_waiting_tip"] = tip
    return tip  # type: ignore[return-value]


def render_ai_analysis_waiting(
    session_id: str,
    *,
    stage_label: Optional[str] = None,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    footnote: Optional[str] = None,
) -> None:
    """Waiting card with CSS animation + one OPIc tip (no external assets)."""
    tip = ensure_waiting_tip(session_id)
    stage = (stage_label or "").strip()
    stage_html = (
        f'<p class="mx-ai-wait-stage">{html.escape(stage)}</p>' if stage else ""
    )
    wait_title = (title or "치료사가 답변을 듣고 있어요").strip()
    wait_sub = (
        subtitle
        or "문법, 표현, 흐름을 차근차근 확인하는 중입니다.<br/>잠시만 기다려 주세요."
    ).strip()
    footnote_html = ""
    if footnote and footnote.strip():
        footnote_html = (
            f'<p class="mx-ai-wait-footnote">{html.escape(footnote.strip())}</p>'
        )
    pat = html.escape(str(tip.get("pattern") or ""))
    meaning = html.escape(str(tip.get("meaning") or ""))
    example = html.escape(str(tip.get("example") or ""))

    character_svg = render_character_svg("listening", 84)
    wave_svg = (
        '<svg class="mx-ai-wait-wave" width="150" height="26" viewBox="0 0 150 26" '
        'aria-hidden="true" xmlns="http://www.w3.org/2000/svg">'
        '<polyline class="mx-ai-wait-wave-line" '
        'points="6,13 32,13 42,5 54,21 66,2 78,18 88,13 144,13" '
        'fill="none" stroke="#1D9E75" stroke-width="2.4" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg>"
    )

    st.markdown(
        f"""
        <div class="mx-ai-wait-marker" aria-hidden="true"></div>
        <section class="mx-ai-wait" role="status" aria-live="polite" aria-busy="true">
          <div class="mx-ai-wait-anim" aria-hidden="true">
            {character_svg}
            {wave_svg}
          </div>
          <h2 class="mx-ai-wait-title">{html.escape(wait_title)}</h2>
          <p class="mx-ai-wait-sub">{wait_sub}</p>
          {footnote_html}
          {stage_html}
          <div class="mx-ai-wait-tip">
            <p class="mx-ai-wait-tip-eyebrow">기다리는 동안 보는 오픽 꿀패턴</p>
            <p class="mx-ai-wait-tip-label">Pattern</p>
            <p class="mx-ai-wait-tip-pattern">{pat}</p>
            <p class="mx-ai-wait-tip-label">Meaning</p>
            <p class="mx-ai-wait-tip-text">{meaning}</p>
            <p class="mx-ai-wait-tip-label">Example</p>
            <p class="mx-ai-wait-tip-example">{example}</p>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_topic_mini_report_waiting(
    session_id: str,
    *,
    stage_label: Optional[str] = None,
) -> None:
    render_ai_analysis_waiting(
        session_id,
        stage_label=stage_label,
        title="AI가 3개 답변을 분석하고 있어요",
        subtitle=(
            "복원 발화, 문법, 표현, 답변 흐름을 한 번에 정리하는 중입니다.<br/>"
            "조금 시간이 걸릴 수 있어요."
        ),
        footnote="분석이 완료되면 주제별 풀 리포트가 표시됩니다.",
    )
