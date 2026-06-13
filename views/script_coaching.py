"""Script Coaching — written OPIc script diagnose (Stage 1) + upgrade (Stage 2)."""

from __future__ import annotations

import html
import logging
import time
from typing import Any, Dict, List

import streamlit as st

from components.score_donut_bars import render_score_donut_bars_html
from components.smart_feedback import (
    render_alternative_expressions,
    render_grammar_corrections,
)
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
        if result.get("ok"):
            result = _merge_user_script_fields(result)
        st.session_state[_KEY_DIAGNOSE_RESULT] = result
        if result.get("ok"):
            st.session_state[_KEY_STEP] = "result"
            try:
                from utils.history_sync import save_script_diagnose

                save_script_diagnose(result, question=q, sig=str(time.time()))
            except Exception:
                pass
        st.rerun()


def _sc_card(title: str, body_html: str) -> None:
    """Render a script-report section inside the boxed card style."""
    st.markdown(
        f'<section class="sc-report-card" role="region">'
        f'<div class="sc-card-title">{html.escape(title)}</div>'
        f'<div class="sc-card-body">{body_html}</div>'
        f"</section>",
        unsafe_allow_html=True,
    )


def _merge_user_script_fields(result: Dict[str, Any]) -> Dict[str, Any]:
    """Attach session question/script to a result dict for save & display (no AI changes)."""
    if not isinstance(result, dict):
        return result
    merged = dict(result)
    merged["question_en"] = str(st.session_state.get(_KEY_QUESTION_EN) or "").strip()
    merged["original_script"] = str(st.session_state.get(_KEY_SCRIPT_TEXT) or "").strip()
    return merged


def _resolve_original_script(report: Dict[str, Any]) -> str:
    """Original script from saved report fields or live session."""
    if isinstance(report, dict):
        saved = str(report.get("original_script") or "").strip()
        if saved:
            return saved
    return str(st.session_state.get(_KEY_SCRIPT_TEXT) or "").strip()


