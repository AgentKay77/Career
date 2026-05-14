"""Generate the PWA icon PNGs ("RC" monogram, dark background).

Invoked by setup.sh; idempotent — won't overwrite existing files.

    python -m app.scripts.make_icons
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "static" / "icons"
BG = (10, 10, 11)
FG = (59, 130, 246)


def _font(size: int) -> ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def make(size: int, path: Path) -> None:
    img = Image.new("RGB", (size, size), BG)
    draw = ImageDraw.Draw(img)
    radius = int(size * 0.18)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    img.putalpha(mask)
    text = "RC"
    font = _font(int(size * 0.42))
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]), text, fill=FG, font=font)
    img.save(path)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    targets = {192: OUT / "icon-192.png", 512: OUT / "icon-512.png"}
    for size, path in targets.items():
        if path.exists():
            continue
        make(size, path)
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
