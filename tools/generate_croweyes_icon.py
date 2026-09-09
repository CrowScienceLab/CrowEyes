"""Generate the compact multi-resolution CrowEyes Windows application icon."""

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "icons" / "croweyes.ico"
SOURCE = ROOT / "assets" / "icons" / "croweyes-1.9.png"


def make_icon(side: int = 256) -> Image.Image:
    with Image.open(SOURCE) as opened:
        image = opened.convert("RGBA")
    return image.resize((side, side), Image.Resampling.LANCZOS)


if __name__ == "__main__":
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    icon = make_icon()
    icon.save(
        OUTPUT,
        format="ICO",
        sizes=[(16, 16), (20, 20), (24, 24), (32, 32), (48, 48),
               (64, 64), (128, 128), (256, 256)],
    )
    print(OUTPUT)
