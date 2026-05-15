"""Pattern detail — guided speaking-learning stack (UI redesign step 5).

Layered cards: hero → short example → real OPIc → IH upgrade → tip → practice.
Optional example audio from ``assets/pattern_audio`` when files exist.
"""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import streamlit as st

from config.pattern_roles import normalize_role

_ROOT = Path(__file__).resolve().parent.parent
_PATTERN_AUDIO_DIR = _ROOT / "assets" / "pattern_audio"

# Guided stack uses the first (STACK_HEAD + 1) examples (Steps 1–3: short / real / IH).
STACK_HEAD = 2
# Cap on extra example lines shown per "더보기" expand (beyond the guided stack).
STACK_MAX = 6
# Beyond the stack, how many extra lines to show per "더보기" toggle slice
ADDITIONAL_EXAMPLE_SLICE = 4

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


def _safe_fragment(s: str, max_len: int = 56) -> str:
    x = re.sub(r"[^a-zA-Z0-9가-힣_-]", "_", (s or "").strip())
    return (x[:max_len]) or "x"


def _pattern_line(pat: Dict[str, Any]) -> str:
    return (pat.get("pattern_en") or pat.get("pattern") or "").strip() or "—"


def _meaning_line(pat: Dict[str, Any]) -> str:
    return (pat.get("meaning") or "").strip() or "—"


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


def _learn_card(
    *,
    kind: str,
    eyebrow: str,
    title: str,
    body_html: str,
    extra_class: str = "",
) -> None:
    cls = f"pat-learn-card pat-learn-card--{kind}"
    if extra_class:
        cls += f" {extra_class}"
    eb = html.escape(eyebrow)
    tt = html.escape(title)
    st.markdown(
        f'<section class="{cls}">'
        f'<p class="pat-learn-eyebrow">{eb}</p>'
        f'<h3 class="pat-learn-title">{tt}</h3>'
        f'<div class="pat-learn-body">{body_html}</div>'
        "</section>",
        unsafe_allow_html=True,
    )


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
    """Guided stack: hero → examples → IH → tip → lightweight practice."""
    add_n = (
        additional_example_count
        if additional_example_count is not None
        else ADDITIONAL_EXAMPLE_SLICE
    )
    pid = (pat.get("pattern_id") or "").strip() or f"{tab_id}_{idx}"
    row_key = _safe_fragment(f"{tab_id}_{sec_uid}_{pid}_{idx}")
    expand_key = f"pat_ex_expand_{row_key}"

    tpl = _pattern_line(pat)
    meaning = _meaning_line(pat)
    tpl_h = html.escape(tpl)
    meaning_h = html.escape(meaning)
    usage_inner = _usage_blurb(pat, tab_id)

    # --- 1) Hero ---------------------------------------------------------
    st.markdown(
        f"""
        <article class="pat-detail-hero" aria-label="패턴 히어로">
          <p class="pat-detail-eyebrow">패턴</p>
          <p class="pat-detail-pattern">{tpl_h}</p>
          <p class="pat-detail-meaning">{meaning_h}</p>
          <p class="pat-detail-usage">{usage_inner}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )

    ex_rows = _examples_dicts(pat)
    first_ko = (ex_rows[0].get("ko") or "") if ex_rows else ""

    # --- 2) Short example -------------------------------------------------
    if ex_rows:
        short = ex_rows[0]
        en0 = html.escape(short["en"])
        ko0 = html.escape(short["ko"]) if short.get("ko") else ""
        ko_block = f'<p class="pat-learn-ko">{ko0}</p>' if ko0 else ""
        _learn_card(
            kind="short",
            eyebrow="Step 1",
            title="짧은 예문 · 바로 이해",
            body_html=f'<p class="pat-learn-en">{en0}</p>{ko_block}',
        )
        _try_play_example_audio(short.get("audio_file") or "")

    # --- 3) Real OPIc example --------------------------------------------
    if len(ex_rows) >= 2:
        real = ex_rows[1]
        en1 = html.escape(real["en"])
        ko1 = html.escape(real["ko"]) if real.get("ko") else ""
        ko_block = f'<p class="pat-learn-ko">{ko1}</p>' if ko1 else ""
        _learn_card(
            kind="opic",
            eyebrow="Step 2",
            title="실전 OPIc 예문",
            body_html=f'<p class="pat-learn-en pat-learn-en--long">{en1}</p>{ko_block}',
        )
        _try_play_example_audio(real.get("audio_file") or "")

    # --- 4) IH upgrade ----------------------------------------------------
    if len(ex_rows) >= 3:
        ih = ex_rows[2]
        en2 = html.escape(ih["en"])
        ko2 = html.escape(ih["ko"]) if ih.get("ko") else ""
        ko_block = f'<p class="pat-learn-ko">{ko2}</p>' if ko2 else ""
        _learn_card(
            kind="ih",
            eyebrow="Step 3",
            title="IH 업그레이드 예시",
            body_html=f'<p class="pat-learn-en pat-learn-en--long">{en2}</p>{ko_block}',
        )
        _try_play_example_audio(ih.get("audio_file") or "")
    else:
        body = (
            f'<p class="pat-learn-en">{tpl_h}</p>'
            f'<p class="pat-learn-ih-hint">{_IH_CONNECTOR_HINT}</p>'
        )
        _learn_card(
            kind="ih",
            eyebrow="Step 3",
            title="IH 업그레이드 · 연결어",
            body_html=body,
        )

    # --- 5) Speaking tip --------------------------------------------------
    tip_html = _speaking_tip_body(pat, first_ko)
    _learn_card(
        kind="tip",
        eyebrow="Step 4",
        title="스피킹 팁",
        body_html=f'<p class="pat-learn-tip">{tip_html}</p>',
    )

    # --- 6) Try speaking (lightweight) ------------------------------------
    practice_seed = ex_rows[0]["en"] if ex_rows else tpl
    prompt = (
        f"위 패턴으로 한 문장을 직접 말해 보세요. "
        f"아래에 적어도 되고, 소리 내어 연습해도 좋아요.\n"
        f"예: {practice_seed}"
    )
    st.markdown(
        '<section class="pat-practice-shell" aria-label="직접 말해보기">'
        '<p class="pat-practice-eyebrow">Step 5</p>'
        '<h3 class="pat-practice-title">직접 말해보기</h3>'
        "</section>",
        unsafe_allow_html=True,
    )
    st.caption("마이크 녹음은 아직 가볍게만 — 문장을 적거나 소리 내어 따라 해 보세요.")
    st.text_area(
        "연습 노트",
        value="",
        height=88,
        key=f"pat_practice_{row_key}",
        placeholder=prompt[:220],
        label_visibility="collapsed",
    )

    # --- Extra examples (beyond first 3) ---------------------------------
    if len(ex_rows) <= STACK_HEAD + 1:
        return

    tail = ex_rows[STACK_HEAD + 1 :]
    expanded = bool(st.session_state.get(expand_key))
    btn_label = collapse_label if expanded else expand_more_label
    if st.button(btn_label, key=f"pat_ex_toggle_{row_key}", type="secondary"):
        st.session_state[expand_key] = not expanded
        expanded = bool(st.session_state.get(expand_key))

    if expanded:
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
