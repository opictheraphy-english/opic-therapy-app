"""오픽치료사 브랜드 캐릭터 — inline SVG only (no image files / external URLs)."""

from __future__ import annotations


def render_character_svg(
    variant: str = "default",
    size: int = 92,
    bg: str = "#E1F5EE",
) -> str:
    """오픽치료사 브랜드 캐릭터 인라인 SVG를 반환. variant: default | listening | sorry"""
    v = (variant or "default").strip().lower()
    if v not in ("default", "listening", "sorry"):
        v = "default"
    bg_fill = (bg or "#E1F5EE").strip() or "#E1F5EE"

    headset = (
        '<path d="M32 50 Q60 24 88 50" fill="none" stroke="#04342C" '
        'stroke-width="3.4" stroke-linecap="round"/>'
        '<circle cx="33" cy="53" r="4.8" fill="#04342C"/>'
    )
    body = (
        f'<circle cx="60" cy="60" r="54" fill="{bg_fill}"/>'
        f'<ellipse cx="60" cy="64" rx="32" ry="37" fill="#5DCAA5"/>'
        f'<ellipse cx="60" cy="90" rx="24" ry="15" fill="#ffffff"/>'
        f"{headset}"
    )

    if v == "sorry":
        face = (
            '<circle cx="41" cy="62" r="3.4" fill="#F5C4B3" opacity="0.7"/>'
            '<circle cx="79" cy="62" r="3.4" fill="#F5C4B3" opacity="0.7"/>'
            '<path d="M44 47 Q49 44 54 47" fill="none" stroke="#04342C" '
            'stroke-width="2" stroke-linecap="round"/>'
            '<path d="M66 47 Q71 44 76 47" fill="none" stroke="#04342C" '
            'stroke-width="2" stroke-linecap="round"/>'
            '<circle cx="50" cy="56" r="2.8" fill="#04342C"/>'
            '<circle cx="70" cy="56" r="2.8" fill="#04342C"/>'
            '<path d="M54 67 Q60 63 66 67" fill="none" stroke="#04342C" '
            'stroke-width="1.8" stroke-linecap="round"/>'
            '<path d="M91 40 Q97 48 91 52 Q85 48 91 40 Z" fill="#A8D8EA"/>'
            '<path d="M35 59 Q42 71 52 72" fill="none" stroke="#04342C" '
            'stroke-width="2" stroke-linecap="round"/>'
            '<circle cx="54" cy="72" r="3" fill="#04342C"/>'
        )
    elif v == "default":
        face = (
            '<circle cx="41" cy="62" r="3.4" fill="#F5C4B3" opacity="0.85"/>'
            '<circle cx="79" cy="62" r="3.4" fill="#F5C4B3" opacity="0.85"/>'
            '<path d="M53 65 Q60 70 67 65" fill="none" stroke="#04342C" '
            'stroke-width="1.8" stroke-linecap="round"/>'
            '<circle cx="50" cy="55" r="3" fill="#04342C"/>'
            '<circle cx="70" cy="55" r="3" fill="#04342C"/>'
            '<path d="M35 59 Q42 71 52 72" fill="none" stroke="#04342C" '
            'stroke-width="2" stroke-linecap="round"/>'
            '<circle cx="54" cy="72" r="3" fill="#04342C"/>'
        )
    else:
        face = (
            '<circle cx="41" cy="62" r="3.4" fill="#F5C4B3" opacity="0.85"/>'
            '<circle cx="79" cy="62" r="3.4" fill="#F5C4B3" opacity="0.85"/>'
            '<path d="M53 65 Q60 70 67 65" fill="none" stroke="#04342C" '
            'stroke-width="1.8" stroke-linecap="round"/>'
            '<path d="M46 55 Q50 51 54 55" fill="none" stroke="#04342C" '
            'stroke-width="2.4" stroke-linecap="round"/>'
            '<path d="M66 55 Q70 51 74 55" fill="none" stroke="#04342C" '
            'stroke-width="2.4" stroke-linecap="round"/>'
            '<circle cx="87" cy="53" r="4.8" fill="#04342C"/>'
        )

    return (
        f'<svg width="{int(size)}" height="{int(size)}" viewBox="0 0 120 120" '
        f'aria-hidden="true" xmlns="http://www.w3.org/2000/svg">'
        f"{body}"
        f"{face}"
        f"</svg>"
    )


def render_celebration_scene(width: int = 240) -> str:
    """축하 캐릭터 + 색종이 장면 SVG (viewBox 0 0 240 120)."""
    w = max(120, int(width))
    h = max(60, int(round(w * 120 / 240)))
    return (
        f'<svg width="{w}" height="{h}" viewBox="0 0 240 120" '
        f'aria-hidden="true" xmlns="http://www.w3.org/2000/svg" '
        f'class="mx-fr-celebration-scene">'
        f'<circle cx="34" cy="26" r="4" fill="#534AB7"/>'
        f'<circle cx="206" cy="20" r="3.4" fill="#BA7517"/>'
        f'<circle cx="214" cy="82" r="3" fill="#D9537E"/>'
        f'<rect x="18" y="54" width="8" height="7" rx="2" fill="#D9537E" '
        f'transform="rotate(18 22 57.5)"/>'
        f'<rect x="192" y="44" width="7" height="8" rx="2" fill="#1D9E75" '
        f'transform="rotate(-14 195.5 48)"/>'
        f'<rect x="42" y="88" width="8" height="7" rx="2" fill="#534AB7" '
        f'transform="rotate(24 46 91.5)"/>'
        f'<circle cx="120" cy="62" r="52" fill="#ffffff"/>'
        f'<ellipse cx="120" cy="66" rx="31" ry="36" fill="#5DCAA5"/>'
        f'<ellipse cx="120" cy="91" rx="23" ry="14" fill="#ffffff"/>'
        f'<circle cx="100" cy="63" r="4" fill="#E8967A" opacity="1"/>'
        f'<circle cx="140" cy="63" r="4" fill="#E8967A" opacity="1"/>'
        f'<path d="M105 56 Q110 50 115 56" fill="none" stroke="#04342C" '
        f'stroke-width="2.4" stroke-linecap="round"/>'
        f'<path d="M125 56 Q130 50 135 56" fill="none" stroke="#04342C" '
        f'stroke-width="2.4" stroke-linecap="round"/>'
        f'<path d="M110 63 Q120 74 130 63 Z" fill="#04342C"/>'
        f'<path d="M92 51 Q120 26 148 51" fill="none" stroke="#04342C" '
        f'stroke-width="3.4" stroke-linecap="round"/>'
        f'<circle cx="93" cy="54" r="4.8" fill="#04342C"/>'
        f'<circle cx="147" cy="54" r="4.8" fill="#04342C"/>'
        f"</svg>"
    )
