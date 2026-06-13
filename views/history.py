"""학습 기록 보기 — 로그인 사용자의 모의고사·주제별·스크립트 첨삭 결과.

Stage 4: 목록 + 상세 뷰 + 진입점. 데이터는 ``services.history_store`` 가 Supabase
PostgREST 에서 가져온다(본인 행만, RLS). 비로그인은 로그인 안내만 보여준다.
"""

from __future__ import annotations

import html
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

from components.navigation import navigate_to
from components.topbar import render_top_bar
from components.brand_character import render_character_svg
from services.history_store import get_history_record, list_history
from utils.auth import is_authenticated

_KEY_SELECTED = "history_selected_id"
_KEY_FILTER = "history_filter"

_KST = timezone(timedelta(hours=9))

_SCORE_AXES = (
    ("fluency", "유창성"),
    ("delivery", "전달력"),
    ("grammar", "문법"),
    ("vocabulary", "어휘"),
    ("coherence", "일관성"),
    ("response_amount", "답변량"),
)

_FILTERS = (
    ("all", "전체"),
    ("mock_exam", "모의고사"),
    ("topic_practice", "주제별"),
    ("script_coaching", "스크립트"),
)

_TOPIC_FB_FALLBACK_SUMMARY = "답변을 분석했어요."
_TOPIC_FB_FALLBACK_STRENGTH = "질문에 맞춰 답변하려는 시도가 좋았어요."
_TOPIC_FB_FALLBACK_CORRECTION = (
    "다음 답변에서는 구체적인 이유나 예시를 한 문장 더 추가해 보세요."
)
_TOPIC_FB_FALLBACK_MISSION = (
    "같은 질문에 한 번 더 답하면서 이유를 한 문장 추가해 보세요."
)
_EMPTY_PLACEHOLDER = "—"

_OPIC_KIND_LABELS: Dict[str, str] = {
    "Q1": "묘사",
    "Q2": "루틴",
    "Q3": "경험",
    "Q4": "문제/경험",
    "Q6": "질문하기",
    "Q7": "문제 해결",
    "Q8": "관련 경험",
}

_CORRECTION_ARROW_QUOTE = re.compile(r'"([^"]+)"\s*(?:→|->)\s*')

_HIST_TOPIC_SCOPED_CSS = """
<style>
[data-testid="stMain"]:has(.hist-topic-screen) .hist-topic-wrap {
  margin: 4px 0 0;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-q-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-q-block:last-child {
  margin-bottom: 0;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-q-label {
  font-size: 11px;
  font-weight: 500;
  letter-spacing: 0.05em;
  color: #0F6E56;
  margin: 0 0 6px;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-q-text {
  font-size: 15px;
  font-weight: 500;
  color: #111827;
  line-height: 1.5;
  margin: 0;
  word-break: break-word;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card {
  background: #ffffff;
  border: 0.5px solid rgba(17, 24, 39, 0.10);
  border-radius: 14px;
  padding: 14px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  box-sizing: border-box;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card--mint {
  background: #E1F5EE;
  border-color: rgba(8, 80, 65, 0.12);
  box-shadow: none;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-head-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-label {
  font-size: 12px;
  font-weight: 500;
  margin: 0 0 8px;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-head-row .hist-card-label {
  margin-bottom: 0;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-label--mint { color: #085041; }
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-label--green { color: #3B6D11; }
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-label--coral { color: #993C1D; }
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-label--purple { color: #534AB7; }
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-label--teal { color: #0F6E56; }
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-label--amber { color: #854F0B; }
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-label--blue { color: #185FA5; }
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-body {
  font-size: 13px;
  font-weight: 400;
  color: #444441;
  line-height: 1.6;
  margin: 0;
  word-break: break-word;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-body--mint {
  color: #085041;
  line-height: 1.6;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-card-body--quote {
  line-height: 1.7;
  border-left: 2px solid #5DCAA5;
  padding-left: 10px;
  border-radius: 0;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-level-pill {
  flex-shrink: 0;
  background: #9FE1CB;
  color: #04342C;
  font-size: 12px;
  font-weight: 500;
  padding: 3px 10px;
  border-radius: 999px;
  white-space: nowrap;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-correction-orig {
  text-decoration: line-through;
  color: #888780;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-correction-fix {
  color: #0F6E56;
  font-weight: 500;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-chip {
  background: #EEEDFE;
  color: #26215C;
  font-size: 12px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 999px;
  white-space: nowrap;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-empty-note {
  font-size: 13px;
  font-weight: 400;
  color: #888780;
  margin: 0;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-transcript-wrap {
  margin: 0;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-transcript-wrap [data-testid="stExpander"] {
  background: #ffffff;
  border: 0.5px solid rgba(17, 24, 39, 0.10);
  border-radius: 14px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
  overflow: hidden;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-transcript-wrap [data-testid="stExpander"] details summary {
  font-size: 13px;
  font-weight: 500;
  color: #444441;
  padding: 12px 14px;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-transcript-wrap [data-testid="stExpander"] details summary p {
  font-size: 13px;
  font-weight: 500;
  color: #444441;
  margin: 0;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-transcript-wrap [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
  padding: 0 14px 14px;
}
[data-testid="stMain"]:has(.hist-topic-screen) .hist-transcript-body {
  font-size: 13px;
  font-weight: 400;
  color: #444441;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}
@media (max-width: 480px) {
  [data-testid="stMain"]:has(.hist-topic-screen) .hist-card {
    padding: 12px;
  }
  [data-testid="stMain"]:has(.hist-topic-screen) .hist-card-head-row {
    flex-wrap: wrap;
  }
}
</style>
"""


