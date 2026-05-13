"""Limited-play exam question audio (HTML5 + sessionStorage)."""

from __future__ import annotations

import base64
import json

import streamlit.components.v1 as components

from utils.audio_utils import mime_from_audio_format


def render_exam_question_audio_player(
    audio_bytes: bytes,
    audio_format: str,
    listen_nonce: str,
    q_id: int,
    max_plays: int = 2,
) -> None:
    if not audio_bytes or len(audio_bytes) < 64:
        return
    mime = mime_from_audio_format(audio_format)
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    src = f"data:{mime};base64,{b64}"
    uid = f"exam_aud_{q_id}_{abs(hash(listen_nonce)) % (10**8)}"
    nonce_js = json.dumps(str(listen_nonce))
    qid_js = json.dumps(int(q_id))
    max_js = json.dumps(int(max_plays))

    components.html(
        f"""
        <div>
          <audio id="{uid}" controls preload="metadata" src="{src}"></audio>
          <div id="{uid}_hint" style="font-size:13px;color:#475569;margin-top:6px;"></div>
        </div>
        <script>
        (function() {{
          const audio = document.getElementById("{uid}");
          const hint = document.getElementById("{uid}_hint");
          const storageKey = "opic_listen_" + {nonce_js} + "_" + {qid_js};
          const maxPlays = {max_js};
          function syncHint() {{
            const n = parseInt(sessionStorage.getItem(storageKey) || "0", 10);
            if (n >= maxPlays) {{
              hint.textContent = "재생 한도(" + maxPlays + "회)를 모두 사용했습니다.";
            }} else {{
              hint.textContent = "남은 재생: " + (maxPlays - n) + "회 · 재생(▶) 시작마다 1회 차감";
            }}
          }}
          syncHint();
          audio.addEventListener("play", function () {{
            let n = parseInt(sessionStorage.getItem(storageKey) || "0", 10);
            if (n >= maxPlays) {{
              audio.pause();
              audio.currentTime = 0;
              hint.textContent = "재생 한도(" + maxPlays + "회)를 모두 사용했습니다.";
              try {{
                audio.removeAttribute("src");
                audio.load();
              }} catch (e) {{}}
              audio.controls = false;
              return;
            }}
            n += 1;
            sessionStorage.setItem(storageKey, String(n));
            syncHint();
          }}, true);
        }})();
        </script>
        """,
        height=140,
    )
