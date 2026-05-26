"""Script Coaching — written OPIc script diagnose (Stage 1) + upgrade (Stage 2)."""

from __future__ import annotations

import html
import logging
from typing import Any, Dict, List

import streamlit as st

from components.topbar import render_top_bar

logger = logging.getLogger(__name__)

_KEY_STEP = "script_coaching_step"
_KEY_QUESTION_EN = "script_coaching_question_en"
_KEY_SCRIPT_TEXT = "script_coaching_script_text"
_KEY_DIAGNOSE_RESULT = "script_coaching_diagnose_result"
_KEY_UPGRADE_RESULT = "script_coaching_upgrade_result"
_KEY_CLEAR_INPUTS = "script_coaching_clear_inputs"

_SCORE_LABELS: Dict[str, str] = {
    "response_amount": "분량",
    "vocabulary": "어휘",
    "grammar": "문법",
    "context": "맥락",
    "structure": "구조",
}


def clear_script_coaching_session() -> None:
    """Clear script coaching UI state (portal reset / leave flow)."""
    for k in (
        _KEY_STEP,
        _KEY_QUESTION_EN,
        _KEY_SCRIPT_TEXT,
        _KEY_DIAGNOSE_RESULT,
        _KEY_UPGRADE_RESULT,
        _KEY_CLEAR_INPUTS,
    ):
        st.session_state.pop(k, None)


def _ensure_defaults() -> None:
    if st.session_state.pop(_KEY_CLEAR_INPUTS, False):
        st.session_state[_KEY_QUESTION_EN] = ""
        st.session_state[_KEY_SCRIPT_TEXT] = ""
    if _KEY_STEP not in st.session_state:
        st.session_state[_KEY_STEP] = "input"
    if _KEY_QUESTION_EN not in st.session_state:
        st.session_state[_KEY_QUESTION_EN] = ""
    if _KEY_SCRIPT_TEXT not in st.session_state:
        st.session_state[_KEY_SCRIPT_TEXT] = ""


