"""Exam audio players — question listen (play limit) and recording playback (unlimited)."""

from __future__ import annotations

import base64
import html as html_module
import json
import re

import streamlit.components.v1 as components

from utils.audio_utils import mime_from_audio_format

_ACCENT_HEX: dict[str, str] = {
    "teal": "#0F6E56",
    "blue": "#185FA5",
    "purple": "#534AB7",
    "pink": "#993556",
    "amber": "#854F0B",
    "coral": "#993C1D",
}

_PLAY_SVG = (
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="#ffffff" aria-hidden="true">'
    '<path d="M8 5v14l11-7z"/></svg>'
)
_PAUSE_SVG = (
    '<svg viewBox="0 0 24 24" width="14" height="14" fill="#ffffff" aria-hidden="true">'
    '<path d="M6 5h4v14H6zm8 0h4v14h-4z"/></svg>'
)
_SPEAKER_SVG = (
    '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" '
    'stroke="#0F6E56" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M11 5L6 9H2v6h4l5 4V5z"/>'
    '<path d="M15.54 8.46a5 5 0 010 7.07"/>'
    '<path d="M19.07 4.93a10 10 0 010 14.14"/>'
    "</svg>"
)


def _resolve_accent_hex(accent: str) -> str:
    key = re.sub(r"[^a-z]", "", str(accent or "teal").strip().lower())
    return _ACCENT_HEX.get(key, _ACCENT_HEX["teal"])


def _safe_player_dom_id(player_id: str) -> str:
    raw = re.sub(r"[^a-zA-Z0-9_-]", "_", str(player_id or "recording").strip())
    return f"rec_{raw}"[:96]


def render_exam_question_audio_player(
    audio_bytes: bytes,
    audio_format: str,
    listen_nonce: str,
    q_id: int,
    max_plays: int = 2,
    accent: str = "teal",
) -> None:
    if not audio_bytes or len(audio_bytes) < 64:
        return
    mime = mime_from_audio_format(audio_format)
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    src = f"data:{mime};base64,{b64}"
    uid = f"exam_aud_{q_id}_{abs(hash(listen_nonce)) % (10**8)}"
    accent_hex = _resolve_accent_hex(accent)
    nonce_js = json.dumps(str(listen_nonce))
    qid_js = json.dumps(int(q_id))
    max_js = json.dumps(int(max_plays))

    components.html(
        f"""
        <style>
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: transparent;
          }}
          .opic-listen-wrap {{
            width: 100%;
            margin: 0 0 14px 0;
          }}
          .opic-listen-player {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 14px;
            border-radius: 999px;
            border: 0.5px solid rgba(17, 24, 39, 0.08);
            background: #FAFAF9;
            cursor: pointer;
            width: auto;
            max-width: 100%;
            font: inherit;
            text-align: left;
          }}
          .opic-listen-player:disabled {{
            opacity: 0.55;
            cursor: not-allowed;
          }}
          .opic-listen-ico {{
            flex-shrink: 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            line-height: 0;
          }}
          .opic-listen-label {{
            font-size: 13px;
            font-weight: 500;
            color: #444441;
            line-height: 1.3;
            white-space: nowrap;
          }}
          .opic-listen-hint {{
            font-size: 12px;
            color: #888780;
            line-height: 1.35;
            white-space: nowrap;
          }}
          .opic-listen-time {{
            display: none;
          }}
        </style>
        <div class="opic-listen-wrap">
          <audio id="{uid}" preload="metadata" src="{src}" style="display:none"></audio>
          <button type="button" class="opic-listen-player" id="{uid}_btn" aria-label="질문 듣기 재생">
            <span class="opic-listen-ico">{_SPEAKER_SVG}</span>
            <span class="opic-listen-label">질문 듣기</span>
            <span class="opic-listen-hint" id="{uid}_hint"></span>
          </button>
          <div class="opic-listen-time" id="{uid}_time" aria-hidden="true">0:00</div>
        </div>
        <script>
        (function() {{
          const audio = document.getElementById("{uid}");
          const btn = document.getElementById("{uid}_btn");
          const hint = document.getElementById("{uid}_hint");
          const timeEl = document.getElementById("{uid}_time");
          const storageKey = "opic_listen_" + {nonce_js} + "_" + {qid_js};
          const maxPlays = {max_js};
          const playIcon = {json.dumps(_PLAY_SVG)};
          const pauseIcon = {json.dumps(_PAUSE_SVG)};
          let isPlaying = false;

          function pad2(n) {{
            return String(Math.floor(n)).padStart(2, "0");
          }}

          function formatSec(sec) {{
            if (!isFinite(sec) || sec < 0) return "0:00";
            const s = Math.floor(sec);
            const m = Math.floor(s / 60);
            return m + ":" + pad2(s % 60);
          }}

          function playCount() {{
            return parseInt(sessionStorage.getItem(storageKey) || "0", 10);
          }}

          function isExhausted() {{
            return playCount() >= maxPlays;
          }}

          function syncHint() {{
            const n = playCount();
            if (n >= maxPlays) {{
              hint.textContent = "재생 한도 도달";
            }} else {{
              hint.textContent = "남은 " + (maxPlays - n) + "회";
            }}
          }}

          function syncBtn() {{
            if (isExhausted()) {{
              btn.disabled = true;
              isPlaying = false;
              btn.setAttribute("aria-pressed", "false");
              return;
            }}
            btn.disabled = false;
            btn.setAttribute("aria-pressed", isPlaying ? "true" : "false");
          }}

          function syncTime() {{
            const dur = audio.duration;
            if (isPlaying && isFinite(dur) && dur > 0) {{
              timeEl.textContent = formatSec(audio.currentTime) + " / " + formatSec(dur);
            }} else if (isFinite(dur) && dur > 0) {{
              timeEl.textContent = formatSec(dur);
            }} else {{
              timeEl.textContent = "0:00";
            }}
          }}

          function refresh() {{
            syncHint();
            syncBtn();
            syncTime();
          }}

          btn.addEventListener("click", function() {{
            if (btn.disabled || isExhausted()) return;
            if (isPlaying) {{
              audio.pause();
              return;
            }}
            const p = audio.play();
            if (p && typeof p.catch === "function") {{
              p.catch(function() {{}});
            }}
          }});

          audio.addEventListener("play", function() {{
            let n = playCount();
            if (n >= maxPlays) {{
              audio.pause();
              audio.currentTime = 0;
              isPlaying = false;
              refresh();
              return;
            }}
            n += 1;
            sessionStorage.setItem(storageKey, String(n));
            isPlaying = true;
            refresh();
          }}, true);

          audio.addEventListener("pause", function() {{
            isPlaying = false;
            refresh();
          }});
          audio.addEventListener("ended", function() {{
            isPlaying = false;
            refresh();
          }});
          audio.addEventListener("loadedmetadata", syncTime);
          audio.addEventListener("timeupdate", syncTime);

          refresh();
        }})();
        </script>
        """,
        height=68,
    )


