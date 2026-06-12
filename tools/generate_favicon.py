#!/usr/bin/env python3
"""Generate assets/branding/favicon.png — re-run only when the ECG logo changes."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "branding" / "favicon.png"

SIZE = 256
RADIUS = 56
BG = "#0F6E56"
STROKE = "#FFFFFF"
STROKE_W = 18

POLYLINE = [(6, 28), (28, 28), (36, 16), (46, 40), (56, 6), (66, 34), (74, 28), (124, 28)]
VIEWBOX_W = 130
VIEWBOX_H = 48


def _scaled_points(size: int, pad: int) -> list[tuple[float, float]]:
    avail_w = size - 2 * pad
    avail_h = size - 2 * pad
    scale = min(avail_w / VIEWBOX_W, avail_h / VIEWBOX_H)
    ox = (size - VIEWBOX_W * scale) / 2
    oy = (size - VIEWBOX_H * scale) / 2
    return [(ox + x * scale, oy + y * scale) for x, y in POLYLINE]


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=RADIUS, fill=BG)

    pts = _scaled_points(SIZE, pad=52)
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=STROKE, width=STROKE_W, joint="curve")

    img.save(OUT, format="PNG")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
