"""Live microphone visualizer (single mount per key — avoid duplicate keys on rerun)."""

from __future__ import annotations

import streamlit.components.v1 as components


def render_realtime_visualizer(component_key: str, auto_start: bool = True) -> None:
    auto_flag = "true" if auto_start else "false"
    components.html(
        f"""
        <div id="viz-wrap-{component_key}" style="
            position: relative;
            background: rgba(15,23,42,0.62);
            border-radius: 16px;
            padding: 12px 14px;
            border: 1px solid rgba(148,163,184,0.25);
        ">
          <div style="display:flex;justify-content:space-between;align-items:center;color:#cbd5e1;font-size:12px;margin-bottom:6px;">
            <span>Focus Mode · Live Voice Analyzer</span>
            <span id="viz-state-{component_key}" style="color:#67e8f9;">ready</span>
          </div>
          <canvas id="viz-canvas-{component_key}" width="840" height="92" style="width:100%;height:92px;border-radius:12px;background:rgba(2,6,23,0.7);"></canvas>
          <div id="viz-toast-{component_key}" style="
              display:none; position:absolute; top:10px; right:10px; background:#0f172a;
              color:#bae6fd; border:1px solid #22d3ee; border-radius:10px; padding:8px 10px; font-size:12px;">
              마이크 권한이 필요합니다. 브라우저 권한을 허용해주세요.
          </div>
        </div>
        <script>
        (() => {{
          const key = "{component_key}";
          const autoStart = {auto_flag};
          const canvas = document.getElementById(`viz-canvas-${{key}}`);
          const ctx = canvas.getContext("2d");
          const stateEl = document.getElementById(`viz-state-${{key}}`);
          const toast = document.getElementById(`viz-toast-${{key}}`);
          let audioCtx = null, analyser = null, source = null, stream = null, rafId = null, timeData = null, running = false;
          const showToast = () => {{ toast.style.display = "block"; setTimeout(() => (toast.style.display = "none"), 2800); }};
          const drawIdle = () => {{
            const w = canvas.width, h = canvas.height;
            ctx.clearRect(0,0,w,h); ctx.lineWidth = 2; ctx.strokeStyle = "rgba(45,212,191,0.45)"; ctx.beginPath();
            for (let x = 0; x < w; x++) {{ const y = h/2 + Math.sin(x * 0.02) * 1.8; if (x === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); }}
            ctx.stroke();
          }};
          const render = () => {{
            if (!running || !analyser) return;
            analyser.getByteTimeDomainData(timeData);
            const w = canvas.width, h = canvas.height;
            ctx.clearRect(0, 0, w, h); ctx.fillStyle = "rgba(15,23,42,0.75)"; ctx.fillRect(0,0,w,h);
            ctx.lineWidth = 2.2; ctx.strokeStyle = "#14b8a6"; ctx.shadowColor = "#22d3ee"; ctx.shadowBlur = 10; ctx.beginPath();
            const slice = w / timeData.length; let x = 0;
            for (let i = 0; i < timeData.length; i++) {{
              const v = (timeData[i] - 128) / 128; const y = h / 2 + v * (h * 0.34);
              if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y); x += slice;
            }}
            ctx.stroke(); rafId = requestAnimationFrame(render);
          }};
          const stop = () => {{
            running = false; if (rafId) cancelAnimationFrame(rafId); rafId = null;
            if (source) source.disconnect(); source = null; if (analyser) analyser.disconnect(); analyser = null;
            if (stream) stream.getTracks().forEach(t => t.stop()); stream = null; if (audioCtx) audioCtx.close(); audioCtx = null;
            stateEl.textContent = "idle"; drawIdle();
          }};
          const start = async () => {{
            try {{
              if (running) return;
              stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
              audioCtx = new (window.AudioContext || window.webkitAudioContext)();
              analyser = audioCtx.createAnalyser(); analyser.fftSize = 1024; analyser.smoothingTimeConstant = 0.82;
              timeData = new Uint8Array(analyser.fftSize); source = audioCtx.createMediaStreamSource(stream); source.connect(analyser);
              running = true; stateEl.textContent = "listening"; render();
            }} catch (err) {{ console.error("mic permission/error", err); stateEl.textContent = "permission denied"; showToast(); drawIdle(); }}
          }};
          window.addEventListener("beforeunload", stop);
          document.addEventListener("visibilitychange", () => {{ if (document.hidden) stop(); }});
          drawIdle(); if (autoStart) start(); else stateEl.textContent = "standby";
        }})();
        </script>
        """,
        height=145,
    )
