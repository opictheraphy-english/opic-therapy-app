"""Mock-exam report — premium coaching presentation (UI step 6).

Purely presentational: reads ``result`` / ``item`` dicts produced by the
existing AI pipeline. No scoring changes, no Gemini calls.
"""

from __future__ import annotations

import html
import re
from typing import Any, Dict, List, Optional

import streamlit as st

from components.collapsible_section import render_collapsible_section

_RUBRIC_LABELS = {
    "fluency": "유창성 · 리듬",
    "lexical": "어휘 다양성",
    "logic": "논리 전개",
    "grammar": "문법 안정감",
}


def _first_sentence(text: str, *, max_len: int = 140) -> str:
    t = (text or "").strip()
    if not t:
        return ""
    cut = re.split(r"(?<=[.!?。])\s+", t, maxsplit=1)[0].strip()
    if len(cut) > max_len:
        return cut[: max_len - 1].rstrip() + "…"
    return cut


def coaching_headline_subtitle(
    result: Dict[str, Any],
    transcript: str = "",
) -> tuple[str, str]:
    """Varied coach summary (title + 2–3 sentences)."""
    from utils.coaching_feedback import (
        build_coach_headline,
        merge_alt_hits,
        merge_grammar_hits,
    )

    t = (transcript or result.get("transcript") or "").strip()
    g = merge_grammar_hits(t, result)
    a = merge_alt_hits(t, result)
    if t or result:
        return build_coach_headline(result, t, g, a)

    summary = (result.get("summary_speech_rehab") or "").strip()
    if summary:
        return "답변을 들었어요", _first_sentence(summary, max_len=200)
    return "답변 잘 들었어요", "아래에서 문법·표현·구조를 정리했어요."


def collect_strong_points(result: Dict[str, Any]) -> List[str]:
    """Short encouraging bullets (rule-based from existing scores)."""
    out: List[str] = []
    rs = result.get("rubric_scores") or {}
    if isinstance(rs, dict):
        for key, label in _RUBRIC_LABELS.items():
            raw = rs.get(key)
            try:
                v = float(raw)
            except (TypeError, ValueError):
                continue
            if v >= 78:
                out.append(f"{label} 쪽에서 균형이 좋았어요.")
            elif v >= 68:
                out.append(f"{label}에서 괜찮은 기반이 보였어요.")

    wpm = result.get("wpm")
    try:
        w = float(wpm) if wpm is not None else 0.0
    except (TypeError, ValueError):
        w = 0.0
    if 80 <= w <= 170:
        out.append("전체적으로 듣기 편한 속도였어요.")

    try:
        wc = int(result.get("word_count") or 0)
    except (TypeError, ValueError):
        wc = 0
    if wc >= 75:
        out.append("발화량이 충분해서 이야기가 잘 펼쳐졌어요.")

    fs = result.get("fact_scores") or {}
    if isinstance(fs, dict):
        try:
            tt = float(fs.get("text_type", 0))
        except (TypeError, ValueError):
            tt = 0.0
        if tt >= 72:
            out.append("문장을 묶어 말하려는 시도가 보였어요.")

    if not out:
        out.append("질문 주제에 맞게 답을 시작했어요.")
        out.append("다음엔 이유나 예시를 한 문장만 더 붙여 보세요.")
    return out[:5]


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[: n - 1].rstrip() + "…"


def native_upgrade_html(result: Dict[str, Any]) -> str:
    """Aspirational 'native-style' snippet from existing AI text fields."""
    sem = (result.get("semantic_feedback") or "").strip()
    rx = (result.get("prescription") or "").strip()
    body = ""
    if sem:
        body = html.escape(_truncate(sem, 420))
    elif rx:
        body = html.escape(_truncate(rx, 420))
    else:
        body = "한 문장 더 덧붙여 ‘왜 그랬는지’를 살짝만 설명하면 원어민 톤에 더 가까워져요."
    return body


