"""Animated examiner avatar for practice question screens (inline SVG + CSS)."""

from __future__ import annotations

import html
import logging
from typing import Any, Mapping

import streamlit as st
import streamlit.components.v1 as components

logger = logging.getLogger(__name__)

VALID_MODES = frozenset({"idle", "speaking", "listening", "nodding"})


def _normalize_mode(mode: str) -> str:
    key = str(mode or "idle").strip().lower()
    return key if key in VALID_MODES else "idle"


def build_examiner_avatar_html(
    mode: str,
    *,
    size: int = 120,
    has_tts: bool = False,
) -> str:
    """Inline SVG avatar (B-1 Ava); ``data-base-mode`` restored after live JS overrides."""
    m = _normalize_mode(mode)
    px = max(72, min(160, int(size)))
    tts_flag = "1" if has_tts else "0"
    return (
        f'<div class="examiner-avatar-host" style="--ea-size:{px}px">'
        f'<div class="examiner-avatar" data-mode="{html.escape(m)}" '
        f'data-base-mode="{html.escape(m)}" data-hint-tts="{tts_flag}" '
        f'role="img" aria-label="시험관 아바타">'
        f'<svg class="examiner-avatar-svg" viewBox="0 0 100 100" width="{px}" height="{px}" '
        f'xmlns="http://www.w3.org/2000/svg" aria-hidden="true">'
        f'<circle class="examiner-avatar-frame" cx="50" cy="50" r="48" fill="#eefaf5"/>'
        f'<g class="examiner-avatar-figure">'
        f'<path class="examiner-avatar-shirt" d="M24 78 Q50 68 76 78 L80 100 L20 100 Z" fill="#1d9e75"/>'
        f'<path class="examiner-avatar-collar" d="M38 76 L50 86 L62 76 L50 80 Z" fill="#ffffff" opacity="0.95"/>'
        f'<path class="examiner-avatar-hair" d="M27 50 Q24 62 28 74 Q34 70 36 54 Q32 42 50 30 '
        f'Q68 42 64 54 Q62 70 72 74 Q76 62 73 50 Q70 28 50 24 Q30 28 27 50 Z" '
        f'fill="#d9a94e" stroke="#c79338" stroke-width="0.8"/>'
        f'<path class="examiner-avatar-hair" d="M34 36 Q50 28 66 36 Q62 32 50 30 Q38 32 34 36 Z" '
        f'fill="#d9a94e" stroke="#c79338" stroke-width="0.6"/>'
        f'<ellipse class="examiner-avatar-head" cx="50" cy="44" rx="22" ry="23" fill="#f8e3cf"/>'
        f'<g class="examiner-avatar-face">'
        f'<ellipse class="examiner-avatar-cheek examiner-avatar-cheek--l" cx="36" cy="48" '
        f'rx="4" ry="2.5" fill="#f3b9a0" opacity="0.5"/>'
        f'<ellipse class="examiner-avatar-cheek examiner-avatar-cheek--r" cx="64" cy="48" '
        f'rx="4" ry="2.5" fill="#f3b9a0" opacity="0.5"/>'
        f'<path class="examiner-avatar-brow examiner-avatar-brow--l" d="M37 37 Q42 34 47 37" '
        f'fill="none" stroke="#b98e3e" stroke-width="1.3" stroke-linecap="round"/>'
        f'<path class="examiner-avatar-brow examiner-avatar-brow--r" d="M53 37 Q58 34 63 37" '
        f'fill="none" stroke="#b98e3e" stroke-width="1.3" stroke-linecap="round"/>'
        f'<g class="examiner-avatar-eye examiner-avatar-eye--l">'
        f'<circle class="examiner-avatar-eye-open" cx="42" cy="43" r="3" fill="#4a6fa5"/>'
        f'<circle class="examiner-avatar-eye-highlight" cx="43.1" cy="42.1" r="0.9" fill="#ffffff"/>'
        f'<path class="examiner-avatar-eye-closed" d="M39 43 Q42 41.2 45 43" fill="none" '
        f'stroke="#4a6fa5" stroke-width="1.5" stroke-linecap="round"/>'
        f"</g>"
        f'<g class="examiner-avatar-eye examiner-avatar-eye--r">'
        f'<circle class="examiner-avatar-eye-open" cx="58" cy="43" r="3" fill="#4a6fa5"/>'
        f'<circle class="examiner-avatar-eye-highlight" cx="59.1" cy="42.1" r="0.9" fill="#ffffff"/>'
        f'<path class="examiner-avatar-eye-closed" d="M55 43 Q58 41.2 61 43" fill="none" '
        f'stroke="#4a6fa5" stroke-width="1.5" stroke-linecap="round"/>'
        f"</g>"
        f'<path class="examiner-avatar-nose" d="M50 45 Q50.5 48 50 50" fill="none" '
        f'stroke="#e0b894" stroke-width="1.6" stroke-linecap="round"/>'
        f'<g class="examiner-avatar-mouth">'
        f'<path class="examiner-avatar-mouth-shape examiner-avatar-mouth--closed" '
        f'd="M43 52 Q50 56 57 52" fill="none" stroke="#c2593b" stroke-width="1.6" '
        f'stroke-linecap="round"/>'
        f'<path class="examiner-avatar-mouth-shape examiner-avatar-mouth--half" '
        f'd="M43 52 Q50 55 57 52" fill="none" stroke="#c2593b" stroke-width="1.6" '
        f'stroke-linecap="round"/>'
        f'<ellipse class="examiner-avatar-mouth-shape examiner-avatar-mouth--open" cx="50" cy="53" '
        f'rx="4.5" ry="3" fill="#c2593b"/>'
        f'<path class="examiner-avatar-mouth-shape examiner-avatar-mouth--smile" '
        f'd="M42 51 Q50 58 58 51" fill="none" stroke="#c2593b" stroke-width="1.6" '
        f'stroke-linecap="round"/>'
        f"</g>"
        f"</g>"
        f"</g>"
        f"</svg>"
        f"</div>"
        f"</div>"
    )


