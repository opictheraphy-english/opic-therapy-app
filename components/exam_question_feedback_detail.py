"""Premium per-question feedback detail — grey / green / amber card layers (render only)."""

from __future__ import annotations

import html
from typing import Any, Callable, Dict, List, Optional

import streamlit as st

from services.exam_analytics import detect_risk_flags, result_is_no_speech_row
from services.mock_v2_report_display import format_duration
from utils.feedback_text import (
    normalize_feedback_md,
    normalize_feedback_md_html,
    parse_prescription_sections,
    split_improved_answer_and_mission,
)
from utils.text_utils import DISCOURSE_MARKERS, NO_SPEECH_EMPTY_TEXT, is_real_speech_transcript


def _h(text: Any) -> str:
    return html.escape(str(text or ""))


def _metric_chips_html(res: Dict[str, Any]) -> str:
    metrics = res.get("metrics") or {}
    chips: List[str] = []
    wpm = res.get("wpm")
    if wpm is None:
        wpm = metrics.get("wpm")
    try:
        if wpm is not None and float(wpm) > 0:
            chips.append(f"WPM {float(wpm):.0f}")
    except (TypeError, ValueError):
        pass
    dur = metrics.get("duration_seconds") or res.get("duration_seconds")
    try:
        if dur is not None and float(dur) > 0:
            fmt = format_duration(float(dur))
            if fmt:
                chips.append(fmt)
    except (TypeError, ValueError):
        pass
    sc = metrics.get("sentence_count")
    try:
        if sc is not None and float(sc) > 0:
            chips.append(f"문장 {float(sc):.0f}")
    except (TypeError, ValueError):
        pass
    if not chips:
        return ""
    inner = "".join(f'<span class="eqfd-metric-chip">{_h(c)}</span>' for c in chips)
    return f'<div class="eqfd-metric-chips">{inner}</div>'


def _row_state(res: Dict[str, Any], tx_raw: str) -> tuple[bool, bool, bool]:
    no_speech = result_is_no_speech_row(res)
    pending = (
        not no_speech
        and (
            res.get("diagnosis_status") == "analysis_pending"
            or str(res.get("analysis_status") or "").lower() == "pending"
        )
    )
    tx_no_speech = bool(res.get("no_speech_detected")) or (
        res.get("diagnosis_status") == "no_speech"
    )
    tx_is_real = (
        bool(tx_raw)
        and not tx_no_speech
        and is_real_speech_transcript(tx_raw)
    )
    return no_speech, pending, tx_is_real


def _feedback_text(res: Dict[str, Any]) -> str:
    return normalize_feedback_md(
        str(res.get("semantic_feedback") or res.get("summary_speech_rehab") or "").strip()
    )


def _prescription_html(prescription: str) -> str:
    parsed = parse_prescription_sections(prescription)
    body = parsed.get("body") or ""
    structure = str(parsed.get("structure") or "").strip()
    connectors: List[str] = list(parsed.get("connectors") or [])
    if not connectors:
        connectors = [m for m in DISCOURSE_MARKERS[:5]]

    parts: List[str] = [
        '<div class="eqfd-box eqfd-box--amber">',
        '<div class="eqfd-box-label eqfd-box-label--amber">에릭 노의 처방전</div>',
    ]
    if body:
        parts.append(
            f'<div class="eqfd-box-body eqfd-box-body--amber">'
            f"{normalize_feedback_md_html(body)}</div>"
        )
    if structure:
        parts.append(
            f'<p class="eqfd-rx-line"><span class="eqfd-rx-key">순서 구조</span>'
            f'<span class="eqfd-rx-val">{_h(structure)}</span></p>'
        )
    if connectors:
        chips = "".join(
            f'<span class="eqfd-conn-chip">{_h(c)}</span>' for c in connectors
        )
        parts.append(
            f'<p class="eqfd-rx-line"><span class="eqfd-rx-key">연결어 예시</span>'
            f'<span class="eqfd-conn-row">{chips}</span></p>'
        )
    parts.append("</div>")
    return "".join(parts)


