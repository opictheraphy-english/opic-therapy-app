"""Pattern drill cards — phase-1 compact UI.

Collapsed: single tappable row (``.pat-row``). Expanded: merged 예문 block, inline tip,
optional practice note (collapsed by default). No duplicate hero or Step 1–5 card stack.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from config.pattern_roles import normalize_role
from utils.streamlit_ui import ascii_widget_key, is_leaked_internal_label

_ROOT = Path(__file__).resolve().parent.parent
_PATTERN_AUDIO_DIR = _ROOT / "assets" / "pattern_audio"

# Guided stack uses the first (STACK_HEAD + 1) examples (Steps 1–3: short / real / IH).
STACK_HEAD = 2
# Cap on extra example lines shown per "더보기" expand (beyond the guided stack).
STACK_MAX = 6
# Beyond the stack, how many extra lines to show per "더보기" toggle slice
ADDITIONAL_EXAMPLE_SLICE = 2

_TAB_LABEL_KO: Dict[str, str] = {
    "describe": "묘사",
    "routine": "루틴",
    "experience": "경험",
    "comparison": "비교",
    "opinion": "의견",
    "roleplay": "롤플레이",
}

_ROLE_USAGE: Dict[str, str] = {
    "starter": "답변 첫머리에서 주제와 분위기를 잡을 때 가장 잘 맞습니다.",
    "detail": "그림·상황·사실을 구체적으로 채울 때 씁니다.",
    "atmosphere": "장면의 분위기·느낌을 살릴 때 씁니다.",
    "emotion": "감정의 변화나 이유를 설명할 때 씁니다.",
    "comparison": "둘 이상을 비교하거나 대조할 때 씁니다.",
    "transition": "앞 내용과 뒤 경험을 자연스럽게 잇습니다.",
    "closing": "답변을 정리하거나 마무리할 때 씁니다.",
    "opinion": "생각·입장을 분명히 밝힐 때 씁니다.",
}

_IH_CONNECTOR_HINT = (
    "IH 이상에서는 <b>First of all</b>, <b>What happened next was</b>, "
    "<b>Looking back</b> 같은 연결어로 문장을 묶어 길게 가져가 보세요."
)


def _pattern_line(pat: Dict[str, Any]) -> str:
    for field in ("pattern_en", "pattern", "template", "title"):
        raw = (pat.get(field) or "").strip()
        if raw and not is_leaked_internal_label(raw):
            return raw
    return "패턴 문장 없음"


def _meaning_line(pat: Dict[str, Any]) -> str:
    for field in ("meaning", "meaning_ko", "ko", "label_ko"):
        raw = (pat.get(field) or "").strip()
        if raw and not is_leaked_internal_label(raw):
            return raw
    return "의미 없음"


def _examples_dicts(pat: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = pat.get("examples") if isinstance(pat.get("examples"), list) else []
    out: List[Dict[str, Any]] = []
    for x in raw:
        if not isinstance(x, dict):
            continue
        en = (x.get("en") or "").strip()
        if not en:
            continue
        out.append(
            {
                "en": en,
                "ko": (x.get("ko") or "").strip(),
                "audio_file": (x.get("audio_file") or "").strip(),
            }
        )
    if not out:
        ex1 = (pat.get("example_en") or "").strip()
        if ex1:
            out.append(
                {
                    "en": ex1,
                    "ko": (pat.get("example_ko") or "").strip(),
                    "audio_file": "",
                }
            )
    return out


def _usage_blurb(pat: Dict[str, Any], tab_id: str) -> str:
    role = normalize_role(pat.get("pattern_role")) or ""
    base = _ROLE_USAGE.get(role, "자연스러운 영어 답변을 이어 가는 데 쓰입니다.")
    tab_ko = _TAB_LABEL_KO.get(tab_id, tab_id)
    sub = (pat.get("subcategory") or "").strip().replace("_", " ")
    if sub:
        return f"{base} · <span class=\"pat-usage-meta\">{html.escape(tab_ko)} · {html.escape(sub)}</span>"
    return f"{base} · <span class=\"pat-usage-meta\">{html.escape(tab_ko)}</span>"


def _speaking_tip_body(pat: Dict[str, Any], first_ko: str) -> str:
    tags = pat.get("tags") if isinstance(pat.get("tags"), list) else []
    tag_bits = [html.escape(str(t).strip()) for t in tags if str(t).strip()]
    parts: List[str] = []
    if tag_bits:
        parts.append("태그: " + ", ".join(tag_bits[:5]) + ".")
    parts.append(
        "문장 끝을 살짝 내려 말하면 차분하게 들리고, "
        "같은 두 단어를 연속으로 세게 쓰지 않도록 리듬을 나눠 보세요."
    )
    if first_ko:
        parts.append("뉘앙스(한국어): " + html.escape(first_ko))
    return " ".join(parts)


def _try_play_example_audio(filename: str) -> None:
    fn = (filename or "").strip()
    if not fn:
        return
    p = _PATTERN_AUDIO_DIR / fn
    if not p.is_file():
        return
    try:
        st.audio(p.read_bytes(), format="audio/mp3")
    except Exception:
        return


_EXAMPLE_LABELS = ("짧은 예문", "실전 OPIc", "IH 업그레이드")

_PAT_CHEVRON_SVG = (
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">'
    '<polyline points="9 6 15 12 9 18"></polyline></svg>'
)


def pat_chevron_markup() -> str:
    """Small right chevron (one per row/section — no duplicate Streamlit arrow)."""
    return f'<span class="pat-chevron" aria-hidden="true">{_PAT_CHEVRON_SVG}</span>'


def _pat_row_html(*, tpl_h: str, meaning_h: str, open: bool) -> str:
    open_cls = " pat-row--open" if open else ""
    return (
        f'<div class="pat-row{open_cls}" aria-expanded="{"true" if open else "false"}">'
        f'<div class="pat-row-body">'
        f'<div class="pat-en">{tpl_h}</div>'
        f'<div class="pat-ko">{meaning_h}</div>'
        "</div>"
        f"{pat_chevron_markup()}"
        "</div>"
    )


def _render_merged_examples(ex_rows: List[Dict[str, Any]], tpl_h: str) -> None:
    """Steps 1–3 in one card."""
    lines: List[str] = []
    for i, label in enumerate(_EXAMPLE_LABELS):
        if i < len(ex_rows):
            row = ex_rows[i]
            en = html.escape(row["en"])
            ko = html.escape(row["ko"]) if row.get("ko") else ""
            ko_block = f'<p class="pat-ex-line-ko">{ko}</p>' if ko else ""
            lines.append(
                f'<div class="pat-ex-line">'
                f'<span class="pat-ex-line-label">{html.escape(label)}</span>'
                f'<p class="pat-ex-line-en">{en}</p>{ko_block}'
                f"</div>"
            )
        elif i == 2:
            lines.append(
                f'<div class="pat-ex-line pat-ex-line--hint">'
                f'<span class="pat-ex-line-label">{html.escape(label)}</span>'
                f'<p class="pat-ex-line-en">{tpl_h}</p>'
                f'<p class="pat-learn-ih-hint">{_IH_CONNECTOR_HINT}</p>'
                f"</div>"
            )
    if not lines:
        return
    st.markdown(
        '<section class="pat-detail-block" aria-label="예문">'
        '<p class="pat-detail-block-title">예문</p>'
        f'{"".join(lines)}'
        "</section>",
        unsafe_allow_html=True,
    )
    for i, row in enumerate(ex_rows[:3]):
        _try_play_example_audio(row.get("audio_file") or "")


def render_compact_pattern_card(
    pat: Dict[str, Any],
    *,
    tab_id: str,
    sec_uid: str,
    idx: int,
    expand_more_label: str = "나머지 예문 더보기",
    collapse_label: str = "접기",
    additional_example_count: int | None = None,
) -> None:
    """Tappable row; expanded body is one 예문 block + tip + optional practice."""
    add_n = (
        additional_example_count
        if additional_example_count is not None
        else ADDITIONAL_EXAMPLE_SLICE
    )
    pid = (pat.get("pattern_id") or "").strip() or f"p{idx}"
    row_key = ascii_widget_key("pat", tab_id, sec_uid, pid, idx)
    expand_key = f"pat_ex_expand_{row_key}"
    practice_key = f"pat_practice_open_{row_key}"

    tpl = _pattern_line(pat)
    meaning = _meaning_line(pat)
    tpl_h = html.escape(tpl)
    meaning_h = html.escape(meaning)
    usage_inner = _usage_blurb(pat, tab_id)

    st.session_state.setdefault("open_pattern_key", None)
    this_open_key = row_key
    detail_open = st.session_state.get("open_pattern_key") == this_open_key

    st.markdown(
        f'<div class="pat-row-stack">{_pat_row_html(tpl_h=tpl_h, meaning_h=meaning_h, open=detail_open)}</div>',
        unsafe_allow_html=True,
    )
    if st.button(
        " ",
        key=f"pat_row_toggle_{row_key}",
        use_container_width=True,
        help="패턴 펼치기/접기",
        label_visibility="collapsed",
    ):
        if detail_open:
            st.session_state["open_pattern_key"] = None
            st.session_state.pop(expand_key, None)
            st.session_state.pop(practice_key, None)
        else:
            st.session_state["open_pattern_key"] = this_open_key
        st.rerun()

    if not detail_open:
        return

    st.markdown(
        f'<div class="pat-detail-panel" aria-label="패턴 상세">'
        f'<p class="pat-detail-usage">{usage_inner}</p>',
        unsafe_allow_html=True,
    )

    ex_rows = _examples_dicts(pat)
    first_ko = (ex_rows[0].get("ko") or "") if ex_rows else ""
    _render_merged_examples(ex_rows, tpl_h)

    tip_html = _speaking_tip_body(pat, first_ko)
    st.markdown(
        f'<p class="pat-detail-tip"><span class="pat-detail-tip-label">스피킹 팁</span> {tip_html}</p>',
        unsafe_allow_html=True,
    )

    practice_seed = ex_rows[0]["en"] if ex_rows else tpl
    prompt = f"위 패턴으로 한 문장을 직접 말해 보세요. 예: {practice_seed}"
    if not st.session_state.get(practice_key):
        if st.button(
            "연습 노트 열기",
            key=f"pat_practice_open_{row_key}",
            type="secondary",
            use_container_width=True,
        ):
            st.session_state[practice_key] = True
            st.rerun()
    else:
        st.text_area(
            "연습 노트",
            value="",
            height=72,
            key=f"pat_practice_{row_key}",
            placeholder=prompt[:220],
            label_visibility="collapsed",
        )

    show_tail = len(ex_rows) > STACK_HEAD + 1
    if show_tail:
        tail = ex_rows[STACK_HEAD + 1 :]
        tail_open = bool(st.session_state.get(expand_key))
        btn_label = collapse_label if tail_open else expand_more_label
        if st.button(btn_label, key=f"pat_ex_toggle_{row_key}", type="secondary"):
            st.session_state[expand_key] = not tail_open
            tail_open = bool(st.session_state.get(expand_key))

        if tail_open:
            slice_n = min(add_n, len(tail), STACK_MAX)
            for j, row in enumerate(tail[:slice_n]):
                en = html.escape(row["en"])
                st.markdown(
                    f'<div class="pat-ex-wrap pat-ex-wrap--extra pat-ex-wrap--tail">'
                    f'<span class="pat-ex-label">추가 예문 {j + 1}</span>'
                    f'<ul><li>{en}</li></ul>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                _try_play_example_audio(row.get("audio_file") or "")

    st.markdown("</div>", unsafe_allow_html=True)
