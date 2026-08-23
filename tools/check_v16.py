#!/usr/bin/env python3
"""Focused non-destructive checks for CrowEyes 1.6 additions."""

from __future__ import annotations

import importlib.util
import inspect
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "CrowEyes_Image_Viewer_1.6.py"
spec = importlib.util.spec_from_file_location("croweyes_v16", SOURCE)
assert spec and spec.loader
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_versions_and_hashes(folder: Path) -> None:
    require(app.is_newer_version("v1.10", "1.9"), "numeric semantic comparison failed")
    require(not app.is_newer_version("v1.6.0", "1.6"), "equal semantic version was newer")
    asset = app.release_asset({"assets": [{"name": "CrowEyes_Setup_1.6_Windows_x64.exe"}]}, r"CrowEyes_Setup_.+\.exe")
    require(asset is not None, "release asset selection failed")
    payload = folder / "asset.bin"
    payload.write_bytes(b"CrowEyes v1.6")
    digest = app.sha256_file(payload)
    parsed = app.parse_sha256s(f"{digest}  asset.bin\n")
    require(parsed.get("asset.bin") == digest, "SHA256SUMS parsing failed")


def check_rename(folder: Path) -> None:
    source = folder / "before.png"
    source.write_bytes(b"x")
    renamed = app.CrowEyesImageViewer._rename_path(source, "after")
    require(renamed.name == "after.png" and renamed.exists(), "stem-only rename failed")
    for invalid in ("", "CON", "bad:name", "trail."):
        try:
            app.validate_filename_stem(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"invalid Windows filename accepted: {invalid!r}")
    duplicate = folder / "exists.png"
    duplicate.write_bytes(b"y")
    try:
        app.CrowEyesImageViewer._rename_path(renamed, "exists")
    except FileExistsError:
        pass
    else:
        raise AssertionError("duplicate filename overwrite was allowed")


def check_svg(folder: Path) -> None:
    variants = {
        "px": ('width="640px" height="360px"', "utf-8"),
        "mm": ('width="169.333mm" height="95.25mm"', "utf-8"),
        "cm": ('width="16.9333cm" height="9.525cm"', "utf-8"),
        "pt": ('width="480pt" height="270pt"', "utf-8"),
        "in": ('width="6.6667in" height="3.75in"', "utf-8"),
        "viewbox": ('viewBox="0 0 640 360"', "utf-8"),
        "utf16": ('width="640" height="360"', "utf-16"),
    }
    for name, (attributes, encoding) in variants.items():
        path = folder / f"{name}.svg"
        text = f'<svg xmlns="http://www.w3.org/2000/svg" {attributes}><rect width="100%" height="100%" fill="#4098c8"/></svg>'
        path.write_text(text, encoding=encoding)
        rendered, logical = app.render_svg(path, 640, 360)
        require(rendered.width > 0 and rendered.height > 0, f"{name} SVG produced invalid size")
        require(logical[0] > 0 and logical[1] > 0, f"{name} SVG logical size invalid")
    blocked = folder / "external.svg"
    blocked.write_text('<svg xmlns="http://www.w3.org/2000/svg"><image href="file:///C:/secret.png"/></svg>', encoding="utf-8")
    try:
        app.inspect_svg(blocked)
    except app.FormatSupportError:
        pass
    else:
        raise AssertionError("local linked SVG resource was not blocked")


def check_print_and_source() -> None:
    fit = app.calculate_print_rect((4000, 2000), (800, 1000), "fit")
    require(fit == (0, 300, 800, 700), f"fit layout mismatch: {fit}")
    actual = app.calculate_print_rect((960, 480), (1200, 1200), "actual", (96, 96))
    require(actual == (120, 360, 1080, 840), f"actual layout mismatch: {actual}")
    source = SOURCE.read_text(encoding="utf-8")
    for marker in (
        'APP_VERSION = "1.6"', "class NavigationBar", "class CrowEyesToolbar", "class PrintPreview",
        "def check_for_updates", "def copy_selected_files", "def delete_selected_files",
        "def navigate_to_computer", "def enumerate_printer_names",
        "Print directly with app-supplied settings and no second preview dialog",
    ):
        require(marker in source, f"missing v1.6 source marker: {marker}")
    require("os.remove(" not in source, "permanent delete call found")
    require(app.DEFAULT_SETTINGS["ui_theme"] == "croweyes_dark", "black theme is not the default")
    require(app.DEFAULT_SETTINGS["design_generation"] >= 8, "v1.6 theme migration is missing")
    direct_print_source = inspect.getsource(app.print_image_windows)
    require("PrintDlgW" not in direct_print_source, "direct print path still opens the Windows print dialog")
    require("CreateDCW" in direct_print_source and "DocumentPropertiesW" in direct_print_source,
            "direct printer configuration path is incomplete")


def check_raster_save(folder: Path) -> None:
    rgba = Image.new("RGBA", (12, 8), (30, 120, 200, 80))
    for suffix in (".png", ".webp", ".bmp", ".tiff"):
        path = folder / f"roundtrip{suffix}"
        image = rgba if suffix not in {".bmp"} else rgba.convert("RGB")
        image.save(path)
        with Image.open(path) as opened:
            require(opened.size == rgba.size, f"{suffix} raster save regression")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="croweyes-v16-") as temp:
        folder = Path(temp)
        check_versions_and_hashes(folder)
        check_rename(folder)
        check_svg(folder)
        check_print_and_source()
        check_raster_save(folder)
    print("PASS: CrowEyes 1.6 navigation/print/file checks")


if __name__ == "__main__":
    main()