# ---------------------------------------------------------------------------
# Labels & formatting
# ---------------------------------------------------------------------------

def _type_label(practice_type: str, subtype: str) -> str:
    pt = (practice_type or "").strip()
    sub = (subtype or "").strip()
    if pt == "mock_exam":
        return "실전 모의고사"
    if pt == "topic_practice":
        return "주제별 연습"
    if pt == "script_coaching":
        if sub == "upgrade":
            return "스크립트 업그레이드"
        return "스크립트 첨삭"
    return pt or "기록"


def _format_dt(raw: Any) -> str:
    s = str(raw or "").strip()
    if not s:
        return "—"
    try:
        iso = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is not None:
            dt = dt.astimezone(_KST)
        return dt.strftime("%Y.%m.%d %H:%M")
    except Exception:
        return s[:16]


def _level_badge(level: Any) -> str:
    lv = str(level or "").strip()
    if not lv:
        return ""
    token = lv.upper()
    if token.startswith("AL") or token.startswith("IH"):
        bg, fg = "#0d9488", "#ffffff"
    elif token.startswith("IM"):
        bg, fg = "#2563eb", "#ffffff"
    elif token.startswith("IL") or token.startswith("NH"):
        bg, fg = "#f59e0b", "#ffffff"
    else:
        bg, fg = "#64748b", "#ffffff"
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
        f'background:{bg};color:{fg};font-weight:700;font-size:12px;">'
        f"{html.escape(lv)}</span>"
    )


def _is_topic_practice_record(practice_type: str, content: Dict[str, Any]) -> bool:
    if str(practice_type or "").strip() == "topic_practice":
        return True
    return str(content.get("report_source") or "").strip() == "topic_practice_v2"


def _truncate_preview(text: str, max_len: int = 48) -> str:
    s = str(text or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1].rstrip() + "…"


def _opic_header_label(opic_type: str, idx: int) -> str:
    key = str(opic_type or f"Q{idx}").strip().upper()
    kind = _OPIC_KIND_LABELS.get(key, key.replace("Q", "문항 "))
    qnum = key if key.startswith("Q") else f"Q{idx}"
    return f"{qnum} · {kind}"


def _estimated_level_from_item(
    item: Dict[str, Any], fb: Optional[Dict[str, Any]] = None
) -> str:
    for src in (item, fb or {}):
        if not isinstance(src, dict):
            continue
        for key in (
            "answer_level",
            "estimated_level_display",
            "estimated_level",
            "level",
            "overall_level",
        ):
            value = str(src.get(key) or "").strip()
            if value:
                return value
    return ""


def _inject_hist_topic_css() -> None:
    st.markdown(_HIST_TOPIC_SCOPED_CSS, unsafe_allow_html=True)


def _hist_white_card(label: str, body_html: str, *, tone: str) -> str:
    return (
        f'<div class="hist-card">'
        f'<div class="hist-card-label hist-card-label--{html.escape(tone)}">'
        f"{html.escape(label)}</div>"
        f"{body_html}"
        f"</div>"
    )


