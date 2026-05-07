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
    """Violet circle + white ring + white dot — matches app round button style."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    cx = cy = size / 2

    # Outer violet filled circle (full icon)
    d.ellipse([0, 0, size - 1, size - 1], fill=(*VIOLET2[:3], 255))

    # White ring (thick outline circle — the "○" shape)
    ring_r  = size * 0.36      # ring radius (center of stroke)
    ring_lw = max(2, int(size * 0.10))
    r1 = cx - ring_r - ring_lw / 2
    r2 = cx + ring_r + ring_lw / 2
    d.ellipse([r1, r1, r2, r2], outline=(255, 255, 255, 255), width=ring_lw)

    # Small white dot in center
    dot_r = max(2, int(size * 0.07))
    d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r],
              fill=(255, 255, 255, 255))

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
