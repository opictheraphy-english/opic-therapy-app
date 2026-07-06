"""Premium mock_v2 final report — display markup and row render helpers (no data pipeline)."""

from __future__ import annotations

import html
from typing import Any, Callable, Dict, List, Optional, Tuple

import streamlit as st

from components.exam_question_feedback_detail import render_exam_question_feedback_detail
from services.exam_analytics import result_display_status, result_is_no_speech_row
from services.mock_v2_report_display import (
    RUBRIC_LABELS,
    diagnosis_tip_text,
    has_hangul,
    hero_note,
    level_gap_chip_text,
    metric_chip_labels,
    next_level_token,
    row_feedback_text,
    row_is_no_response,
    sorted_rubric_bars,
    today_kst_label,
)


_SCREEN_MARKER = "m2fr-screen-marker"
_SHOW_ALL_KEY = "m2fr_show_all_questions"


def m2fr_screen_marker_html() -> str:
    return f'<div class="{_SCREEN_MARKER}" aria-hidden="true"></div>'


def _h(text: Any) -> str:
    return html.escape(str(text or ""))


def _level_gap_chip(overall_raw: str, ss: Any) -> str:
    return level_gap_chip_text(overall_raw, resolve_target_level(ss))


_hero_note = hero_note


def build_m2fr_header_html(
    *,
    date_label: str,
    exam_label: str = "실전 모의고사",
    question_count: int = 15,
) -> str:
    return (
        f'<div class="m2fr-header">'
        f'<div class="m2fr-header-left">'
        f'<div class="m2fr-eyebrow">{_h(date_label)} · {_h(exam_label)}</div>'
        f'<h1 class="m2fr-title">최종 리포트</h1>'
        f"</div>"
        f'<span class="m2fr-count-pill">{int(question_count)}문항</span>'
        f"</div>"
    )


def build_m2fr_hero_html(
    *,
    overall_raw: str,
    confidence: Any,
    note: str,
    avg_wpm: Any,
    answered_label: str,
    gap_chip: str,
) -> str:
    grade = _h(overall_raw or "—")
    conf_txt = ""
    try:
        if confidence is not None and str(confidence).strip() != "":
            conf_txt = f"신뢰도 {int(float(confidence))}%"
    except (TypeError, ValueError):
        conf_txt = ""
    wpm_txt = "—"
    try:
        if avg_wpm is not None and str(avg_wpm).strip() not in ("", "—"):
            wpm_txt = f"{float(avg_wpm):.0f}"
    except (TypeError, ValueError):
        wpm_txt = str(avg_wpm or "—")

    chips = [
        f"평균 {wpm_txt} WPM",
        f"답변 {answered_label}",
        gap_chip,
    ]
    chip_html = "".join(f'<span class="m2fr-hero-chip">{_h(c)}</span>' for c in chips)
    note_html = (
        f'<p class="m2fr-hero-note">{_h(note)}</p>' if note.strip() else ""
    )
    conf_html = (
        f'<span class="m2fr-hero-conf">{_h(conf_txt)}</span>' if conf_txt else ""
    )
    return (
        f'<section class="m2fr-hero">'
        f'<div class="m2fr-hero-top">'
        f'<div class="m2fr-hero-grade-block">'
        f'<div class="m2fr-hero-label">종합 예측 등급</div>'
        f'<div class="m2fr-hero-grade-row">'
        f'<span class="m2fr-hero-grade">{grade}</span>'
        f"{conf_html}"
        f"</div>"
        f"</div>"
        f"</div>"
        f"{note_html}"
        f'<div class="m2fr-hero-chips">{chip_html}</div>'
        f"</section>"
    )


