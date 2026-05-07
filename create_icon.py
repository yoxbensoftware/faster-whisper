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
    """Clean white mic on solid violet — readable at 16x16 and up."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx = cy = size / 2

    # Solid violet circle background
    d.ellipse([0, 0, size - 1, size - 1], fill=(*VIOLET2[:3], 255))

    # Mic capsule — white bold pill
    mw = size * 0.175
    mt = size * 0.12
    mb = size * 0.55
    d.ellipse([cx - mw, mt, cx + mw, mt + mw * 2],         fill=(255, 255, 255, 255))
    d.rectangle([cx - mw, mt + mw, cx + mw, mb - mw],      fill=(255, 255, 255, 255))
    d.ellipse([cx - mw, mb - mw * 2, cx + mw, mb],         fill=(255, 255, 255, 255))

    # Stand arc — white
    aw  = size * 0.30
    at  = size * 0.42
    ab  = size * 0.66
    alw = max(2, size // 16)
    d.arc([cx - aw, at, cx + aw, ab], start=0, end=180,
          fill=(255, 255, 255, 220), width=alw)

    # Stem
    stem_top = (at + ab) / 2
    stem_bot = size * 0.80
    sw = alw
    d.rectangle([cx - sw / 2, stem_top, cx + sw / 2, stem_bot],
                fill=(255, 255, 255, 220))

    # Base
    bw = size * 0.22
    bh = max(2, size // 20)
    d.rectangle([cx - bw, stem_bot, cx + bw, stem_bot + bh],
                fill=(255, 255, 255, 220))

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