def _format_correction_focus_html(text: str) -> str:
    raw = str(text or "").strip() or _TOPIC_FB_FALLBACK_CORRECTION
    if not _CORRECTION_ARROW_QUOTE.search(raw):
        return f'<p class="hist-card-body">{html.escape(raw)}</p>'

    out: List[str] = []
    last = 0
    for match in _CORRECTION_ARROW_QUOTE.finditer(raw):
        if match.start() > last:
            out.append(html.escape(raw[last : match.start()]))
        original = match.group(1)
        fix_start = match.end()
        next_match = _CORRECTION_ARROW_QUOTE.search(raw, fix_start)
        fix_end = next_match.start() if next_match else len(raw)
        fix = raw[fix_start:fix_end].strip()
        out.append(
            f'<span class="hist-correction-orig">"{html.escape(original)}"</span> '
            f'<span class="hist-correction-fix">{html.escape(fix)}</span>'
        )
        last = fix_end
    if last < len(raw):
        out.append(html.escape(raw[last:]))
    return f'<p class="hist-card-body">{"".join(out)}</p>'


def _format_keyword_chips_html(keywords: List[str]) -> str:
    clean = [str(w or "").strip() for w in keywords if str(w or "").strip()]
    if not clean:
        return f'<p class="hist-card-body">{html.escape(_EMPTY_PLACEHOLDER)}</p>'
    chips = "".join(
        f'<span class="hist-chip">{html.escape(word)}</span>' for word in clean
    )
    return f'<div class="hist-chips">{chips}</div>'


def _format_summary_card_html(summary: str, level: str) -> str:
    pill = (
        f'<span class="hist-level-pill">{html.escape(level)}</span>' if level else ""
    )
    return (
        f'<div class="hist-card hist-card--mint">'
        f'<div class="hist-card-head-row">'
        f'<span class="hist-card-label hist-card-label--mint">한 줄 진단</span>'
        f"{pill}"
        f"</div>"
        f'<p class="hist-card-body hist-card-body--mint">'
        f"{html.escape(summary)}</p>"
        f"</div>"
    )


def _short_feedback_text(fb: Any, key: str, default: str = "") -> str:
    if not isinstance(fb, dict):
        return default
    value = str(fb.get(key) or "").strip()
    return value if value else default


def _short_feedback_keywords(fb: Any) -> List[str]:
    if not isinstance(fb, dict):
        return []
    kd = fb.get("keyword_drill")
    if not isinstance(kd, list):
        return []
    return [str(x or "").strip() for x in kd if str(x or "").strip()][:20]


