"""학습 기록 보기 — 로그인 사용자의 모의고사·주제별·스크립트 첨삭 결과.

Stage 4: 목록 + 상세 뷰 + 진입점. 데이터는 ``services.history_store`` 가 Supabase
PostgREST 에서 가져온다(본인 행만, RLS). 비로그인은 로그인 안내만 보여준다.
"""

from __future__ import annotations

import html
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import streamlit as st

from components.navigation import navigate_to
from components.topbar import render_top_bar
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
        st.markdown(
            '<p class="ds-muted" style="text-align:center;margin-top:28px;">'
            "아직 저장된 기록이 없어요.<br/>모의고사나 스크립트 첨삭을 완료하면 여기에 쌓여요.</p>",
            unsafe_allow_html=True,
        )
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
    _render_text_sections(content, subtype)
    _render_per_question(content)

    with st.expander("원본 데이터 (개발용)"):
        st.code(json.dumps(content, ensure_ascii=False, indent=2)[:8000], language="json")


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


def _render_text_sections(content: Dict[str, Any], subtype: str) -> None:
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


def _render_per_question(content: Dict[str, Any]) -> None:
    results = content.get("results")
    if not isinstance(results, list) or not results:
        return
    st.markdown('<div class="home-section-h">문항별 결과</div>', unsafe_allow_html=True)
    for idx, item in enumerate(results, start=1):
        if not isinstance(item, dict):
            continue
        topic = str(item.get("topic") or item.get("question") or "").strip()
        level = str(item.get("level") or item.get("overall_level") or "").strip()
        label = f"Q{idx}" + (f" · {topic[:40]}" if topic else "")
        with st.expander(label + (f"  [{level}]" if level else "")):
            transcript = str(
                item.get("transcript") or item.get("answer_text") or ""
            ).strip()
            if transcript:
                st.markdown(
                    f'<div class="ds-muted" style="font-size:12px;margin-bottom:4px;">내 답변</div>'
                    f'<div style="color:#334155;font-size:13px;line-height:1.6;white-space:pre-wrap;">{html.escape(transcript)}</div>',
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