def build_examiner_beside_row_html(
    slot: str,
    body_html: str,
    *,
    avatar_html: str = "",
    row_modifier: str = "",
) -> str:
    """Flex row: optional avatar slot + body (question / recording / saved)."""
    slot_key = html.escape(str(slot or "question").strip().lower())
    mod = str(row_modifier or "").strip()
    mod_class = f" {html.escape(mod)}" if mod else ""
    av = str(avatar_html or "")
    body = str(body_html or "")
    return (
        f'<div class="tq-examiner-beside-row tq-examiner-beside-row--{slot_key}{mod_class}">'
        f'<div class="examiner-avatar-slot examiner-avatar-slot--{slot_key}">{av}</div>'
        f'<div class="tq-examiner-beside-row__body">{body}</div>'
        f"</div>"
    )


def render_examiner_avatar(
    mode: str,
    *,
    size: int = 120,
    has_tts: bool = False,
) -> None:
    block = build_examiner_avatar_html(mode, size=size, has_tts=has_tts)
    st.markdown("".join(line.strip() for line in block.splitlines()), unsafe_allow_html=True)


def render_examiner_avatar_safe(
    mode: str,
    *,
    size: int = 120,
    has_tts: bool = False,
) -> None:
    try:
        render_examiner_avatar(mode, size=size, has_tts=has_tts)
    except Exception:
        logger.exception("[EXAMINER_AVATAR] render failed mode=%s", mode)