def flow_coaching_bodies(result: Dict[str, Any]) -> List[tuple[str, str]]:
    """(title, body) pairs for flow / delivery coaching."""
    pairs: List[tuple[str, str]] = []
    tense = (result.get("tense_appropriateness_feedback") or result.get("breakdown") or "").strip()
    if tense:
        pairs.append(("말의 흐름 · 시제", _truncate(tense, 380)))

    acting = (result.get("acting_feedback") or "").strip()
    wpm = result.get("wpm")
    wc = result.get("word_count", 0)
    try:
        w = float(wpm) if wpm is not None else 0.0
    except (TypeError, ValueError):
        w = 0.0
    try:
        words = int(wc)
    except (TypeError, ValueError):
        words = 0
    if not acting and isinstance(wpm, (int, float)) and w >= 200 and words < 120:
        acting = (
            "속도는 빠른 편이에요. 숨을 한 번 넣고 강조할 단어만 살짝 늘리면 "
            "암기 톤이 줄어들어요."
        )
    if acting:
        pairs.append(("호흡 · 전달감", _truncate(acting, 320)))

    if not pairs:
        pairs.append(
            (
                "리듬 팁",
                "문장 끝을 너무 올리지 말고, 두 번째 문장부터는 살짝 내려 말하면 차분하게 들려요.",
            )
        )
    return pairs


