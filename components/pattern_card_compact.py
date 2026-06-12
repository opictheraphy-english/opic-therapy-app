"""Pattern drill cards — tap header column + detail body outside column."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st

from config.pattern_roles import normalize_role
from utils.streamlit_ui import ascii_widget_key, is_leaked_internal_label

_ROOT = Path(__file__).resolve().parent.parent
_PATTERN_AUDIO_DIR = _ROOT / "assets" / "pattern_audio"

STACK_HEAD = 2
STACK_MAX = 6
ADDITIONAL_EXAMPLE_SLICE = 2

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


def _usage_role_only(pat: Dict[str, Any]) -> str:
    role = normalize_role(pat.get("pattern_role")) or ""
    return _ROLE_USAGE.get(role, "자연스러운 영어 답변을 이어 가는 데 쓰입니다.")


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


def _divider_html() -> str:
    return '<hr class="pat-divider" aria-hidden="true">'


def _example_block_html(
    *,
    label: str,
    en: str,
    ko: str = "",
    en_weight: str = "500",
    label_class: str = "pat-ex-label",
) -> str:
    ko_block = f'<p class="pat-ex-ko">{html.escape(ko)}</p>' if ko else ""
    return (
        f'<div class="pat-ex-block">'
        f'<p class="{label_class}">{html.escape(label)}</p>'
        f'<p class="pat-ex-en pat-ex-en--{en_weight}">{html.escape(en)}</p>'
        f"{ko_block}"
        f"</div>"
    )


def _header_card_html(*, tpl_h: str, meaning_h: str, is_open: bool) -> str:
    chevron = "▴" if is_open else "▾"
    open_cls = " pat-card--header-open" if is_open else ""
    return (
        f'<article class="pat-card pat-card--header{open_cls}" aria-label="패턴 카드">'
        f'<div class="pat-card-main">'
        f'<p class="pat-card-en">{tpl_h}</p>'
        f'<p class="pat-card-ko">{meaning_h}</p>'
        f"</div>"
        f'<span class="pat-card-chevron" aria-hidden="true">{chevron}</span>'
        f"</article>"
    )


def _detail_body_html(
    *,
    tpl_h: str,
    meaning_h: str,
    usage_h: str,
    ex_rows: List[Dict[str, Any]],
    tail_rows: List[Dict[str, Any]],
) -> str:
    parts: List[str] = [
        '<div class="pat-card-detail">',
        '<p class="pat-pattern-label">패턴</p>',
        f'<p class="pat-pattern-en">{tpl_h}</p>',
        f'<p class="pat-pattern-meaning">{meaning_h}</p>',
        f'<p class="pat-pattern-usage">{usage_h}</p>',
    ]

    if ex_rows:
        parts.append(_divider_html())
        short = ex_rows[0]
        parts.append(
            _example_block_html(
                label="짧은 예문",
                en=short["en"],
                ko=short.get("ko") or "",
                en_weight="500",
            )
        )

    if len(ex_rows) >= 2:
        parts.append(_divider_html())
        real = ex_rows[1]
        parts.append(
            _example_block_html(
                label="실전 OPIc 예문",
                en=real["en"],
                ko=real.get("ko") or "",
                en_weight="400",
            )
        )

    parts.append(_divider_html())
    if len(ex_rows) >= 3:
        ih = ex_rows[2]
        parts.append(
            _example_block_html(
                label="IH 업그레이드",
                en=ih["en"],
                ko=ih.get("ko") or "",
                en_weight="400",
                label_class="pat-ex-label pat-ex-label--purple",
            )
        )
    else:
        parts.append(
            '<div class="pat-ex-block">'
            '<p class="pat-ex-label pat-ex-label--purple">IH 업그레이드</p>'
            f'<p class="pat-ex-en pat-ex-en--400">{_IH_CONNECTOR_HINT}</p>'
            "</div>"
        )

    first_ko = (ex_rows[0].get("ko") or "").strip() if ex_rows else ""
    if first_ko:
        parts.append(f'<div class="pat-nuance">{html.escape(first_ko)}</div>')

    for row in tail_rows:
        parts.append(_divider_html())
        parts.append(
            _example_block_html(
                label="추가 예문",
                en=row["en"],
                ko=row.get("ko") or "",
                en_weight="400",
            )
        )

    parts.append("</div>")
    return "".join(parts)


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
    add_n = (
        additional_example_count
        if additional_example_count is not None
        else ADDITIONAL_EXAMPLE_SLICE
    )
    pid = (pat.get("pattern_id") or "").strip() or f"p{idx}"
    row_key = ascii_widget_key("pat", tab_id, sec_uid, pid, idx)
    expand_key = f"pat_ex_expand_{row_key}"

    tpl = _pattern_line(pat)
    meaning = _meaning_line(pat)
    tpl_h = html.escape(tpl)
    meaning_h = html.escape(meaning)
    usage_h = html.escape(_usage_role_only(pat))

    st.session_state.setdefault("open_pattern_key", None)
    this_open_key = row_key
    detail_open = st.session_state.get("open_pattern_key") == this_open_key

    ex_rows = _examples_dicts(pat)
    tail_all = ex_rows[STACK_HEAD + 1 :] if len(ex_rows) > STACK_HEAD + 1 else []
    tail_open = bool(st.session_state.get(expand_key))
    tail_visible = tail_all[: min(add_n, len(tail_all), STACK_MAX)] if tail_open else []

    # Overlay column: header markdown + exactly one transparent toggle button.
    col, = st.columns(1)
    with col:
        header_html = _header_card_html(tpl_h=tpl_h, meaning_h=meaning_h, is_open=detail_open)
        st.markdown(
            f'<div class="pat-card-shell pat-card-shell--tap">{header_html}</div>',
            unsafe_allow_html=True,
        )
        if st.button(
            " ",
            key=f"pat_card_toggle_{row_key}",
            use_container_width=True,
        ):
            if detail_open:
                st.session_state["open_pattern_key"] = None
                st.session_state.pop(expand_key, None)
            else:
                st.session_state["open_pattern_key"] = this_open_key
            st.rerun()

    # Detail body and action buttons render outside the overlay column.
    if not detail_open:
        return

    st.markdown(
        f'<div class="pat-card-detail-wrap">{_detail_body_html(tpl_h=tpl_h, meaning_h=meaning_h, usage_h=usage_h, ex_rows=ex_rows, tail_rows=tail_visible)}</div>',
        unsafe_allow_html=True,
    )

    if ex_rows:
        _try_play_example_audio(ex_rows[0].get("audio_file") or "")
    if len(ex_rows) >= 2:
        _try_play_example_audio(ex_rows[1].get("audio_file") or "")
    if len(ex_rows) >= 3:
        _try_play_example_audio(ex_rows[2].get("audio_file") or "")
    for row in tail_visible:
        _try_play_example_audio(row.get("audio_file") or "")

    btn_cols = st.columns(2 if tail_all else 1)
    col_i = 0
    if tail_all:
        with btn_cols[col_i]:
            more_label = "예문 접기" if tail_open else f"예문 {len(tail_all)}개 더보기"
            if st.button(
                more_label,
                key=f"pat_ex_toggle_{row_key}",
                use_container_width=True,
            ):
                st.session_state[expand_key] = not tail_open
                st.rerun()
        col_i += 1
    with btn_cols[col_i]:
        if st.button(
            collapse_label,
            key=f"pat_detail_close_{row_key}",
            use_container_width=True,
        ):
            st.session_state["open_pattern_key"] = None
            st.session_state.pop(expand_key, None)
            st.rerun()