def _render_input_form() -> None:
    render_top_bar("스크립트 첨삭", back_href="?nav=MOCK", eyebrow="스크립트 첨삭")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    st.markdown(
        """
        <section class="continue-card continue-card--start mx-mode-card" role="region">
          <div class="cc-title">스크립트 첨삭</div>
          <div class="cc-meta">영어 질문과 내가 쓴 답변 스크립트를 입력하면 AI가 등급과 첨삭 피드백을 알려줘요.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    question_en = st.text_area(
        "질문 (영어)",
        key=_KEY_QUESTION_EN,
        height=100,
        placeholder="예: What kind of music do you usually listen to?",
    )
    script_text = st.text_area(
        "내 답변 스크립트 (영어)",
        key=_KEY_SCRIPT_TEXT,
        height=200,
        placeholder="여기에 답변 스크립트를 영어로 입력해 주세요.",
    )

    if st.button(
        "진단받기",
        type="primary",
        use_container_width=True,
        key="script_coaching_run_diagnose",
    ):
        from services.script_coaching_diagnose_analysis import diagnose_script

        q = str(question_en or "").strip()
        s = str(script_text or "").strip()
        with st.spinner("AI가 스크립트를 진단하고 있어요…"):
            result = diagnose_script(q, s)
        st.session_state[_KEY_DIAGNOSE_RESULT] = result
        if result.get("ok"):
            st.session_state[_KEY_STEP] = "result"
        st.rerun()


def _render_bullet_list(title: str, items: List[str]) -> None:
    if not items:
        return
    st.markdown(f"##### {title}")
    for item in items:
        st.markdown(f"- {html.escape(str(item))}")


def _run_upgrade(current_level: str, target_level: str = "") -> None:
    from services.script_coaching_upgrade_analysis import upgrade_script

    question_en = str(st.session_state.get(_KEY_QUESTION_EN) or "").strip()
    script_text = str(st.session_state.get(_KEY_SCRIPT_TEXT) or "").strip()
    with st.spinner("AI가 스크립트를 변환하고 있어요…"):
        result = upgrade_script(
            question_en,
            script_text,
            current_level,
            target_level=target_level,
            question_ko="",
        )
    st.session_state[_KEY_UPGRADE_RESULT] = result
    if result.get("ok"):
        st.session_state[_KEY_STEP] = "upgrade_result"
    st.rerun()


def _render_upgrade_section(report: Dict[str, Any]) -> None:
    from services.script_coaching_upgrade_analysis import upgrade_options_for

    overall_level = str(report.get("overall_level") or "").strip()
    opts = upgrade_options_for(overall_level)
    mode = str(opts.get("mode") or "").strip().lower()
    one_step = opts.get("one_step")
    two_step = opts.get("two_step")

    upgrade_result = st.session_state.get(_KEY_UPGRADE_RESULT)
    if isinstance(upgrade_result, dict) and not upgrade_result.get("ok"):
        msg = str(upgrade_result.get("error_message") or "").strip()
        if msg:
            st.error(msg)

    st.markdown(
        """
        <section class="continue-card" role="region">
          <div class="cc-eyebrow">스크립트 변환</div>
          <div class="cc-title">더 높은 등급으로 다시 써 보기</div>
          <div class="cc-meta">진단 등급을 기준으로 AI가 스크립트를 목표 등급 수준으로 변환해 줍니다.</div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if mode == "polish":
        st.markdown(
            "이미 최상위 등급입니다. 표현을 더 다듬어 볼까요?",
        )
        if st.button(
            "보완본 받기",
            type="primary",
            use_container_width=True,
            key="script_coaching_upgrade_polish",
        ):
            _run_upgrade(overall_level, target_level="")
        return

    if mode != "upgrade" or not one_step:
        return

    if two_step:
        col1, col2 = st.columns(2)
        with col1:
            if st.button(
                f"한 단계 업그레이드 ({one_step})",
                type="primary",
                use_container_width=True,
                key="script_coaching_upgrade_one_step",
            ):
                _run_upgrade(overall_level, target_level=str(one_step))
        with col2:
            if st.button(
                f"두 단계 업그레이드 ({two_step})",
                type="primary",
                use_container_width=True,
                key="script_coaching_upgrade_two_step",
            ):
                _run_upgrade(overall_level, target_level=str(two_step))
    else:
        if st.button(
            f"한 단계 업그레이드 ({one_step})",
            type="primary",
            use_container_width=True,
            key="script_coaching_upgrade_one_step_only",
        ):
            _run_upgrade(overall_level, target_level=str(one_step))


def _render_diagnose_result(report: Dict[str, Any]) -> None:
    render_top_bar("스크립트 첨삭", back_href="?nav=MOCK", eyebrow="스크립트 첨삭 · 진단 결과")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    level = html.escape(str(report.get("overall_level") or "—"))
    wc = int(report.get("word_count") or 0)
    st.markdown(
        f"""
        <section class="continue-card continue-card--start mx-landing-card" role="region">
          <div class="cc-eyebrow">스크립트 첨삭</div>
          <div class="cc-title">스크립트 진단 결과</div>
          <div class="cc-meta">예상 등급: <strong>{level}</strong> · 단어 수: <strong>{wc}</strong></div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    summary = html.escape(str(report.get("summary") or "").strip())
    if summary:
        st.markdown(
            f"""
            <section class="continue-card" role="region">
              <div class="cc-eyebrow">요약</div>
              <div class="cc-meta">{summary}</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    conn = report.get("connector_summary")
    if isinstance(conn, dict):
        hits = int(conn.get("total_hits") or 0)
        distinct = int(conn.get("distinct_count") or 0)
        found = conn.get("found") or []
        found_txt = ", ".join(html.escape(str(x)) for x in found if str(x).strip())
        st.markdown(
            f"""
            <section class="continue-card" role="region">
              <div class="cc-eyebrow">접속사</div>
              <div class="cc-meta">총 {hits}회 · {distinct}종류{f" · {found_txt}" if found_txt else ""}</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    breakdown = report.get("score_breakdown")
    if isinstance(breakdown, dict) and breakdown:
        st.markdown("##### 점수 요약")
        for key, label in _SCORE_LABELS.items():
            try:
                score = int(breakdown.get(key) or 0)
            except (TypeError, ValueError):
                score = 0
            st.progress(max(0, min(100, score)) / 100.0)
            st.caption(f"{label}: {score}/100")

    feedback_blocks = (
        ("접속사 피드백", "connector_feedback"),
        ("어휘 피드백", "vocabulary_feedback"),
        ("맥락 피드백", "context_feedback"),
        ("문법 교정", "correction_focus"),
        ("표현 개선", "better_expression"),
    )
    for title, key in feedback_blocks:
        text = str(report.get(key) or "").strip()
        if not text:
            continue
        st.markdown(
            f"""
            <section class="continue-card" role="region">
              <div class="cc-eyebrow">{html.escape(title)}</div>
              <div class="cc-meta">{html.escape(text)}</div>
            </section>
            """,
            unsafe_allow_html=True,
        )

    _render_bullet_list("강점", report.get("strengths") or [])
    _render_bullet_list("보완점", report.get("weaknesses") or [])

    _render_upgrade_section(report)

    if st.button(
        "답변 고쳐서 다시 진단",
        use_container_width=True,
        key="script_coaching_rediagnose_keep_inputs",
    ):
        st.session_state.pop(_KEY_DIAGNOSE_RESULT, None)
        st.session_state[_KEY_STEP] = "input"
        st.rerun()

    if st.button(
        "새 스크립트 진단하기",
        use_container_width=True,
        key="script_coaching_new_script_diagnose",
    ):
        st.session_state[_KEY_CLEAR_INPUTS] = True
        st.session_state.pop(_KEY_DIAGNOSE_RESULT, None)
        st.session_state[_KEY_STEP] = "input"
        st.rerun()

    if st.button(
        "학습 방식 다시 선택",
        use_container_width=True,
        key="script_coaching_back_portal",
    ):
        from views.mock_exam import reset_to_learning_portal

        clear_script_coaching_session()
        reset_to_learning_portal()
        st.rerun()


def _level_transition_label(report: Dict[str, Any]) -> str:
    mode = str(report.get("mode") or "").strip().lower()
    current = html.escape(str(report.get("current_level") or "—"))
    if mode == "polish":
        return f"{current} → AL 보완"
    target = html.escape(str(report.get("target_level") or "—"))
    return f"{current} → {target}"


def _render_upgrade_result(report: Dict[str, Any]) -> None:
    render_top_bar("스크립트 첨삭", back_href="?nav=MOCK", eyebrow="스크립트 첨삭 · 변환 결과")
    st.markdown('<div class="mx-marker" aria-hidden="true"></div>', unsafe_allow_html=True)

    transition = _level_transition_label(report)
    st.markdown(
        f"""
        <section class="continue-card continue-card--start mx-landing-card" role="region">
          <div class="cc-eyebrow">스크립트 첨삭</div>
          <div class="cc-title">스크립트 변환 결과</div>
          <div class="cc-meta">등급 변환: <strong>{transition}</strong></div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    upgraded = str(report.get("upgraded_script") or "").strip()
    st.markdown("##### 업그레이드된 스크립트")
    st.text_area(
        "업그레이드된 스크립트",
        value=upgraded,
        height=280,
        disabled=True,
        label_visibility="collapsed",
        key="script_coaching_upgraded_script_display",
    )

    _render_bullet_list("이렇게 바꿨어요", report.get("change_notes") or [])

    fill_guides = report.get("fill_in_guides") or []
    if fill_guides:
        st.markdown(
            "아래 항목은 AI가 지어내지 않고, **직접 추가하면 좋을 내용**이에요. "
            "빈칸을 채워 넣으면 스크립트가 더 풍부해집니다."
        )
        _render_bullet_list("직접 추가해 보세요", fill_guides)

    if st.button(
        "진단 결과로 돌아가기",
        use_container_width=True,
        key="script_coaching_back_to_diagnose",
    ):
        st.session_state[_KEY_STEP] = "result"
        st.rerun()

    if st.button(
        "학습 방식 다시 선택",
        use_container_width=True,
        key="script_coaching_back_portal_from_upgrade",
    ):
        from views.mock_exam import reset_to_learning_portal

        clear_script_coaching_session()
        reset_to_learning_portal()
        st.rerun()


def render_script_coaching() -> None:
    """Entry: diagnose form → result report → upgrade result."""
    _ensure_defaults()
    step = str(st.session_state.get(_KEY_STEP) or "input").strip()

    if step == "upgrade_result":
        upgrade_report = st.session_state.get(_KEY_UPGRADE_RESULT)
        if isinstance(upgrade_report, dict) and upgrade_report.get("ok"):
            _render_upgrade_result(upgrade_report)
            return
        st.session_state[_KEY_STEP] = "result"

    if step == "result":
        report = st.session_state.get(_KEY_DIAGNOSE_RESULT)
        if isinstance(report, dict) and report.get("ok"):
            _render_diagnose_result(report)
            return
        else:
            st.session_state[_KEY_STEP] = "input"

    _render_input_form()
    report = st.session_state.get(_KEY_DIAGNOSE_RESULT)
    if isinstance(report, dict) and not report.get("ok"):
        msg = str(report.get("error_message") or "").strip()
        if msg:
            st.error(msg)