def _resolve_short_feedback(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sf = item.get("short_feedback")
    if isinstance(sf, dict):
        if sf.get("ok") is False:
            return None
        keys = (
            "answer_level",
            "summary",
            "strength",
            "correction_focus",
            "practice_mission",
            "upgrade_sample",
            "better_expression",
            "keyword_drill",
        )
        if any(sf.get(k) for k in keys):
            return sf
    fb = str(item.get("feedback") or item.get("summary") or item.get("comment") or "").strip()
    if fb:
        return {"summary": fb}
    return None


def _question_text_from_item(item: Dict[str, Any]) -> str:
    return str(item.get("question") or item.get("topic") or "").strip()


def _transcript_from_item(item: Dict[str, Any]) -> str:
    return str(item.get("transcript") or item.get("answer_text") or "").strip()


def _axis_value(breakdown: Any, key: str) -> Optional[float]:
    if not isinstance(breakdown, dict):
        return None
    v = breakdown.get(key)
    if isinstance(v, dict):
        v = v.get("score")
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def render_history() -> None:
    ss = st.session_state
    render_top_bar("학습 기록", back_href="?nav=HOME", eyebrow="내 기록")

    if not is_authenticated(ss):
        _render_login_gate()
        return

    selected = ss.get(_KEY_SELECTED)
    if selected:
        _render_detail(str(selected))
    else:
        _render_list()


def _render_login_gate() -> None:
    st.markdown(
        """
        <div class="glass-card-quiet" style="margin:8px 0 14px 0;">
          <p style="margin:0 0 6px 0;font-weight:700;color:#0f172a;">로그인하면 기록이 보여요</p>
          <p class="ds-muted" style="margin:0;">
            구글로 로그인하면 모의고사·주제별 연습·스크립트 첨삭 결과가
            계정에 저장되어 언제든 다시 볼 수 있어요.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("로그인하러 가기", type="primary", use_container_width=True, key="history_go_login"):
        navigate_to("SETTINGS")
        st.rerun()


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------

def _render_empty_list() -> None:
    character = render_character_svg("default", 104, bg="#ffffff")
    wave_svg = (
        '<svg class="hist-empty-wave" width="170" height="26" viewBox="0 0 150 26" '
        'aria-hidden="true" xmlns="http://www.w3.org/2000/svg">'
        '<polyline points="6,13 32,13 42,5 54,21 66,2 78,18 88,13 144,13" '
        'fill="none" stroke="#1D9E75" stroke-width="2.2" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
        "</svg>"
    )
    st.markdown(
        f"""
        <div class="hist-list-marker" aria-hidden="true"></div>
        <div class="hist-empty-card">
          <div class="hist-empty-stage">
            <span class="hist-empty-chip hist-empty-chip--desc">묘사</span>
            <span class="hist-empty-chip hist-empty-chip--role">롤플레이</span>
            <span class="hist-empty-chip hist-empty-chip--cmp">비교</span>
            <div class="hist-empty-char-wrap">
              {character}
              {wave_svg}
            </div>
          </div>
          <div class="hist-empty-body">
            <p class="hist-empty-title">아직 진료 기록이 없어요</p>
            <p class="hist-empty-sub">첫 연습을 마치면 오픽치료사의 진단 기록이 여기에 쌓여요</p>
            <p class="hist-empty-preview-label">앞으로 쌓일 기록</p>
            <div class="hist-empty-skel hist-empty-skel--primary">
              <div class="hist-empty-skel-tile" aria-hidden="true"></div>
              <div class="hist-empty-skel-bars">
                <div class="hist-empty-skel-bar hist-empty-skel-bar--w72"></div>
                <div class="hist-empty-skel-bar hist-empty-skel-bar--w46"></div>
              </div>
              <span class="hist-empty-skel-pill">등급</span>
            </div>
            <div class="hist-empty-skel hist-empty-skel--secondary">
              <div class="hist-empty-skel-tile" aria-hidden="true"></div>
              <div class="hist-empty-skel-bars">
                <div class="hist-empty-skel-bar hist-empty-skel-bar--w64"></div>
                <div class="hist-empty-skel-bar hist-empty-skel-bar--w38"></div>
              </div>
            </div>
            <a class="hist-empty-cta" href="?nav=MOCK&amp;reset_practice=1" target="_self">
              첫 진료 시작하기
            </a>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_list() -> None:
    ss = st.session_state
    active = str(ss.get(_KEY_FILTER) or "all")

    cols = st.columns(len(_FILTERS), gap="small")
    for col, (key, label) in zip(cols, _FILTERS):
        with col:
            is_active = key == active
            if st.button(
                label,
                key=f"history_filter_{key}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                ss[_KEY_FILTER] = key
                st.rerun()

    practice_type = None if active == "all" else active
    rows = list_history(practice_type=practice_type, limit=100)

    if not rows:
        _render_empty_list()
        return

    for row in rows:
        if not isinstance(row, dict):
            continue
        _render_list_row(row)


def _render_list_row(row: Dict[str, Any]) -> None:
    rid = str(row.get("id") or "")
    title = str(row.get("title") or "").strip() or _type_label(
        str(row.get("practice_type") or ""), str(row.get("subtype") or "")
    )
    type_label = _type_label(
        str(row.get("practice_type") or ""), str(row.get("subtype") or "")
    )
    when = _format_dt(row.get("created_at"))
    badge = _level_badge(row.get("overall_level"))

    st.markdown(
        f"""
        <div class="glass-card-quiet" style="margin:8px 0 0 0;padding:12px 14px;">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">
            <span class="ds-muted" style="font-size:12px;font-weight:600;">{html.escape(type_label)}</span>
            {badge}
          </div>
          <div style="font-weight:700;color:#0f172a;margin:4px 0 2px 0;font-size:15px;
                      overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
            {html.escape(title)}
          </div>
          <div class="ds-muted" style="font-size:12px;">{html.escape(when)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("자세히 보기", key=f"history_open_{rid}", use_container_width=True):
        st.session_state[_KEY_SELECTED] = rid
        st.rerun()


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------

def _render_detail(record_id: str) -> None:
    if st.button("← 목록으로", key="history_back_to_list"):
        st.session_state.pop(_KEY_SELECTED, None)
        st.rerun()

    record = get_history_record(record_id)
    if not isinstance(record, dict):
        st.markdown(
            '<p class="ds-muted" style="margin-top:20px;">기록을 불러오지 못했어요. 다시 시도해 주세요.</p>',
            unsafe_allow_html=True,
        )
        return

    practice_type = str(record.get("practice_type") or "")
    subtype = str(record.get("subtype") or "")
    title = str(record.get("title") or "").strip() or _type_label(practice_type, subtype)
    type_label = _type_label(practice_type, subtype)
    when = _format_dt(record.get("created_at"))
    badge = _level_badge(record.get("overall_level"))
    score = record.get("score")
    score_html = (
        f'<span style="font-weight:700;color:#0f172a;">평균 {score}점</span>'
        if score is not None
        else ""
    )

    st.markdown(
        f"""
        <div class="glass-card" style="margin:10px 0 14px 0;border-left:4px solid #0D9488;">
          <div class="ds-muted" style="font-size:12px;font-weight:600;">{html.escape(type_label)} · {html.escape(when)}</div>
          <div style="font-weight:800;color:#0f172a;font-size:18px;margin:6px 0 8px 0;">{html.escape(title)}</div>
          <div style="display:flex;align-items:center;gap:10px;">{badge}{score_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    content = record.get("content")
    if not isinstance(content, dict):
        content = {}

    _render_score_breakdown(content.get("score_breakdown"))
    _render_text_sections(content, subtype, practice_type)
    _render_per_question(content, practice_type)


def _render_score_breakdown(breakdown: Any) -> None:
    if not isinstance(breakdown, dict):
        return
    rows = []
    for key, label in _SCORE_AXES:
        val = _axis_value(breakdown, key)
        if val is None:
            continue
        pct = max(0, min(100, int(round(val))))
        rows.append(
            f'<div style="margin:6px 0;">'
            f'<div style="display:flex;justify-content:space-between;font-size:13px;color:#334155;">'
            f"<span>{html.escape(label)}</span><span style=\"font-weight:700;\">{int(round(val))}</span></div>"
            f'<div style="height:7px;background:#e2e8f0;border-radius:999px;overflow:hidden;margin-top:3px;">'
            f'<span style="display:block;height:100%;width:{pct}%;background:#0d9488;"></span></div>'
            f"</div>"
        )
    if not rows:
        return
    st.markdown('<div class="home-section-h">항목별 점수</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="glass-card-quiet" style="padding:12px 14px;">{"".join(rows)}</div>',
        unsafe_allow_html=True,
    )


def _render_script_coaching_before_after(content: Dict[str, Any]) -> None:
    original = str(content.get("original_script") or "").strip()
    upgraded = str(content.get("upgraded_script") or "").strip()
    has_feedback = bool(
        str(content.get("summary") or content.get("overall_feedback") or "").strip()
        or content.get("strengths")
        or content.get("weaknesses")
    )

    if not original and (upgraded or has_feedback):
        st.markdown(
            '<p class="hist-sc-legacy-note">이전 기록이라 원문이 저장되지 않았어요.</p>',
            unsafe_allow_html=True,
        )

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


def _render_script_coaching_text_sections(
    content: Dict[str, Any], subtype: str
) -> None:
    st.markdown('<div class="hist-script-screen" aria-hidden="true"></div>', unsafe_allow_html=True)

    question = str(content.get("question_en") or "").strip()
    if question:
        st.markdown(
            f'<p class="hist-sc-question">Q. {html.escape(question)}</p>',
            unsafe_allow_html=True,
        )

    _render_script_coaching_before_after(content)

    summary = str(
        content.get("summary") or content.get("overall_feedback") or ""
    ).strip()
    if summary:
        st.markdown('<div class="home-section-h">총평</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="glass-card-quiet" style="padding:12px 14px;color:#334155;font-size:14px;line-height:1.6;">{html.escape(summary)}</div>',
            unsafe_allow_html=True,
        )

    _render_bullets("강점", content.get("strengths"))
    _render_bullets("보완점", content.get("weaknesses"))

    mission = content.get("practice_mission") or content.get("mission")
    if isinstance(mission, str) and mission.strip():
        st.markdown('<div class="home-section-h">연습 미션</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="glass-card-quiet" style="padding:12px 14px;color:#334155;font-size:14px;line-height:1.6;">{html.escape(mission.strip())}</div>',
            unsafe_allow_html=True,
        )


def _render_text_sections(
    content: Dict[str, Any], subtype: str, practice_type: str = ""
) -> None:
    if _is_topic_practice_record(practice_type, content):
        return
    if str(practice_type or "").strip() == "script_coaching":
        _render_script_coaching_text_sections(content, subtype)
        return

    summary = str(
        content.get("summary") or content.get("overall_feedback") or ""
    ).strip()
    if summary:
        st.markdown('<div class="home-section-h">총평</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="glass-card-quiet" style="padding:12px 14px;color:#334155;font-size:14px;line-height:1.6;">{html.escape(summary)}</div>',
            unsafe_allow_html=True,
        )

    _render_bullets("강점", content.get("strengths"))
    _render_bullets("보완점", content.get("weaknesses"))

    mission = content.get("practice_mission") or content.get("mission")
    if isinstance(mission, str) and mission.strip():
        st.markdown('<div class="home-section-h">연습 미션</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="glass-card-quiet" style="padding:12px 14px;color:#334155;font-size:14px;line-height:1.6;">{html.escape(mission.strip())}</div>',
            unsafe_allow_html=True,
        )

    upgraded = str(content.get("upgraded_script") or "").strip()
    if upgraded:
        st.markdown('<div class="home-section-h">업그레이드된 스크립트</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="glass-card-quiet" style="padding:12px 14px;color:#0f172a;font-size:14px;line-height:1.7;white-space:pre-wrap;">{html.escape(upgraded)}</div>',
            unsafe_allow_html=True,
        )


def _render_bullets(title: str, items: Any) -> None:
    if not isinstance(items, (list, tuple)) or not items:
        return
    lis = "".join(
        f"<li style=\"margin:4px 0;\">{html.escape(str(it))}</li>"
        for it in items
        if str(it).strip()
    )
    if not lis:
        return
    st.markdown(f'<div class="home-section-h">{html.escape(title)}</div>', unsafe_allow_html=True)
    st.markdown(
        f'<ul class="glass-card-quiet" style="padding:12px 14px 12px 30px;color:#334155;font-size:14px;line-height:1.6;margin:0;">{lis}</ul>',
        unsafe_allow_html=True,
    )


def _render_topic_practice_question(item: Dict[str, Any], idx: int) -> None:
    q_text = _question_text_from_item(item)
    opic = str(item.get("opic_type") or f"Q{idx}").strip()
    header_label = _opic_header_label(opic, idx)
    transcript = _transcript_from_item(item)
    fb = _resolve_short_feedback(item)

    st.markdown('<div class="hist-q-block">', unsafe_allow_html=True)
    st.markdown(
        f'<div class="hist-q-head">'
        f'<p class="hist-q-label">{html.escape(header_label)}</p>'
        f'<p class="hist-q-text">{html.escape(q_text) if q_text else html.escape(_EMPTY_PLACEHOLDER)}</p>'
        f"</div>",
        unsafe_allow_html=True,
    )

    if transcript:
        st.markdown('<div class="hist-transcript-wrap">', unsafe_allow_html=True)
        with st.expander("내 답변", expanded=False):
            st.markdown(
                f'<p class="hist-transcript-body">{html.escape(transcript)}</p>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown(
            '<p class="hist-empty-note">저장된 답변 transcript가 없어요.</p>',
            unsafe_allow_html=True,
        )

    if not fb:
        if transcript:
            st.markdown(
                '<p class="hist-empty-note">이 문항은 저장된 AI 피드백이 없어요. 답변만 확인할 수 있어요.</p>',
                unsafe_allow_html=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    level = _estimated_level_from_item(item, fb)
    summary = _short_feedback_text(fb, "summary", _TOPIC_FB_FALLBACK_SUMMARY)
    st.markdown(_format_summary_card_html(summary, level), unsafe_allow_html=True)

    strength = _short_feedback_text(fb, "strength", _TOPIC_FB_FALLBACK_STRENGTH)
    st.markdown(
        _hist_white_card("잘한 점", f'<p class="hist-card-body">{html.escape(strength)}</p>', tone="green"),
        unsafe_allow_html=True,
    )

    correction = _short_feedback_text(fb, "correction_focus", _TOPIC_FB_FALLBACK_CORRECTION)
    st.markdown(
        _hist_white_card("교정 포인트", _format_correction_focus_html(correction), tone="coral"),
        unsafe_allow_html=True,
    )

    keywords = _short_feedback_keywords(fb)
    st.markdown(
        _hist_white_card("키워드 드릴", _format_keyword_chips_html(keywords), tone="purple"),
        unsafe_allow_html=True,
    )

    upgrade = _short_feedback_text(fb, "upgrade_sample", "")
    upgrade_body = (
        f'<p class="hist-card-body hist-card-body--quote">{html.escape(upgrade)}</p>'
        if upgrade
        else f'<p class="hist-card-body">{html.escape(_EMPTY_PLACEHOLDER)}</p>'
    )
    st.markdown(
        _hist_white_card("업그레이드 예문", upgrade_body, tone="teal"),
        unsafe_allow_html=True,
    )

    better = _short_feedback_text(fb, "better_expression", "")
    better_body = (
        f'<p class="hist-card-body">{html.escape(better)}</p>'
        if better
        else f'<p class="hist-card-body">{html.escape(_EMPTY_PLACEHOLDER)}</p>'
    )
    st.markdown(
        _hist_white_card("표현 개선", better_body, tone="blue"),
        unsafe_allow_html=True,
    )

    mission = _short_feedback_text(fb, "practice_mission", _TOPIC_FB_FALLBACK_MISSION)
    st.markdown(
        _hist_white_card(
            "연습 미션",
            f'<p class="hist-card-body">{html.escape(mission)}</p>',
            tone="amber",
        ),
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_topic_practice_results(content: Dict[str, Any]) -> None:
    results = content.get("results")
    if not isinstance(results, list) or not results:
        return

    _inject_hist_topic_css()
    st.markdown(
        '<div class="hist-topic-screen" aria-hidden="true"></div>'
        '<div class="hist-topic-wrap">',
        unsafe_allow_html=True,
    )

    for idx, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue
        _render_topic_practice_question(item, idx)

    st.markdown("</div>", unsafe_allow_html=True)


def _render_per_question(content: Dict[str, Any], practice_type: str = "") -> None:
    if _is_topic_practice_record(practice_type, content):
        _render_topic_practice_results(content)
        return

    results = content.get("results")
    if not isinstance(results, list) or not results:
        return
    st.markdown('<div class="home-section-h">문항별 결과</div>', unsafe_allow_html=True)
    for idx, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue
        preview = _truncate_preview(_question_text_from_item(item), 48)
        level = str(item.get("level") or item.get("overall_level") or "").strip()
        label = f"Q{idx}" + (f" · {preview}" if preview else "")
        with st.expander(label + (f"  [{level}]" if level else "")):
            q_text = _question_text_from_item(item)
            if q_text:
                st.markdown(
                    f'<div class="ds-muted" style="font-size:12px;margin-bottom:4px;">질문</div>'
                    f'<div style="color:#0f172a;font-size:13px;line-height:1.6;margin-bottom:10px;">'
                    f"{html.escape(q_text)}</div>",
                    unsafe_allow_html=True,
                )
            transcript = _transcript_from_item(item)
            if transcript:
                st.markdown(
                    f'<div class="ds-muted" style="font-size:12px;margin-bottom:4px;">내 답변</div>'
                    f'<div style="color:#334155;font-size:13px;line-height:1.6;white-space:pre-wrap;">'
                    f"{html.escape(transcript)}</div>",
                    unsafe_allow_html=True,
                )
            fb = str(
                item.get("feedback") or item.get("summary") or item.get("comment") or ""
            ).strip()
            if fb:
                st.markdown(
                    f'<div class="ds-muted" style="font-size:12px;margin:8px 0 4px 0;">피드백</div>'
                    f'<div style="color:#334155;font-size:13px;line-height:1.6;">{html.escape(fb)}</div>',
                    unsafe_allow_html=True,
                )
