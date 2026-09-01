"""Build the lightweight blocked-content mascot and a valid multi-size app ICO."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image


def square_fit(image: Image.Image, size: int, margin: int = 0) -> Image.Image:
    image = image.convert("RGBA")
    target = max(1, size - margin * 2)
    image.thumbnail((target, target), Image.Resampling.LANCZOS, reducing_gap=3.0)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.paste(image, ((size - image.width) // 2, (size - image.height) // 2), image)
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mascot-source", type=Path, required=True)
    parser.add_argument("--mascot-output", type=Path, required=True)
    parser.add_argument("--logo-source", type=Path, required=True)
    parser.add_argument("--ico-output", type=Path, required=True)
    args = parser.parse_args()

    with Image.open(args.mascot_source) as opened:
        mascot = square_fit(opened, 320, margin=3)
    args.mascot_output.parent.mkdir(parents=True, exist_ok=True)
    mascot.save(
        args.mascot_output, "WEBP", lossless=False, quality=88,
        method=6, exact=True, exif=b"", xmp=b"",
    )

    with Image.open(args.logo_source) as opened:
        logo = square_fit(opened, 256, margin=12)
    args.ico_output.parent.mkdir(parents=True, exist_ok=True)
    logo.save(
        args.ico_output, "ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )

    print(
        f"mascot={args.mascot_output} {args.mascot_output.stat().st_size} bytes "
        f"ico={args.ico_output} {args.ico_output.stat().st_size} bytes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
