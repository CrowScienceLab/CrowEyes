"""Crop and optimize the generated CrowEyes toolbar logo for packaging."""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: prepare_logo_asset.py INPUT OUTPUT")
    source, destination = map(Path, sys.argv[1:])
    with Image.open(source) as opened:
        image = opened.convert("RGBA")
    alpha_box = image.getchannel("A").getbbox()
    if alpha_box is None:
        raise SystemExit("logo has no visible pixels")
    image = image.crop(alpha_box)
    image.thumbnail((384, 192), Image.Resampling.LANCZOS)
    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination, "PNG", optimize=True)


if __name__ == "__main__":
    main()
