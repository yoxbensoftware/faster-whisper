#!/usr/bin/env python3
"""Mikrofon ikonu oluşturur → icon.ico"""

from PIL import Image, ImageDraw
import os


def create_icon(path: str = "icon.ico"):
    sizes = [256, 128, 64, 48, 32, 16]
    imgs  = []

    for s in sizes:
        img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
        d   = ImageDraw.Draw(img)

        # Arka plan dairesi (mavi)
        d.ellipse([0, 0, s - 1, s - 1], fill=(59, 130, 246, 255))

        cx  = s / 2
        lw  = max(2, s // 18)  # çizgi kalınlığı

        # Mikrofon kapsülü (yuvarlatılmış dikdörtgen, beyaz)
        mw = s * 0.16
        mt = s * 0.13
        mb = s * 0.54
        d.rounded_rectangle(
            [cx - mw, mt, cx + mw, mb],
            radius=mw,
            fill=(255, 255, 255, 255),
        )

        # Stand yayı
        aw = s * 0.36
        at = s * 0.43
        ab = s * 0.70
        d.arc(
            [cx - aw, at, cx + aw, ab],
            start=180, end=0,
            fill=(255, 255, 255, 255),
            width=lw,
        )

        # Dikey çubuk
        st = (at + ab) / 2
        sb = s * 0.82
        d.rectangle(
            [cx - lw / 2, st, cx + lw / 2, sb],
            fill=(255, 255, 255, 255),
        )

        # Taban
        bw = s * 0.22
        d.rectangle(
            [cx - bw, sb - lw, cx + bw, sb],
            fill=(255, 255, 255, 255),
        )

        imgs.append(img)

    imgs[0].save(
        path,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=imgs[1:],
    )
    print(f"İkon oluşturuldu → {os.path.abspath(path)}")


if __name__ == "__main__":
    create_icon()
