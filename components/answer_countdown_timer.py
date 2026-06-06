"""
Client-side answer countdown timer for V2 exam flows.

Countdown runs entirely in the browser (no Streamlit rerun per second).
When time reaches zero, JS clicks the mic stop button; if recording does not
stop, a query-param fallback (`atimeup`) triggers Streamlit to commit/advance.
"""

from __future__ import annotations

import html
import json
import re
from typing import Any

import streamlit as st
import streamlit.components.v1 as components

QUERY_PARAM = "atimeup"
DEFAULT_DURATION_SEC = 120
DEFAULT_WARN_SEC = 30
_STOP_HINT = "녹음 완료"
_START_HINT = "답변 시작"


def build_answer_timer_id(flow: str, *parts: str) -> str:
    """Build a URL-safe timer id scoped to one question attempt."""
    flow_safe = re.sub(r"[^a-zA-Z0-9_-]", "_", str(flow or "").strip())[:32] or "flow"
    safe_parts: list[str] = []
    for part in parts:
        s = re.sub(r"[^a-zA-Z0-9_-]", "_", str(part or "").strip())[:48]
        safe_parts.append(s or "x")
    return f"{flow_safe}__{'__'.join(safe_parts)}"


def _guard_key(timer_id: str) -> str:
    return f"_answer_timer_up_done_{timer_id}"


def dismiss_answer_timer_signal(timer_id: str) -> None:
    """Clear time-up signal after a normal manual recording complete."""
    st.session_state.pop(_guard_key(timer_id), None)
    try:
        if st.query_params.get(QUERY_PARAM) == timer_id:
            del st.query_params[QUERY_PARAM]
    except Exception:
        pass


def consume_answer_timer_time_up(timer_id: str) -> bool:
    """
    Return True once when the browser reported timer expiry for ``timer_id``.

    Clears the query param and sets a session guard to prevent double handling.
    """
    tid = (timer_id or "").strip()
    if not tid:
        return False
    if st.session_state.get(_guard_key(tid)):
        return False
    try:
        qp = st.query_params.get(QUERY_PARAM)
    except Exception:
        qp = None
    if qp != tid:
        return False
    try:
        del st.query_params[QUERY_PARAM]
    except Exception:
        pass
    st.session_state[_guard_key(tid)] = True
    return True


def _format_mm_ss(total_sec: int) -> str:
    s = max(0, int(total_sec))
    return f"{s // 60}:{s % 60:02d}"


def _timer_shell_html(
    timer_id: str,
    *,
    accent: str,
    duration_sec: int,
) -> str:
    accent_norm = re.sub(r"[^a-z]", "", str(accent or "teal").lower()) or "teal"
    if accent_norm not in {"teal", "blue", "purple", "pink", "amber", "coral"}:
        accent_norm = "teal"
    tid = html.escape(timer_id)
    time_display = html.escape(_format_mm_ss(duration_sec))
    return f"""
<div id="opic-answer-timer-{tid}"
     class="opic-answer-timer mx-rec-timer mx-answer-timer mx-rec-timer--idle mx-answer-timer--accent-{accent_norm}"
     data-timer-id="{tid}"
     data-duration="{int(duration_sec)}"
     role="timer"
     aria-live="polite"
     aria-atomic="true">
  <div class="mx-answer-timer-head">
    <p class="mx-rec-timer-label mx-answer-timer-label">답변 시간</p>
    <span class="mx-answer-timer-status mx-answer-timer-status--idle opic-answer-timer-status">대기 중</span>
  </div>
  <p class="mx-rec-timer-value mx-answer-timer-value opic-answer-timer-value">{time_display}</p>
  <div class="mx-rec-timer-progress mx-answer-timer-bar" aria-hidden="true">
    <span class="mx-rec-timer-progress-fill mx-answer-timer-bar-fill opic-answer-timer-fill" style="width:100%;"></span>
  </div>
</div>
"""


