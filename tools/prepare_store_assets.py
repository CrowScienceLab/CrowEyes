"""Generate the Microsoft Store package logo set from the CrowEyes artwork."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def save_square(source: Image.Image, size: int, target: Path) -> None:
    source.resize((size, size), Image.Resampling.LANCZOS).save(target, optimize=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    source_path = Path(__file__).resolve().parents[1] / "assets" / "icons" / "croweyes-1.9.png"
    with Image.open(source_path) as opened:
        source = opened.convert("RGBA")

    save_square(source, 50, args.output / "StoreLogo.png")
    save_square(source, 44, args.output / "Square44x44Logo.png")
    save_square(source, 150, args.output / "Square150x150Logo.png")
    wide = Image.new("RGBA", (310, 150), "#0B0F14")
    tile = source.resize((132, 132), Image.Resampling.LANCZOS)
    wide.alpha_composite(tile, ((wide.width - tile.width) // 2, (wide.height - tile.height) // 2))
    wide.save(args.output / "Wide310x150Logo.png", optimize=True)


if __name__ == "__main__":
    main()
