#!/usr/bin/env python3
"""Regression checks for CrowEyes 1.5 printing and extended image formats."""

from __future__ import annotations

import importlib.util
import os
import struct
import tempfile
import time
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "CrowEyes_Image_Viewer_1.5.py"
spec = importlib.util.spec_from_file_location("croweyes_v15", SOURCE)
assert spec and spec.loader
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_svg(folder: Path) -> None:
    svg = folder / "complex.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
        <defs><linearGradient id="g"><stop stop-color="#101820"/><stop offset="1" stop-color="#38bdf8"/></linearGradient></defs>
        <rect width="640" height="360" rx="28" fill="url(#g)" opacity="0.92"/>
        <circle cx="130" cy="180" r="78" fill="#ffffff" fill-opacity="0.45"/>
        <text x="245" y="195" font-family="Segoe UI" font-size="54" fill="white">CrowEyes SVG</text>
        </svg>""",
        encoding="utf-8",
    )
    sizes = []
    for target in ((320, 180), (1280, 720), (3840, 2160)):
        rendered, logical = app.render_svg(svg, *target)
        sizes.append(rendered.size)
        require(logical == (640.0, 360.0), f"SVG logical size mismatch: {logical}")
        require(rendered.width * rendered.height <= app.MAX_RENDER_PIXELS, "SVG pixel cap exceeded")
        require(rendered.getbbox() is not None, "SVG rendered transparent/empty")
    require(sizes[0][0] < sizes[1][0] < sizes[2][0], f"SVG rerender did not grow: {sizes}")

    huge = folder / "huge.svg"
    huge.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="80000" height="40000"><rect width="100%" height="100%" fill="#334155"/></svg>',
        encoding="utf-8",
    )
    rendered, _ = app.render_svg(huge, 80000, 40000)
    require(rendered.width * rendered.height <= app.MAX_RENDER_PIXELS, "Huge SVG escaped memory cap")

    external = folder / "external.svg"
    external.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><style>.x{fill:url(https://example.com/a)}</style></svg>',
        encoding="utf-8",
    )
    try:
        app.inspect_svg(external)
    except app.FormatSupportError:
        pass
    else:
        raise AssertionError("External SVG resource was not rejected")

    broken = folder / "broken.svg"
    broken.write_text("<svg><broken>", encoding="utf-8")
    try:
        app.render_svg(broken, 100, 100)
    except app.FormatSupportError:
        pass
    else:
        raise AssertionError("Malformed SVG did not fail cleanly")


def create_flat_psd(path: Path, width: int, height: int) -> Path:
    """Create a standards-compliant uncompressed RGB PSD without test-only dependencies."""
    header = (
        b"8BPS" + struct.pack(">H", 1) + b"\0" * 6 + struct.pack(">HIIHH", 3, height, width, 8, 3)
        + struct.pack(">IIIH", 0, 0, 0, 0)
    )
    plane = width * height
    path.write_bytes(header + b"\x20" * plane + b"\x78" * plane + b"\xd0" * plane)
    return path


def check_psd(path: Path, label: str) -> None:
    started = time.perf_counter()
    frames, delays, animated, source_type, logical, scale = app.load_source_image(path, 1200, 900)
    elapsed = time.perf_counter() - started
    require(source_type == "psd", f"{label}: source type is {source_type}")
    require(len(frames) == 1 and not animated and delays == [0], f"{label}: invalid PSD frame state")
    require(frames[0].mode == "RGBA" and frames[0].getbbox() is not None, f"{label}: empty composite")
    require(logical == tuple(map(float, frames[0].size)) and scale == 1.0, f"{label}: dimensions mismatch")
    print(f"PASS {label}: {frames[0].width}x{frames[0].height}, {elapsed:.3f}s")


def check_psd_thumbnail(path: Path) -> None:
    """Exercise the real playlist thumbnail path without requiring a Tk window."""
    viewer = object.__new__(app.CrowEyesImageViewer)
    placeholder = object()
    viewer._placeholder_photo = placeholder
    viewer._theme = lambda: {"panel": "#20252B"}
    original_photo_image = app.ImageTk.PhotoImage
    app.ImageTk.PhotoImage = lambda image: image
    try:
        thumbnail = viewer._make_thumb(path, 96)
    finally:
        app.ImageTk.PhotoImage = original_photo_image
    require(thumbnail is not placeholder, "PSD playlist thumbnail fell back to the placeholder")
    require(isinstance(thumbnail, Image.Image), "PSD playlist thumbnail did not produce an image")
    require(thumbnail.size == (96, 96) and thumbnail.getbbox() is not None, "PSD playlist thumbnail is empty")


def check_regressions(folder: Path) -> None:
    for suffix, file_format in ((".png", "PNG"), (".jpg", "JPEG"), (".webp", "WEBP")):
        path = folder / f"static{suffix}"
        base = Image.new("RGB", (160, 90), (32, 120, 208))
        base.save(path, format=file_format)
        frames, _delays, animated, source_type, logical, _scale = app.load_source_image(path, 600, 400)
        require(len(frames) == 1 and not animated and source_type == "raster", f"{file_format} regression")
        require(logical == (160.0, 90.0) and frames[0].mode == "RGBA", f"{file_format} decode mismatch")

    first = Image.new("RGBA", (96, 64), (255, 0, 0, 255))
    second = Image.new("RGBA", (96, 64), (0, 128, 255, 180))
    gif = folder / "animation.gif"
    first.save(gif, save_all=True, append_images=[second], duration=[80, 120], loop=0)
    frames, delays, animated, source_type, logical, _ = app.load_source_image(gif, 600, 400)
    require(animated and len(frames) == 2 and source_type == "raster", "GIF animation regression")
    require(logical == (96.0, 64.0) and delays == [80, 120], f"GIF metadata mismatch: {delays}")

    corrupt_psd = folder / "corrupt.psd"
    corrupt_psd.write_bytes(b"8BPS\x00\x01broken")
    try:
        app.load_source_image(corrupt_psd, 400, 300)
    except Exception:
        pass
    else:
        raise AssertionError("Corrupt PSD did not fail cleanly")

    eps = folder / "sample.eps"
    eps.write_text("%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 100 100\nshowpage\n", encoding="ascii")
    real_find = app.find_ghostscript
    app.find_ghostscript = lambda: None
    try:
        try:
            app.render_eps(eps, 400, 400)
        except app.FormatSupportError as exc:
            require("Ghostscript" in str(exc), "EPS dependency guidance missing")
        else:
            raise AssertionError("EPS unexpectedly rendered without Ghostscript")
    finally:
        app.find_ghostscript = real_find

    require({".psd", ".svg", ".eps"}.issubset(app.SUPPORTED_EXT), "Extension scan list incomplete")
    require((0, 250, 1000, 750) == app.fit_print_rect((400, 200), (1000, 1000)), "Landscape print fit")
    require((250, 0, 750, 1000) == app.fit_print_rect((200, 400), (1000, 1000)), "Portrait print fit")

    viewer = object.__new__(app.CrowEyesImageViewer)
    viewer.flip_h, viewer.flip_v, viewer.rotation = True, False, 90
    viewer.brightness, viewer.contrast = 0.8, 1.15
    source = Image.new("RGBA", (80, 40), (180, 90, 30, 255))
    transformed = viewer._apply_current_transforms(source)
    require(transformed.size == (40, 80) and transformed.getpixel((0, 0)) != source.getpixel((0, 0)), "Print transforms")
    viewer.display_image, viewer.source_type, viewer.source_path = transformed, "raster", None
    print_image = viewer._image_for_print(1200, 900)
    require(print_image.size == transformed.size and print_image.tobytes() == transformed.tobytes(), "Raster print source quality")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="croweyes-v15-") as temp:
        folder = Path(temp)
        check_svg(folder)
        check_regressions(folder)
        normal = Path(os.environ["CROWEYES_TEST_PSD"]) if os.environ.get("CROWEYES_TEST_PSD") else create_flat_psd(folder / "normal.psd", 320, 240)
        large = Path(os.environ["CROWEYES_TEST_LARGE_PSD"]) if os.environ.get("CROWEYES_TEST_LARGE_PSD") else create_flat_psd(folder / "large.psd", 2400, 1600)
        check_psd(normal, "normal PSD")
        check_psd(large, "large PSD")
        check_psd_thumbnail(normal)
    print("PASS v1.5 extended formats, print layout, and raster regression checks")


if __name__ == "__main__":
    main()