def render_examiner_avatar_observer() -> None:
    """Sync avatar mode + move host between question/recording slots on parent DOM."""
    components.html(
        """
        <script>
        (function () {
          var POLL_MS = 280;
          var STOP_HINT = "녹음 완료";
          var TTS_HINT_MS = 3500;
          var NOD_IDLE_MS = 1600;
          var timer = null;
          var ttsHintTimer = null;

          function parentDoc() {
            try {
              if (window.parent && window.parent.document) {
                return window.parent.document;
              }
            } catch (e) { /* cross-origin */ }
            return null;
          }

          function findAvatar(doc) {
            return doc.querySelector(".examiner-avatar");
          }

          function findAvatarHost(doc) {
            return doc.querySelector(".examiner-avatar-host");
          }

          function baseMode(av) {
            return (av.getAttribute("data-base-mode") || "idle").trim() || "idle";
          }

          function setMode(av, mode) {
            if (!av) return;
            av.setAttribute("data-mode", mode || "idle");
          }

          function restoreBase(av) {
            if (!av) return;
            setMode(av, baseMode(av));
          }

          function slotEl(doc, name) {
            return doc.querySelector(".examiner-avatar-slot--" + name);
          }

          function moveHostToSlot(doc, slotName) {
            try {
              var host = findAvatarHost(doc);
              var slot = slotEl(doc, slotName);
              if (!host || !slot) return;
              if (host.parentElement !== slot) {
                slot.appendChild(host);
              }
            } catch (e) { /* ignore */ }
          }

          function pickQuestionSlot(doc) {
            if (slotEl(doc, "saved")) return "saved";
            if (micShowsRecording(doc) && slotEl(doc, "recording")) return "recording";
            if (slotEl(doc, "question")) return "question";
            if (slotEl(doc, "recording")) return "recording";
            return "";
          }

          function anyListenAudioPlaying(doc) {
            try {
              var audios = doc.querySelectorAll("audio");
              for (var i = 0; i < audios.length; i++) {
                var a = audios[i];
                if (!a || a.paused || a.ended) continue;
                if (a.currentTime > 0 || !a.paused) return true;
              }
            } catch (e) { /* ignore */ }
            return false;
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

          function scheduleTtsHint(av) {
            if (!av || av.getAttribute("data-hint-tts") !== "1") return;
            if (baseMode(av) !== "speaking") return;
            if (ttsHintTimer) clearTimeout(ttsHintTimer);
            setMode(av, "speaking");
            ttsHintTimer = setTimeout(function () {
              try {
                var doc = parentDoc();
                if (!doc) return;
                var node = findAvatar(doc);
                if (!node) return;
                if (micShowsRecording(doc) || anyListenAudioPlaying(doc)) return;
                if (baseMode(node) === "speaking") restoreBase(node);
              } catch (e) { /* ignore */ }
            }, TTS_HINT_MS);
          }

          function scheduleNodIdle(av) {
            if (!av || av._nodIdleScheduled) return;
            if (baseMode(av) !== "nodding") return;
            av._nodIdleScheduled = true;
            setTimeout(function () {
              try {
                if (baseMode(av) === "nodding") setMode(av, "idle");
              } catch (e) { /* ignore */ }
            }, NOD_IDLE_MS);
          }

          function bindAudioListeners(doc) {
            try {
              var audios = doc.querySelectorAll("audio");
              for (var i = 0; i < audios.length; i++) {
                var a = audios[i];
                if (!a || a._eaBound) continue;
                a._eaBound = true;
                a.addEventListener("play", function () {
                  var d = parentDoc();
                  if (!d) return;
                  var av = findAvatar(d);
                  if (av) setMode(av, "speaking");
                });
                a.addEventListener("pause", function () {
                  var d = parentDoc();
                  if (!d) return;
                  var av = findAvatar(d);
                  if (!av || micShowsRecording(d)) return;
                  restoreBase(av);
                });
                a.addEventListener("ended", function () {
                  var d = parentDoc();
                  if (!d) return;
                  var av = findAvatar(d);
                  if (!av || micShowsRecording(d)) return;
                  restoreBase(av);
                });
              }
            } catch (e) { /* ignore */ }
          }

          function tick() {
            try {
              var doc = parentDoc();
              if (!doc || !doc.querySelector(".tq-screen-marker, .mx-marker")) return;
              var av = findAvatar(doc);
              if (!av) return;
              bindAudioListeners(doc);
              var slotName = pickQuestionSlot(doc);
              if (slotName) moveHostToSlot(doc, slotName);
              if (micShowsRecording(doc)) {
                setMode(av, "listening");
                return;
              }
              if (anyListenAudioPlaying(doc)) {
                setMode(av, "speaking");
                return;
              }
              if (baseMode(av) === "nodding") {
                setMode(av, "nodding");
                scheduleNodIdle(av);
                return;
              }
              restoreBase(av);
            } catch (e) { /* ignore */ }
          }

          function start() {
            if (timer) clearInterval(timer);
            tick();
            try {
              var doc = parentDoc();
              if (doc) {
                var av = findAvatar(doc);
                if (av) {
                  scheduleTtsHint(av);
                  scheduleNodIdle(av);
                }
              }
            } catch (e) { /* ignore */ }
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


def _ss_get(ss: Any, key: str, default: Any = None) -> Any:
    if ss is None:
        return default
    try:
        return ss.get(key, default)
    except Exception:
        return default


def resolve_topic_v2_avatar_mode(
    ss: Mapping[str, Any],
    *,
    phase: str = "question",
    has_tts: bool = False,
    flow: str = "topic_v2",
) -> str:
    step = str(_ss_get(ss, "topic_v2_step") or "").strip()
    if phase == "saved" or step == "saved":
        return "nodding"
    if bool(_ss_get(ss, "topic_v2_stt_in_flight")):
        return "listening"
    if step == "question":
        if str(flow or "").strip().lower() == "keyword_constraint":
            return "speaking"
        return "speaking" if has_tts else "idle"
    return "idle"


def resolve_mock_v2_avatar_mode(
    ss: Mapping[str, Any],
    *,
    phase: str = "question",
    has_tts: bool = False,
) -> str:
    step = str(_ss_get(ss, "mock_v2_step") or "").strip()
    if phase == "saved" or step == "saved":
        return "nodding"
    if bool(_ss_get(ss, "_mock_v2_stt_in_flight")):
        return "listening"
    if step == "question":
        return "speaking" if has_tts else "idle"
    return "idle"


def resolve_mini_mock_v2_avatar_mode(
    ss: Mapping[str, Any],
    *,
    phase: str = "question",
) -> str:
    step = str(_ss_get(ss, "mini_v2_step") or "").strip()
    if phase == "saved" or step == "saved":
        return "nodding"
    if bool(_ss_get(ss, "_mini_v2_stt_in_flight")):
        return "listening"
    if step in ("question", "recording"):
        return "idle"
    return "idle"


def _resolve_avatar_mode(
    ss: Mapping[str, Any],
    *,
    flow: str,
    phase: str = "question",
    has_tts: bool = False,
) -> tuple[str, bool]:
    flow_key = str(flow or "").strip().lower()
    if flow_key in ("topic_v2", "keyword_constraint"):
        mode = resolve_topic_v2_avatar_mode(
            ss, phase=phase, has_tts=has_tts, flow=flow_key
        )
        tts_hint = has_tts or (
            flow_key == "keyword_constraint" and phase == "question"
        )
    elif flow_key == "mock_v2":
        mode = resolve_mock_v2_avatar_mode(ss, phase=phase, has_tts=has_tts)
        tts_hint = has_tts
    elif flow_key == "mini_mock_v2":
        mode = resolve_mini_mock_v2_avatar_mode(ss, phase=phase)
        tts_hint = False
    else:
        mode = "idle"
        tts_hint = False
    return mode, tts_hint


def render_practice_examiner_question_sections(
    ss: Mapping[str, Any],
    *,
    flow: str,
    header_html: str,
    question_card_html: str,
    answer_card_html: str,
    has_tts: bool = False,
    size: int = 100,
) -> None:
    """Question screen: avatar beside question card; empty recording slot for JS move."""
    mode, tts_hint = _resolve_avatar_mode(
        ss, flow=flow, phase="question", has_tts=has_tts
    )
    try:
        avatar = build_examiner_avatar_html(mode, size=size, has_tts=tts_hint)
        q_row = build_examiner_beside_row_html(
            "question", question_card_html, avatar_html=avatar
        )
        r_row = build_examiner_beside_row_html("recording", answer_card_html)
        block = str(header_html or "") + q_row + r_row
        st.markdown(
            "".join(line.strip() for line in block.splitlines()),
            unsafe_allow_html=True,
        )
        render_examiner_avatar_observer()
    except Exception:
        logger.exception("[EXAMINER_AVATAR] question sections failed flow=%s", flow)
        try:
            fallback = (
                str(header_html or "")
                + str(question_card_html or "")
                + str(answer_card_html or "")
            )
            st.markdown(fallback, unsafe_allow_html=True)
        except Exception:
            logger.exception("[EXAMINER_AVATAR] question fallback failed flow=%s", flow)


def render_practice_examiner_saved_beside(
    ss: Mapping[str, Any],
    *,
    flow: str,
    size: int = 90,
) -> None:
    """Saved screen: nodding avatar beside replay area (pair with st.columns)."""
    mode, tts_hint = _resolve_avatar_mode(ss, flow=flow, phase="saved")
    render_examiner_avatar_safe(mode, size=size, has_tts=tts_hint)
    render_examiner_avatar_observer()


def render_practice_examiner_avatar(
    ss: Mapping[str, Any],
    *,
    flow: str,
    phase: str = "question",
    has_tts: bool = False,
    size: int = 100,
) -> None:
    """Standalone avatar (saved column)."""
    mode, tts_hint = _resolve_avatar_mode(
        ss, flow=flow, phase=phase, has_tts=has_tts
    )
    render_examiner_avatar_safe(mode, size=size, has_tts=tts_hint)
    if phase in ("question", "saved"):
        render_examiner_avatar_observer()