def build_m2fr_diagnosis_html(
    rubric: Dict[str, Any],
    *,
    overall_raw: str,
) -> str:
    bars = sorted_rubric_bars(rubric)
    if not bars:
        return (
            '<section class="m2fr-card m2fr-diagnosis">'
            '<h2 class="m2fr-section-title">영역별 진단</h2>'
            '<p class="m2fr-empty">세션 점수 데이터가 아직 없습니다.</p>'
            "</section>"
        )
    lowest_score = min(v for _, v in bars)
    lowest_labels = {lbl for lbl, v in bars if v == lowest_score}
    next_lv = next_level_token(overall_raw)
    lowest_name = next(iter(lowest_labels))
    tip = (
        f'가장 낮은 <span class="m2fr-amber-text">{_h(lowest_name)}</span>'
        f"부터 잡으면 {_h(next_lv)}이 빨라져요"
    )
    rows: List[str] = []
    for label, score in bars:
        is_low = label in lowest_labels and len(bars) > 1
        fill_cls = "m2fr-bar-fill--warn" if is_low else "m2fr-bar-fill"
        val_cls = "m2fr-bar-val--warn" if is_low else "m2fr-bar-val"
        pct = max(4.0, min(100.0, score))
        rows.append(
            f'<div class="m2fr-bar-row">'
            f'<div class="m2fr-bar-head">'
            f'<span class="m2fr-bar-label">{_h(label)}</span>'
            f'<span class="{val_cls}">{score:.0f}</span>'
            f"</div>"
            f'<div class="m2fr-bar-track">'
            f'<div class="{fill_cls}" style="width:{pct:.1f}%"></div>'
            f"</div>"
            f"</div>"
        )
    return (
        f'<section class="m2fr-card m2fr-diagnosis">'
        f'<h2 class="m2fr-section-title">영역별 진단</h2>'
        f'{"".join(rows)}'
        f'<p class="m2fr-diagnosis-tip">{tip}</p>'
        f"</section>"
    )


def build_m2fr_session_summary_html(
    strengths: List[str],
    weaknesses: List[str],
    mission: str = "",
) -> str:
    """Three white session cards: strengths, improvements (+ score bars), mission."""
    from utils.feedback_text import normalize_feedback_md, parse_weakness_bullet

    def _bullet_rows(items: List[str], *, with_scores: bool = False) -> str:
        rows: List[str] = []
        bars: List[str] = []
        for raw in items:
            text = normalize_feedback_md(str(raw).strip())
            if not text:
                continue
            if with_scores:
                label, score, aux = parse_weakness_bullet(text)
                if score is not None and label:
                    pct = max(4.0, min(100.0, score))
                    warn = score < 60.0
                    fill_cls = "m2fr-bar-fill--warn" if warn else "m2fr-bar-fill"
                    val_cls = "m2fr-bar-val--warn" if warn else "m2fr-bar-val"
                    bars.append(
                        f'<div class="m2fr-bar-row m2fr-bar-row--compact">'
                        f'<div class="m2fr-bar-head">'
                        f'<span class="m2fr-bar-label">{_h(label)}</span>'
                        f'<span class="{val_cls}">{score:.0f}</span>'
                        f"</div>"
                        f'<div class="m2fr-bar-track">'
                        f'<div class="{fill_cls}" style="width:{pct:.1f}%"></div>'
                        f"</div></div>"
                    )
                    if aux:
                        rows.append(
                            f'<li class="m2fr-sum-bullet m2fr-sum-bullet--aux">'
                            f'<span class="m2fr-sum-dot"></span>'
                            f'<span>{_h(aux)}</span></li>'
                        )
                    continue
                if aux and not label:
                    rows.append(
                        f'<li class="m2fr-sum-bullet m2fr-sum-bullet--aux">'
                        f'<span class="m2fr-sum-dot"></span>'
                        f'<span>{_h(aux)}</span></li>'
                    )
                    continue
            rows.append(
                f'<li class="m2fr-sum-bullet">'
                f'<span class="m2fr-sum-dot"></span>'
                f'<span>{_h(text)}</span></li>'
            )
        list_html = f"<ul class='m2fr-sum-list'>{''.join(rows)}</ul>" if rows else ""
        bars_html = "".join(bars)
        return list_html + bars_html

    cards: List[str] = []
    s_items = [str(s).strip() for s in strengths if str(s).strip()]
    w_items = [str(w).strip() for w in weaknesses if str(w).strip()]
    mission_txt = normalize_feedback_md(mission)

    if s_items:
        cards.append(
            f'<section class="m2fr-sum-card">'
            f'<div class="m2fr-sum-head">'
            f'<span class="m2fr-sum-icon" aria-hidden="true">✦</span>'
            f'<h3 class="m2fr-sum-title">강점</h3></div>'
            f"{_bullet_rows(s_items)}"
            f"</section>"
        )
    if w_items:
        cards.append(
            f'<section class="m2fr-sum-card">'
            f'<div class="m2fr-sum-head">'
            f'<span class="m2fr-sum-icon" aria-hidden="true">◎</span>'
            f'<h3 class="m2fr-sum-title">주요 개선 포인트</h3></div>'
            f"{_bullet_rows(w_items, with_scores=True)}"
            f"</section>"
        )
    if mission_txt:
        mission_rows = "".join(
            f'<li class="m2fr-sum-bullet">'
            f'<span class="m2fr-sum-dot"></span>'
            f'<span>{_h(line)}</span></li>'
            for line in mission_txt.splitlines()
            if line.strip()
        )
        cards.append(
            f'<section class="m2fr-sum-card">'
            f'<div class="m2fr-sum-head">'
            f'<span class="m2fr-sum-icon" aria-hidden="true">💡</span>'
            f'<h3 class="m2fr-sum-title">추천 미션</h3></div>'
            f"<ul class='m2fr-sum-list'>{mission_rows}</ul>"
            f"</section>"
        )

    if not cards:
        return ""
    return f'<div class="m2fr-session-summary">{"".join(cards)}</div>'