def render_overall_coaching_hero(
    result: Dict[str, Any],
    qid: int,
    transcript: str = "",
) -> None:
    title, sub = coaching_headline_subtitle(result, transcript)
    st.markdown(
        f"""
        <section class="mx-coach-hero" aria-label="코치 총평">
          <p class="mx-coach-eyebrow">Q{qid} · 코치 총평</p>
          <h2 class="mx-coach-hero-title">{html.escape(title)}</h2>
          <p class="mx-coach-hero-sub">{html.escape(sub)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_coach_section_header(eyebrow: str, title: str) -> None:
    from utils.streamlit_ui import clean_visible_label

    safe_eyebrow = clean_visible_label(eyebrow, "코칭")
    safe_title = clean_visible_label(title, "피드백")
    st.markdown(
        f"""
        <section class="mx-coach-section" aria-label="{html.escape(safe_eyebrow)}">
          <p class="mx-coach-sec-eyebrow">{html.escape(safe_eyebrow)}</p>
          <h3 class="mx-coach-sec-title">{html.escape(safe_title)}</h3>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_structure_section(transcript: str) -> None:
    from utils.coaching_feedback import build_structure_feedback

    struct = build_structure_feedback(transcript)
    good_li = "".join(f"<li>{html.escape(x)}</li>" for x in struct.get("good", []))
    miss_li = "".join(f"<li>{html.escape(x)}</li>" for x in struct.get("missing", []))
    next_li = "".join(f"<li>{html.escape(x)}</li>" for x in struct.get("next", []))
    _render_coach_section_header("답변 구조", "내용 전개를 이렇게 보면 좋아요")
    st.markdown(
        f"""
        <div class="mx-coach-struct">
          <p class="mx-coach-struct-label">Good</p>
          <ul class="mx-coach-struct-list">{good_li or "<li>핵심 주제로 답을 시작했어요</li>"}</ul>
          <p class="mx-coach-struct-label">Missing</p>
          <ul class="mx-coach-struct-list mx-coach-struct-miss">{miss_li or "<li>구체적인 이유·예시를 한 문장 더</li>"}</ul>
          <p class="mx-coach-struct-label">Next</p>
          <ul class="mx-coach-struct-list">{next_li}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_improved_example_section(
    transcript: str,
    grammar_hits: List[Dict[str, str]],
    alt_hits: List[Dict[str, Any]],
) -> None:
    from utils.coaching_feedback import build_improved_answer_example

    example = build_improved_answer_example(transcript, grammar_hits, alt_hits)
    _render_coach_section_header("자연스러운 답변 예시", "이렇게 다시 말해볼 수 있어요")
    st.markdown(
        f'<div class="mx-coach-example-body">{html.escape(example)}</div>',
        unsafe_allow_html=True,
    )


def _render_mission_section(
    transcript: str,
    grammar_hits: List[Dict[str, str]],
    alt_hits: List[Dict[str, Any]],
) -> None:
    from utils.coaching_feedback import build_next_missions

    missions = build_next_missions(transcript, grammar_hits, alt_hits)
    items = "".join(
        f'<li class="mx-coach-mission-item">{html.escape(m)}</li>' for m in missions
    )
    _render_coach_section_header("다음 답변 미션", "바로 다음 연습에 써 보세요")
    st.markdown(
        f'<ol class="mx-coach-mission-list">{items}</ol>',
        unsafe_allow_html=True,
    )


def render_structured_coaching_report(
    result: Dict[str, Any],
    transcript: str,
    qid: int,
    *,
    show_hero: bool = True,
) -> None:
    """Sections A–G from existing analysis + local post-processing (no LLM)."""
    from components.smart_feedback import (
        render_alternative_expressions,
        render_grammar_corrections,
    )
    from utils.coaching_feedback import (
        grammar_empty_message,
        merge_alt_hits,
        merge_grammar_hits,
    )

    t = (transcript or "").strip()
    g_hits = merge_grammar_hits(t, result)
    a_hits = merge_alt_hits(t, result)

    if show_hero:
        render_overall_coaching_hero(result, qid, t)

    _render_coach_section_header("문법 교정", "바로 고치면 좋은 표현")
    render_grammar_corrections(
        t,
        title="",
        show_heading=False,
        hits=g_hits,
        empty_message=grammar_empty_message(a_hits),
    )

    _render_coach_section_header("표현 업그레이드", "한 단계 더 자연스럽게")
    alt_empty = (
        "눈에 띄는 평이한 표현은 적었어요. 다음엔 구체적인 형용사를 한 번 더 써 보세요."
        if not a_hits
        else None
    )
    render_alternative_expressions(
        t,
        title="",
        show_heading=False,
        hits=a_hits,
        empty_message=alt_empty,
    )

    _render_structure_section(t)
    _render_improved_example_section(t, g_hits, a_hits)
    render_pronunciation_section(result)
    _render_mission_section(t, g_hits, a_hits)

    _sum = (result.get("summary_speech_rehab") or "").strip()
    _sem = (result.get("semantic_feedback") or "").strip()
    long_ai = _sum if len(_sum) > 160 else ""
    if not long_ai and len(_sem) > 200:
        long_ai = _sem
    if long_ai:

        def _ai_full_summary_body() -> None:
            st.write(long_ai)

        render_collapsible_section(
            "AI 총평 전문 보기",
            f"coach_ai_full_q{int(qid)}",
            _ai_full_summary_body,
            toggle_open_label="펼치기",
            toggle_close_label="접기",
            css_scope="mx-col",
        )


def render_strong_points_cards(result: Dict[str, Any]) -> None:
    pts = collect_strong_points(result)
    if not pts:
        return
    chips = "".join(
        f'<div class="mx-coach-chip"><span class="mx-coach-chip-ico">✓</span>'
        f'<span class="mx-coach-chip-txt">{html.escape(p)}</span></div>'
        for p in pts
    )
    st.markdown(
        f"""
        <section class="mx-coach-section" aria-label="잘한 점">
          <p class="mx-coach-sec-eyebrow">잘한 점</p>
          <h3 class="mx-coach-sec-title">계속 가져가면 좋은 강점이에요</h3>
          <div class="mx-coach-chip-row">{chips}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_native_upgrade_section(result: Dict[str, Any]) -> None:
    body = native_upgrade_html(result)
    st.markdown(
        """
        <section class="mx-coach-section mx-coach-native" aria-label="원어민 업그레이드">
          <p class="mx-coach-sec-eyebrow">원어민 업그레이드</p>
          <h3 class="mx-coach-sec-title">이렇게 말하면 더 자연스러워요</h3>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="mx-coach-native-body">{body}</div>',
        unsafe_allow_html=True,
    )


def render_pronunciation_section(result: Dict[str, Any]) -> None:
    """Lightweight 발음·강세 전달력 section using pronunciation_scores."""
    pron = result.get("pronunciation_scores")
    sem = result.get("semantic_dimensions") or {}
    # Fall back to semantic_dimensions when pronunciation_scores absent (old results)
    if not isinstance(pron, dict) or not pron:
        pron = {k: sem.get(k) for k in ("pronunciation_clarity", "intonation_control", "stress_rhythm", "linking_naturalness")}
        pron = {k: v for k, v in pron.items() if v is not None}
    if not pron:
        return

    from utils.coaching_feedback import pronunciation_comment

    feedback = pronunciation_comment(result)

    labels = {
        "pronunciation_clarity": "발음 명확도",
        "intonation_control": "억양 조절",
        "stress_rhythm": "강세·리듬",
        "linking_naturalness": "연음 자연스러움",
    }

    chips = []
    for k, lab in labels.items():
        v = pron.get(k)
        if v is None:
            continue
        try:
            score = float(v)
        except (TypeError, ValueError):
            continue
        color = "#0f766e" if score >= 70 else ("#b45309" if score >= 45 else "#b91c1c")
        chips.append(
            f'<div class="mx-coach-pron-chip">'
            f'<span class="mx-coach-pron-label">{html.escape(lab)}</span>'
            f'<span class="mx-coach-pron-score" style="color:{color};">{round(score)}</span>'
            f"</div>"
        )

    if not chips:
        return

    st.markdown(
        f"""
        <section class="mx-coach-section" aria-label="발음 강세">
          <p class="mx-coach-sec-eyebrow">발음·강세 전달력</p>
          <h3 class="mx-coach-sec-title">청자에게 얼마나 잘 전달됐나요</h3>
          <div class="mx-coach-pron-grid">{"".join(chips)}</div>
          <p class="mx-coach-pron-feedback">{html.escape(feedback)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def render_flow_coaching_section(result: Dict[str, Any]) -> None:
    pairs = flow_coaching_bodies(result)
    cards = []
    for tit, body in pairs:
        cards.append(
            f'<div class="mx-coach-flow-card">'
            f'<p class="mx-coach-flow-title">{html.escape(tit)}</p>'
            f'<p class="mx-coach-flow-body">{html.escape(body)}</p>'
            f"</div>"
        )
    st.markdown(
        """
        <section class="mx-coach-section" aria-label="말하기 흐름">
          <p class="mx-coach-sec-eyebrow">말하기 흐름</p>
          <h3 class="mx-coach-sec-title">호흡과 이야기 전개</h3>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f'<div class="mx-coach-flow-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_coaching_retry_banner(*, has_next: bool) -> None:
    """Friendly retry / practice spirit (copy only — no new navigation)."""
    if has_next:
        msg = (
            "방금 배운 표현을 입에 붙여 보고 싶다면, 다음 문항에서 바로 써먹어 보세요. "
            "한 번 더 연습하는 느낌으로 가볍게 이어가도 좋아요."
        )
    else:
        msg = (
            "마음에 남는 한 가지만 골라, 다음 세션에서 다시 말해 보세요. "
            "완벽하지 않아도 괜찮아요 — 조금씩 자연스러워져요."
        )
    st.markdown(
        f'<div class="mx-coach-retry-banner">{html.escape(msg)}</div>',
        unsafe_allow_html=True,
    )


def render_coaching_cta_preamble(*, has_next: bool) -> None:
    if has_next:
        msg = "준비되면 다음 단계로 가볼까요? 방금 팁을 한 문장만 떠올려도 좋아요."
    else:
        msg = "오늘 연습 여기까지도 충분해요. 천천히 소화한 뒤 다시 도전해 보세요."
    st.markdown(
        f'<div class="mx-coach-cta-preamble">{html.escape(msg)}</div>',
        unsafe_allow_html=True,
    )


def compact_score_strip_html(result: Dict[str, Any]) -> str:
    """One-line visual summary for history expanders (no new scoring)."""
    level = html.escape(str(result.get("estimated_level_display") or result.get("estimated_level") or "—"))
    rs = result.get("rubric_scores") or {}
    if not isinstance(rs, dict):
        return f'<div class="mx-coach-mini-scores"><span>등급 {level}</span></div>'
    bits = []
    for k, lab in (("fluency", "Fluency"), ("grammar", "Grammar")):
        v = rs.get(k)
        if v is not None:
            bits.append(f"{lab} {html.escape(str(v))}")
    inner = " · ".join(bits) if bits else ""
    rest = (
        f'<span class="mx-coach-mini-rest">{inner}</span>'
        if inner
        else ""
    )
    return (
        f'<div class="mx-coach-mini-scores">'
        f'<span class="mx-coach-mini-pill">등급 {level}</span>'
        f"{rest}"
        f"</div>"
    )


def render_history_expander_coaching(item: Dict[str, Any]) -> None:
    """Per-question expander: compact coaching without the top overall hero."""
    from utils.text_utils import NO_SPEECH_EMPTY_TEXT, is_real_speech_transcript

    result = item.get("result") or {}
    qid = item.get("q_id")
    transcript = (result.get("transcript") or "").strip()
    no_speech_flag = bool(result.get("no_speech_detected")) or (
        result.get("diagnosis_status") == "no_speech"
    )
    transcript_is_real = (
        bool(transcript)
        and not no_speech_flag
        and is_real_speech_transcript(transcript)
    )

    st.markdown(compact_score_strip_html(result), unsafe_allow_html=True)

    if result.get("diagnosis_status") == "analysis_pending":
        st.info(
            (
                (result.get("summary_speech_rehab") or "").strip()
                + " "
                + (result.get("prescription") or "").strip()
            ).strip()
            or "이 문항은 AI 분석이 완료되지 않았습니다. 시험은 계속 진행할 수 있어요."
        )
        return

    if result.get("diagnosis_status") == "ok" and transcript_is_real:
        st.text_area(
            f"Q{qid} 복원 텍스트",
            value=transcript,
            height=100,
            key=f"transcript_{qid}",
        )
        render_structured_coaching_report(result, transcript, int(qid or 0), show_hero=True)
    elif transcript_is_real:
        st.text_area(
            f"Q{qid} 복원 텍스트",
            value=transcript,
            height=100,
            key=f"transcript_{qid}",
        )
        render_structured_coaching_report(result, transcript, int(qid or 0), show_hero=True)
    else:
        st.markdown(
            f'<div class="mx-status mx-status--warn">'
            f'<span class="mx-status-icon">🎤</span>'
            f'<span>{html.escape(NO_SPEECH_EMPTY_TEXT)}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )


def render_grammar_and_expression_coaching(
    transcript: str,
    result: Optional[Dict[str, Any]] = None,
    qid: int = 0,
) -> Dict[str, int]:
    """Backward-compatible wrapper — prefer render_structured_coaching_report."""
    render_structured_coaching_report(result or {}, transcript, qid, show_hero=False)
    from utils.coaching_feedback import merge_alt_hits, merge_grammar_hits

    g = len(merge_grammar_hits(transcript, result))
    a = len(merge_alt_hits(transcript, result))
    return {"grammar": g, "alternatives": a}


__all__ = [
    "render_pronunciation_section",
    "collect_strong_points",
    "compact_score_strip_html",
    "coaching_headline_subtitle",
    "flow_coaching_bodies",
    "native_upgrade_html",
    "render_coaching_retry_banner",
    "render_coaching_cta_preamble",
    "render_flow_coaching_section",
    "render_grammar_and_expression_coaching",
    "render_history_expander_coaching",
    "render_native_upgrade_section",
    "render_overall_coaching_hero",
    "render_strong_points_cards",
    "render_structured_coaching_report",
]