def _sc_bullets_html(items: Any) -> str:
    if not isinstance(items, (list, tuple)):
        return ""
    lis = "".join(
        f"<li>{html.escape(str(x))}</li>" for x in items if str(x).strip()
    )
    return f"<ul>{lis}</ul>" if lis else ""


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
    if result.get("ok"):
        result = _merge_user_script_fields(result)
    st.session_state[_KEY_UPGRADE_RESULT] = result
    if result.get("ok"):
        st.session_state[_KEY_STEP] = "upgrade_result"
        try:
            from utils.history_sync import save_script_upgrade

            save_script_upgrade(result, sig=str(time.time()))
        except Exception:
            pass
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

    _sc_card(
        "더 높은 등급으로 다시 써 보기",
        "<p>진단 등급을 기준으로 AI가 스크립트를 목표 등급 수준으로 변환해 줍니다.</p>",
    )

    if mode == "polish":
        _sc_card(
            "이미 최상위 등급이에요",
            "<p>표현을 한 단계 더 다듬은 보완본을 만들어 드릴까요?</p>",
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
        <section class="mx-mode-intro" role="region" aria-label="스크립트 진단 리포트">
          <h2 class="mx-mode-title">스크립트 진단 리포트</h2>
          <p class="mx-mode-subtitle">입력한 답변 스크립트를 바탕으로 AI가 정리했어요.</p>
          <p class="tp-mini-topic">예상 등급 · {level} · 단어 수 {wc}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    question = str(st.session_state.get(_KEY_QUESTION_EN) or "").strip()
    script_text = str(st.session_state.get(_KEY_SCRIPT_TEXT) or "").strip()
    if question or script_text:
        parts: List[str] = []
        if question:
            parts.append(f'<p class="sc-q">Q. {html.escape(question)}</p>')
        if script_text:
            parts.append(f'<p class="sc-script">{html.escape(script_text)}</p>')
        _sc_card("내가 작성한 스크립트", "".join(parts))

    summary = str(report.get("summary") or "").strip()
    _sc_card(
        "전체 총평",
        f"<p>{html.escape(summary)}</p>"
        if summary
        else "<p>진단 결과를 아래에서 함께 확인해 주세요.</p>",
    )

    breakdown = report.get("score_breakdown")
    score_html = render_score_donut_bars_html(
        breakdown if isinstance(breakdown, dict) else {},
        _SCORE_LABELS,
        str(report.get("overall_level") or ""),
    )
    if score_html:
        st.markdown("##### 점수 요약")
        st.markdown(score_html, unsafe_allow_html=True)

    strengths = report.get("strengths") or []
    _sc_card(
        "가장 좋았던 점",
        _sc_bullets_html(strengths)
        or "<p>이번 답변에서 강점을 더 끌어올릴 여지가 있어요.</p>",
    )

    st.markdown("##### 바로 고치면 좋은 문법")
    render_grammar_corrections(
        "",
        hits=report.get("grammar_corrections") or [],
        show_heading=False,
        empty_message="이번 스크립트에서 눈에 띄는 문법 슬립은 많지 않았어요.",
    )

    st.markdown("##### 표현 업그레이드")
    render_alternative_expressions(
        "",
        hits=report.get("expression_upgrades") or [],
        show_heading=False,
        empty_message="표현을 한 단계 올릴 만한 포인트를 찾지 못했어요.",
    )

    structure_fb = report.get("structure_feedback")
    if isinstance(structure_fb, dict) and (
        structure_fb.get("good") or structure_fb.get("missing") or structure_fb.get("next")
    ):
        lines: List[str] = []
        for g in structure_fb.get("good") or []:
            lines.append(f"<li>잘한 점: {html.escape(str(g))}</li>")
        for m in structure_fb.get("missing") or []:
            lines.append(f"<li>보완: {html.escape(str(m))}</li>")
        nxt = str(structure_fb.get("next") or "").strip()
        if nxt:
            lines.append(f"<li>다음: {html.escape(nxt)}</li>")
        structure_body = f"<ul>{''.join(lines)}</ul>"
    else:
        structure_body = "<p>도입 → 뒷받침 2~3개 → 마무리 흐름을 의식해 보세요.</p>"
    _sc_card("답변 구조 피드백", structure_body)

    improved = report.get("improved_sentences") or []
    if improved:
        sents: List[str] = []
        for item in improved:
            if isinstance(item, dict):
                sent = str(item.get("sentence") or "").strip()
            else:
                sent = str(item or "").strip()
            if sent:
                sents.append(sent)
        body = _sc_bullets_html(sents)
        if body:
            _sc_card("다시 말하기 추천 문장", body)

    missions = report.get("missions") or []
    if missions:
        body = _sc_bullets_html(missions)
        if body:
            _sc_card("다음 연습 미션", body)

    weaknesses = report.get("weaknesses") or []
    if weaknesses:
        body = _sc_bullets_html(weaknesses)
        if body:
            _sc_card("보완점", body)

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
    st.markdown(
        '<div class="mx-marker sc-upgrade-ba-marker" aria-hidden="true"></div>',
        unsafe_allow_html=True,
    )

    transition = _level_transition_label(report)
    st.markdown(
        f"""
        <section class="mx-mode-intro" role="region" aria-label="스크립트 변환 리포트">
          <h2 class="mx-mode-title">스크립트 변환 리포트</h2>
          <p class="mx-mode-subtitle">목표 등급 수준으로 다시 쓴 스크립트예요.</p>
          <p class="tp-mini-topic">등급 변환 · {transition}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    original = _resolve_original_script(report)
    upgraded = str(report.get("upgraded_script") or "").strip()

    if original:
        st.markdown(
            '<div class="sc-ba-block">'
            '<div class="sc-ba-label">내 원래 스크립트</div>'
            f'<div class="sc-ba-original"><p>{html.escape(original)}</p></div>'
            "</div>",
            unsafe_allow_html=True,
        )

    if upgraded:
        st.markdown(
            '<div class="sc-ba-block">'
            '<div class="sc-ba-label sc-ba-label--accent">업그레이드</div>'
            f'<div class="sc-ba-upgraded"><p>{html.escape(upgraded)}</p></div>'
            "</div>",
            unsafe_allow_html=True,
        )
    elif not original:
        _sc_card("업그레이드된 스크립트", "<p>변환된 스크립트를 불러오지 못했어요.</p>")

    change_notes = report.get("change_notes") or []
    if change_notes:
        body = _sc_bullets_html(change_notes)
        if body:
            _sc_card("이렇게 바꿨어요", body)

    fill_guides = report.get("fill_in_guides") or []
    if fill_guides:
        body = _sc_bullets_html(fill_guides)
        if body:
            note = (
                "<p>아래 항목은 AI가 지어내지 않고 <strong>직접 추가하면 좋을 내용</strong>이에요. "
                "빈칸을 채워 넣으면 스크립트가 더 풍부해집니다.</p>"
            )
            _sc_card("직접 추가해 보세요", note + body)

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