def build_m2fr_sw_html(strengths: List[str], weaknesses: List[str]) -> str:
    """Backward-compatible wrapper — prefer ``build_m2fr_session_summary_html``."""
    return build_m2fr_session_summary_html(strengths, weaknesses)


def build_m2fr_mission_html(mission: str) -> str:
    if not str(mission or "").strip():
        return ""
    return (
        f'<section class="m2fr-mission">'
        f'<div class="m2fr-mission-head">'
        f'<span class="m2fr-mission-icon" aria-hidden="true">💡</span>'
        f'<span class="m2fr-mission-title">이번 주 처방</span>'
        f"</div>"
        f'<p class="m2fr-mission-body">{_h(mission)}</p>'
        f"</section>"
    )


def build_m2fr_qlist_header_html(*, answered: int, no_response: int) -> str:
    return (
        f'<div class="m2fr-qlist-head">'
        f'<h2 class="m2fr-section-title">문항별 피드백</h2>'
        f'<span class="m2fr-qlist-meta">{int(answered)} 답변 · {int(no_response)} 미응답</span>'
        f"</div>"
    )


def _row_feedback_preview(res: Dict[str, Any]) -> str:
    fb = (
        str(res.get("semantic_feedback") or res.get("summary_speech_rehab") or "")
        .strip()
    )
    return fb


def _row_level_pill(res: Dict[str, Any], *, no_response: bool) -> str:
    if no_response:
        return ""
    lvl = str(
        res.get("estimated_level_display") or res.get("estimated_level") or ""
    ).strip()
    if not lvl or lvl in ("—", "분석 대기", "측정 불가"):
        return ""
    return f'<span class="m2fr-pill m2fr-pill--level">{_h(lvl)}</span>'


def build_m2fr_qrow_header_html(
    row: Dict[str, Any],
    *,
    is_open: bool,
) -> str:
    qid = int(row.get("q_id") or 0)
    res = row.get("result") or {}
    topic = str(row.get("topic") or "—").strip()
    no_resp = result_is_no_speech_row(res) or result_display_status(res) in (
        "음성 미감지",
        "응답 부족",
    )
    open_cls = " m2fr-qrow--open" if is_open else ""
    chev = "▴" if is_open else "▾"
    if no_resp:
        status_pill = '<span class="m2fr-pill m2fr-pill--warn">미응답</span>'
        level_pill = ""
    else:
        status_pill = ""
        level_pill = _row_level_pill(res, no_response=False)
    preview = _row_feedback_preview(res)
    if no_resp:
        preview = str(
            res.get("summary_speech_rehab")
            or res.get("semantic_feedback")
            or "응답이 충분하지 않았어요."
        ).strip()
    preview_html = (
        f'<p class="m2fr-qrow-preview">{_h(preview)}</p>' if preview else ""
    )
    return (
        f'<div class="m2fr-qrow-head{open_cls}">'
        f'<div class="m2fr-qrow-top">'
        f'<span class="m2fr-qrow-num">Q{qid}</span>'
        f'<span class="m2fr-pill m2fr-pill--topic">{_h(topic)}</span>'
        f"{status_pill}{level_pill}"
        f'<span class="m2fr-qrow-chev" aria-hidden="true">{chev}</span>'
        f"</div>"
        f"{preview_html}"
        f"</div>"
    )