def _grammar_expression_rows_html(
    grammar_hits: List[Dict[str, str]],
    alt_hits: List[Dict[str, Any]],
) -> str:
    rows: List[str] = []
    for row in grammar_hits[:6]:
        wrong = str(row.get("wrong") or row.get("before") or "").strip()
        right = str(row.get("right") or row.get("after") or "").strip()
        if not wrong and not right:
            continue
        rows.append(
            f'<div class="eqfd-fix-row">'
            f'<span class="eqfd-fix-src">{_h(wrong)}</span>'
            f'<span class="eqfd-fix-arrow" aria-hidden="true">→</span>'
            f'<span class="eqfd-fix-alt">{_h(right)}</span>'
            f"</div>"
        )
    for row in alt_hits[:4]:
        phrase = str(row.get("phrase") or row.get("before") or "").strip()
        upgrade = str(row.get("upgrade") or row.get("after") or row.get("suggestion") or "").strip()
        if not phrase and not upgrade:
            continue
        rows.append(
            f'<div class="eqfd-fix-row">'
            f'<span class="eqfd-fix-src">{_h(phrase)}</span>'
            f'<span class="eqfd-fix-arrow" aria-hidden="true">→</span>'
            f'<span class="eqfd-fix-alt">{_h(upgrade)}</span>'
            f"</div>"
        )
    if not rows:
        return ""
    return (
        '<div class="eqfd-coach-section">'
        '<div class="eqfd-box-label">문법 · 표현 · 구조</div>'
        f'{"".join(rows)}'
        "</div>"
    )


def _structure_summary_html(struct: Optional[Dict[str, Any]]) -> str:
    if not struct:
        return ""
    good = [str(x).strip() for x in (struct.get("good") or [])[:2] if str(x).strip()]
    missing = [str(x).strip() for x in (struct.get("missing") or [])[:2] if str(x).strip()]
    if not good and not missing:
        return ""
    lines: List[str] = []
    if good:
        lines.append(f'<p class="eqfd-struct-line"><span class="eqfd-struct-k">Good</span>{_h(" · ".join(good))}</p>')
    if missing:
        lines.append(
            f'<p class="eqfd-struct-line"><span class="eqfd-struct-k">Missing</span>{_h(" · ".join(missing))}</p>'
        )
    return f'<div class="eqfd-struct-block">{"".join(lines)}</div>'


def _coach_quote_html(title: str, body: str) -> str:
    if not title and not body:
        return ""
    title_html = (
        f'<p class="eqfd-quote-title">{_h(title)}</p>' if title.strip() else ""
    )
    body_html = (
        f'<div class="eqfd-quote-body">{normalize_feedback_md_html(body)}</div>'
        if body.strip()
        else ""
    )
    return (
        '<div class="eqfd-quote-card">'
        '<span class="eqfd-quote-dot" aria-hidden="true"></span>'
        '<div class="eqfd-quote-inner">'
        f"{title_html}{body_html}"
        "</div></div>"
    )


def _model_answer_html(text: str) -> str:
    answer, _ = split_improved_answer_and_mission(text)
    if not answer.strip():
        return ""
    return (
        '<div class="eqfd-box eqfd-box--green eqfd-model-box">'
        '<div class="eqfd-box-label eqfd-box-label--green">이렇게 다시 말해볼 수 있어요</div>'
        f'<p class="eqfd-model-quote">"{_h(answer)}"</p>'
        "</div>"
    )


def _mission_checklist_html(missions: List[str]) -> str:
    items = [str(m).strip() for m in missions if str(m).strip()]
    if not items:
        return ""
    rows = "".join(
        f'<div class="eqfd-check-row">'
        f'<span class="eqfd-check-dot" aria-hidden="true"></span>'
        f'<span class="eqfd-check-txt">{_h(m)}</span>'
        f"</div>"
        for m in items
    )
    return (
        '<div class="eqfd-box eqfd-box--amber">'
        '<div class="eqfd-box-label eqfd-box-label--amber">바로 다음 연습에 써 보세요</div>'
        f'<div class="eqfd-checklist">{rows}</div>'
        "</div>"
    )


def _risk_row_html(res: Dict[str, Any]) -> str:
    risks = detect_risk_flags(res)
    if risks:
        msg = risks[0]
        if len(risks) > 1:
            msg = f"{msg} (+{len(risks) - 1})"
        return (
            '<div class="eqfd-risk eqfd-risk--warn">'
            '<span class="eqfd-risk-ico" aria-hidden="true">!</span>'
            f'<span class="eqfd-risk-txt">{_h(msg)}</span>'
            "</div>"
        )
    return (
        '<div class="eqfd-risk eqfd-risk--ok">'
        '<span class="eqfd-risk-ico eqfd-risk-ico--ok" aria-hidden="true">✓</span>'
        '<span class="eqfd-risk-txt">특이 위험 패턴 없음</span>'
        "</div>"
    )


