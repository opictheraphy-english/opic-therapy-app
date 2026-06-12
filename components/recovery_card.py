"""Analysis failure / recovery card — display markup only."""

from __future__ import annotations

import html

from components.brand_character import render_character_svg

ANALYSIS_RECOVERY_EYEBROW = "잠시 연결이 고르지 않아요"
ANALYSIS_RECOVERY_TITLE = "치료사가 잠깐 자리를 비웠어요"
ANALYSIS_RECOVERY_BODY = (
    '방금 답변은 <span class="rv-emphasis">안전하게 보관 중</span>이에요. '
    '재녹음 없이 <span class="rv-emphasis">분석만 다시</span> 받을 수 있어요.'
)

RECOVERY_RETRY_CAPTION = "45초 정도 기다렸다 눌러주시면 성공률이 높아요"


def render_recovery_card_html(
    *,
    eyebrow: str,
    title: str,
    body_html: str,
    meta_html: str = "",
    character_size: int = 96,
    compact: bool = False,
    show_character: bool = True,
) -> str:
    """Two-zone recovery card with optional sorry character."""
    compact_cls = " recovery-card--compact" if compact else ""
    stage = ""
    if show_character:
        char = render_character_svg("sorry", character_size, bg="#ffffff")
        stage = f'<div class="rv-stage">{char}</div>'

    meta_block = meta_html.strip()
    if meta_block and not meta_block.startswith("<"):
        meta_block = f'<div class="rv-meta"><span>{html.escape(meta_block)}</span></div>'
    elif meta_block and not meta_block.startswith("<div"):
        meta_block = f'<div class="rv-meta">{meta_block}</div>'

    body_block = (
        f'<div class="rv-body">{body_html}</div>' if str(body_html or "").strip() else ""
    )

    return f"""
<section class="recovery-card{compact_cls}" role="alert" aria-live="polite">
  {stage}
  <div class="rv-content">
    <p class="rv-eyebrow">{html.escape(eyebrow)}</p>
    <h2 class="rv-title">{html.escape(title)}</h2>
    {body_block}
    {meta_block}
  </div>
</section>
"""


def render_analysis_recovery_card(
    *,
    meta_html: str = "",
    compact: bool = False,
    character_size: int | None = None,
) -> str:
    """Standard analysis-failure copy with sorry character."""
    size = character_size if character_size is not None else (72 if compact else 96)
    return render_recovery_card_html(
        eyebrow=ANALYSIS_RECOVERY_EYEBROW,
        title=ANALYSIS_RECOVERY_TITLE,
        body_html=ANALYSIS_RECOVERY_BODY,
        meta_html=meta_html,
        character_size=size,
        compact=compact,
    )


def render_recovery_retry_caption_html() -> str:
    return f'<p class="rv-retry-caption">{html.escape(RECOVERY_RETRY_CAPTION)}</p>'