def _timer_controller_js(
    timer_id: str,
    *,
    duration_sec: int,
    warn_sec: int,
) -> str:
    cfg = json.dumps(
        {
            "timerId": timer_id,
            "durationSec": int(duration_sec),
            "warnSec": int(warn_sec),
            "queryParam": QUERY_PARAM,
            "stopHint": _STOP_HINT,
            "startHint": _START_HINT,
        }
    )
    return f"""
<script>
(function () {{
  var CFG = {cfg};
  var POLL_MS = 250;
  var pollTimer = null;
  var countdownTimer = null;
  var remaining = CFG.durationSec;
  var running = false;
  var fired = false;
  var manualDone = false;

  function parentDoc() {{
    try {{
      if (window.parent && window.parent.document) return window.parent.document;
    }} catch (e) {{}}
    return null;
  }}

  function timerEl(doc) {{
    if (!doc) return null;
    return doc.getElementById("opic-answer-timer-" + CFG.timerId);
  }}

  function findMicIframe(doc) {{
    try {{
      var ifr = doc.querySelector('iframe[src*="streamlit_mic_recorder"]');
      if (ifr) return ifr;
      var hosts = doc.querySelectorAll(
        '[data-testid="stCustomComponentV1"], [data-testid="stCustomComponent"]'
      );
      for (var i = 0; i < hosts.length; i++) {{
        var inner = hosts[i].querySelector("iframe");
        if (!inner) continue;
        var src = inner.getAttribute("src") || "";
        if (src.indexOf("streamlit_mic_recorder") >= 0) return inner;
      }}
    }} catch (e) {{}}
    return null;
  }}

  function micButton(doc) {{
    try {{
      var ifr = findMicIframe(doc);
      if (!ifr || !ifr.contentDocument) return null;
      return ifr.contentDocument.querySelector("button");
    }} catch (e) {{}}
    return null;
  }}

  function micShowsRecording(doc) {{
    var btn = micButton(doc);
    if (!btn) return false;
    var text = (btn.innerText || btn.textContent || "").trim();
    return text.indexOf(CFG.stopHint) >= 0;
  }}

  function clickMicStop(doc) {{
    var btn = micButton(doc);
    if (!btn) return false;
    var text = (btn.innerText || btn.textContent || "").trim();
    if (text.indexOf(CFG.stopHint) < 0) return false;
    try {{
      btn.click();
      return true;
    }} catch (e) {{
      return false;
    }}
  }}

  function formatTime(sec) {{
    var s = Math.max(0, Math.floor(sec));
    var m = Math.floor(s / 60);
    var r = s % 60;
    return m + ":" + (r < 10 ? "0" : "") + r;
  }}

  function stateFor(rem, active) {{
    if (!active) return "idle";
    if (rem <= 0) return "up";
    if (rem <= CFG.warnSec) return "warn";
    return "normal";
  }}

  function statusLabel(active, state) {{
    if (!active) return "대기 중";
    if (state === "up") return "시간 종료";
    return "녹음 중";
  }}

  function paint(doc, rem, active) {{
    var el = timerEl(doc);
    if (!el) return;
    var state = stateFor(rem, active);
    el.classList.remove("mx-rec-timer--idle", "mx-rec-timer--normal", "mx-rec-timer--warn", "mx-rec-timer--up");
    el.classList.add("mx-rec-timer--" + state);
    var val = el.querySelector(".opic-answer-timer-value");
    if (val) val.textContent = formatTime(rem);
    var fill = el.querySelector(".opic-answer-timer-fill");
    if (fill) {{
      var pct = CFG.durationSec > 0 ? Math.round((rem / CFG.durationSec) * 100) : 0;
      fill.style.width = Math.max(0, Math.min(100, pct)) + "%";
    }}
    var status = el.querySelector(".opic-answer-timer-status");
    if (status) {{
      status.textContent = statusLabel(active, state);
      status.className = "mx-answer-timer-status opic-answer-timer-status mx-answer-timer-status--" + state;
    }}
  }}

  function stopCountdown(resetIdle) {{
    if (countdownTimer) {{
      clearInterval(countdownTimer);
      countdownTimer = null;
    }}
    running = false;
    if (resetIdle) {{
      remaining = CFG.durationSec;
      var doc = parentDoc();
      paint(doc, remaining, false);
    }}
  }}

  function signalTimeUp() {{
    if (fired || manualDone) return;
    fired = true;
    try {{
      var win = window.parent || window;
      var url = new URL(win.location.href);
      if (url.searchParams.get(CFG.queryParam) === CFG.timerId) return;
      url.searchParams.set(CFG.queryParam, CFG.timerId);
      win.location.href = url.toString();
    }} catch (e) {{}}
  }}

  function onTimeUp(doc) {{
    if (fired || manualDone) return;
    stopCountdown(false);
    paint(doc, 0, true);
    clickMicStop(doc);
    var checks = 0;
    var iv = setInterval(function () {{
      checks += 1;
      var d = parentDoc();
      var stillRec = d && micShowsRecording(d);
      if (!stillRec || checks >= 8) {{
        clearInterval(iv);
        if (stillRec) signalTimeUp();
      }}
    }}, 300);
  }}

  function tickCountdown() {{
    if (!running || manualDone || fired) return;
    remaining -= 1;
    var doc = parentDoc();
    paint(doc, remaining, true);
    if (remaining <= 0) {{
      onTimeUp(doc);
    }}
  }}

  function startCountdown(doc) {{
    if (running || manualDone || fired) return;
    running = true;
    remaining = CFG.durationSec;
    paint(doc, remaining, true);
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = setInterval(tickCountdown, 1000);
  }}

  function pollMic() {{
    try {{
      var doc = parentDoc();
      if (!doc || !doc.querySelector(".tq-screen-marker")) return;
      if (!timerEl(doc)) return;
      var rec = micShowsRecording(doc);
      if (rec && !manualDone && !fired && !running) {{
        startCountdown(doc);
      }} else if (!rec && running && remaining > 0) {{
        manualDone = true;
        stopCountdown(true);
      }}
    }} catch (e) {{}}
  }}

  function boot() {{
    var doc = parentDoc();
    paint(doc, CFG.durationSec, false);
    if (pollTimer) clearInterval(pollTimer);
    pollMic();
    pollTimer = setInterval(pollMic, POLL_MS);
  }}

  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", boot);
  }} else {{
    boot();
  }}
}})();
</script>
"""