def render_m2fr_question_row(
    row: Dict[str, Any],
    *,
    on_retry_stt: Optional[Callable[[int], bool]] = None,
) -> None:
    qid = int(row.get("q_id") or 0)
    wid = ascii_widget_key(f"m2fr_q_{qid}")
    open_key = f"m2fr_open_{wid}"
    if open_key not in st.session_state:
        st.session_state[open_key] = False
    is_open = bool(st.session_state[open_key])

    open_wrap_cls = " m2fr-qrow-wrap--open" if is_open else ""
    st.markdown(f'<div class="m2fr-qrow-wrap{open_wrap_cls}">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="m2fr-qrow-toggle-row">'
        f'{build_m2fr_qrow_header_html(row, is_open=is_open)}'
        f"</div>",
        unsafe_allow_html=True,
    )
    if st.button(
        " ",
        key=f"m2fr_toggle_{wid}",
        use_container_width=True,
    ):
        st.session_state[open_key] = not is_open
        st.rerun()

    if is_open:
        _render_m2fr_question_body(row, qid=qid, on_retry_stt=on_retry_stt)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_m2fr_question_body(
    row: Dict[str, Any],
    *,
    qid: int,
    on_retry_stt: Optional[Callable[[int], bool]],
) -> None:
    def _retry(idx: int) -> bool:
        if not on_retry_stt:
            return False
        ok = on_retry_stt(idx)
        if ok:
            for k in (
                "mock_v2_new_final_sig",
                "mock_v2_new_final_bundle",
                "mock_v2_new_final_pdf_bytes",
            ):
                st.session_state.pop(k, None)
        return ok

    st.markdown('<div class="m2fr-qrow-body">', unsafe_allow_html=True)
    render_exam_question_feedback_detail(
        row,
        key_prefix=f"m2fr_{qid}",
        on_retry_stt=_retry if on_retry_stt else None,
        show_type_pill=True,
        show_coaching=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_m2fr_question_list(
    results: List[Dict[str, Any]],
    stats: Dict[str, int],
    *,
    on_retry_stt: Optional[Callable[[int], bool]] = None,
) -> None:
    rows = sorted(
        [r for r in results if isinstance(r, dict)],
        key=lambda x: int(x.get("q_id") or 0),
    )
    answered = int(stats.get("completed") or 0)
    no_response = int(stats.get("no_speech") or 0)
    st.markdown(
        f'<section class="m2fr-card m2fr-qlist">{build_m2fr_qlist_header_html(answered=answered, no_response=no_response)}',
        unsafe_allow_html=True,
    )
    show_all = bool(st.session_state.get(_SHOW_ALL_KEY))
    visible = rows if show_all or len(rows) <= 5 else rows[:5]
    for row in visible:
        render_m2fr_question_row(row, on_retry_stt=on_retry_stt)
    if not show_all and len(rows) > 5:
        st.markdown(
            '<div class="m2fr-show-all-marker" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        if st.button(
            f"전체 {len(rows)}문항 보기",
            key="m2fr_show_all_btn",
            use_container_width=True,
        ):
            st.session_state[_SHOW_ALL_KEY] = True
            st.rerun()
    st.markdown("</section>", unsafe_allow_html=True)


def render_m2fr_actions(
    *,
    pdf_bytes: Optional[bytes],
    pdf_ok: bool,
    pdf_name: str,
    on_restart: Optional[Callable[[], None]],
) -> None:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="m2fr-btn-pdf-marker" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        if pdf_ok and pdf_bytes:
            st.download_button(
                "PDF 저장",
                data=pdf_bytes,
                file_name=pdf_name,
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                key="m2fr_pdf_download",
            )
        elif pdf_ok:
            st.caption("PDF 생성에 실패했습니다. 잠시 후 다시 열어 주세요.")
        else:
            st.caption("PDF 생성을 사용할 수 없습니다.")
    with c2:
        st.markdown(
            '<div class="m2fr-btn-restart-marker" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        if st.button(
            "다시 연습하기",
            use_container_width=True,
            key="m2fr_restart",
        ):
            if on_restart:
                on_restart()

