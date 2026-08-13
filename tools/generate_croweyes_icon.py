"""Generate the compact multi-resolution CrowEyes Windows application icon."""

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "icons" / "croweyes.ico"


def make_icon(side: int = 256) -> Image.Image:
    scale = 4
    size = side * scale
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    graphite = (18, 21, 24, 255)
    charcoal = (31, 35, 39, 255)
    silver = (191, 198, 205, 255)
    highlight = (229, 232, 235, 255)
    pupil = (7, 9, 11, 255)

    inset = int(size * 0.035)
    radius = int(size * 0.22)
    draw.rounded_rectangle(
        (inset, inset, size - inset, size - inset),
        radius=radius,
        fill=graphite,
        outline=(59, 65, 71, 255),
        width=max(2, int(size * 0.018)),
    )

    top = [
        (size * 0.12, size * 0.52), (size * 0.26, size * 0.34),
        (size * 0.50, size * 0.27), (size * 0.74, size * 0.34),
        (size * 0.88, size * 0.52),
    ]
    bottom = [
        (size * 0.12, size * 0.52), (size * 0.27, size * 0.67),
        (size * 0.50, size * 0.73), (size * 0.73, size * 0.67),
        (size * 0.88, size * 0.52),
    ]
    line = max(4, int(size * 0.035))
    draw.line(top, fill=highlight, width=line, joint="curve")
    draw.line(bottom, fill=silver, width=line, joint="curve")

    iris = (size * 0.33, size * 0.33, size * 0.67, size * 0.67)
    draw.ellipse(iris, fill=silver, outline=highlight, width=max(2, line // 3))
    pupil_box = (size * 0.425, size * 0.425, size * 0.575, size * 0.575)
    draw.ellipse(pupil_box, fill=pupil)
    glint = (size * 0.455, size * 0.445, size * 0.49, size * 0.48)
    draw.ellipse(glint, fill=(255, 255, 255, 230))

    # A restrained upper shadow suggests a crow's brow without adding detail.
    draw.arc(
        (size * 0.17, size * 0.17, size * 0.83, size * 0.57),
        start=198,
        end=342,
        fill=charcoal,
        width=max(2, int(size * 0.018)),
    )
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
