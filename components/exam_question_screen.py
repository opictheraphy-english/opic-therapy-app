"""
Shared exam question-screen UI (topic practice shell, mini mock, real mock).

HTML/CSS uses ``.tq-screen-marker`` scope in ``ui/styles.py``. Does not replace
``views/topic_practice_v2`` helpers — that module keeps its own copies.
"""

from __future__ import annotations

import html
from typing import Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components

from views.topic_icons import TOPIC_ICONS

_ACCENT_NAMES: Tuple[str, ...] = (
    "teal",
    "blue",
    "purple",
    "pink",
    "amber",
    "coral",
)

_WAVE_BAR_HEIGHTS_PX: Tuple[int, ...] = (
    14, 18, 22, 28, 32, 36, 34, 36, 34, 32, 28, 22, 18, 16, 14
)

_DEFAULT_ANSWER_DESC = (
    "답변 시작을 누르고 영어로 말해 보세요. "
    "녹음이 끝나면 AI가 텍스트로 인식합니다."
)

# Same mapping as topic_practice_v2 (badge copy for question cards).
_OPIC_TYPE_LABELS: dict[str, str] = {
    "Q1": "Q1 유형 · 묘사",
    "Q2": "Q2 유형 · 루틴",
    "Q3": "Q3 유형 · 경험",
    "Q4": "Q4 유형 · 문제/경험",
    "Q6": "Q6 유형 · 질문하기",
    "Q7": "Q7 유형 · 문제 해결",
    "Q8": "Q8 유형 · 관련 경험",
}

_OPIC_TYPE_BADGE_LABELS: dict[str, str] = {
    "Q1": "Q1 · 묘사하기",
    "Q2": "Q2 · 루틴하기",
    "Q3": "Q3 · 경험하기",
    "Q4": "Q4 · 문제/경험",
    "Q6": "Q6 · 질문하기",
    "Q7": "Q7 · 문제 해결",
    "Q8": "Q8 · 관련 경험",
    "INTRO": "소개",
}


def opic_type_badge_label(opic_type: str) -> str:
    """
    Short badge text for ``.tq-type-badge`` (e.g. ``Q1 · 묘사하기``).

    Returns empty string when the type is unknown so callers can omit the badge.
    """
    raw = str(opic_type or "").strip()
    if not raw:
        return ""
    key = raw.upper()
    if key in _OPIC_TYPE_BADGE_LABELS:
        return _OPIC_TYPE_BADGE_LABELS[key]
    if key in _OPIC_TYPE_LABELS:
        return _OPIC_TYPE_BADGE_LABELS.get(key, _OPIC_TYPE_LABELS[key])
    if key.startswith("Q") and len(key) <= 3:
        return f"{key} 유형"
    return ""


def _normalize_accent(accent: str) -> str:
    key = str(accent or "teal").strip().lower()
    if key not in _ACCENT_NAMES:
        return "teal"
    return key


def build_progress_segments_html(
    current: int,
    total: int,
    *,
    badge_label: str = "",
) -> str:
    """
    Progress row + bar (``.mx-progress`` / ``.mx-progress-bar``).

    Optional ``badge_label`` renders the type pill on the right of row 1.
    """
    total_n = max(1, int(total))
    current_n = min(max(1, int(current)), total_n)
    pct = int(round((current_n / total_n) * 100))
    pct = max(0, min(100, pct))
    badge = html.escape(str(badge_label or "").strip())
    chip_block = (
        f'<div class="mx-progress-chip">{badge}</div>' if badge else ""
    )
    return (
        f'<div class="mx-progress">'
        f'<div class="mx-progress-meta">'
        f'<span class="mx-progress-count">'
        f'문항 <span class="mx-progress-num">{current_n}</span> '
        f'<span class="mx-progress-of">/ {total_n}</span>'
        f"</span>"
        f"</div>"
        f"{chip_block}"
        f"</div>"
        f'<div class="mx-progress-bar" role="progressbar" '
        f'aria-valuenow="{current_n}" aria-valuemin="1" aria-valuemax="{total_n}">'
        f'<span class="mx-progress-fill" style="width:{pct}%;"></span>'
        f"</div>"
    )


def _wave_bars_html() -> str:
    bars = "".join(
        f'<span class="tq-wave-bar" style="height:{h}px"></span>'
        for h in _WAVE_BAR_HEIGHTS_PX
    )
    return f'<div class="tq-wave-bars" aria-hidden="true">{bars}</div>'


def build_exam_answer_card_top_html(*, accent: str = "teal") -> str:
    """Answer card top HTML (mic header + static wave slot)."""
    accent_key = html.escape(_normalize_accent(accent))
    mic_svg = TOPIC_ICONS.get("microphone-2", TOPIC_ICONS["circle"])
    desc = html.escape(_DEFAULT_ANSWER_DESC)
    return (
        f'<div class="mx-record-stage mx-record-stage--v2">'
        f'<p class="mx-record-eyebrow">답변 녹음</p>'
        f'<div class="tq-answer-card-top">'
        f'<div class="tq-answer-head">'
        f'<span class="tq-answer-ico tq-answer-ico--{accent_key}">{mic_svg}</span>'
        f'<span class="tq-answer-title">말로 답변하기</span>'
        f"</div>"
        f'<p class="tq-answer-desc">{desc}</p>'
        f'<div class="tq-wave-slot tq-wave-slot--{accent_key}">'
        f"{_wave_bars_html()}"
        f"</div>"
        f"</div>"
        f"</div>"
    )


