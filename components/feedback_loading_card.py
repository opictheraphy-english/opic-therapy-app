"""Rotating expression cards shown while AI feedback/report requests run."""

from __future__ import annotations

import html
import json
import random
import re
import uuid
from typing import Dict, List

import streamlit as st

from data.keyword_constraint_sets import KEYWORD_CONSTRAINT_SETS

_CARD_ROTATE_MS = 4500
_FADE_MS = 400
_SAMPLE_MIN = 5
_SAMPLE_MAX = 8


def _flatten_target_expressions() -> List[Dict[str, str]]:
    """Flatten all combo target_expressions; dedupe by expr (first ko wins)."""
    by_expr: Dict[str, Dict[str, str]] = {}
    for entry in KEYWORD_CONSTRAINT_SETS:
        if not isinstance(entry, dict):
            continue
        combos = entry.get("combos")
        if not isinstance(combos, list):
            continue
        for combo in combos:
            if not isinstance(combo, dict):
                continue
            targets = combo.get("target_expressions")
            if not isinstance(targets, list):
                continue
            for raw in targets:
                if isinstance(raw, dict):
                    expr = str(raw.get("expr") or "").strip()
                    ko = str(raw.get("ko") or "").strip()
                else:
                    expr = str(raw or "").strip()
                    ko = ""
                if not expr or expr in by_expr:
                    continue
                by_expr[expr] = {"expr": expr, "ko": ko}
    return list(by_expr.values())


_FLAT_TARGET_EXPRESSIONS: List[Dict[str, str]] = _flatten_target_expressions()


def _pick_sample_expressions() -> List[Dict[str, str]]:
    pool = _FLAT_TARGET_EXPRESSIONS
    if not pool:
        return [{"expr": "I tend to", "ko": "보통 ~한다"}]
    upper = min(len(pool), _SAMPLE_MAX)
    lower = min(_SAMPLE_MIN, upper)
    count = random.randint(lower, upper) if upper > lower else upper
    return random.sample(pool, count)


def _normalize_html_one_line(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _build_card_html(*, card_id: str, message: str, expressions: List[Dict[str, str]]) -> str:
    first = expressions[0] if expressions else {"expr": "I tend to", "ko": "보통 ~한다"}
    expr_esc = html.escape(str(first.get("expr") or ""))
    ko_esc = html.escape(str(first.get("ko") or ""))
    msg_esc = html.escape(message)
    items_json = json.dumps(expressions, ensure_ascii=False)
    fade_ms = int(_FADE_MS)
    rotate_ms = int(_CARD_ROTATE_MS)
    return f"""<div id="{card_id}" class="opic-fb-loading" role="status" aria-live="polite" aria-atomic="true"><style>#{card_id}{{border-radius:16px;background:linear-gradient(180deg,#f8fafc 0%,#f1f5f9 100%);border:1px solid #e2e8f0;padding:20px 18px 16px;margin:12px 0 16px;text-align:center;box-shadow:0 1px 3px rgba(15,23,42,.06);}}#{card_id} .opic-fb-loading-eyebrow{{font-size:12px;font-weight:700;letter-spacing:.04em;color:#64748b;margin:0 0 8px;text-transform:none;}}#{card_id} .opic-fb-loading-msg{{font-size:14px;color:#334155;margin:0 0 14px;line-height:1.45;}}#{card_id} .opic-fb-loading-expr-wrap{{transition:opacity {fade_ms}ms ease;opacity:1;min-height:72px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;}}#{card_id} .opic-fb-loading-expr{{font-size:22px;font-weight:700;color:#0f172a;line-height:1.3;margin:0;}}#{card_id} .opic-fb-loading-ko{{font-size:14px;color:#475569;line-height:1.4;margin:0;}}#{card_id} .opic-fb-loading-dots{{display:flex;justify-content:center;gap:6px;margin-top:14px;}}#{card_id} .opic-fb-loading-dots span{{width:7px;height:7px;border-radius:50%;background:#94a3b8;display:inline-block;animation:opic-fb-dot-{card_id} 1.2s infinite ease-in-out both;}}#{card_id} .opic-fb-loading-dots span:nth-child(1){{animation-delay:-0.24s;}}#{card_id} .opic-fb-loading-dots span:nth-child(2){{animation-delay:-0.12s;}}@keyframes opic-fb-dot-{card_id}{{0%,80%,100%{{transform:scale(.65);opacity:.45;}}40%{{transform:scale(1);opacity:1;}}}}</style><p class="opic-fb-loading-eyebrow">오늘의 표현</p><p class="opic-fb-loading-msg">{msg_esc}</p><div class="opic-fb-loading-expr-wrap"><p class="opic-fb-loading-expr">{expr_esc}</p><p class="opic-fb-loading-ko">{ko_esc}</p></div><div class="opic-fb-loading-dots" aria-hidden="true"><span></span><span></span><span></span></div></div><script>(function(){{var ROOT_ID={json.dumps(card_id)};var ITEMS={items_json};var ROTATE_MS={rotate_ms};var FADE_MS={fade_ms};var idx=0;var timer=null;var root=document.getElementById(ROOT_ID);if(!root||!ITEMS||!ITEMS.length)return;var wrap=root.querySelector(".opic-fb-loading-expr-wrap");var exprEl=root.querySelector(".opic-fb-loading-expr");var koEl=root.querySelector(".opic-fb-loading-ko");if(!wrap||!exprEl||!koEl)return;function showAt(i){{if(!ITEMS.length)return;var item=ITEMS[i]||ITEMS[0];wrap.style.opacity="0";window.setTimeout(function(){{exprEl.textContent=item.expr||"";koEl.textContent=item.ko||"";wrap.style.opacity="1";}},FADE_MS);}}function tick(){{if(ITEMS.length<2)return;idx=(idx+1)%ITEMS.length;showAt(idx);}}function start(){{if(timer)window.clearInterval(timer);if(ITEMS.length>1){{timer=window.setInterval(tick,ROTATE_MS);}}}}if(document.readyState==="loading"){{document.addEventListener("DOMContentLoaded",start);}}else{{start();}}}})();</script>"""


def render_feedback_loading_card(
    *,
    message: str = "AI가 답변을 분석하고 있어요",
) -> None:
    """Render a client-side rotating expression card (no server reruns)."""
    card_id = f"opic-fb-loading-{uuid.uuid4().hex[:10]}"
    expressions = _pick_sample_expressions()
    block = _build_card_html(
        card_id=card_id,
        message=(message or "AI가 답변을 분석하고 있어요").strip(),
        expressions=expressions,
    )
    st.markdown(_normalize_html_one_line(block), unsafe_allow_html=True)