def render_recording_playback_player(
    audio_bytes: bytes,
    audio_format: str,
    player_id: str,
    *,
    accent: str = "teal",
    label: str = "",
    show_progress: bool = True,
) -> None:
    """Unlimited student recording playback — ▶/⏸, seek bar, elapsed / duration."""
    if not audio_bytes or len(audio_bytes) < 64:
        return
    mime = mime_from_audio_format(audio_format)
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    src = f"data:{mime};base64,{b64}"
    uid = _safe_player_dom_id(player_id)
    accent_hex = _resolve_accent_hex(accent)
    label_html = ""
    label_s = str(label or "").strip()
    if label_s:
        label_html = f'<div class="opic-rec-label">{html_module.escape(label_s)}</div>'

    progress_html = ""
    progress_script = ""
    if show_progress:
        progress_html = (
            f'<input type="range" class="opic-rec-seek" id="{uid}_seek" '
            f'min="0" max="1000" value="0" step="1" '
            f'aria-label="재생 위치" />'
        )
        progress_script = """
          const seek = document.getElementById("{uid}_seek");
          let seekDragging = false;

          seek.addEventListener("input", function() {
            seekDragging = true;
            const dur = audio.duration;
            if (isFinite(dur) && dur > 0) {
              audio.currentTime = (parseFloat(seek.value) / 1000) * dur;
              syncTime();
            }
          });
          seek.addEventListener("change", function() {
            seekDragging = false;
          });
          seek.addEventListener("pointerdown", function() { seekDragging = true; });
          seek.addEventListener("pointerup", function() { seekDragging = false; });

          function syncSeek() {
            const dur = audio.duration;
            if (!seek || seekDragging) return;
            if (isFinite(dur) && dur > 0) {
              seek.max = "1000";
              seek.value = String(Math.round((audio.currentTime / dur) * 1000));
            } else {
              seek.value = "0";
            }
          }
        """.replace("{uid}", uid)
    else:
        progress_script = "function syncSeek() {}"

    components.html(
        f"""
        <style>
          * {{ box-sizing: border-box; }}
          body {{
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: transparent;
          }}
          .opic-rec-wrap {{
            width: 100%;
          }}
          .opic-rec-player {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 4px 2px 2px 2px;
          }}
          .opic-rec-btn {{
            flex-shrink: 0;
            width: 36px;
            height: 36px;
            border: none;
            border-radius: 50%;
            background: {accent_hex};
            color: #ffffff;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0;
            line-height: 1;
          }}
          .opic-rec-btn:disabled {{
            background: #d1d5db !important;
            cursor: not-allowed;
          }}
          .opic-rec-main {{
            flex: 1 1 auto;
            min-width: 0;
            display: flex;
            flex-direction: column;
            gap: 6px;
          }}
          .opic-rec-label {{
            font-size: 13px;
            font-weight: 600;
            color: #0f172a;
            line-height: 1.3;
          }}
          .opic-rec-seek {{
            width: 100%;
            height: 4px;
            margin: 0;
            padding: 0;
            -webkit-appearance: none;
            appearance: none;
            background: rgba(17, 24, 39, 0.10);
            border-radius: 999px;
            outline: none;
            cursor: pointer;
          }}
          .opic-rec-seek::-webkit-slider-thumb {{
            -webkit-appearance: none;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: {accent_hex};
            border: 2px solid #ffffff;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.18);
          }}
          .opic-rec-seek::-moz-range-thumb {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: {accent_hex};
            border: 2px solid #ffffff;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.18);
          }}
          .opic-rec-time {{
            font-size: 11px;
            color: #6b7280;
            line-height: 1.3;
            white-space: nowrap;
            text-align: right;
          }}
        </style>
        <div class="opic-rec-wrap">
          <audio id="{uid}" preload="metadata" src="{src}" style="display:none"></audio>
          <div class="opic-rec-player">
            <button type="button" class="opic-rec-btn" id="{uid}_btn" aria-label="녹음 재생">
              {_PLAY_SVG}
            </button>
            <div class="opic-rec-main">
              {label_html}
              {progress_html}
              <div class="opic-rec-time" id="{uid}_time">0:00 / 0:00</div>
            </div>
          </div>
        </div>
        <script>
        (function() {{
          const audio = document.getElementById("{uid}");
          const btn = document.getElementById("{uid}_btn");
          const timeEl = document.getElementById("{uid}_time");
          const playIcon = {json.dumps(_PLAY_SVG)};
          const pauseIcon = {json.dumps(_PAUSE_SVG)};
          let isPlaying = false;

          {progress_script}

          function pad2(n) {{
            return String(Math.floor(n)).padStart(2, "0");
          }}

          function formatSec(sec) {{
            if (!isFinite(sec) || sec < 0) return "0:00";
            const s = Math.floor(sec);
            const m = Math.floor(s / 60);
            return m + ":" + pad2(s % 60);
          }}

          function syncTime() {{
            const dur = audio.duration;
            if (isFinite(dur) && dur > 0) {{
              timeEl.textContent =
                formatSec(audio.currentTime) + " / " + formatSec(dur);
            }} else {{
              timeEl.textContent = "0:00 / 0:00";
            }}
            syncSeek();
          }}

          function syncBtn() {{
            btn.innerHTML = isPlaying ? pauseIcon : playIcon;
          }}

          function refresh() {{
            syncBtn();
            syncTime();
          }}

          btn.addEventListener("click", function() {{
            if (isPlaying) {{
              audio.pause();
              return;
            }}
            const p = audio.play();
            if (p && typeof p.catch === "function") {{
              p.catch(function() {{}});
            }}
          }});

          audio.addEventListener("play", function() {{
            isPlaying = true;
            refresh();
          }});
          audio.addEventListener("pause", function() {{
            isPlaying = false;
            refresh();
          }});
          audio.addEventListener("ended", function() {{
            isPlaying = false;
            refresh();
          }});
          audio.addEventListener("loadedmetadata", syncTime);
          audio.addEventListener("timeupdate", syncTime);

          refresh();
        }})();
        </script>
        """,
        height=88 if show_progress else 68,
    )