def build_exam_question_shell_html(
    *,
    title: Optional[str] = None,
    eyebrow: Optional[str] = None,
    progress_html: str,
    badge_label: str,
    question_en: str,
    question_ko: str = "",
    accent: str = "teal",
    chip_icon: Optional[str] = None,
) -> str:
    """Full question shell HTML (marker + header + question card)."""
    accent_key = _normalize_accent(accent)
    accent_esc = html.escape(accent_key)
    badge = html.escape(str(badge_label or "").strip())
    en = html.escape(str(question_en or ""))
    ko_raw = str(question_ko or "").strip()
    ko_block = (
        f'<p class="tq-question-ko">{html.escape(ko_raw)}</p>' if ko_raw else ""
    )

    title_s = str(title or "").strip()
    topic_header = ""
    if title_s:
        icon_name = str(chip_icon or "circle").strip() or "circle"
        svg = TOPIC_ICONS.get(icon_name, TOPIC_ICONS["circle"])
        topic_header = (
            f'<div class="tq-header">'
            f'<div class="tq-topic-chip tq-topic-chip--{accent_esc}">'
            f'<span class="tq-topic-chip-ico">{svg}</span>'
            f'<span class="tq-topic-chip-name">{html.escape(title_s)}</span>'
            f"</div>"
            f"</div>"
        )

    progress_block = str(progress_html or "").strip()
    if not progress_block:
        progress_block = build_progress_segments_html(1, 1, badge_label=badge)

    return (
        '<div class="tq-screen-marker" aria-hidden="true"></div>'
        f"{topic_header}"
        f"{progress_block}"
        f'<div class="mx-question-card tq-card">'
        f'<p class="mx-question-topic tq-question">{en}</p>'
        f"{ko_block}"
        f"</div>"
    )


def render_exam_question_shell(
    *,
    title: Optional[str] = None,
    eyebrow: Optional[str] = None,
    progress_html: str,
    badge_label: str,
    question_en: str,
    question_ko: str = "",
    accent: str = "teal",
    chip_icon: Optional[str] = None,
) -> None:
    """Render question shell via ``st.markdown`` (``.tq-screen-marker`` + card)."""
    st.markdown(
        build_exam_question_shell_html(
            title=title,
            eyebrow=eyebrow,
            progress_html=progress_html,
            badge_label=badge_label,
            question_en=question_en,
            question_ko=question_ko,
            accent=accent,
            chip_icon=chip_icon,
        ),
        unsafe_allow_html=True,
    )


def render_exam_answer_card_top(*, accent: str = "teal") -> None:
    """Render answer card top (mic header + wave slot)."""
    st.markdown(build_exam_answer_card_top_html(accent=accent), unsafe_allow_html=True)


def render_exam_wave_mic_observer() -> None:
    """Read-only poll of mic iframe button label; toggles ``.tq-wave-slot--active``."""
    components.html(
        """
        <script>
        (function () {
          var POLL_MS = 280;
          var STOP_HINT = "녹음 완료";
          var timer = null;

          function parentDoc() {
            try {
              if (window.parent && window.parent.document) {
                return window.parent.document;
              }
            } catch (e) { /* cross-origin */ }
            return null;
          }

          function findMicIframe(doc) {
            try {
              var ifr = doc.querySelector('iframe[src*="streamlit_mic_recorder"]');
              if (ifr) return ifr;
              var hosts = doc.querySelectorAll(
                '[data-testid="stCustomComponentV1"], [data-testid="stCustomComponent"]'
              );
              for (var i = 0; i < hosts.length; i++) {
                var inner = hosts[i].querySelector("iframe");
                if (!inner) continue;
                var src = inner.getAttribute("src") || "";
                if (src.indexOf("streamlit_mic_recorder") >= 0) return inner;
              }
            } catch (e) { /* ignore */ }
            return null;
          }

          function micShowsRecording(doc) {
            try {
              var ifr = findMicIframe(doc);
              if (!ifr) return false;
              var idoc = ifr.contentDocument;
              if (!idoc) return false;
              var btn = idoc.querySelector("button");
              if (!btn) return false;
              var text = (btn.innerText || btn.textContent || "").trim();
              return text.indexOf(STOP_HINT) >= 0;
            } catch (e) {
              return false;
            }
          }

          function tick() {
            try {
              var doc = parentDoc();
              if (!doc || !doc.querySelector(".tq-screen-marker")) return;
              var slot = doc.querySelector(".tq-wave-slot");
              if (!slot) return;
              slot.classList.toggle("tq-wave-slot--active", micShowsRecording(doc));
            } catch (e) { /* ignore */ }
          }

          function start() {
            if (timer) clearInterval(timer);
            tick();
            timer = setInterval(tick, POLL_MS);
          }

          if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", start);
          } else {
            start();
          }
        })();
        </script>
        """,
        height=0,
    )
