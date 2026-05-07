#!/usr/bin/env python3
"""
Sesli Yazı — Cyberpunk icon generator
Dark theme mic icon matching the app UI (violet + cyan).
Requires Pillow: pip install pillow
"""

from PIL import Image, ImageDraw
import os


# ── Palette (matches voice_typer.py) ─────────────────────────────────────────
BG      = (11,  11,  20,  255)   # #0b0b14
DARK    = (18,  18,  30,  255)   # #12121e
CARD    = (20,  20,  40,  240)
VIOLET  = (139, 92,  246, 255)   # #8b5cf6
VIOLET2 = (109, 40,  217, 255)   # #6d28d9
CYAN    = (34,  211, 238, 255)   # #22d3ee
WHITE   = (226, 232, 240, 255)   # #e2e8f0


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx = cy = size / 2

    # ── Background circle ─────────────────────────────────────────────────────
    m = size * 0.03
    d.ellipse([m, m, size - m, size - m], fill=DARK)

    # ── Outer glow rings (violet, layered transparency) ───────────────────────
    ring_w = max(1, size // 18)
    for i, alpha in enumerate([30, 60, 130]):
        rm = m - i * (size / 28)
        d.ellipse([rm, rm, size - rm, size - rm],
                  outline=(*VIOLET[:3], alpha), width=ring_w)

    # ── Inner accent ring (cyan, thin) ────────────────────────────────────────
    inner = size * 0.16
    d.ellipse([inner, inner, size - inner, size - inner],
              outline=(*CYAN[:3], 90), width=max(1, size // 40))

    # ── Mic capsule (violet pill, properly elongated) ─────────────────────────
    mw  = size * 0.115          # half-width
    mt  = size * 0.13           # top
    mb  = size * 0.52           # bottom  (height/width ≈ 1.7 → pill shaped)
    rad = mw
    # top cap
    d.ellipse([cx - mw, mt, cx + mw, mt + rad * 2],          fill=VIOLET)
    # body
    d.rectangle([cx - mw, mt + rad, cx + mw, mb - rad],      fill=VIOLET)
    # bottom cap
    d.ellipse([cx - mw, mb - rad * 2, cx + mw, mb],           fill=VIOLET)

    # ── Stand arc (cyan U-shape) ──────────────────────────────────────────────
    aw  = size * 0.305
    at  = size * 0.385
    ab  = size * 0.66
    alw = max(2, size // 20)
    d.arc([cx - aw, at, cx + aw, ab], start=0, end=180,
          fill=(*CYAN[:3], 230), width=alw)

    # ── Stem ─────────────────────────────────────────────────────────────────
    stem_top = (at + ab) / 2
    stem_bot = size * 0.80
    sw = alw
    d.rectangle([cx - sw / 2, stem_top, cx + sw / 2, stem_bot],
                fill=(*CYAN[:3], 230))

    # ── Base ─────────────────────────────────────────────────────────────────
    bw  = size * 0.24
    bh  = max(2, size // 22)
    d.rectangle([cx - bw, stem_bot, cx + bw, stem_bot + bh],
                fill=(*CYAN[:3], 230))

    return img


def create_icon(path: str = "icon.ico"):
    sizes = [256, 128, 64, 48, 32, 16]
    imgs  = [draw_icon(s) for s in sizes]
    imgs[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=imgs[1:],
    )
    print(f"Icon saved → {os.path.abspath(path)}")


if __name__ == "__main__":
    create_icon()