def render_answer_countdown_timer(
    *,
    timer_id: str,
    accent: str = "teal",
    duration_sec: int = DEFAULT_DURATION_SEC,
    warn_sec: int = DEFAULT_WARN_SEC,
) -> None:
    """Render idle timer shell + client-side countdown controller."""
    try:
        duration = max(1, int(duration_sec))
    except (TypeError, ValueError):
        duration = DEFAULT_DURATION_SEC
    try:
        warn = max(1, int(warn_sec))
    except (TypeError, ValueError):
        warn = DEFAULT_WARN_SEC

    tid = (timer_id or "").strip()
    if not tid:
        return

    st.markdown(
        _timer_shell_html(tid, accent=accent, duration_sec=duration),
        unsafe_allow_html=True,
    )
    components.html(
        _timer_controller_js(tid, duration_sec=duration, warn_sec=warn),
        height=0,
    )


def handle_answer_timer_expiry(
    timer_id: str,
    *,
    mic_result: Any,
    extract_audio: Any,
    commit_audio: Any,
    commit_empty: Any,
) -> bool:
    """
    Process timer expiry fallback when ``atimeup`` query param is set.

    Returns True if expiry was handled (caller should ``st.rerun()``).
    """
    if mic_result is not None:
        dismiss_answer_timer_signal(timer_id)
        return False
    if not consume_answer_timer_time_up(timer_id):
        return False

    audio_bytes = b""
    mime_type = "audio/webm"
    mic_payload: Any = None
    try:
        extracted = extract_audio()
        if isinstance(extracted, tuple):
            if len(extracted) >= 1:
                audio_bytes = bytes(extracted[0] or b"")
            if len(extracted) >= 2:
                mime_type = str(extracted[1] or mime_type)
            if len(extracted) >= 3:
                mic_payload = extracted[2]
    except Exception:
        audio_bytes = b""

    if len(audio_bytes) > 0:
        commit_audio(audio_bytes, mime_type, mic_payload)
    else:
        commit_empty()
    return True