def _load_student_feedback(
    result: Dict[str, Any],
    transcript: str,
    question_text: str,
) -> Optional[Dict[str, Any]]:
    try:
        from services.feedback.feedback_builder import build_student_feedback

        return build_student_feedback(result, transcript, question_text=question_text)
    except Exception:
        return None


def render_eqfd_coaching_layers(
    result: Dict[str, Any],
    transcript: str,
    *,
    question_text: str = "",
    show_coach_quote: bool = True,
    extra_missions: Optional[List[str]] = None,
) -> None:
    """Layers 5–8: coaching quote, fixes, model answer, missions, risk."""
    t = (transcript or "").strip()
    if not t or not is_real_speech_transcript(t):
        st.markdown(_risk_row_html(result), unsafe_allow_html=True)
        return

    student_feedback = _load_student_feedback(result, t, question_text)
    from utils.coaching_feedback import merge_alt_hits, merge_grammar_hits

    g_hits = merge_grammar_hits(t, result)
    a_hits = merge_alt_hits(t, result)
    struct_fb = None
    improved_ans: Optional[str] = None
    next_missions: Optional[List[str]] = None
    coach_title: Optional[str] = None
    coach_body: Optional[str] = None

    if student_feedback:
        g_hits = student_feedback.get("grammar_corrections") or g_hits
        a_hits = student_feedback.get("expression_upgrades") or a_hits
        struct_fb = student_feedback.get("structure_feedback")
        improved_ans = (student_feedback.get("improved_answer") or "").strip() or None
        next_missions = student_feedback.get("next_missions")
        coach_title = (student_feedback.get("coach_title") or "").strip() or None
        coach_body = (student_feedback.get("coach_body") or "").strip() or None

    if show_coach_quote and (coach_title or coach_body):
        st.markdown(
            _coach_quote_html(coach_title or "답변 잘 들었어요", coach_body or ""),
            unsafe_allow_html=True,
        )

    fix_html = _grammar_expression_rows_html(g_hits or [], a_hits or [])
    struct_html = _structure_summary_html(struct_fb)
    if fix_html or struct_html:
        st.markdown(fix_html + struct_html, unsafe_allow_html=True)

    if not improved_ans:
        from utils.coaching_feedback import build_improved_answer_example

        improved_ans = build_improved_answer_example(t, g_hits or [], a_hits or [])

    missions: List[str] = list(extra_missions or [])
    split_answer, split_missions = split_improved_answer_and_mission(improved_ans or "")
    if split_answer:
        improved_ans = split_answer
    missions.extend(split_missions)
    if next_missions:
        missions.extend(str(m) for m in next_missions if str(m).strip())
    if not missions:
        from utils.coaching_feedback import build_next_missions

        missions = build_next_missions(t, g_hits or [], a_hits or [])

    model_html = _model_answer_html(improved_ans or "")
    if model_html:
        st.markdown(model_html, unsafe_allow_html=True)

    mission_html = _mission_checklist_html(missions)
    if mission_html:
        st.markdown(mission_html, unsafe_allow_html=True)

    st.markdown(_risk_row_html(result), unsafe_allow_html=True)


def render_exam_question_feedback_detail(
    row: Dict[str, Any],
    *,
    key_prefix: str = "eqfd",
    on_retry_stt: Optional[Callable[[int], bool]] = None,
    on_retry_analysis: Optional[Callable[[], None]] = None,
    show_type_pill: bool = True,
    show_coaching: bool = True,
) -> None:
    """Render premium expand body for one question (layers 1–8)."""
    qid = int(row.get("q_id") or 0)
    res = row.get("result") or {}
    typ = str(row.get("type") or "").strip()
    question = str(row.get("question") or "—").strip()
    tx_raw = str(res.get("transcript") or "").strip()
    no_speech, pending, tx_is_real = _row_state(res, tx_raw)

    st.markdown('<div class="eqfd-body">', unsafe_allow_html=True)

    if show_type_pill and typ and typ != "—":
        st.markdown(
            f'<div class="eqfd-type-row">'
            f'<span class="eqfd-type-pill">{_h(typ)}</span></div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<p class="eqfd-question">{_h(question)}</p>{_metric_chips_html(res)}',
        unsafe_allow_html=True,
    )

    # Layer 2 — my answer (grey)
    st.markdown('<div class="eqfd-box eqfd-box--grey">', unsafe_allow_html=True)
    st.markdown('<div class="eqfd-box-label">내 답변</div>', unsafe_allow_html=True)
    if no_speech:
        st.markdown(
            '<p class="eqfd-answer eqfd-answer--muted">'
            f"{_h('응답이 충분하지 않았어요. 최소 20~30초 이상 영어로 답변해 주세요.')}"
            "</p>",
            unsafe_allow_html=True,
        )
    elif pending:
        st.markdown(
            '<p class="eqfd-answer eqfd-answer--muted">음성 인식이 완료되지 않았습니다.</p>',
            unsafe_allow_html=True,
        )
        if on_retry_stt and st.button(
            "음성 인식 다시 시도",
            key=f"{key_prefix}_retry_stt_{qid}",
        ):
            try:
                q_idx = int(row.get("question_index", qid - 1))
            except (TypeError, ValueError):
                q_idx = max(0, qid - 1)
            if on_retry_stt(q_idx):
                st.rerun()
        elif on_retry_analysis and st.button(
            "AI 분석 다시 시도",
            key=f"{key_prefix}_retry_ai_{qid}",
        ):
            on_retry_analysis()
            st.rerun()
    else:
        display_tx = tx_raw if tx_is_real else NO_SPEECH_EMPTY_TEXT
        full_key = f"{key_prefix}_tx_full_{qid}"
        show_full = bool(st.session_state.get(full_key))
        clamp_cls = "" if show_full else " eqfd-answer--clamp"
        st.markdown(
            f'<p class="eqfd-answer{clamp_cls}">{_h(display_tx)}</p>',
            unsafe_allow_html=True,
        )
        if tx_is_real and len(display_tx) > 180:
            toggle_label = "접기" if show_full else "전체 보기"
            if st.button(toggle_label, key=f"{key_prefix}_tx_toggle_{qid}"):
                st.session_state[full_key] = not show_full
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    if no_speech:
        fb = normalize_feedback_md(
            str(
                res.get("summary_speech_rehab")
                or res.get("semantic_feedback")
                or "응답이 충분하지 않았어요."
            )
        )
        if fb:
            st.markdown(
                f'<div class="eqfd-box eqfd-box--green">'
                f'<div class="eqfd-box-label eqfd-box-label--green">'
                f'<span aria-hidden="true">✦</span> Ava의 피드백</div>'
                f'<div class="eqfd-box-body eqfd-box-body--green">'
                f"{normalize_feedback_md_html(fb)}</div></div>",
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if pending:
        st.markdown(
            '<div class="eqfd-box eqfd-box--green">'
            '<div class="eqfd-box-label eqfd-box-label--green">'
            '<span aria-hidden="true">✦</span> Ava의 피드백</div>'
            '<p class="eqfd-box-body eqfd-box-body--green">'
            "AI 분석이 완료되면 이 영역에 상세 피드백이 표시됩니다."
            "</p></div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Layer 3 — Ava feedback (green)
    feedback = _feedback_text(res)
    if feedback:
        st.markdown(
            f'<div class="eqfd-box eqfd-box--green">'
            f'<div class="eqfd-box-label eqfd-box-label--green">'
            f'<span aria-hidden="true">✦</span> Ava의 피드백</div>'
            f'<div class="eqfd-box-body eqfd-box-body--green">'
            f"{normalize_feedback_md_html(feedback)}</div></div>",
            unsafe_allow_html=True,
        )

    # Layer 4 — Eric prescription (amber)
    prescription = normalize_feedback_md(str(res.get("prescription") or "").strip())
    if prescription and prescription != "—":
        st.markdown(_prescription_html(prescription), unsafe_allow_html=True)

    # Layers 5–8 — coaching
    if show_coaching and tx_is_real:
        render_eqfd_coaching_layers(
            res,
            tx_raw,
            question_text=question,
            show_coach_quote=True,
        )
    else:
        st.markdown(_risk_row_html(res), unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
