#!/usr/bin/env python3
"""CrowEyes Image Viewer 1.8.

A modern Windows image viewer built with Pillow, tkinter, and ttkbootstrap.
Copyright 2026 Crow Science Lab.
"""

from __future__ import annotations

import json
import hashlib
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.error
import urllib.request
import webbrowser
from io import BytesIO
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Dict, List, Optional, Set, Tuple, Union
from xml.etree import ElementTree

try:
    import winreg
except ImportError:  # pragma: no cover - Windows publishing target
    winreg = None  # type: ignore[assignment]

try:
    from tkinterdnd2 import COPY, DND_FILES, TkinterDnD
except ImportError:  # The viewer still runs; only Explorer drag-out is disabled.
    COPY = DND_FILES = None  # type: ignore[assignment]
    TkinterDnD = None  # type: ignore[assignment]

try:
    import ttkbootstrap as tb
    from ttkbootstrap.constants import *  # noqa: F401,F403 - requested public constants
except ImportError:
    try:
        _dependency_root = tk.Tk()
        _dependency_root.withdraw()
        messagebox.showerror(
            "CrowEyes Image Viewer",
            "ttkbootstrap이 설치되어 있지 않습니다.\n\n"
            "명령 프롬프트에서 다음 명령을 실행해 주세요:\n"
            "pip install ttkbootstrap",
        )
        _dependency_root.destroy()
    except tk.TclError:
        print("ttkbootstrap이 필요합니다: pip install ttkbootstrap", file=sys.stderr)
    raise SystemExit(1)

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageOps, ImageSequence, ImageTk
except ImportError:
    print("Pillow is required:  pip install Pillow", file=sys.stderr)
    sys.exit(1)

try:
    import resvg_py
except ImportError:
    resvg_py = None  # type: ignore[assignment]

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None  # type: ignore[assignment]

from croweyes_safety import (
    BLOCKED,
    ERROR,
    MODE_EXPLICIT,
    MODE_OFF,
    SAFE,
    UNKNOWN,
    SafetyCache,
    SafetyManager,
    SafetyTaskResult,
    SafetyWorker,
)


_ORIGINAL_TK_INIT = tk.Tk.__init__


def resource_path(*parts: str) -> Path:
    """Resolve bundled and source-tree assets through the same path."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def _tk_init_with_anaconda_msgcat(root: tk.Tk, *args, **kwargs) -> None:
    """Load Tcl msgcat when an Anaconda Tk build omits its module search path."""
    _ORIGINAL_TK_INIT(root, *args, **kwargs)
    try:
        root.tk.call("package", "require", "msgcat")
        return
    except tk.TclError:
        pass
    bundle_root = Path(getattr(sys, "_MEIPASS", sys.prefix))
    candidates = (
        bundle_root / "tcl8" / "8.5" / "msgcat-1.6.1.tm",
        Path(sys.prefix) / "Library" / "lib" / "tcl8" / "8.5" / "msgcat-1.6.1.tm",
        Path(sys.prefix) / "lib" / "tcl8" / "8.5" / "msgcat-1.6.1.tm",
    )
    for candidate in candidates:
        if candidate.is_file():
            try:
                root.tk.call("source", candidate.as_posix())
                return
            except tk.TclError:
                continue

APP_NAME = "CrowEyes Image Viewer"
APP_VERSION = "1.8"
APP_TITLE = f"{APP_NAME} {APP_VERSION}"
GITHUB_REPOSITORY = "CrowScienceLab/CrowEyes"
GITHUB_RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
GITHUB_RELEASE_PAGE_URL = f"https://github.com/{GITHUB_REPOSITORY}/releases/latest"
SMART_APP_CONTROL_HELP_URL = (
    "https://support.microsoft.com/en-us/Windows/Security/threat-malware-protection/"
    "smart-app-control-frequently-asked-questions"
)
UPDATE_CHECK_INTERVAL = 24 * 60 * 60

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SUPPORTED_EXT = {
    ".bmp", ".dib", ".jpg", ".jpeg", ".jpe", ".jfif", ".png", ".gif",
    ".webp", ".tif", ".tiff", ".ico", ".tga", ".ppm", ".pgm", ".pbm",
    ".psd", ".svg", ".eps",
}

MAX_RENDER_PIXELS = 16_000_000
SVG_RERENDER_GROWTH = 1.45

# Windows' Default Apps page makes the final user choice. CrowEyes only
# advertises these formats and never writes the protected UserChoice key.
ASSOCIATION_OPTIONS = (
    (".bmp", "BMP 이미지"), (".dib", "DIB 이미지"),
    (".gif", "GIF 이미지"), (".ico", "아이콘 이미지"),
    (".jfif", "JFIF 이미지"), (".jpe", "JPEG 이미지"),
    (".jpeg", "JPEG 이미지"), (".jpg", "JPEG 이미지"),
    (".pbm", "PBM 이미지"), (".pgm", "PGM 이미지"),
    (".png", "PNG 이미지"), (".ppm", "PPM 이미지"),
    (".tga", "TGA 이미지"), (".tif", "TIFF 이미지"),
    (".tiff", "TIFF 이미지"), (".webp", "WebP 이미지"),
    (".psd", "PSD 합성 이미지"), (".svg", "SVG 벡터 이미지"),
)
OPTIONAL_ASSOCIATION_OPTIONS = ((".eps", "EPS 벡터 이미지 · Ghostscript 필요"),)
ASSOCIATION_PROG_ID = "CrowEyes.Image"
ASSOCIATION_APP_NAME = "CrowEyes"

DEFAULT_SETTINGS = {
    "theme": "pastel",
    "bg_color": "",
    "fit_on_open": True,
    "slideshow_ms": 3000,
    "wheel_zoom": 1.15,
    "mouse_wheel_action": "navigate",
    "window_geometry": "1120x760",
    "list_mode": "small",
    "anim_playing": True,
    "sort_by": "name",  # name | date | size | ext
    "sort_desc": False,
    "show_info_panel": True,
    "ui_theme": "croweyes_dark",
    "show_playlist_panel": True,
    "show_context_bar": True,
    "compact_toolbar": False,
    "design_generation": 10,
    "content_filter": MODE_OFF,
    "auto_check_updates": True,
    "last_update_check": 0,
    "print_printer": "",
    "print_paper": "A4",
    "print_orientation": "portrait",
    "print_scale_mode": "fit",
    "print_copies": 1,
    "association_extensions": [ext for ext, _description in ASSOCIATION_OPTIONS],
    "auto_register_associations": False,
    # Initial pane ratios: playlist / image / info
    "pane_ratio_playlist": 0.22,
    "pane_ratio_image": 0.60,
    "pane_ratio_info": 0.18,
}

THEME_LABELS = {
    "croweyes_dark": "CrowEyes Dark · Crow",
    "bright_sky_blue": "Bright Sky Blue",
}

# All visual colors live in these theme tokens.  UI classes never hard-code colors.
CROWEYES_THEMES = {
    "croweyes_dark": {
        "bg": "#202429", "panel": "#282D33", "panel_alt": "#30363D",
        "canvas_bg": "#15181C", "border": "#56616D", "fg": "#FFFFFF",
        "muted": "#B7C0C9", "accent": "#B7C0C8", "accent_hi": "#EEF2F5",
        "accent_button": "#48545F", "accent_pressed": "#35414B",
        "select": "#3A4A58", "select_fg": "#FFFFFF",
        "danger": "#E17A82", "toolbar": "#24292F", "status": "#202429",
        "button": "#38414A", "button_active": "#46525E", "button_pressed": "#252C33",
        "button_fg": "#FFFFFF", "button_highlight": "#8996A3", "button_shadow": "#161A1E",
        "placeholder": "#86919D", "font": ("Segoe UI", 10),
        "font_title": ("Segoe UI Semibold", 11),
    },
    "bright_sky_blue": {
        "bg": "#EAF7FF", "panel": "#F8FCFF", "panel_alt": "#D7EEFA",
        "canvas_bg": "#DCEFF8", "border": "#4D8DAE", "fg": "#153246",
        "muted": "#476779", "accent": "#2086BA", "accent_hi": "#155F88",
        "accent_button": "#1D719B", "accent_pressed": "#155574",
        "select": "#B9E4FA", "select_fg": "#102D40",
        "danger": "#B23D4A", "toolbar": "#D9F0FC", "status": "#CDE8F6",
        "button": "#B9DFF2", "button_active": "#9FD4ED", "button_pressed": "#79BDDE",
        "button_fg": "#133044", "button_highlight": "#F8FDFF", "button_shadow": "#387A9A",
        "placeholder": "#64859A", "font": ("Segoe UI", 10),
        "font_title": ("Segoe UI Semibold", 11),
    },
}

SETTINGS_PATH = Path.home() / ".croweyes_image_viewer.json"
# Migrate legacy settings filename if present
_LEGACY_SETTINGS = Path.home() / ".simple_image_viewer.json"

LIST_MODES = ("names", "small", "icons")
LIST_MODE_LABELS = {
    "names": "파일명만",
    "small": "작은 아이콘 + 파일명",
    "icons": "그림 아이콘만",
}
SORT_KEYS = ("name", "date", "size", "ext")
SORT_LABELS = {
    "name": "파일명",
    "date": "날짜(시간)",
    "size": "용량",
    "ext": "확장자",
}

WHEEL_ACTION_LABELS = {
    "navigate": "이전 / 다음 이미지",
    "zoom": "확대 / 축소",
}

# 0.9 presents normalized Korean labels even when a legacy 0.8c source file
# was saved through a mismatched Windows console encoding.
LIST_MODE_LABELS = {
    "names": "파일명만",
    "small": "작은 아이콘 + 파일명",
    "icons": "아이콘 격자",
}
SORT_LABELS = {
    "name": "파일명",
    "date": "수정 날짜",
    "size": "파일 크기",
    "ext": "확장자",
}

THEMES = {
    "pastel": {
        "bg": "#F5F0FA", "fg": "#4A4458", "panel": "#FFF9FC",
        "accent": "#C4A8D8", "accent_hi": "#A88BC4", "canvas_bg": "#EDE6F5",
        "select": "#E2D4F0", "select_fg": "#3D3550", "button": "#E9D8F5",
        "button_active": "#D9C0EC", "button_fg": "#4A4458", "border": "#E4D8EE",
        "status": "#F0E8F6", "muted": "#9B8DAD", "toolbar": "#F8F3FC",
        "placeholder": "#B0A0C0", "font": ("Segoe UI", 10),
        "font_title": ("Segoe UI", 10, "bold"),
    },
    "pastel_mint": {
        "bg": "#EEF7F4", "fg": "#3D5248", "panel": "#F7FCFA",
        "accent": "#9BC9B8", "accent_hi": "#7DB39E", "canvas_bg": "#E4F2EC",
        "select": "#CDE8DC", "select_fg": "#2E4238", "button": "#D4EDE3",
        "button_active": "#B8DFD0", "button_fg": "#3D5248", "border": "#D0E8DC",
        "status": "#E8F5EF", "muted": "#7A9A8C", "toolbar": "#F2FAF6",
        "placeholder": "#8AADA0", "font": ("Segoe UI", 10),
        "font_title": ("Segoe UI", 10, "bold"),
    },
    "pastel_peach": {
        "bg": "#FBF3EE", "fg": "#5A463C", "panel": "#FFF9F5",
        "accent": "#E8B4A0", "accent_hi": "#D99A82", "canvas_bg": "#F5E8E0",
        "select": "#F0D5C8", "select_fg": "#4A362C", "button": "#F5D9CC",
        "button_active": "#EBC4B2", "button_fg": "#5A463C", "border": "#EEDDD2",
        "status": "#F8EEE8", "muted": "#A89080", "toolbar": "#FCF6F2",
        "placeholder": "#C0A090", "font": ("Segoe UI", 10),
        "font_title": ("Segoe UI", 10, "bold"),
    },
    "light": {
        "bg": "#F7F7F8", "fg": "#2C2C2E", "panel": "#FFFFFF",
        "accent": "#A8B8D0", "accent_hi": "#8AA0C0", "canvas_bg": "#ECEEF2",
        "select": "#D8E4F4", "select_fg": "#1E1E20", "button": "#E4EAF2",
        "button_active": "#D0DAE8", "button_fg": "#2C2C2E", "border": "#D8DCE4",
        "status": "#F0F2F6", "muted": "#888890", "toolbar": "#F4F5F8",
        "placeholder": "#A0A0A8", "font": ("Segoe UI", 10),
        "font_title": ("Segoe UI", 10, "bold"),
    },
}


def load_settings() -> dict:
    data = dict(DEFAULT_SETTINGS)
    loaded_keys: Set[str] = set()
    path = SETTINGS_PATH if SETTINGS_PATH.is_file() else _LEGACY_SETTINGS
    if path.is_file():
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    loaded_keys = set(loaded)
                    data.update(loaded)
        except (OSError, json.JSONDecodeError):
            pass
    # Apply the final two-theme product system once to existing profiles.
    try:
        design_generation = int(data.get("design_generation", 0))
    except (TypeError, ValueError):
        design_generation = 0
    if design_generation < 3:
        previous_theme = str(data.get("ui_theme", "croweyes_dark"))
        data["ui_theme"] = (
            "bright_sky_blue"
            if previous_theme in {"croweyes_light", "pastel_lavender", "pastel_mint"}
            else "croweyes_dark"
        )
        data["bg_color"] = ""
        data["design_generation"] = 3
    if design_generation < 4:
        data["association_extensions"] = [ext for ext, _description in ASSOCIATION_OPTIONS]
        data["auto_register_associations"] = False
        data["design_generation"] = 4
    if design_generation < 5:
        remembered = set(data.get("association_extensions", []))
        remembered.update({".psd", ".svg"})
        data["association_extensions"] = [
            ext for ext, _description in ASSOCIATION_OPTIONS if ext in remembered
        ]
        data["design_generation"] = 5
    if design_generation < 6:
        data["auto_check_updates"] = True
        data["last_update_check"] = 0
        data["design_generation"] = 6
    if design_generation < 8:
        # v1.6 starts in the CrowEyes black palette for both new and upgraded
        # profiles. A later explicit theme choice remains persistent.
        data["ui_theme"] = "croweyes_dark"
        data["design_generation"] = 8
    if design_generation < 9:
        # Some legacy profiles retained the very early 60 ms slideshow
        # default. Migrate only that unusably fast value; keep intentional
        # custom intervals intact.
        try:
            legacy_slideshow_ms = int(data.get("slideshow_ms", 3000))
        except (TypeError, ValueError):
            legacy_slideshow_ms = 3000
        if legacy_slideshow_ms <= 100:
            data["slideshow_ms"] = 3000
        data["design_generation"] = 9
    if design_generation < 10:
        # The safety filter is deliberately opt-in. Also repair legacy pane
        # positions that could leave either side panel almost invisible.
        data["content_filter"] = MODE_OFF
        ratios = (
            float(data.get("pane_ratio_playlist", 0.22)),
            float(data.get("pane_ratio_image", 0.60)),
            float(data.get("pane_ratio_info", 0.18)),
        )
        if ratios[0] < 0.16 or ratios[1] < 0.44 or ratios[2] < 0.13:
            data["pane_ratio_playlist"] = 0.22
            data["pane_ratio_image"] = 0.60
            data["pane_ratio_info"] = 0.18
        data["design_generation"] = 10

    legacy_theme_map = {
        "pastel": "bright_sky_blue", "pastel_peach": "bright_sky_blue",
        "light": "bright_sky_blue", "dark": "croweyes_dark",
    }
    if not loaded_keys or "ui_theme" in loaded_keys or int(data.get("design_generation", 0)) >= 3:
        ui_theme = data.get("ui_theme", "croweyes_dark")
    else:
        ui_theme = legacy_theme_map.get(data.get("theme"), "croweyes_dark")
    data["ui_theme"] = ui_theme if ui_theme in CROWEYES_THEMES else "croweyes_dark"
    if data.get("list_mode") not in LIST_MODES:
        data["list_mode"] = "small"
    if data.get("sort_by") not in SORT_KEYS:
        data["sort_by"] = "name"
    if data.get("mouse_wheel_action") not in WHEEL_ACTION_LABELS:
        data["mouse_wheel_action"] = "navigate"
    if data.get("content_filter") not in {MODE_OFF, MODE_EXPLICIT}:
        data["content_filter"] = MODE_OFF
    return data


def save_settings(settings: dict) -> None:
    try:
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except OSError:
        pass


def _frame_to_rgba(im: Image.Image) -> Image.Image:
    if im.mode in ("RGBA", "RGB"):
        return im.convert("RGBA") if im.mode != "RGBA" else im.copy()
    if im.mode == "P":
        return im.convert("RGBA")
    return im.convert("RGBA")


class FormatSupportError(OSError):
    """Short, user-facing error for optional or invalid image sources."""


def _bounded_size(width: float, height: float, max_width: float, max_height: float) -> Tuple[int, int]:
    """Fit a positive size into a box and the shared render-pixel ceiling."""
    width, height = max(1.0, float(width)), max(1.0, float(height))
    scale = min(max_width / width, max_height / height)
    scale = max(scale, 1.0 / max(width, height))
    out_w, out_h = max(1, int(round(width * scale))), max(1, int(round(height * scale)))
    pixels = out_w * out_h
    if pixels > MAX_RENDER_PIXELS:
        limit = math.sqrt(MAX_RENDER_PIXELS / pixels)
        out_w, out_h = max(1, int(out_w * limit)), max(1, int(out_h * limit))
    return out_w, out_h


_SVG_LENGTH_RE = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+))(px|pt|pc|mm|cm|in)?\s*$", re.I)
_SVG_UNIT_SCALE = {"": 1.0, "px": 1.0, "pt": 96 / 72, "pc": 16.0, "mm": 96 / 25.4, "cm": 96 / 2.54, "in": 96.0}


def _svg_length(value: Optional[str]) -> Optional[float]:
    if not value or value.strip().endswith("%"):
        return None
    match = _SVG_LENGTH_RE.match(value)
    if not match:
        return None
    return max(0.0, float(match.group(1)) * _SVG_UNIT_SCALE[(match.group(2) or "").lower()])


def _decode_svg_bytes(raw: bytes) -> str:
    """Decode common SVG encodings, including BOM and UTF-16 exports."""
    for encoding in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = raw.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "<svg" in text.lower() or "<?xml" in text.lower():
            return text.lstrip("\ufeff")
    raise FormatSupportError("SVG 문자 인코딩을 읽을 수 없습니다.")


def _svg_resource_is_safe(value: str) -> bool:
    candidate = value.strip().strip("'\"").lower()
    return not candidate or candidate.startswith(("#", "data:"))


def inspect_svg(path: Path) -> Tuple[str, Tuple[float, float]]:
    """Read an SVG safely, reject remote resources, and return logical pixels."""
    try:
        if path.stat().st_size > 64 * 1024 * 1024:
            raise FormatSupportError("SVG 파일이 너무 큽니다.")
    except OSError as exc:
        raise FormatSupportError(f"SVG 파일을 읽을 수 없습니다: {exc}") from exc
    try:
        text = _decode_svg_bytes(path.read_bytes())
    except OSError as exc:
        raise FormatSupportError(f"SVG 파일을 읽을 수 없습니다: {exc}") from exc
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise FormatSupportError(f"올바르지 않은 SVG입니다: {exc}") from exc
    if root.tag.rsplit("}", 1)[-1].lower() != "svg":
        raise FormatSupportError("SVG 루트 요소를 찾을 수 없습니다.")
    for element in root.iter():
        local_tag = element.tag.rsplit("}", 1)[-1].lower()
        if local_tag == "script":
            raise FormatSupportError("스크립트가 포함된 SVG는 표시하지 않습니다.")
        for key, value in element.attrib.items():
            local_key = key.rsplit("}", 1)[-1].lower()
            if local_key in {"href", "src"} and not _svg_resource_is_safe(value):
                raise FormatSupportError("외부 네트워크 또는 파일 리소스가 포함된 SVG는 표시하지 않습니다.")
            if local_key == "style":
                for resource in re.findall(r"url\(\s*([^)]*?)\s*\)", value, re.I):
                    if not _svg_resource_is_safe(resource):
                        raise FormatSupportError("외부 리소스가 포함된 SVG는 표시하지 않습니다.")
        if local_tag == "style" and element.text:
            if re.search(r"@import\s+", element.text, re.I):
                raise FormatSupportError("외부 스타일을 가져오는 SVG는 표시하지 않습니다.")
            for resource in re.findall(r"url\(\s*([^)]*?)\s*\)", element.text, re.I):
                if not _svg_resource_is_safe(resource):
                    raise FormatSupportError("외부 리소스가 포함된 SVG는 표시하지 않습니다.")
    width, height = _svg_length(root.get("width")), _svg_length(root.get("height"))
    view_box = root.get("viewBox") or root.get("viewbox")
    view_size: Optional[Tuple[float, float]] = None
    if view_box:
        try:
            values = [float(value) for value in re.split(r"[\s,]+", view_box.strip()) if value]
            if len(values) == 4 and values[2] > 0 and values[3] > 0:
                view_size = (values[2], values[3])
        except ValueError:
            pass
    if width is None and height is None:
        width, height = view_size or (300.0, 150.0)
    elif width is None:
        ratio = (view_size[0] / view_size[1]) if view_size else 2.0
        width = max(1.0, float(height) * ratio)
    elif height is None:
        ratio = (view_size[1] / view_size[0]) if view_size else 0.5
        height = max(1.0, float(width) * ratio)
    assert width is not None and height is not None
    if width <= 0 or height <= 0:
        raise FormatSupportError("SVG 크기 정보가 올바르지 않습니다.")
    return text, (width, height)


def _normalized_svg_text(svg_text: str, logical_size: Tuple[float, float]) -> str:
    """Normalize physical/unitless exports to explicit 96-DPI pixel dimensions."""
    root = ElementTree.fromstring(svg_text)
    width, height = logical_size
    root.set("width", f"{max(1.0, width):.6f}px")
    root.set("height", f"{max(1.0, height):.6f}px")
    if not (root.get("viewBox") or root.get("viewbox")):
        root.set("viewBox", f"0 0 {max(1.0, width):.6f} {max(1.0, height):.6f}")
    return ElementTree.tostring(root, encoding="unicode")


def render_svg(path: Path, target_width: int, target_height: int) -> Tuple[Image.Image, Tuple[float, float]]:
    if resvg_py is None:
        raise FormatSupportError("SVG 렌더러(resvg_py)가 설치되어 있지 않습니다.")
    svg_text, logical_size = inspect_svg(path)
    width, height = _bounded_size(logical_size[0], logical_size[1], target_width, target_height)
    errors: List[str] = []
    for candidate in (svg_text, _normalized_svg_text(svg_text, logical_size)):
        try:
            png = resvg_py.svg_to_bytes(
                svg_string=candidate,
                width=width,
                height=height,
                dpi=96.0,
                resources_dir=None,
                skip_system_fonts=False,
            )
            with Image.open(BytesIO(png)) as opened:
                rendered = opened.convert("RGBA")
            if rendered.width <= 0 or rendered.height <= 0:
                raise ValueError("SVG has an invalid size")
            return rendered, logical_size
        except Exception as exc:
            errors.append(str(exc))
    detail = errors[-1] if errors else "알 수 없는 오류"
    raise FormatSupportError(f"SVG 렌더링에 실패했습니다: {detail}")


def find_ghostscript() -> Optional[Path]:
    """Find a Windows Ghostscript console executable without running a shell."""
    for name in ("gswin64c.exe", "gswin32c.exe", "gs.exe"):
        found = shutil.which(name)
        if found:
            return Path(found)
    roots = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "gs"]
    program_files_x86 = os.environ.get("ProgramFiles(x86)")
    if program_files_x86:
        roots.append(Path(program_files_x86) / "gs")
    candidates: List[Path] = []
    for root in roots:
        try:
            candidates.extend(root.glob("gs*/bin/gswin64c.exe"))
            candidates.extend(root.glob("gs*/bin/gswin32c.exe"))
        except OSError:
            continue
    return sorted(candidates, reverse=True)[0] if candidates else None


def render_eps(path: Path, target_width: int, target_height: int) -> Tuple[Image.Image, Tuple[float, float]]:
    ghostscript = find_ghostscript()
    if ghostscript is None:
        raise FormatSupportError("EPS 파일을 표시하려면 Ghostscript가 필요합니다.")
    try:
        from PIL import EpsImagePlugin

        EpsImagePlugin.gs_binary = str(ghostscript)
        with Image.open(path) as opened:
            logical_size = (float(opened.width), float(opened.height))
            target = _bounded_size(opened.width, opened.height, target_width, target_height)
            scale = max(1, int(math.ceil(max(target[0] / opened.width, target[1] / opened.height))))
            if opened.width * opened.height * scale * scale > MAX_RENDER_PIXELS:
                scale = max(1, int(math.sqrt(MAX_RENDER_PIXELS / (opened.width * opened.height))))
            opened.load(scale=scale)
            return opened.convert("RGBA"), logical_size
    except FormatSupportError:
        raise
    except Exception as exc:
        raise FormatSupportError(f"EPS 렌더링에 실패했습니다: {exc}") from exc


def fit_print_rect(image_size: Tuple[int, int], page_size: Tuple[int, int]) -> Tuple[int, int, int, int]:
    """Return a centered aspect-fit rectangle for a printable device area."""
    image_w, image_h = image_size
    page_w, page_h = page_size
    if min(image_w, image_h, page_w, page_h) <= 0:
        raise ValueError("이미지와 인쇄 영역의 크기는 0보다 커야 합니다.")
    scale = min(page_w / image_w, page_h / image_h)
    draw_w, draw_h = max(1, int(round(image_w * scale))), max(1, int(round(image_h * scale)))
    left, top = (page_w - draw_w) // 2, (page_h - draw_h) // 2
    return left, top, left + draw_w, top + draw_h


def calculate_print_rect(
    image_size: Tuple[int, int], page_size: Tuple[int, int], scale_mode: str = "fit",
    printer_dpi: Tuple[int, int] = (96, 96),
) -> Tuple[int, int, int, int]:
    """Shared preview/print layout: aspect-fit or 96-DPI actual size, centered."""
    if scale_mode == "fit":
        return fit_print_rect(image_size, page_size)
    image_w, image_h = image_size
    page_w, page_h = page_size
    dpi_x, dpi_y = printer_dpi
    draw_w = max(1, int(round(image_w * max(1, dpi_x) / 96.0)))
    draw_h = max(1, int(round(image_h * max(1, dpi_y) / 96.0)))
    left, top = (page_w - draw_w) // 2, (page_h - draw_h) // 2
    return left, top, left + draw_w, top + draw_h


def get_default_printer_name() -> str:
    if os.name != "nt":
        return "Windows 기본 프린터"
    import ctypes
    from ctypes import wintypes

    try:
        # Python 3.14 no longer resolves the legacy ``winspool`` alias;
        # Windows ships the print spooler API as winspool.drv.
        winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
    except OSError:
        return "Windows 기본 프린터"
    winspool.GetDefaultPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    winspool.GetDefaultPrinterW.restype = wintypes.BOOL
    needed = wintypes.DWORD(0)
    winspool.GetDefaultPrinterW(None, ctypes.byref(needed))
    if needed.value <= 1:
        return "Windows 기본 프린터"
    buffer = ctypes.create_unicode_buffer(needed.value)
    return buffer.value if winspool.GetDefaultPrinterW(buffer, ctypes.byref(needed)) else "Windows 기본 프린터"


def show_printer_properties(printer_name: str, owner_hwnd: int) -> bool:
    """Open the native properties dialog for the named Windows printer."""
    if os.name != "nt":
        raise OSError("프린터 속성은 Windows에서만 지원됩니다.")
    if not printer_name or printer_name == "Windows 기본 프린터":
        raise OSError("Windows 기본 프린터가 설정되어 있지 않습니다.")
    import ctypes
    from ctypes import wintypes

    winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
    winspool.OpenPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
    winspool.OpenPrinterW.restype = wintypes.BOOL
    winspool.PrinterProperties.argtypes = [wintypes.HWND, wintypes.HANDLE]
    winspool.PrinterProperties.restype = wintypes.BOOL
    winspool.ClosePrinter.argtypes = [wintypes.HANDLE]
    winspool.ClosePrinter.restype = wintypes.BOOL
    handle = wintypes.HANDLE()
    if not winspool.OpenPrinterW(printer_name, ctypes.byref(handle), None):
        raise ctypes.WinError()
    try:
        ctypes.set_last_error(0)
        shown = bool(winspool.PrinterProperties(owner_hwnd, handle))
        error = ctypes.get_last_error()
        if not shown and error:
            raise ctypes.WinError(error)
        return shown
    finally:
        winspool.ClosePrinter(handle)


def _print_image_windows_dialog_legacy(
    image_factory: Callable[[int, int], Image.Image], owner_hwnd: int, document_name: str,
    orientation: str = "portrait", paper: str = "A4", scale_mode: str = "fit",
) -> bool:
    """Legacy native-dialog path retained only for source compatibility."""
    if os.name != "nt":
        raise OSError("인쇄는 Windows에서만 지원됩니다.")
    import ctypes
    from ctypes import wintypes
    from PIL import ImageWin

    class PRINTDLGW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD), ("hwndOwner", wintypes.HWND),
            ("hDevMode", wintypes.HGLOBAL), ("hDevNames", wintypes.HGLOBAL),
            ("hDC", wintypes.HDC), ("Flags", wintypes.DWORD),
            ("nFromPage", wintypes.WORD), ("nToPage", wintypes.WORD),
            ("nMinPage", wintypes.WORD), ("nMaxPage", wintypes.WORD),
            ("nCopies", wintypes.WORD), ("hInstance", wintypes.HINSTANCE),
            ("lCustData", wintypes.LPARAM), ("lpfnPrintHook", ctypes.c_void_p),
            ("lpfnSetupHook", ctypes.c_void_p), ("lpPrintTemplateName", wintypes.LPCWSTR),
            ("lpSetupTemplateName", wintypes.LPCWSTR), ("hPrintTemplate", wintypes.HGLOBAL),
            ("hSetupTemplate", wintypes.HGLOBAL),
        ]

    class DOCINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_int), ("lpszDocName", wintypes.LPCWSTR),
            ("lpszOutput", wintypes.LPCWSTR), ("lpszDatatype", wintypes.LPCWSTR),
            ("fwType", wintypes.DWORD),
        ]

    class DEVMODEW(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
            ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD),
            ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
            ("dmOrientation", ctypes.c_short), ("dmPaperSize", ctypes.c_short),
            ("dmPaperLength", ctypes.c_short), ("dmPaperWidth", ctypes.c_short),
            ("dmScale", ctypes.c_short), ("dmCopies", ctypes.c_short),
            ("dmDefaultSource", ctypes.c_short), ("dmPrintQuality", ctypes.c_short),
            ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short),
            ("dmYResolution", ctypes.c_short), ("dmTTOption", ctypes.c_short),
            ("dmCollate", ctypes.c_short), ("dmFormName", wintypes.WCHAR * 32),
            ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD),
            ("dmPelsWidth", wintypes.DWORD), ("dmPelsHeight", wintypes.DWORD),
            ("dmDisplayFlags", wintypes.DWORD), ("dmDisplayFrequency", wintypes.DWORD),
            ("dmICMMethod", wintypes.DWORD), ("dmICMIntent", wintypes.DWORD),
            ("dmMediaType", wintypes.DWORD), ("dmDitherType", wintypes.DWORD),
            ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
            ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD),
        ]

    comdlg32, gdi32, kernel32 = ctypes.windll.comdlg32, ctypes.windll.gdi32, ctypes.windll.kernel32
    comdlg32.PrintDlgW.argtypes = [ctypes.POINTER(PRINTDLGW)]
    comdlg32.PrintDlgW.restype = wintypes.BOOL
    comdlg32.CommDlgExtendedError.restype = wintypes.DWORD
    gdi32.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.GetDeviceCaps.restype = ctypes.c_int
    gdi32.StartDocW.argtypes = [wintypes.HDC, ctypes.POINTER(DOCINFOW)]
    gdi32.StartDocW.restype = ctypes.c_int
    kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalFree.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    gdi32.ResetDCW.argtypes = [wintypes.HDC, ctypes.POINTER(DEVMODEW)]
    gdi32.ResetDCW.restype = wintypes.HDC
    for name in ("StartPage", "EndPage", "EndDoc", "AbortDoc", "DeleteDC"):
        getattr(gdi32, name).argtypes = [wintypes.HDC]
        getattr(gdi32, name).restype = ctypes.c_int

    dialog = PRINTDLGW()
    dialog.lStructSize = ctypes.sizeof(PRINTDLGW)
    dialog.hwndOwner = owner_hwnd
    dialog.Flags = 0x00000100 | 0x00040000 | 0x00000008 | 0x00000004  # RETURNDC, DEVMODE copies, no pages/selection
    dialog.nMinPage = dialog.nMaxPage = dialog.nFromPage = dialog.nToPage = 1
    dialog.nCopies = 1
    try:
        if not comdlg32.PrintDlgW(ctypes.byref(dialog)):
            code = int(comdlg32.CommDlgExtendedError())
            if code == 0:
                return False
            raise OSError(f"프린터 선택 창을 열 수 없습니다. (0x{code:04X})")
        if not dialog.hDC:
            raise OSError("선택한 프린터의 출력 정보를 가져올 수 없습니다.")
        if dialog.hDevMode:
            pointer = kernel32.GlobalLock(dialog.hDevMode)
            if pointer:
                try:
                    devmode = ctypes.cast(pointer, ctypes.POINTER(DEVMODEW))
                    devmode.contents.dmFields |= 0x00000001 | 0x00000002  # orientation, paper size
                    devmode.contents.dmOrientation = 2 if orientation == "landscape" else 1
                    devmode.contents.dmPaperSize = 1 if paper == "Letter" else 9
                    reset_dc = gdi32.ResetDCW(dialog.hDC, devmode)
                    if reset_dc:
                        dialog.hDC = reset_dc
                finally:
                    kernel32.GlobalUnlock(dialog.hDevMode)
        printable_w = int(gdi32.GetDeviceCaps(dialog.hDC, 8))
        printable_h = int(gdi32.GetDeviceCaps(dialog.hDC, 10))
        dpi_x = max(1, int(gdi32.GetDeviceCaps(dialog.hDC, 88)))
        dpi_y = max(1, int(gdi32.GetDeviceCaps(dialog.hDC, 90)))
        if printable_w <= 0 or printable_h <= 0:
            raise OSError("프린터의 인쇄 가능 영역이 올바르지 않습니다.")
        image = image_factory(printable_w, printable_h)
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        print_rect = calculate_print_rect(
            image.size, (printable_w, printable_h), scale_mode, (dpi_x, dpi_y),
        )
        doc = DOCINFOW(ctypes.sizeof(DOCINFOW), document_name, None, None, 0)
        if gdi32.StartDocW(dialog.hDC, ctypes.byref(doc)) <= 0:
            raise OSError("프린터가 인쇄 작업을 시작하지 못했습니다.")
        started = True
        try:
            if gdi32.StartPage(dialog.hDC) <= 0:
                raise OSError("프린터가 페이지 출력을 시작하지 못했습니다.")
            ImageWin.Dib(image).draw(dialog.hDC, print_rect)
            if gdi32.EndPage(dialog.hDC) <= 0 or gdi32.EndDoc(dialog.hDC) <= 0:
                raise OSError("프린터가 출력 작업을 완료하지 못했습니다.")
            started = False
        finally:
            if started:
                gdi32.AbortDoc(dialog.hDC)
        return True
    finally:
        if dialog.hDC:
            gdi32.DeleteDC(dialog.hDC)
        if dialog.hDevMode:
            kernel32.GlobalFree(dialog.hDevMode)
        if dialog.hDevNames:
            kernel32.GlobalFree(dialog.hDevNames)


def enumerate_printer_names() -> List[str]:
    """Return installed local and connected Windows printer names."""
    if os.name != "nt":
        return []
    import ctypes
    from ctypes import wintypes

    class PRINTER_INFO_4W(ctypes.Structure):
        _fields_ = [
            ("pPrinterName", wintypes.LPWSTR),
            ("pServerName", wintypes.LPWSTR),
            ("Attributes", wintypes.DWORD),
        ]

    winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
    winspool.EnumPrintersW.argtypes = [
        wintypes.DWORD, wintypes.LPWSTR, wintypes.DWORD, ctypes.c_void_p,
        wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
    ]
    winspool.EnumPrintersW.restype = wintypes.BOOL
    needed, returned = wintypes.DWORD(), wintypes.DWORD()
    flags = 0x00000002 | 0x00000004  # PRINTER_ENUM_LOCAL | CONNECTIONS
    winspool.EnumPrintersW(flags, None, 4, None, 0, ctypes.byref(needed), ctypes.byref(returned))
    if needed.value == 0:
        return []
    buffer = ctypes.create_string_buffer(needed.value)
    if not winspool.EnumPrintersW(
        flags, None, 4, buffer, needed.value, ctypes.byref(needed), ctypes.byref(returned),
    ):
        raise ctypes.WinError()
    records = ctypes.cast(buffer, ctypes.POINTER(PRINTER_INFO_4W))
    names = sorted(
        {records[i].pPrinterName for i in range(returned.value) if records[i].pPrinterName},
        key=str.casefold,
    )
    default = get_default_printer_name()
    if default in names:
        names.remove(default)
        names.insert(0, default)
    return names


def print_image_windows(
    image_factory: Callable[[int, int], Image.Image], owner_hwnd: int, document_name: str,
    orientation: str = "portrait", paper: str = "A4", scale_mode: str = "fit",
    printer_name: str = "", copies: int = 1, output_path: Optional[str] = None,
) -> bool:
    """Print directly with app-supplied settings and no second preview dialog."""
    if os.name != "nt":
        raise OSError("인쇄는 Windows에서만 지원됩니다.")
    import ctypes
    from ctypes import wintypes
    from PIL import ImageWin

    class DOCINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.c_int), ("lpszDocName", wintypes.LPCWSTR),
            ("lpszOutput", wintypes.LPCWSTR), ("lpszDatatype", wintypes.LPCWSTR),
            ("fwType", wintypes.DWORD),
        ]

    class DEVMODEW(ctypes.Structure):
        _fields_ = [
            ("dmDeviceName", wintypes.WCHAR * 32), ("dmSpecVersion", wintypes.WORD),
            ("dmDriverVersion", wintypes.WORD), ("dmSize", wintypes.WORD),
            ("dmDriverExtra", wintypes.WORD), ("dmFields", wintypes.DWORD),
            ("dmOrientation", ctypes.c_short), ("dmPaperSize", ctypes.c_short),
            ("dmPaperLength", ctypes.c_short), ("dmPaperWidth", ctypes.c_short),
            ("dmScale", ctypes.c_short), ("dmCopies", ctypes.c_short),
            ("dmDefaultSource", ctypes.c_short), ("dmPrintQuality", ctypes.c_short),
            ("dmColor", ctypes.c_short), ("dmDuplex", ctypes.c_short),
            ("dmYResolution", ctypes.c_short), ("dmTTOption", ctypes.c_short),
            ("dmCollate", ctypes.c_short), ("dmFormName", wintypes.WCHAR * 32),
            ("dmLogPixels", wintypes.WORD), ("dmBitsPerPel", wintypes.DWORD),
            ("dmPelsWidth", wintypes.DWORD), ("dmPelsHeight", wintypes.DWORD),
            ("dmDisplayFlags", wintypes.DWORD), ("dmDisplayFrequency", wintypes.DWORD),
            ("dmICMMethod", wintypes.DWORD), ("dmICMIntent", wintypes.DWORD),
            ("dmMediaType", wintypes.DWORD), ("dmDitherType", wintypes.DWORD),
            ("dmReserved1", wintypes.DWORD), ("dmReserved2", wintypes.DWORD),
            ("dmPanningWidth", wintypes.DWORD), ("dmPanningHeight", wintypes.DWORD),
        ]

    printer_name = printer_name or get_default_printer_name()
    if not printer_name or printer_name == "Windows 기본 프린터":
        raise OSError("사용 가능한 기본 프린터가 없습니다.")
    copies = max(1, min(999, int(copies)))
    winspool = ctypes.WinDLL("winspool.drv", use_last_error=True)
    gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
    handle = wintypes.HANDLE()
    winspool.OpenPrinterW.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p]
    winspool.OpenPrinterW.restype = wintypes.BOOL
    winspool.ClosePrinter.argtypes = [wintypes.HANDLE]
    winspool.DocumentPropertiesW.argtypes = [
        wintypes.HWND, wintypes.HANDLE, wintypes.LPWSTR, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
    ]
    winspool.DocumentPropertiesW.restype = wintypes.LONG
    gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
    gdi32.CreateDCW.restype = wintypes.HDC
    gdi32.GetDeviceCaps.argtypes = [wintypes.HDC, ctypes.c_int]
    gdi32.GetDeviceCaps.restype = ctypes.c_int
    gdi32.StartDocW.argtypes = [wintypes.HDC, ctypes.POINTER(DOCINFOW)]
    gdi32.StartDocW.restype = ctypes.c_int
    for name in ("StartPage", "EndPage", "EndDoc", "AbortDoc", "DeleteDC"):
        getattr(gdi32, name).argtypes = [wintypes.HDC]
        getattr(gdi32, name).restype = ctypes.c_int
    if not winspool.OpenPrinterW(printer_name, ctypes.byref(handle), None):
        raise ctypes.WinError()
    hdc = wintypes.HDC()
    try:
        size = int(winspool.DocumentPropertiesW(owner_hwnd, handle, printer_name, None, None, 0))
        if size <= 0:
            raise OSError("프린터의 기본 설정을 불러오지 못했습니다.")
        devmode_buffer = ctypes.create_string_buffer(size)
        devmode_ptr = ctypes.cast(devmode_buffer, ctypes.c_void_p)
        if winspool.DocumentPropertiesW(
            owner_hwnd, handle, printer_name, devmode_ptr, None, 0x00000002,
        ) < 0:
            raise OSError("프린터 설정을 초기화하지 못했습니다.")
        devmode = ctypes.cast(devmode_ptr, ctypes.POINTER(DEVMODEW))
        devmode.contents.dmFields |= 0x00000001 | 0x00000002 | 0x00000100
        devmode.contents.dmOrientation = 2 if orientation == "landscape" else 1
        devmode.contents.dmPaperSize = 1 if paper == "Letter" else 9
        devmode.contents.dmCopies = copies
        if winspool.DocumentPropertiesW(
            owner_hwnd, handle, printer_name, devmode_ptr, devmode_ptr, 0x0000000A,
        ) < 0:
            raise OSError("선택한 인쇄 설정을 프린터에 적용하지 못했습니다.")
        hdc = gdi32.CreateDCW("WINSPOOL", printer_name, None, devmode_ptr)
        if not hdc:
            raise ctypes.WinError()
        printable_w = int(gdi32.GetDeviceCaps(hdc, 8))
        printable_h = int(gdi32.GetDeviceCaps(hdc, 10))
        dpi_x = max(1, int(gdi32.GetDeviceCaps(hdc, 88)))
        dpi_y = max(1, int(gdi32.GetDeviceCaps(hdc, 90)))
        if printable_w <= 0 or printable_h <= 0:
            raise OSError("프린터의 인쇄 가능 영역이 올바르지 않습니다.")
        image = image_factory(printable_w, printable_h)
        if image.mode == "RGBA":
            background = Image.new("RGB", image.size, "white")
            background.paste(image, mask=image.getchannel("A"))
            image = background
        else:
            image = image.convert("RGB")
        print_rect = calculate_print_rect(image.size, (printable_w, printable_h), scale_mode, (dpi_x, dpi_y))
        doc = DOCINFOW(ctypes.sizeof(DOCINFOW), document_name, output_path, None, 0)
        if gdi32.StartDocW(hdc, ctypes.byref(doc)) <= 0:
            raise OSError("프린터가 인쇄 작업을 시작하지 못했습니다.")
        started = True
        try:
            if gdi32.StartPage(hdc) <= 0:
                raise OSError("프린터가 페이지 출력을 시작하지 못했습니다.")
            ImageWin.Dib(image).draw(hdc, print_rect)
            if gdi32.EndPage(hdc) <= 0 or gdi32.EndDoc(hdc) <= 0:
                raise OSError("프린터가 출력 작업을 완료하지 못했습니다.")
            started = False
        finally:
            if started:
                gdi32.AbortDoc(hdc)
        return True
    finally:
        if hdc:
            gdi32.DeleteDC(hdc)
        winspool.ClosePrinter(handle)


def load_animation_frames(path: Path) -> Tuple[List[Image.Image], List[int], bool]:
    # TODO: Very large/long GIFs are still decoded to full RGBA frames for 0.8c
    # compatibility. A future release should add a bounded streaming frame cache.
    with Image.open(path) as src:
        fmt = (src.format or "").upper()
        n_frames = getattr(src, "n_frames", 1) or 1
        is_anim = n_frames > 1 and fmt in {"GIF", "WEBP"}

        if not is_anim:
            frame = ImageOps.exif_transpose(src)
            return [_frame_to_rgba(frame)], [0], False

        canvas_size = src.size
        base = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
        frames: List[Image.Image] = []
        delays: List[int] = []
        prev_canvas: Optional[Image.Image] = None

        for frame in ImageSequence.Iterator(src):
            duration = frame.info.get("duration", 100)
            try:
                duration = int(duration)
            except (TypeError, ValueError):
                duration = 100
            if duration <= 0:
                duration = 100
            if duration < 10:
                duration = max(duration * 10, 40)

            disposal = frame.info.get("disposal", 0)
            try:
                disposal = int(disposal)
            except (TypeError, ValueError):
                disposal = 0

            layer = _frame_to_rgba(frame)
            offset = frame.info.get("offset", (0, 0))
            if not isinstance(offset, tuple) or len(offset) != 2:
                offset = (0, 0)

            if disposal == 3 and prev_canvas is not None:
                work = prev_canvas.copy()
            else:
                work = base.copy()
            if disposal != 3:
                prev_canvas = work.copy()

            if layer.size != canvas_size or offset != (0, 0):
                tmp = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
                tmp.paste(layer, offset, layer)
                layer = tmp

            composed = Image.alpha_composite(work, layer)
            frames.append(composed.copy())
            if disposal == 2:
                base = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
            else:
                base = composed.copy()
            delays.append(duration)

        if not frames:
            return [_frame_to_rgba(ImageOps.exif_transpose(src))], [0], False
        return frames, delays, True


def load_source_image(
    path: Path, target_width: int, target_height: int,
) -> Tuple[List[Image.Image], List[int], bool, str, Tuple[float, float], float]:
    """Load a raster/vector source into the existing PIL frame pipeline."""
    suffix = path.suffix.lower()
    if suffix == ".svg":
        _text, logical = inspect_svg(path)
        # Start at logical 100% or the canvas size, whichever is larger.
        initial_w = max(int(math.ceil(logical[0])), target_width)
        initial_h = max(int(math.ceil(logical[1])), target_height)
        image, logical = render_svg(path, initial_w, initial_h)
        scale = image.width / max(1.0, logical[0])
        return [image], [0], False, "svg", logical, scale
    if suffix == ".eps":
        image, logical = render_eps(path, target_width, target_height)
        scale = image.width / max(1.0, logical[0])
        return [image], [0], False, "eps", logical, scale
    frames, delays, animated = load_animation_frames(path)
    source_type = "psd" if suffix == ".psd" else "raster"
    logical = (float(frames[0].width), float(frames[0].height))
    return frames, delays, animated, source_type, logical, 1.0


def is_image_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXT


def list_image_paths_fast(folder: Path) -> List[Path]:
    """Fast name-only scan via os.scandir (no thumbnail I/O)."""
    out: List[Path] = []
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if not entry.is_file(follow_symlinks=False):
                    continue
                name = entry.name
                ext = os.path.splitext(name)[1].lower()
                if ext in SUPPORTED_EXT:
                    out.append(Path(entry.path))
    except OSError:
        pass
    return out


def list_subdirs(folder: Path) -> List[Path]:
    dirs: List[Path] = []
    try:
        with os.scandir(folder) as it:
            for entry in it:
                if entry.is_dir(follow_symlinks=False) and not entry.name.startswith("."):
                    dirs.append(Path(entry.path))
    except OSError:
        pass
    dirs.sort(key=lambda p: p.name.lower())
    return dirs


def list_windows_drives() -> List[Path]:
    """Return available drive roots on Windows (C:\\, D:\\, …)."""
    drives: List[Path] = []
    if os.name != "nt":
        return [Path("/")]
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        root = f"{letter}:\\"
        if os.path.exists(root):
            drives.append(Path(root))
    return drives


INVALID_WINDOWS_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_WINDOWS_NAMES = {
    "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def validate_filename_stem(stem: str) -> str:
    stem = stem.strip()
    if not stem:
        raise ValueError("파일 이름을 입력해 주세요.")
    if INVALID_WINDOWS_FILENAME.search(stem):
        raise ValueError('파일 이름에 < > : " / \\ | ? * 문자를 사용할 수 없습니다.')
    if stem.endswith((" ", ".")):
        raise ValueError("파일 이름은 공백이나 마침표로 끝날 수 없습니다.")
    if stem.upper() in RESERVED_WINDOWS_NAMES:
        raise ValueError("Windows에서 예약된 파일 이름은 사용할 수 없습니다.")
    return stem


def semantic_version(value: str) -> Tuple[int, ...]:
    match = re.search(r"(?:^|[^0-9])(\d+(?:\.\d+){0,3})", value.strip())
    if not match:
        raise ValueError(f"올바른 버전이 아닙니다: {value}")
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer_version(latest: str, current: str = APP_VERSION) -> bool:
    left, right = semantic_version(latest), semantic_version(current)
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) > right + (0,) * (width - len(right))


def release_asset(release: dict, pattern: str) -> Optional[dict]:
    regex = re.compile(pattern, re.I)
    return next((asset for asset in release.get("assets", []) if regex.fullmatch(str(asset.get("name", "")))), None)


def parse_sha256s(text: str) -> Dict[str, str]:
    hashes: Dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([0-9a-fA-F]{64})\s+\*?(.+?)\s*$", line)
        if match:
            hashes[Path(match.group(2)).name] = match.group(1).lower()
    return hashes


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_files_to_windows_clipboard(paths: List[Path]) -> None:
    """Place real files on the Windows clipboard as CF_HDROP."""
    if os.name != "nt" or not paths:
        raise OSError("파일 복사는 Windows에서만 지원됩니다.")
    import ctypes
    from ctypes import wintypes

    class DROPFILES(ctypes.Structure):
        _fields_ = [
            ("pFiles", wintypes.DWORD), ("pt_x", wintypes.LONG), ("pt_y", wintypes.LONG),
            ("fNC", wintypes.BOOL), ("fWide", wintypes.BOOL),
        ]

    payload = ("\0".join(str(path.resolve()) for path in paths) + "\0\0").encode("utf-16-le")
    header = DROPFILES(ctypes.sizeof(DROPFILES), 0, 0, False, True)
    kernel32, user32 = ctypes.windll.kernel32, ctypes.windll.user32
    kernel32.GlobalAlloc.argtypes = (wintypes.UINT, ctypes.c_size_t)
    kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel32.GlobalLock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalLock.restype = ctypes.c_void_p
    kernel32.GlobalUnlock.argtypes = (wintypes.HGLOBAL,)
    kernel32.GlobalFree.argtypes = (wintypes.HGLOBAL,)
    user32.OpenClipboard.argtypes = (wintypes.HWND,)
    user32.SetClipboardData.argtypes = (wintypes.UINT, wintypes.HANDLE)
    user32.SetClipboardData.restype = wintypes.HANDLE
    handle = kernel32.GlobalAlloc(0x0042, ctypes.sizeof(header) + len(payload))
    if not handle:
        raise MemoryError("클립보드 메모리를 할당할 수 없습니다.")
    pointer = kernel32.GlobalLock(handle)
    try:
        ctypes.memmove(pointer, ctypes.byref(header), ctypes.sizeof(header))
        ctypes.memmove(ctypes.c_void_p(pointer + ctypes.sizeof(header)), payload, len(payload))
    finally:
        kernel32.GlobalUnlock(handle)
    if not user32.OpenClipboard(None):
        kernel32.GlobalFree(handle)
        raise OSError("Windows 클립보드를 열 수 없습니다.")
    try:
        user32.EmptyClipboard()
        if not user32.SetClipboardData(15, handle):
            kernel32.GlobalFree(handle)
            raise OSError("파일을 클립보드에 복사하지 못했습니다.")
        handle = None
    finally:
        user32.CloseClipboard()


def special_folders() -> List[Tuple[str, Path]]:
    """Common Windows user folders for quick access."""
    home = Path.home()
    resolved: Dict[str, Path] = {}
    if os.name == "nt" and winreg is not None:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        registry_names = {
            "바탕 화면": "Desktop",
            "문서": "Personal",
            "사진": "My Pictures",
            "다운로드": "{374DE290-123F-4565-9164-39C4925E467B}",
            "음악": "My Music",
            "비디오": "My Video",
        }
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                for label, value_name in registry_names.items():
                    try:
                        value, _kind = winreg.QueryValueEx(key, value_name)
                        resolved[label] = Path(os.path.expandvars(str(value)))
                    except OSError:
                        pass
        except OSError:
            pass
    candidates = [("홈", home)]
    fallbacks = (
        ("바탕 화면", home / "Desktop"), ("문서", home / "Documents"),
        ("사진", home / "Pictures"), ("다운로드", home / "Downloads"),
        ("음악", home / "Music"), ("비디오", home / "Videos"),
    )
    candidates.extend((label, resolved.get(label, fallback)) for label, fallback in fallbacks)
    out: List[Tuple[str, Path]] = []
    for label, p in candidates:
        try:
            if p.is_dir():
                out.append((label, p.resolve()))
        except OSError:
            pass
    return out


# ---------------------------------------------------------------------------
# Custom folder picker
#  - ".." parent navigation + drive list / special folders
#  - Current folder as "이 폴더 이미지 (N장)" checkbox
#  - Subfolders as multi-check; enter with double-click
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------

# Replace the legacy folder dialog with a compact Windows-friendly multi-folder picker.
# The original class is intentionally left above to keep the 0.8c implementation intact.
class FolderPicker(tk.Toplevel):
    def __init__(self, master: tk.Tk, start: Optional[Path] = None) -> None:
        super().__init__(master)
        self.title("폴더로 보기")
        self.transient(master)
        self.grab_set()
        self.geometry("580x500")
        self.minsize(480, 400)
        self.result: Optional[List[Path]] = None
        self.current = (start or Path.home()).resolve()
        if not self.current.is_dir():
            self.current = Path.home()
        self._paths: List[Path] = []

        outer = ttk.Frame(self, style="Panel.TFrame", padding=14)
        outer.pack(fill=tk.BOTH, expand=True)
        ttk.Label(outer, text="여러 폴더에서 이미지 모으기", style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Ctrl 또는 Shift를 누른 채 여러 폴더를 선택할 수 있습니다.",
                  style="Muted.TLabel").pack(anchor="w", pady=(2, 10))
        nav = ttk.Frame(outer, style="Panel.TFrame")
        nav.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(nav, text="상위 폴더", command=self._go_parent, style="Pastel.TButton").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value=str(self.current))
        ttk.Entry(nav, textvariable=self.path_var, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        list_wrap = ttk.Frame(outer, style="Panel.TFrame")
        list_wrap.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(list_wrap, orient=tk.VERTICAL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.listbox = tk.Listbox(list_wrap, selectmode=tk.EXTENDED, exportselection=False,
                                  bd=0, activestyle="none", yscrollcommand=scroll.set)
        theme = master._theme()  # type: ignore[attr-defined]
        self.configure(bg=theme["bg"])
        self.listbox.configure(bg=theme["panel_alt"], fg=theme["fg"],
                               selectbackground=theme["select"], selectforeground=theme["select_fg"],
                               highlightthickness=1, highlightbackground=theme["border"], font=theme["font"])
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.configure(command=self.listbox.yview)
        self.listbox.bind("<Double-Button-1>", self._enter_selected)

        buttons = ttk.Frame(outer, style="Panel.TFrame")
        buttons.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(buttons, text="현재 폴더만", command=self._choose_current, style="Pastel.TButton").pack(side=tk.LEFT)
        ttk.Button(buttons, text="전체 선택", command=lambda: self.listbox.select_set(0, tk.END),
                   style="Pastel.TButton").pack(side=tk.LEFT, padx=6)
        ttk.Button(buttons, text="취소", command=self._cancel, style="Pastel.TButton").pack(side=tk.RIGHT)
        ttk.Button(buttons, text="선택한 폴더 열기", command=self._open_selected,
                   style="Pastel.TButton").pack(side=tk.RIGHT, padx=6)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._refresh()
        self.wait_window(self)

    def _refresh(self) -> None:
        self.path_var.set(str(self.current))
        self.listbox.delete(0, tk.END)
        self._paths = [self.current] + list_subdirs(self.current)
        current_count = len(list_image_paths_fast(self.current))
        self.listbox.insert(tk.END, f"● 현재 폴더 — {self.current.name or self.current} ({current_count}개)")
        for path in self._paths[1:]:
            self.listbox.insert(tk.END, f"▸ {path.name}")
        self.listbox.selection_set(0)

    def _go_parent(self) -> None:
        parent = self.current.parent
        if parent != self.current:
            self.current = parent
            self._refresh()

    def _enter_selected(self, _event=None) -> None:
        selected = self.listbox.curselection()
        if not selected:
            return
        path = self._paths[int(selected[0])]
        if path.is_dir():
            self.current = path
            self._refresh()

    def _choose_current(self) -> None:
        self.result = [self.current]
        self.destroy()

    def _open_selected(self) -> None:
        selected = self.listbox.curselection()
        self.result = [self._paths[int(i)] for i in selected if int(i) < len(self._paths)]
        if not self.result:
            messagebox.showinfo("폴더로 보기", "폴더를 하나 이상 선택해 주세요.", parent=self)
            return
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class CrowEyesIconSet:
    """Antialiased command glyphs plus the packaged CrowEyes brand mark."""

    def __init__(self, root: tk.Misc, colors: dict) -> None:
        self.root = root
        self.colors = colors
        self.images: Dict[str, ImageTk.PhotoImage] = {}
        toolbar_icons = (
            "previous", "next", "fit", "zoom_in", "zoom_out", "rotate_right",
            "rotate_left", "fullscreen", "play", "pause", "info", "settings",
            "more", "actual", "gif", "folder", "open_image", "save", "flip_h",
            "flip_v", "brightness", "contrast", "theme", "panel", "shortcuts",
            "slideshow", "close", "print", "up", "refresh", "search", "view",
            "sort", "ascending", "descending", "copy", "delete", "rename", "location",
            "computer",
        )
        for name in toolbar_icons:
            self.images[name] = self._render(name, 20)
        self.images["eye"] = self._load_brand_eye()
        self.images["eye_large"] = self._render("eye", 64)
        self.images["folder_large"] = self._render("folder", 44)
        self.images["computer_large"] = self._render("computer", 44)
        self.images["app"] = self._render("eye", 32, app_badge=True)

    def __getitem__(self, name: str) -> ImageTk.PhotoImage:
        return self.images[name]

    @staticmethod
    def _rgb(value: str) -> Tuple[int, int, int, int]:
        value = value.lstrip("#")
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)

    def _load_brand_eye(self) -> ImageTk.PhotoImage:
        path = resource_path("assets", "icons", "croweyes-eye-logo.png")
        try:
            with Image.open(path) as opened:
                logo = opened.convert("RGBA")
            logo.thumbnail((64, 42), Image.Resampling.LANCZOS)
            canvas = Image.new("RGBA", (66, 44), (0, 0, 0, 0))
            canvas.alpha_composite(logo, ((canvas.width - logo.width) // 2, (canvas.height - logo.height) // 2))
            return ImageTk.PhotoImage(canvas, master=self.root)
        except (OSError, ValueError):
            return self._render("eye", 34)

    def _render(self, name: str, size: int, app_badge: bool = False) -> ImageTk.PhotoImage:
        scale = 4
        side = size * scale
        image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        fg = self._rgb(self.colors["fg"])
        muted = self._rgb(self.colors["muted"])
        accent = self._rgb(self.colors["accent"])
        panel = self._rgb(self.colors["panel_alt"])
        # The glyphs use one SVG-like visual language: a 1.5 px optical
        # stroke, rounded caps/corners, and a restrained accent color.
        line = max(5, int(size * 0.075 * scale))
        s = scale

        def poly(points, fill=fg, width=line, rounded=True) -> None:
            scaled = [(int(x * s), int(y * s)) for x, y in points]
            draw.line(scaled, fill=fill, width=width, joint="curve")
            if rounded and scaled:
                radius = width / 2
                for x, y in (scaled[0], scaled[-1]):
                    draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill)

        def ellipse(box, outline=fg, fill=None, width=line) -> None:
            draw.ellipse(tuple(int(v * s) for v in box), outline=outline, fill=fill, width=width)

        def rectangle(box, outline=fg, fill=None, width=line, radius=0) -> None:
            box_scaled = tuple(int(v * s) for v in box)
            if radius:
                draw.rounded_rectangle(box_scaled, radius=int(radius * s), outline=outline, fill=fill, width=width)
            else:
                draw.rectangle(box_scaled, outline=outline, fill=fill, width=width)

        if name == "eye":
            if app_badge:
                ellipse((1.5, 1.5, size - 1.5, size - 1.5), outline=None, fill=panel, width=0)
            top = [(size * .10, size * .53), (size * .24, size * .34), (size * .50, size * .25),
                   (size * .76, size * .34), (size * .90, size * .53)]
            bottom = [(size * .10, size * .53), (size * .26, size * .68), (size * .50, size * .75),
                      (size * .74, size * .68), (size * .90, size * .53)]
            poly(top, fg, max(line, 2 * s))
            poly(bottom, fg, max(line, 2 * s))
            ellipse((size * .34, size * .34, size * .66, size * .66), outline=accent, fill=accent, width=line)
            ellipse((size * .44, size * .44, size * .56, size * .56), outline=panel, fill=panel, width=line)
        elif name in {"previous", "next"}:
            if name == "previous":
                poly([(size * .64, size * .22), (size * .34, size * .50), (size * .64, size * .78)])
            else:
                poly([(size * .36, size * .22), (size * .66, size * .50), (size * .36, size * .78)])
        elif name == "up":
            poly([(size * .22, size * .55), (size * .50, size * .27), (size * .78, size * .55)])
            poly([(size * .50, size * .28), (size * .50, size * .82)], accent)
        elif name == "refresh":
            draw.arc(tuple(int(v * s) for v in (size*.16, size*.16, size*.84, size*.84)), 30, 325, fill=fg, width=line)
            draw.polygon([(int(size*.72*s), int(size*.13*s)), (int(size*.91*s), int(size*.18*s)),
                          (int(size*.78*s), int(size*.34*s))], fill=accent)
        elif name in {"zoom_in", "zoom_out"}:
            ellipse((size * .16, size * .13, size * .65, size * .62))
            poly([(size * .60, size * .58), (size * .84, size * .82)])
            poly([(size * .28, size * .38), (size * .53, size * .38)])
            if name == "zoom_in":
                poly([(size * .405, size * .25), (size * .405, size * .51)])
        elif name == "search":
            ellipse((size * .14, size * .12, size * .65, size * .63))
            poly([(size * .59, size * .57), (size * .84, size * .82)], accent)
        elif name in {"fit", "fullscreen"}:
            if name == "fullscreen":
                corners = (
                    [(size*.40, size*.18), (size*.18, size*.18), (size*.18, size*.40)],
                    [(size*.60, size*.18), (size*.82, size*.18), (size*.82, size*.40)],
                    [(size*.18, size*.60), (size*.18, size*.82), (size*.40, size*.82)],
                    [(size*.82, size*.60), (size*.82, size*.82), (size*.60, size*.82)],
                )
            else:
                rectangle((size*.12, size*.16, size*.88, size*.84), outline=muted, radius=size*.07)
                corners = (
                    [(size*.20, size*.42), (size*.36, size*.42), (size*.36, size*.26)],
                    [(size*.80, size*.42), (size*.64, size*.42), (size*.64, size*.26)],
                    [(size*.20, size*.58), (size*.36, size*.58), (size*.36, size*.74)],
                    [(size*.80, size*.58), (size*.64, size*.58), (size*.64, size*.74)],
                )
            for corner in corners:
                poly(corner)
        elif name in {"rotate_right", "rotate_left"}:
            box = tuple(int(v * s) for v in (size * .17, size * .17, size * .83, size * .83))
            if name == "rotate_right":
                draw.arc(box, start=205, end=525, fill=fg, width=line)
                arrow = [(size * .76, size * .16), (size * .91, size * .23), (size * .78, size * .34)]
            else:
                draw.arc(box, start=15, end=335, fill=fg, width=line)
                arrow = [(size * .24, size * .16), (size * .09, size * .23), (size * .22, size * .34)]
            draw.polygon([(int(x * s), int(y * s)) for x, y in arrow], fill=accent)
        elif name == "actual":
            rectangle((size * .14, size * .14, size * .86, size * .86), outline=muted, radius=size * .08)
            rectangle((size * .30, size * .30, size * .70, size * .70), outline=fg, radius=size * .04)
            ellipse((size * .46, size * .46, size * .54, size * .54), outline=None, fill=accent, width=0)
        elif name in {"play", "slideshow"}:
            if name == "slideshow":
                rectangle((size * .10, size * .15, size * .90, size * .85), outline=muted, radius=size * .08)
            draw.polygon([(int(size * .38 * s), int(size * .25 * s)),
                          (int(size * .76 * s), int(size * .50 * s)),
                          (int(size * .38 * s), int(size * .75 * s))], fill=accent)
        elif name == "pause":
            rectangle((size * .28, size * .22, size * .42, size * .78), outline=None, fill=accent, width=0, radius=size * .03)
            rectangle((size * .58, size * .22, size * .72, size * .78), outline=None, fill=accent, width=0, radius=size * .03)
        elif name in {"info", "close"}:
            if name == "info":
                ellipse((size * .15, size * .15, size * .85, size * .85))
                ellipse((size * .46, size * .27, size * .54, size * .35), outline=None, fill=accent, width=0)
                poly([(size * .50, size * .44), (size * .50, size * .70)], accent)
            else:
                poly([(size * .24, size * .24), (size * .76, size * .76)])
                poly([(size * .76, size * .24), (size * .24, size * .76)])
        elif name == "settings":
            ellipse((size * .31, size * .31, size * .69, size * .69), outline=accent)
            ellipse((size * .43, size * .43, size * .57, size * .57), outline=accent, fill=accent)
            for dx, dy in ((0, -.38), (.27, -.27), (.38, 0), (.27, .27), (0, .38), (-.27, .27), (-.38, 0), (-.27, -.27)):
                poly([(size * (.50 + dx * .55), size * (.50 + dy * .55)),
                      (size * (.50 + dx), size * (.50 + dy))])
        elif name == "more":
            for x in (.27, .50, .73):
                ellipse((size * (x - .055), size * .445, size * (x + .055), size * .555), outline=None, fill=fg, width=0)
        elif name == "view":
            for row in range(2):
                for col in range(2):
                    rectangle((size*(.15+col*.39), size*(.15+row*.39),
                               size*(.45+col*.39), size*(.45+row*.39)), outline=accent, radius=size*.03)
        elif name == "sort":
            for y, length in ((.25,.58),(.50,.42),(.75,.26)):
                poly([(size*.18,size*y),(size*length,size*y)])
            poly([(size*.78,size*.20),(size*.78,size*.80)], accent)
            draw.polygon([(int(size*.66*s),int(size*.68*s)),(int(size*.90*s),int(size*.68*s)),
                          (int(size*.78*s),int(size*.86*s))],fill=accent)
        elif name in {"ascending", "descending"}:
            if name == "ascending":
                poly([(size*.50,size*.80),(size*.50,size*.20)], accent)
                draw.polygon([(int(size*.35*s),int(size*.34*s)),(int(size*.65*s),int(size*.34*s)),
                              (int(size*.50*s),int(size*.14*s))],fill=accent)
            else:
                poly([(size*.50,size*.20),(size*.50,size*.80)], accent)
                draw.polygon([(int(size*.35*s),int(size*.66*s)),(int(size*.65*s),int(size*.66*s)),
                              (int(size*.50*s),int(size*.86*s))],fill=accent)
        elif name == "open_image":
            rectangle((size * .12, size * .18, size * .88, size * .82), radius=size * .07)
            ellipse((size * .62, size * .29, size * .73, size * .40), outline=None, fill=accent, width=0)
            poly([(size * .20, size * .69), (size * .38, size * .48), (size * .51, size * .61),
                  (size * .64, size * .49), (size * .80, size * .69)], accent)
        elif name == "folder":
            draw.polygon([(int(size * .10 * s), int(size * .30 * s)), (int(size * .39 * s), int(size * .30 * s)),
                          (int(size * .47 * s), int(size * .20 * s)), (int(size * .88 * s), int(size * .20 * s)),
                          (int(size * .88 * s), int(size * .78 * s)), (int(size * .10 * s), int(size * .78 * s))],
                         outline=fg, fill=None)
            poly([(size * .10, size * .39), (size * .88, size * .39)], accent)
        elif name == "computer":
            rectangle((size * .10, size * .14, size * .90, size * .70), outline=fg, radius=size * .05)
            rectangle((size * .18, size * .22, size * .82, size * .61), outline=accent, radius=size * .02)
            poly([(size * .50, size * .70), (size * .50, size * .82)], muted)
            poly([(size * .32, size * .84), (size * .68, size * .84)], fg)
        elif name == "save":
            rectangle((size * .15, size * .13, size * .85, size * .87), radius=size * .05)
            rectangle((size * .29, size * .13, size * .69, size * .38), outline=accent)
            rectangle((size * .28, size * .58, size * .72, size * .87), outline=fg)
        elif name == "print":
            rectangle((size * .25, size * .10, size * .75, size * .38), outline=muted, radius=size * .025)
            rectangle((size * .14, size * .34, size * .86, size * .72), radius=size * .07)
            rectangle((size * .25, size * .61, size * .75, size * .90), outline=accent, radius=size * .025)
            ellipse((size * .70, size * .43, size * .77, size * .50), outline=None, fill=accent, width=0)
        elif name == "copy":
            rectangle((size*.30,size*.18,size*.82,size*.70),outline=muted,radius=size*.04)
            rectangle((size*.16,size*.32,size*.68,size*.84),outline=accent,radius=size*.04)
        elif name == "delete":
            rectangle((size*.25,size*.28,size*.75,size*.86),outline=fg,radius=size*.04)
            poly([(size*.18,size*.25),(size*.82,size*.25)],accent)
            poly([(size*.38,size*.14),(size*.62,size*.14)],accent)
        elif name == "rename":
            poly([(size*.20,size*.75),(size*.34,size*.70),(size*.76,size*.28),(size*.64,size*.16),(size*.22,size*.58),(size*.20,size*.75)],accent)
        elif name == "location":
            rectangle((size*.12,size*.24,size*.88,size*.80),outline=muted,radius=size*.05)
            poly([(size*.48,size*.58),(size*.84,size*.22)],accent)
            poly([(size*.63,size*.22),(size*.84,size*.22),(size*.84,size*.43)],accent)
        elif name in {"flip_h", "flip_v"}:
            if name == "flip_h":
                poly([(size * .50, size * .12), (size * .50, size * .88)], muted)
                draw.polygon([(int(size * .16 * s), int(size * .50 * s)), (int(size * .42 * s), int(size * .27 * s)),
                              (int(size * .42 * s), int(size * .73 * s))], outline=fg)
                draw.polygon([(int(size * .84 * s), int(size * .50 * s)), (int(size * .58 * s), int(size * .27 * s)),
                              (int(size * .58 * s), int(size * .73 * s))], outline=accent)
            else:
                poly([(size * .12, size * .50), (size * .88, size * .50)], muted)
                draw.polygon([(int(size * .50 * s), int(size * .16 * s)), (int(size * .27 * s), int(size * .42 * s)),
                              (int(size * .73 * s), int(size * .42 * s))], outline=fg)
                draw.polygon([(int(size * .50 * s), int(size * .84 * s)), (int(size * .27 * s), int(size * .58 * s)),
                              (int(size * .73 * s), int(size * .58 * s))], outline=accent)
        elif name == "brightness":
            ellipse((size * .34, size * .34, size * .66, size * .66), outline=accent)
            for dx, dy in ((0, -.38), (.27, -.27), (.38, 0), (.27, .27), (0, .38), (-.27, .27), (-.38, 0), (-.27, -.27)):
                poly([(size * (.50 + dx * .72), size * (.50 + dy * .72)),
                      (size * (.50 + dx), size * (.50 + dy))])
        elif name == "contrast":
            ellipse((size * .16, size * .16, size * .84, size * .84))
            draw.pieslice(tuple(int(v * s) for v in (size * .16, size * .16, size * .84, size * .84)),
                          start=90, end=270, fill=accent)
        elif name == "theme":
            ellipse((size * .14, size * .14, size * .86, size * .86))
            for x, y, color in ((.36, .34, accent), (.64, .34, muted), (.34, .62, fg)):
                ellipse((size * (x - .07), size * (y - .07), size * (x + .07), size * (y + .07)), outline=None, fill=color, width=0)
        elif name == "panel":
            rectangle((size * .12, size * .16, size * .88, size * .84), radius=size * .05)
            poly([(size * .38, size * .16), (size * .38, size * .84)], accent)
        elif name == "shortcuts":
            rectangle((size * .10, size * .22, size * .90, size * .78), radius=size * .08)
            for row in range(2):
                for col in range(4):
                    rectangle((size * (.20 + col * .16), size * (.34 + row * .18),
                               size * (.29 + col * .16), size * (.41 + row * .18)), outline=accent, width=max(2, line // 2))
        elif name == "gif":
            rectangle((size * .10, size * .22, size * .90, size * .78), radius=size * .08)
            poly([(size * .32, size * .50), (size * .45, size * .38), (size * .45, size * .62)], accent)
            poly([(size * .55, size * .38), (size * .68, size * .50), (size * .55, size * .62)], accent)

        image = image.resize((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image, master=self.root)


class ToolTip:
    """Small native tooltip used by every icon-first toolbar button."""

    def __init__(self, widget: tk.Widget, text: Union[str, Callable[[], str]]) -> None:
        self.widget = widget
        self.text = text
        self.tip: Optional[tk.Toplevel] = None
        self._after_id: Optional[str] = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        self._cancel_pending()
        self._after_id = self.widget.after(420, self._display)

    def _display(self) -> None:
        self._after_id = None
        text = self.text() if callable(self.text) else self.text
        if self.tip or not text:
            return
        x = self.widget.winfo_rootx() + 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 7
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        self.tip.wm_attributes("-topmost", True)
        ttk.Label(
            self.tip, text=text, style="Tooltip.TLabel", padding=(9, 5),
            wraplength=680, justify=tk.LEFT,
        ).pack()

    def _hide(self, _event=None) -> None:
        self._cancel_pending()
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None

    def _cancel_pending(self) -> None:
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None


def _bind_icon_glow(widget: tk.Widget) -> None:
    """Mark a stable icon control; ttk's active state paints its hover glow."""
    widget._croweyes_stable_hover = True  # type: ignore[attr-defined]


def _tool_button(
    parent: tk.Widget,
    text: str,
    tooltip: str,
    command,
    width: int = 2,
    image: Optional[ImageTk.PhotoImage] = None,
) -> ttk.Button:
    button = ttk.Button(
        parent, text=text, image=image, compound=tk.LEFT,
        command=command, width=width, style="Icon.Tool.TButton",
    )
    button._croweyes_image = image  # type: ignore[attr-defined]
    # ttkbootstrap may normalize an as-yet undefined custom style to TButton.
    # _apply_theme restores this marker after all product styles are defined.
    button._croweyes_style = "Icon.Tool.TButton"  # type: ignore[attr-defined]
    button._croweyes_tooltip = ToolTip(button, tooltip)  # type: ignore[attr-defined]
    _bind_icon_glow(button)
    return button


class _LegacyCrowEyesToolbar(ttk.Frame):
    """Brand/header area and the viewer's primary commands."""

    def __init__(self, master: tk.Widget, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(master, style="Toolbar.TFrame", padding=(14, 8))
        self.viewer = viewer
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)

        brand = ttk.Frame(self, style="Toolbar.TFrame")
        brand.grid(row=0, column=0, sticky="w", padx=(0, 18))
        viewer._brand_logo_label = ttk.Label(brand, image=viewer._icons["eye"], style="Logo.TLabel")
        viewer._brand_logo_label.pack(side=tk.LEFT, padx=(0, 9))
        viewer._brand_label = ttk.Label(brand, text="CrowEyes", style="Brand.TLabel")
        viewer._brand_label.pack(side=tk.LEFT)

        buttons = ttk.Frame(self, style="Toolbar.TFrame")
        buttons.grid(row=0, column=1, sticky="w")
        viewer._toolbar_primary = buttons
        viewer._toolbar_actions = buttons
        viewer._toolbar_buttons = []
        specs = [
            ("previous", "이전 이미지 (←)", viewer._action(viewer.prev_image)),
            ("next", "다음 이미지 (→)", viewer._action(viewer.next_image)),
            ("fit", "화면 맞춤 (Ctrl+1)", viewer._action(viewer.fit_to_window)),
            ("actual", "원본 크기 (Ctrl+0)", viewer._action(viewer.actual_size)),
            ("zoom_in", "확대 (+)", viewer._action(lambda: viewer.zoom_by(1.15))),
            ("zoom_out", "축소 (-)", viewer._action(lambda: viewer.zoom_by(1 / 1.15))),
            ("rotate_right", "오른쪽으로 회전 (Ctrl+R)", viewer._action(lambda: viewer.rotate(90))),
            ("fullscreen", "이미지 전체화면 (F11)", viewer.toggle_image_fullscreen),
        ]
        for icon_name, tip, command in specs:
            button = _tool_button(buttons, "", tip, command, width=1, image=viewer._icons[icon_name])
            button.pack(side=tk.LEFT, padx=(0, 4))
            viewer._toolbar_buttons.append(button)

        viewer._slide_btn = _tool_button(
            buttons, "", "슬라이드쇼 재생/일시정지 (F5)", viewer.toggle_slideshow, width=1,
            image=viewer._icons["play"],
        )
        viewer._slide_btn.pack(side=tk.LEFT, padx=(0, 4))
        viewer._toolbar_buttons.append(viewer._slide_btn)
        info_button = _tool_button(
            buttons, "", "정보 패널 표시/숨기기 (F8)", viewer.toggle_info_panel,
            width=1, image=viewer._icons["info"],
        )
        info_button.pack(side=tk.LEFT, padx=(0, 4))
        viewer._toolbar_buttons.append(info_button)
        settings_button = _tool_button(
            buttons, "", "환경설정 (Ctrl+,)", viewer._action(viewer.show_preferences),
            width=1, image=viewer._icons["settings"],
        )
        settings_button.pack(side=tk.LEFT, padx=(0, 4))
        viewer._toolbar_buttons.append(settings_button)
        more = ttk.Menubutton(buttons, image=viewer._icons["more"], width=1, style="Tool.TButton")
        more._croweyes_style = "Tool.TButton"  # type: ignore[attr-defined]
        menu = tk.Menu(more, tearoff=0)
        menu.add_command(label="이미지 열기…", image=viewer._icons["open_image"], compound=tk.LEFT,
                         accelerator="Ctrl+O", command=viewer._action(viewer.open_file_dialog))
        menu.add_command(label="폴더 열기…", image=viewer._icons["folder"], compound=tk.LEFT,
                         accelerator="Ctrl+Shift+O", command=viewer._action(viewer.open_folder_dialog))
        menu.add_separator()
        menu.add_command(label="왼쪽으로 회전", image=viewer._icons["rotate_left"], compound=tk.LEFT,
                         command=viewer._action(lambda: viewer.rotate(-90)))
        menu.add_command(label="좌우 반전", image=viewer._icons["flip_h"], compound=tk.LEFT,
                         command=viewer._action(viewer.toggle_flip_h))
        menu.add_command(label="상하 반전", image=viewer._icons["flip_v"], compound=tk.LEFT,
                         command=viewer._action(viewer.toggle_flip_v))
        menu.add_separator()
        menu.add_command(label="다른 이름으로 저장…", image=viewer._icons["save"], compound=tk.LEFT,
                         accelerator="Ctrl+S", command=viewer._action(viewer.save_as))
        menu.add_command(label="인쇄…", image=viewer._icons["print"], compound=tk.LEFT,
                         accelerator="Ctrl+P", command=viewer._action(viewer.print_current_image))
        more["menu"] = menu
        more.pack(side=tk.LEFT)
        viewer._toolbar_buttons.append(more)
        more._croweyes_tooltip = ToolTip(more, "더 보기 · 추가 명령")  # type: ignore[attr-defined]


class NavigationBar(ttk.Frame):
    """Windows 11-inspired folder navigation, breadcrumb, and live search row."""

    def __init__(self, master: tk.Widget, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(master, style="Chrome.TFrame", padding=(12, 7))
        self.columnconfigure(1, weight=1)
        nav = ttk.Frame(self, style="Chrome.TFrame")
        nav.grid(row=0, column=0, sticky="w", padx=(0, 8))
        for icon, tip, command in (
            ("refresh", "현재 위치 새로고침", viewer.refresh_folder),
            ("computer", "내 컴퓨터 · 드라이브와 사용자 폴더", viewer.navigate_to_computer),
        ):
            button = _tool_button(nav, "", tip, viewer._action(command), 1, viewer._icons[icon])
            button.pack(side=tk.LEFT, padx=(0, 3))
            viewer._navigation_buttons.append(button)

        viewer._breadcrumb_frame = ttk.Frame(self, style="Chrome.TFrame", padding=(0, 0))
        viewer._breadcrumb_frame.grid(row=0, column=1, sticky="ew", padx=(0, 10))

        search_wrap = ttk.Frame(self, style="Chrome.TFrame")
        search_wrap.grid(row=0, column=2, sticky="e")
        ttk.Label(search_wrap, image=viewer._icons["search"], style="Chrome.TLabel").pack(side=tk.LEFT, padx=(0, 5))
        viewer._top_search = ttk.Entry(search_wrap, textvariable=viewer._search_var, width=25, style="Search.TEntry")
        viewer._top_search.pack(side=tk.LEFT, ipady=0)
        viewer._top_search.bind("<KeyRelease>", viewer._apply_playlist_filter)
        viewer._top_search.bind("<Escape>", lambda _e: (viewer._search_var.set(""), viewer._apply_playlist_filter()))
        ToolTip(viewer._top_search, "현재 폴더의 파일·하위 폴더 이름을 즉시 검색")


class CrowEyesToolbar(ttk.Frame):
    """Responsive command bar separating immediate actions from option menus."""

    def __init__(self, master: tk.Widget, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(master, style="Toolbar.TFrame", padding=(12, 7))
        self.viewer = viewer
        viewer._toolbar_buttons = []
        viewer._responsive_buttons = []
        viewer._responsive_dropdowns = []
        viewer._responsive_hide_narrow = []

        brand = ttk.Frame(self, style="Toolbar.TFrame")
        brand.pack(side=tk.LEFT, padx=(0, 12))
        viewer._brand_logo_label = ttk.Label(brand, image=viewer._icons["eye"], style="Logo.TLabel")
        viewer._brand_logo_label.pack(side=tk.LEFT, padx=(0, 6))
        viewer._brand_label = ttk.Label(brand, text="CrowEyes", style="Brand.TLabel")
        viewer._brand_label.pack(side=tk.LEFT)

        buttons = ttk.Frame(self, style="Toolbar.TFrame")
        buttons.pack(side=tk.LEFT, fill=tk.X)
        viewer._toolbar_primary = viewer._toolbar_actions = buttons

        def immediate(
            icon: str, tip: str, command, hide_narrow: bool = False,
            interrupt_slideshow: bool = True,
        ) -> ttk.Button:
            callback = viewer._action(command) if interrupt_slideshow else command
            button = _tool_button(buttons, "", tip, callback, 1, viewer._icons[icon])
            button.pack(side=tk.LEFT, padx=(0, 4))
            viewer._toolbar_buttons.append(button)
            viewer._responsive_buttons.append((button, "", 1))
            if hide_narrow:
                viewer._responsive_hide_narrow.append(button)
            return button

        immediate("open_image", "이미지 열기 (Ctrl+O)", viewer.open_file_dialog)
        immediate("folder", "폴더로 보기 (Ctrl+Shift+O)", viewer.open_folder_dialog)
        immediate("save", "다른 형식으로 저장 (Ctrl+S)", viewer.save_as, True)
        immediate("print", "인쇄 미리보기 및 프린터 선택 (Ctrl+P)", viewer.print_current_image, True)
        ttk.Separator(buttons, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=4)
        immediate("fit", "화면 맞춤 (Ctrl+1)", viewer.fit_to_window, True)
        immediate("actual", "원본 크기 (Ctrl+0)", viewer.actual_size, True)
        immediate("zoom_in", "확대 (+)", lambda: viewer.zoom_by(1.15))
        immediate("zoom_out", "축소 (-)", lambda: viewer.zoom_by(1 / 1.15))
        viewer._slide_btn = immediate(
            "play", "슬라이드쇼 재생/정지 (F5)", viewer.toggle_slideshow,
            interrupt_slideshow=False,
        )

        def dropdown(icon: str, tip: str) -> Tuple[ttk.Menubutton, tk.Menu]:
            button = ttk.Menubutton(
                buttons, image=viewer._icons[icon], text="", compound=tk.LEFT,
                style="Icon.Tool.TButton", width=1,
            )
            button._croweyes_image = viewer._icons[icon]  # type: ignore[attr-defined]
            button._croweyes_style = "Icon.Tool.TButton"  # type: ignore[attr-defined]
            menu = tk.Menu(button, tearoff=0)
            button.configure(menu=menu)
            button.pack(side=tk.LEFT, padx=(0, 4))
            viewer._toolbar_buttons.append(button)
            viewer._responsive_dropdowns.append((button, ""))
            button._croweyes_tooltip = ToolTip(button, tip)  # type: ignore[attr-defined]
            _bind_icon_glow(button)
            return button, menu

        _view_button, view = dropdown("view", "플레이리스트 보기 방식 및 패널 설정")
        for key in LIST_MODES:
            view.add_radiobutton(
                label=LIST_MODE_LABELS[key], variable=viewer._list_mode_var, value=key,
                command=lambda mode=key: viewer.set_list_mode(mode),
            )
        view.add_separator()
        view.add_checkbutton(label="PLAYLIST 패널", variable=viewer._playlist_panel_var, command=viewer.toggle_playlist_panel)
        view.add_checkbutton(label="정보 패널", variable=viewer._info_panel_var, command=viewer.toggle_info_panel)

        _sort_button, sorting = dropdown("sort", "파일 정렬 기준 및 방향")
        for key in SORT_KEYS:
            sorting.add_radiobutton(
                label=SORT_LABELS[key], variable=viewer._sort_var, value=key,
                command=lambda sort_key=key: viewer.set_sort(sort_key),
            )
        sorting.add_separator()
        sorting.add_radiobutton(label="오름차순", variable=viewer._sort_desc_var, value=False, command=lambda: viewer.set_sort_direction(False))
        sorting.add_radiobutton(label="내림차순", variable=viewer._sort_desc_var, value=True, command=lambda: viewer.set_sort_direction(True))

        _transform_button, transform = dropdown("rotate_right", "회전 및 반전")
        transform.add_command(label="오른쪽 회전", image=viewer._icons["rotate_right"], compound=tk.LEFT, command=viewer._action(lambda: viewer.rotate(90)))
        transform.add_command(label="왼쪽 회전", image=viewer._icons["rotate_left"], compound=tk.LEFT, command=viewer._action(lambda: viewer.rotate(-90)))
        transform.add_command(label="좌우 반전", image=viewer._icons["flip_h"], compound=tk.LEFT, command=viewer._action(viewer.toggle_flip_h))
        transform.add_command(label="상하 반전", image=viewer._icons["flip_v"], compound=tk.LEFT, command=viewer._action(viewer.toggle_flip_v))

        viewer._responsive_hide_narrow.append(_transform_button)
        _more_button, more = dropdown("more", "더 보기 · 파일 관리 및 환경설정")
        more.add_command(label="다른 형식으로 저장… (Ctrl+S)", image=viewer._icons["save"], compound=tk.LEFT, command=viewer.save_as)
        more.add_command(label="인쇄 미리보기… (Ctrl+P)", image=viewer._icons["print"], compound=tk.LEFT, command=viewer.print_current_image)
        more.add_separator()
        more.add_command(label="이름 바꾸기 (F2)", image=viewer._icons["rename"], compound=tk.LEFT, command=viewer.rename_selected_file)
        more.add_command(label="휴지통으로 삭제 (Delete)", image=viewer._icons["delete"], compound=tk.LEFT, command=viewer.delete_selected_files)
        more.add_command(label="파일 위치 열기", image=viewer._icons["location"], compound=tk.LEFT, command=viewer.open_selected_file_location)
        more.add_separator()
        more.add_command(label="이미지 전체화면 (F11)", command=viewer.toggle_image_fullscreen)
        more.add_command(label="환경설정", image=viewer._icons["settings"], compound=tk.LEFT, command=viewer.show_preferences)
        more.add_command(label="기본 앱 등록", command=viewer.show_file_association_dialog)
        more.add_command(label="Windows 실행 차단 안내", command=viewer.show_windows_security_help)
        more.add_command(label="업데이트 확인", command=lambda: viewer.check_for_updates(manual=True))
        more.add_command(label="CrowEyes 정보", command=viewer.show_about)
        viewer._toolbar_pack_layout = []
        for widget in buttons.pack_slaves():
            info = dict(widget.pack_info())
            info.pop("in", None)
            viewer._toolbar_pack_layout.append((widget, info))


class PlaylistPanel(ttk.Frame):
    """Playlist controls and the lazily populated list container."""

    def __init__(self, master: tk.Widget, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(master, style="Card.TFrame", padding=12)
        self.viewer = viewer
        header = ttk.Frame(self, style="Panel.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(header, text="PLAYLIST", style="Section.TLabel").pack(side=tk.LEFT)
        close = tk.Button(
            header, image=viewer._icons["close"], command=viewer.hide_playlist_panel,
            bd=0, relief=tk.FLAT, cursor="hand2", padx=4, pady=4,
        )
        close._croweyes_image = viewer._icons["close"]  # type: ignore[attr-defined]
        close.pack(side=tk.RIGHT)
        viewer._playlist_close_btn = close
        ToolTip(close, "플레이리스트 닫기")
        ttk.Label(
            header, textvariable=viewer._playlist_count_var, style="Badge.TLabel",
        ).pack(side=tk.RIGHT, padx=(0, 6))

        viewer.list_container = ttk.Frame(self, style="Panel.TFrame")
        viewer.list_container.pack(fill=tk.BOTH, expand=True, pady=(8, 0))


class ImageCanvasView(ttk.Frame):
    """Central image surface; transformation logic stays on the viewer."""

    def __init__(self, master: tk.Widget, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(master, style="Viewer.TFrame", padding=0)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        viewer.canvas = tk.Canvas(self, highlightthickness=0, bd=0, cursor="arrow")
        viewer.canvas.grid(row=0, column=0, sticky="nsew")
        viewer.canvas.bind("<Configure>", viewer._on_canvas_resize)
        viewer.canvas.bind("<MouseWheel>", viewer._on_mousewheel)
        viewer.canvas.bind("<Button-4>", viewer._on_mousewheel)
        viewer.canvas.bind("<Button-5>", viewer._on_mousewheel)
        viewer.canvas.bind("<Button-1>", lambda _event: viewer.canvas.focus_set(), add="+")
        viewer.canvas.bind("<ButtonPress-1>", viewer._pan_start)
        viewer.canvas.bind("<B1-Motion>", viewer._pan_move)
        viewer.canvas.bind("<ButtonRelease-1>", viewer._pan_end)
        viewer.canvas.bind("<Motion>", viewer._on_motion)
        viewer.canvas.bind("<Double-Button-1>", lambda _e: viewer.toggle_animation())
        viewer.canvas.bind("<Button-3>", viewer.show_image_context_menu)

        def navigation_button(text: str, command, tooltip: str) -> tk.Button:
            button = tk.Button(
                self, text=text, command=viewer._action(command),
                font=("Segoe UI Symbol", 24, "bold"), width=2, height=1,
                bd=0, relief=tk.FLAT, cursor="hand2", takefocus=False,
                highlightthickness=1,
            )
            ToolTip(button, tooltip)
            button.bind("<Enter>", lambda _e, item=button: viewer._style_canvas_nav_button(item, True))
            button.bind("<Leave>", lambda _e, item=button: viewer._style_canvas_nav_button(item, False))
            return button

        viewer._canvas_prev_btn = navigation_button("‹", viewer.prev_image, "이전 이미지 (←)")
        viewer._canvas_next_btn = navigation_button("›", viewer.next_image, "다음 이미지 (→)")
        viewer._update_canvas_navigation_buttons()


class InfoPanel(ttk.Frame):
    """Scrollable information card."""

    def __init__(self, master: tk.Widget, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(master, style="Card.TFrame", padding=0)
        title = ttk.Frame(self, style="Panel.TFrame", padding=(12, 10))
        title.pack(fill=tk.X)
        ttk.Label(title, text="IMAGE INFO", style="Section.TLabel").pack(side=tk.LEFT)
        close = tk.Button(
            title, image=viewer._icons["close"], command=viewer.hide_info_panel,
            bd=0, relief=tk.FLAT, cursor="hand2", padx=4, pady=4,
        )
        close._croweyes_image = viewer._icons["close"]  # type: ignore[attr-defined]
        close.pack(side=tk.RIGHT)
        viewer._info_close_btn = close
        body = ttk.Frame(self, style="Panel.TFrame", padding=(10, 0, 10, 10))
        body.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(body, orient=tk.VERTICAL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        viewer.info_text = tk.Text(
            body, width=22, height=20, wrap=tk.WORD, state=tk.DISABLED,
            bd=0, padx=10, pady=10, yscrollcommand=scroll.set,
        )
        viewer.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.configure(command=viewer.info_text.yview)


class ContextControlBar(ttk.Frame):
    """Image-specific adjustments kept out of the global toolbar."""

    def __init__(self, master: tk.Widget, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(master, style="BottomBar.TFrame", padding=(12, 7))
        self.viewer = viewer
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=0)
        viewer.status = ttk.Label(
            self, text="Pixel (—, —)  #------", style="Status.TLabel",
            anchor="w", width=27,
        )
        viewer.status.grid(row=0, column=0, sticky="ew")

        viewer._zoom_label = ttk.Label(
            self, textvariable=viewer._zoom_text_var, style="BottomBar.TLabel",
            anchor="w", width=10,
        )
        viewer._zoom_label.grid(row=0, column=1, padx=(8, 8), sticky="w")

        viewer._path_label = ttk.Label(
            self, textvariable=viewer._current_path_var, style="Path.TLabel",
            width=1, anchor="w",
        )
        viewer._path_label.grid(row=0, column=2, padx=(0, 14), sticky="ew")
        ToolTip(viewer._path_label, lambda: viewer._current_path_var.get())

        controls = ttk.Frame(self, style="BottomBar.TFrame")
        controls.grid(row=0, column=3, sticky="e")
        viewer._safety_indicator = ttk.Label(
            controls, textvariable=viewer._content_filter_status_var,
            style="Badge.TLabel",
        )
        viewer._safety_indicator.pack(side=tk.LEFT, padx=(0, 10))
        ttk.Label(controls, text="밝기", style="BottomBar.TLabel").pack(side=tk.LEFT, padx=(0, 4))
        viewer.bright_var = tk.DoubleVar(value=1.0)
        viewer._brightness_scale = ttk.Scale(
            controls, from_=0.2, to=2.0, variable=viewer.bright_var, length=56,
            command=viewer._on_adjust, style="CrowEyes.Horizontal.TScale",
        )
        viewer._brightness_scale.pack(side=tk.LEFT)
        ttk.Label(controls, text="대비", style="BottomBar.TLabel").pack(side=tk.LEFT, padx=(10, 4))
        viewer.contrast_var = tk.DoubleVar(value=1.0)
        viewer._contrast_scale = ttk.Scale(
            controls, from_=0.2, to=2.0, variable=viewer.contrast_var, length=56,
            command=viewer._on_adjust, style="CrowEyes.Horizontal.TScale",
        )
        viewer._contrast_scale.pack(side=tk.LEFT)
        ttk.Label(controls, textvariable=viewer._rotation_text_var, style="BottomBar.TLabel", width=6).pack(side=tk.LEFT, padx=(10, 2))
        viewer._anim_btn = _tool_button(
            controls, "", "GIF/WebP 재생/일시정지 (Space)", viewer.toggle_animation,
            image=viewer._icons["gif"],
        )
        viewer._anim_btn.pack(side=tk.LEFT, padx=2)


class PrintPreview(tk.Toplevel):
    """One-page preview using the same layout calculation as actual printing."""

    PAPER_MM = {"A4": (210, 297), "Letter": (216, 279)}

    def __init__(self, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(viewer)
        self.viewer = viewer
        self.title("인쇄 미리보기 · CrowEyes")
        self.geometry("1020x720")
        self.minsize(820, 600)
        self.transient(viewer)
        self.printer_names = enumerate_printer_names()
        default_printer = get_default_printer_name()
        remembered_printer = str(viewer.settings.get("print_printer", ""))
        selected_printer = remembered_printer if remembered_printer in self.printer_names else default_printer
        if selected_printer not in self.printer_names and self.printer_names:
            selected_printer = self.printer_names[0]
        self.printer_var = tk.StringVar(value=selected_printer)
        self.paper_var = tk.StringVar(value=str(viewer.settings.get("print_paper", "A4")))
        self.orientation_var = tk.StringVar(value=str(viewer.settings.get("print_orientation", "portrait")))
        self.scale_var = tk.StringVar(value=str(viewer.settings.get("print_scale_mode", "fit")))
        self.copies_var = tk.IntVar(value=max(1, int(viewer.settings.get("print_copies", 1))))
        self.print_to_file_var = tk.BooleanVar(value=False)
        self.save_defaults_var = tk.BooleanVar(value=False)
        self.preview_photo: Optional[ImageTk.PhotoImage] = None

        body = ttk.Frame(self, padding=14, style="Panel.TFrame")
        body.pack(fill=tk.BOTH, expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.preview = tk.Canvas(body, bg="#171A1E", highlightthickness=0)
        self.preview.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.preview.bind("<Configure>", lambda _e: self.after_idle(self.redraw_preview))

        side = ttk.Frame(body, padding=18, style="Card.TFrame")
        side.grid(row=0, column=1, sticky="ns")
        ttk.Label(side, text="인쇄 설정", style="Title.TLabel").pack(anchor="w", pady=(0, 18))
        self._field(side, "프린터")
        printer = ttk.Combobox(
            side, textvariable=self.printer_var, values=self.printer_names,
            state="readonly", width=28,
        )
        printer.pack(fill=tk.X, pady=(0, 14))
        self._field(side, "용지")
        paper = ttk.Combobox(side, textvariable=self.paper_var, values=("A4", "Letter"), state="readonly", width=22)
        paper.pack(fill=tk.X, pady=(0, 14))
        self._field(side, "방향")
        for text, value in (("세로", "portrait"), ("가로", "landscape")):
            ttk.Radiobutton(side, text=text, variable=self.orientation_var, value=value, command=self.redraw_preview).pack(anchor="w")
        self._field(side, "매수", top=14)
        ttk.Spinbox(side, from_=1, to=999, textvariable=self.copies_var, width=8).pack(anchor="w")
        self._field(side, "크기", top=14)
        for text, value in (("페이지에 맞춤", "fit"), ("원본 크기 (96 DPI)", "actual")):
            ttk.Radiobutton(side, text=text, variable=self.scale_var, value=value, command=self.redraw_preview).pack(anchor="w")
        paper.bind("<<ComboboxSelected>>", lambda _e: self.redraw_preview())

        ttk.Checkbutton(side, text="파일로 출력 (.prn)", variable=self.print_to_file_var).pack(anchor="w", pady=(14, 0))
        ttk.Checkbutton(
            side, text="앱에서 인쇄 기본 설정 변경", variable=self.save_defaults_var,
        ).pack(anchor="w", pady=(5, 0))
        ttk.Separator(side).pack(fill=tk.X, pady=16)
        ttk.Button(side, text="인쇄", style="Accent.TButton", command=self.do_print).pack(fill=tk.X, ipady=4)
        ttk.Button(side, text="닫기", command=self.destroy).pack(fill=tk.X, pady=(8, 0))
        self.after_idle(self.redraw_preview)

    @staticmethod
    def _field(parent: tk.Widget, text: str, top: int = 0) -> None:
        ttk.Label(parent, text=text, style="Section.TLabel").pack(anchor="w", pady=(top, 5))

    def _paper_size(self) -> Tuple[int, int]:
        width, height = self.PAPER_MM[self.paper_var.get()]
        if self.orientation_var.get() == "landscape":
            width, height = height, width
        return width, height

    def redraw_preview(self) -> None:
        if not self.winfo_exists() or self.viewer.display_image is None:
            return
        self.preview.delete("all")
        cw, ch = max(320, self.preview.winfo_width()), max(320, self.preview.winfo_height())
        paper_w, paper_h = self._paper_size()
        scale = min((cw - 80) / paper_w, (ch - 70) / paper_h)
        pw, ph = max(1, int(paper_w * scale)), max(1, int(paper_h * scale))
        px, py = (cw - pw) // 2, (ch - ph) // 2
        self.preview.create_rectangle(px + 7, py + 8, px + pw + 7, py + ph + 8, fill="#08090A", outline="")
        self.preview.create_rectangle(px, py, px + pw, py + ph, fill="white", outline="#B9BDC3")
        margin = max(8, int(min(pw, ph) * 0.055))
        area_w, area_h = max(1, pw - margin * 2), max(1, ph - margin * 2)
        image = self.viewer.display_image.copy()
        rect = calculate_print_rect(image.size, (area_w, area_h), self.scale_var.get(), (96, 96))
        left, top, right, bottom = rect
        draw_w, draw_h = max(1, right - left), max(1, bottom - top)
        visible_left, visible_top = max(0, left), max(0, top)
        visible_right, visible_bottom = min(area_w, right), min(area_h, bottom)
        if visible_right <= visible_left or visible_bottom <= visible_top:
            return
        rendered = image.resize((draw_w, draw_h), Image.Resampling.LANCZOS)
        if left < 0 or top < 0 or right > area_w or bottom > area_h:
            rendered = rendered.crop((visible_left - left, visible_top - top, visible_right - left, visible_bottom - top))
        self.preview_photo = ImageTk.PhotoImage(rendered)
        self.preview.create_image(px + margin + visible_left, py + margin + visible_top, image=self.preview_photo, anchor="nw")
        self.preview.create_rectangle(px + margin, py + margin, px + pw - margin, py + ph - margin, outline="#D7DADF")

    def do_print(self) -> None:
        printer_name = self.printer_var.get().strip()
        if not printer_name:
            messagebox.showwarning("인쇄", "사용할 프린터를 선택해 주세요.", parent=self)
            return
        output_path: Optional[str] = None
        if self.print_to_file_var.get():
            chosen = filedialog.asksaveasfilename(
                parent=self, title="인쇄 파일 저장", defaultextension=".prn",
                filetypes=(("Printer output", "*.prn"), ("모든 파일", "*.*")),
            )
            if not chosen:
                return
            output_path = chosen
        if self.save_defaults_var.get():
            self.viewer.settings.update({
                "print_printer": printer_name,
                "print_paper": self.paper_var.get(),
                "print_orientation": self.orientation_var.get(),
                "print_scale_mode": self.scale_var.get(),
                "print_copies": max(1, int(self.copies_var.get())),
            })
            save_settings(self.viewer.settings)
        if self.viewer._print_with_options(
            self.orientation_var.get(), self.paper_var.get(), self.scale_var.get(),
            printer_name=printer_name, copies=max(1, int(self.copies_var.get())),
            output_path=output_path, parent=self,
        ):
            self.destroy()


class CrowEyesImageViewer(tb.Window):
    def __init__(self, start_path: Optional[str] = None) -> None:
        # ttkbootstrap initializes localization immediately after Tk. Some
        # Anaconda builds ship msgcat but omit its Tcl module search path.
        tk.Tk.__init__ = _tk_init_with_anaconda_msgcat
        try:
            super().__init__(themename="darkly")
        finally:
            tk.Tk.__init__ = _ORIGINAL_TK_INIT
        self._dnd_available = False
        if TkinterDnD is not None:
            try:
                TkinterDnD._require(self)
                self._dnd_available = True
            except RuntimeError:
                pass
        self.settings = load_settings()
        self._icons = CrowEyesIconSet(self, self._theme())
        self.iconphoto(True, self._icons["app"])
        try:
            self.iconbitmap(default=str(resource_path("assets", "icons", "croweyes.ico")))
        except (OSError, tk.TclError):
            pass
        self.title(APP_TITLE)
        self.geometry(self.settings.get("window_geometry", "1120x760"))
        self.minsize(860, 520)
        self._image_fullscreen = False
        self._chrome_visible = True
        self._info_visible = bool(self.settings.get("show_info_panel", True))
        self._playlist_visible = bool(self.settings.get("show_playlist_panel", True))
        self._context_visible = bool(self.settings.get("show_context_bar", True))
        self._icon_cells: Dict[int, tk.Label] = {}
        self._folder_cells: Dict[str, tk.Label] = {}
        self._icon_grid_order: List[tk.Label] = []
        self._playlist_items: List[Tuple[str, Path, Optional[int]]] = []
        self._selected_folder_path: Optional[Path] = None
        self._grid_canvas: Optional[tk.Canvas] = None
        self._grid_inner: Optional[ttk.Frame] = None
        self._right_panel: Optional[ttk.Frame] = None
        self._center_panel: Optional[ttk.Frame] = None
        self._sashes_applied = False
        self._sash_init_job: Optional[str] = None
        self._canvas_resize_job: Optional[str] = None
        self._file_stat_cache: Dict[str, Tuple[float, int]] = {}
        self._filtered_indices: List[int] = []
        self._playlist_selection: Set[int] = set()
        self._selection_anchor: Optional[int] = None
        self._selection_press_snapshot: Optional[Set[int]] = None
        self._syncing_playlist_selection = False
        self._playlist_selection_sync_gen = 0
        self._image_load_gen = 0
        self._image_load_results: Dict[int, tuple] = {}
        self._decoded_cache: Dict[str, tuple] = {}
        self._decoded_cache_order: List[str] = []
        self._decoded_cache_lock = threading.RLock()
        self._image_prefetch_queue: List[Path] = []
        self._image_prefetch_pending: Set[str] = set()
        self._image_prefetch_results: Dict[str, tuple] = {}
        self._image_prefetch_active = False
        self._vector_render_gen = 0
        self._vector_render_results: Dict[int, tuple] = {}
        self._scan_results: Dict[int, tuple] = {}
        self._folder_dirs: List[Path] = []
        self._pending_playlist_build: Optional[Tuple[Path, Path, int]] = None
        self._update_results: Dict[int, tuple] = {}
        self._update_gen = 0
        self._folder_history: List[Path] = []
        self._folder_history_index = -1
        self._history_navigation = False
        self._navigation_buttons: List[ttk.Button] = []
        self._responsive_buttons: List[Tuple[ttk.Button, str, int]] = []
        self._responsive_dropdowns: List[Tuple[ttk.Menubutton, str]] = []
        self._responsive_hide_narrow: List[tk.Widget] = []
        self._toolbar_pack_layout: List[Tuple[tk.Widget, dict]] = []
        self._last_responsive_compact: Optional[int] = None

        self.folder_files: List[Path] = []
        self.index: int = -1
        self.current_folder: Optional[Path] = None
        self._playlist_gen: int = 0  # invalidate async jobs

        self.pil_image: Optional[Image.Image] = None
        self.anim_frames: List[Image.Image] = []
        self.anim_delays: List[int] = []
        self.anim_index: int = 0
        self.anim_job: Optional[str] = None
        self.anim_playing: bool = bool(self.settings.get("anim_playing", True))
        self.is_animated: bool = False

        self.display_image: Optional[Image.Image] = None
        self.tk_image: Optional[ImageTk.PhotoImage] = None
        self.source_type: str = "none"
        self.source_path: Optional[Path] = None
        self.source_logical_size: Tuple[float, float] = (1.0, 1.0)
        self.source_render_scale: float = 1.0
        self._vector_render_pending = False
        self.zoom: float = 1.0
        self._view_mode: str = "fit" if bool(self.settings.get("fit_on_open", True)) else "actual"
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.pan_start: Optional[Tuple[int, int]] = None
        self._region_copy_mode = False
        self._region_start: Optional[Tuple[int, int]] = None
        self._region_rect: Optional[int] = None
        self.brightness: float = 1.0
        self.contrast: float = 1.0
        self.rotation: int = 0
        self.flip_h: bool = False
        self.flip_v: bool = False
        self.slideshow_job: Optional[str] = None
        self._slideshow_active = False
        self._fit_next: bool = bool(self.settings.get("fit_on_open", True))
        self._startup_activation_pending = bool(start_path)

        # Content safety is entirely local and opt-in. ONNX Runtime and the
        # model stay unloaded until the user enables the filter.
        self._content_filter_mode = str(self.settings.get("content_filter", MODE_OFF))
        self._safety_manager: Optional[SafetyManager] = None
        self._safety_worker: Optional[SafetyWorker] = None
        self._safety_generation = 0
        self._safety_poll_job: Optional[str] = None
        self._content_safety_status = UNKNOWN
        self._content_safety_detail = ""
        self._blocked_crow_photo: Optional[ImageTk.PhotoImage] = None
        self._blocked_thumb_photo: Optional[ImageTk.PhotoImage] = None
        self._safety_thumb_pending: Set[str] = set()
        self._safety_known: Dict[str, str] = {}

        self.list_mode = self.settings.get("list_mode", "small")
        self.sort_by = self.settings.get("sort_by", "name")
        self.sort_desc = bool(self.settings.get("sort_desc", False))
        self._list_mode_var = tk.StringVar(value=self.list_mode)
        self._sort_var = tk.StringVar(value=self.sort_by)
        self._sort_desc_var = tk.BooleanVar(value=self.sort_desc)
        self._sort_dir_text_var = tk.StringVar(value="▼" if self.sort_desc else "▲")
        self._search_var = tk.StringVar(value="")
        self._folder_title_var = tk.StringVar(value="폴더를 선택하지 않음")
        self._file_title_var = tk.StringVar(value="이미지를 열어 주세요")
        self._current_path_var = tk.StringVar(value="경로 없음")
        self._zoom_text_var = tk.StringVar(value="크기 100%")
        self._playlist_count_var = tk.StringVar(value="0")
        self._playlist_panel_var = tk.BooleanVar(value=self._playlist_visible)
        self._info_panel_var = tk.BooleanVar(value=self._info_visible)
        self._rotation_text_var = tk.StringVar(value="0°")
        self._content_filter_status_var = tk.StringVar(
            value="Safety ON" if self._content_filter_mode == MODE_EXPLICIT else ""
        )

        # Lazy thumbs
        self._thumb_photos: Dict[str, ImageTk.PhotoImage] = {}  # path -> photo
        self._thumb_loaded: Set[str] = set()
        self._thumb_queue: List[int] = []
        self._thumb_job: Optional[str] = None
        self._thumb_decode_results: Dict[Tuple[int, int], tuple] = {}
        self._thumb_decode_active = False
        self._placeholder_photo: Optional[ImageTk.PhotoImage] = None

        self._list_widget: Optional[tk.Widget] = None
        self.left_panel: Optional[ttk.Frame] = None
        self.list_container: Optional[ttk.Frame] = None
        self._slide_btn: Optional[ttk.Button] = None
        self._list_scroll: Optional[ttk.Scrollbar] = None

        self._build_ui()
        self._apply_theme()
        self.after(0, self._apply_native_window_theme)
        self._bind_keys()
        self._rebuild_file_list_widget()
        self._update_header()
        # Native Tk list/canvas widgets are created after the first theme pass.
        self._apply_theme()
        self._update_slide_button()
        self._update_safety_indicator()

        if self._content_filter_mode == MODE_EXPLICIT:
            self._ensure_safety_worker()

        if start_path:
            self.open_path(Path(start_path))
            # File-association launches should accept arrow keys immediately,
            # even before the asynchronous image decoder has finished.
            self.after(80, self._activate_viewer_window)
        else:
            self.navigate_to_computer()

        if bool(self.settings.get("auto_register_associations", False)):
            self.after(250, self._auto_register_file_associations)

        if bool(self.settings.get("auto_check_updates", True)):
            last_check = float(self.settings.get("last_update_check", 0) or 0)
            if time.time() - last_check >= UPDATE_CHECK_INTERVAL:
                self.after(900, lambda: self.check_for_updates(manual=False))

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----- helpers: slideshow interrupt ------------------------------------

    def _is_slideshow(self) -> bool:
        return self._slideshow_active



    def _action(self, fn):
        """Wrap UI actions so slideshow stops first."""
        def wrapped(*args, **kwargs):
            self._interrupt_slideshow()
            return fn(*args, **kwargs)
        return wrapped

    def _style_canvas_nav_button(self, button: tk.Button, active: bool = False) -> None:
        """Paint an image-edge navigation button without changing its geometry."""
        t = self._theme()
        button.configure(
            bg=t["select"] if active else t["canvas_bg"],
            fg=t["accent_hi"],
            activebackground=t["select"], activeforeground=t["fg"],
            highlightbackground=t["accent"] if active else t["border"],
            highlightcolor=t["accent"],
        )

    def _update_canvas_navigation_buttons(self) -> None:
        """Show centered edge controls only when previous/next navigation is useful."""
        previous = getattr(self, "_canvas_prev_btn", None)
        following = getattr(self, "_canvas_next_btn", None)
        if previous is None or following is None:
            return
        self._style_canvas_nav_button(previous)
        self._style_canvas_nav_button(following)
        navigable = self.display_image is not None or self._content_safety_status in {BLOCKED, ERROR}
        if len(self.folder_files) >= 2 and navigable:
            previous.place(relx=0.0, rely=0.5, x=12, anchor="w")
            following.place(relx=1.0, rely=0.5, x=-12, anchor="e")
            previous.lift()
            following.lift()
        else:
            previous.place_forget()
            following.place_forget()

    # ----- theme / UI ------------------------------------------------------



    def _on_root_configure(self, event) -> None:
        if event.widget is not self:
            return
        if not self._sashes_applied and self.winfo_width() > 200:
            self._init_sashes()
        self._update_responsive_layout(event.width)

    def _update_responsive_layout(self, width: int) -> None:
        compact_level = 2 if width < 1120 else (1 if width < 1340 else 0)
        if compact_level != self._last_responsive_compact:
            self._last_responsive_compact = compact_level
            for button, full_text, priority in self._responsive_buttons:
                show_text = bool(full_text) and (compact_level == 0 or (compact_level == 1 and priority <= 1))
                try:
                    button.configure(text=full_text if show_text else "", width=max(1, len(full_text) + 1) if show_text else 1)
                except tk.TclError:
                    pass
            for button, full_text in self._responsive_dropdowns:
                try:
                    button.configure(text=(full_text + " ▼") if compact_level < 2 else "", width=max(4, len(full_text) + 2) if compact_level < 2 else 1)
                except tk.TclError:
                    pass
            if self._toolbar_pack_layout:
                for widget, _info in self._toolbar_pack_layout:
                    widget.pack_forget()
                hidden = set(self._responsive_hide_narrow) if compact_level >= 2 else set()
                for widget, info in self._toolbar_pack_layout:
                    if widget not in hidden:
                        widget.pack(**info)
            if hasattr(self, "_brand_label"):
                self._brand_label.configure(text="CrowEyes")
            if hasattr(self, "_top_search"):
                self._top_search.configure(width=25 if width >= 1180 else (16 if width >= 920 else 11))






    def _make_placeholder(self) -> None:
        t = self._theme()
        size = self._icon_cell_size() if self.list_mode == "icons" else 22
        ph = Image.new("RGBA", (size, size), self._hex_to_rgba(t["border"]))
        self._placeholder_photo = ImageTk.PhotoImage(ph)

    def _style_list_widget(self) -> None:
        t = self._theme()
        w = self._list_widget
        if isinstance(w, tk.Listbox):
            w.configure(
                bg=t["panel"], fg=t["fg"],
                selectbackground=t["select"], selectforeground=t["select_fg"],
                activestyle="none", highlightthickness=1,
                highlightbackground=t["border"], highlightcolor=t["accent"],
                bd=0, font=t["font"], relief=tk.FLAT,
            )

    def _keyboard_zoom(self, event, factor: float):
        """Zoom with plain +/- without stealing input from editable fields."""
        if isinstance(event.widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Spinbox, ttk.Combobox)):
            return None
        self._action(lambda: self.zoom_by(factor))()
        return "break"

    def _file_shortcut(self, event, command):
        if isinstance(event.widget, (tk.Entry, tk.Text, ttk.Entry, ttk.Spinbox, ttk.Combobox)):
            return None
        command()
        return "break"

    def _bind_keys(self) -> None:
        self.bind("<Control-o>", lambda e: self._action(self.open_file_dialog)())
        self.bind("<Control-O>", lambda e: self._action(self.open_file_dialog)())
        self.bind("<Control-Shift-O>", lambda e: self._action(self.open_folder_dialog)())
        self.bind("<Control-s>", lambda e: self._action(self.save_as)())
        self.bind("<Control-p>", lambda e: self._action(self.print_current_image)())
        self.bind("<Control-P>", lambda e: self._action(self.print_current_image)())
        self.bind("<Left>", lambda e: self._action(self.prev_image)())
        self.bind("<Right>", lambda e: self._action(self.next_image)())
        self.bind("<Home>", lambda e: self._action(lambda: self.goto_index(0))())
        self.bind("<End>", lambda e: self._action(lambda: self.goto_index(len(self.folder_files) - 1))())
        self.bind("<Control-0>", lambda e: self._action(self.actual_size)())
        self.bind("<Control-1>", lambda e: self._action(self.fit_to_window)())
        self.bind("<plus>", lambda e: self._keyboard_zoom(e, 1.15))
        self.bind("<KP_Add>", lambda e: self._keyboard_zoom(e, 1.15))
        self.bind("<minus>", lambda e: self._keyboard_zoom(e, 1 / 1.15))
        self.bind("<KP_Subtract>", lambda e: self._keyboard_zoom(e, 1 / 1.15))
        self.bind("<Control-r>", lambda e: self._action(lambda: self.rotate(90))())
        self.bind("<Control-l>", lambda e: self._action(lambda: self.rotate(-90))())
        self.bind("<F5>", lambda e: self.toggle_slideshow())
        self.bind("<F11>", lambda e: self.toggle_image_fullscreen())
        self.bind("<F8>", lambda e: self.toggle_info_panel())
        self.bind("<Escape>", lambda e: self._escape())
        self.bind("<Control-comma>", lambda e: self._action(self.show_preferences)())
        self.bind("<Control-c>", lambda e: self._file_shortcut(e, self.copy_selected_files))
        self.bind("<Control-C>", lambda e: self._file_shortcut(e, self.copy_selected_files))
        self.bind("<F2>", lambda e: self._file_shortcut(e, self.rename_selected_file))
        self.bind("<Delete>", lambda e: self._file_shortcut(e, self.delete_selected_files))
        self.bind("<space>", lambda e: self.toggle_animation())

    def _activate_viewer_window(self) -> None:
        """Bring a file-association launch forward and focus the image canvas."""
        try:
            self.deiconify()
            self.lift()
            self.update_idletasks()
            if os.name == "nt":
                import ctypes
                from ctypes import wintypes

                user32 = ctypes.windll.user32
                user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
                user32.GetAncestor.restype = wintypes.HWND
                user32.GetForegroundWindow.restype = wintypes.HWND
                user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
                user32.SetForegroundWindow.argtypes = [wintypes.HWND]
                user32.BringWindowToTop.argtypes = [wintypes.HWND]
                user32.SetActiveWindow.argtypes = [wintypes.HWND]
                user32.SetFocus.argtypes = [wintypes.HWND]
                user32.GetWindowThreadProcessId.argtypes = [
                    wintypes.HWND, ctypes.POINTER(wintypes.DWORD),
                ]
                user32.GetWindowThreadProcessId.restype = wintypes.DWORD
                user32.AttachThreadInput.argtypes = [
                    wintypes.DWORD, wintypes.DWORD, wintypes.BOOL,
                ]
                hwnd = user32.GetAncestor(self.winfo_id(), 2)  # GA_ROOT
                if hwnd:
                    foreground = user32.GetForegroundWindow()
                    foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
                    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                    attached = bool(
                        foreground_thread
                        and foreground_thread != current_thread
                        and user32.AttachThreadInput(current_thread, foreground_thread, True)
                    )
                    user32.ShowWindow(hwnd, 9)  # SW_RESTORE
                    user32.BringWindowToTop(hwnd)
                    user32.SetForegroundWindow(hwnd)
                    user32.SetActiveWindow(hwnd)
                    user32.SetFocus(hwnd)
                    if attached:
                        user32.AttachThreadInput(current_thread, foreground_thread, False)
            self.focus_force()
            self.canvas.focus_set()
            # A short topmost pulse handles Windows' delayed z-order update,
            # but CrowEyes does not remain always-on-top.
            self.attributes("-topmost", True)
            self.after(90, lambda: self.attributes("-topmost", False))
        except (AttributeError, OSError, tk.TclError):
            pass

    def _escape(self) -> None:
        self._stop_slideshow()
        if self._region_copy_mode:
            self._cancel_region_copy()
            self.status.configure(text="영역 선택 복사를 취소했습니다")
            return
        if self._image_fullscreen:
            self.exit_image_fullscreen()
            return
        if self.attributes("-fullscreen"):
            self.attributes("-fullscreen", False)


    # ----- list modes / sort -----------------------------------------------

    def set_list_mode(self, mode: str) -> None:
        if mode not in LIST_MODES:
            return
        self.list_mode = mode
        self._list_mode_var.set(mode)
        if hasattr(self, "_list_mode_display_var"):
            self._list_mode_display_var.set(LIST_MODE_LABELS.get(mode, mode))
        self.settings["list_mode"] = mode
        save_settings(self.settings)
        self._cancel_thumb_jobs()
        self._thumb_photos.clear()
        self._thumb_loaded.clear()
        self._rebuild_file_list_widget()
        self._populate_list_names_only()
        self._queue_thumbs_priority()
        if self.index >= 0:
            self._select_list_index(self.index)

    def set_sort(self, key: str) -> None:
        if key not in SORT_KEYS:
            return
        self.sort_by = key
        self._sort_var.set(key)
        if hasattr(self, "_sort_display_var"):
            self._sort_display_var.set(SORT_LABELS.get(key, key))
        self.settings["sort_by"] = key
        save_settings(self.settings)
        self._resort_playlist(keep_current=True)

    def toggle_sort_dir(self) -> None:
        self.set_sort_direction(not self.sort_desc)

    def set_sort_direction(self, descending: bool) -> None:
        self.sort_desc = bool(descending)
        self._sort_desc_var.set(self.sort_desc)
        self._sort_dir_text_var.set("▼" if self.sort_desc else "▲")
        self.settings["sort_desc"] = self.sort_desc
        save_settings(self.settings)
        self._resort_playlist(keep_current=True)

    def _sort_key(self, p: Path):
        name = p.name.lower()
        ext = p.suffix.lower()
        if self.sort_by not in {"date", "size"}:
            return (ext, name) if self.sort_by == "ext" else (name,)
        cache_key = str(p)
        cached = self._file_stat_cache.get(cache_key)
        if cached is None:
            try:
                st = p.stat()
                cached = (st.st_mtime, st.st_size)
            except OSError:
                cached = (0.0, 0)
            self._file_stat_cache[cache_key] = cached
        mtime, size = cached
        if self.sort_by == "date":
            return (mtime, name)
        if self.sort_by == "size":
            return (size, name)
        return (name,)

    def _sorted(self, files: List[Path]) -> List[Path]:
        return sorted(files, key=self._sort_key, reverse=self.sort_desc)

    def _resort_playlist(self, keep_current: bool = True) -> None:
        cur = self.folder_files[self.index] if 0 <= self.index < len(self.folder_files) else None
        self.folder_files = self._sorted(self.folder_files)
        self._cancel_thumb_jobs()
        self._populate_list_names_only()
        if keep_current and cur is not None:
            try:
                self.index = self.folder_files.index(cur)
            except ValueError:
                self.index = 0 if self.folder_files else -1
        self._select_list_index(self.index)
        self._queue_thumbs_priority()
        self._update_info()

    def _rebuild_file_list_widget(self) -> None:
        assert self.list_container is not None
        for child in self.list_container.winfo_children():
            child.destroy()
        self._list_widget = None
        self._list_scroll = None
        self._grid_canvas = None
        self._grid_inner = None
        self._icon_cells.clear()
        self._folder_cells.clear()
        self._icon_grid_order.clear()
        self._make_placeholder()

        wrap = ttk.Frame(self.list_container, style="Panel.TFrame")
        wrap.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._list_scroll = scroll

        if self.list_mode == "names":
            lb = tk.Listbox(
                wrap, width=26, selectmode=tk.EXTENDED, exportselection=False,
                yscrollcommand=self._on_list_yview,
            )
            scroll.config(command=lb.yview)
            lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            lb.bind("<<ListboxSelect>>", self._on_list_select)
            lb.bind("<Button-1>", self._on_playlist_button_press)
            lb.bind("<MouseWheel>", self._on_list_wheel, add="+")
            lb.bind("<ButtonRelease-1>", self._on_playlist_button_release)
            lb.bind("<Double-Button-1>", self._on_playlist_double_click)
            lb.bind("<Button-3>", self.show_playlist_context_menu)
            self._list_widget = lb
            self._style_list_widget()
            self._register_playlist_drag_source(lb)
            return

        if self.list_mode == "icons":
            # Matrix / board layout — multiple thumbs per row
            gc = tk.Canvas(wrap, highlightthickness=0, bd=0, bg=self._theme()["panel"])
            scroll.config(command=gc.yview)
            gc.configure(yscrollcommand=self._on_list_yview)
            gc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            inner = ttk.Frame(gc, style="Panel.TFrame")
            win_id = gc.create_window((0, 0), window=inner, anchor="nw")
            inner.bind("<Configure>", lambda e: gc.configure(scrollregion=gc.bbox("all")))
            gc.bind("<Configure>", lambda e: self._on_icon_grid_resize(e, win_id))
            self._bind_grid_wheel(gc)
            self._bind_grid_wheel(inner)
            self._grid_canvas = gc
            self._grid_inner = inner
            self._list_widget = gc
            return

        tv = ttk.Treeview(
            wrap, show="tree", selectmode="extended",
            yscrollcommand=self._on_list_yview, style="Treeview",
        )
        scroll.config(command=tv.yview)
        tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tv.bind("<<TreeviewSelect>>", self._on_list_select)
        tv.bind("<Button-1>", self._on_playlist_button_press)
        tv.bind("<MouseWheel>", self._on_list_wheel, add="+")
        tv.bind("<ButtonRelease-1>", self._on_playlist_button_release)
        tv.bind("<Double-Button-1>", self._on_playlist_double_click)
        tv.bind("<Button-3>", self.show_playlist_context_menu)
        self._list_widget = tv
        self._register_playlist_drag_source(tv)

    def _on_icon_grid_resize(self, event, win_id) -> None:
        if self._grid_canvas is None:
            return
        self._grid_canvas.itemconfigure(win_id, width=event.width)
        self.after_idle(self._layout_icon_grid)

    def _on_grid_wheel(self, event) -> None:
        if self._grid_canvas is not None:
            delta = int(getattr(event, "delta", 0) or 0)
            if not delta:
                delta = 120 if int(getattr(event, "num", 0) or 0) == 4 else -120
            units = -1 if delta > 0 else 1
            self._grid_canvas.yview_scroll(units * 3, "units")
            self.after(50, self._queue_thumbs_visible)
        return "break"

    def _bind_grid_wheel(self, widget: tk.Widget) -> None:
        widget.bind("<MouseWheel>", self._on_grid_wheel, add="+")
        widget.bind("<Button-4>", self._on_grid_wheel, add="+")
        widget.bind("<Button-5>", self._on_grid_wheel, add="+")

    def _icon_cell_size(self) -> int:
        return 72

    def _layout_icon_grid(self) -> None:
        if self.list_mode != "icons" or self._grid_inner is None or self._grid_canvas is None:
            return
        cell = self._icon_cell_size()
        pad = 4
        cw = max(self._grid_canvas.winfo_width(), cell + pad * 2)
        cols = max(1, cw // (cell + pad * 2))
        for position, lbl in enumerate(self._icon_grid_order):
            r, c = divmod(position, cols)
            lbl.grid(row=r, column=c, padx=pad, pady=pad, sticky="n")
        for c in range(cols):
            self._grid_inner.columnconfigure(c, weight=1)

    def _on_list_yview(self, *args) -> None:
        # Treeview/Listbox yscrollcommand → scrollbar.set(first, last)
        if self._list_scroll is not None and args:
            try:
                self._list_scroll.set(*args)
            except tk.TclError:
                pass
        # When user scrolls, load thumbs for newly visible rows
        self.after_idle(self._queue_thumbs_visible)

    def _on_list_wheel(self, event) -> None:
        # After native scroll, queue visible thumbs
        self.after(50, self._queue_thumbs_visible)
        return None  # let default proceed if bound add=False... use bind with add

    def _register_playlist_drag_source(self, widget: tk.Widget, index: Optional[int] = None) -> None:
        """Expose selected playlist files as a native COPY drag source."""
        if not self._dnd_available or DND_FILES is None:
            return
        try:
            widget.drag_source_register(1, DND_FILES)  # type: ignore[attr-defined]
            widget.dnd_bind(  # type: ignore[attr-defined]
                "<<DragInitCmd>>",
                lambda event, idx=index: self._drag_init_playlist(event, idx),
            )
            widget.dnd_bind("<<DragEndCmd>>", self._drag_end_playlist)  # type: ignore[attr-defined]
        except (AttributeError, tk.TclError):
            pass

    def _selected_playlist_paths(self) -> List[Path]:
        indices = sorted(i for i in self._playlist_selection if 0 <= i < len(self.folder_files))
        if not indices and 0 <= self.index < len(self.folder_files):
            indices = [self.index]
        return [self.folder_files[i] for i in indices]

    def copy_selected_files(self) -> None:
        paths = self._selected_playlist_paths()
        if not paths:
            self.status.configure(text="복사할 파일을 선택해 주세요")
            return
        try:
            copy_files_to_windows_clipboard(paths)
            self.status.configure(text=f"파일 {len(paths)}개를 클립보드에 복사했습니다")
        except Exception as exc:
            messagebox.showerror("파일 복사", str(exc), parent=self)

    @staticmethod
    def _rename_path(path: Path, new_stem: str) -> Path:
        new_stem = validate_filename_stem(new_stem)
        destination = path.with_name(new_stem + path.suffix)
        if destination == path:
            return path
        if destination.exists():
            raise FileExistsError(f"같은 이름의 파일이 이미 있습니다:\n{destination.name}")
        path.rename(destination)
        return destination

    def rename_selected_file(self) -> None:
        paths = self._selected_playlist_paths()
        if len(paths) != 1:
            self.status.configure(text="이름 바꾸기는 파일 하나를 선택했을 때 사용할 수 있습니다")
            return
        path = paths[0]
        win = tk.Toplevel(self)
        win.title("이름 바꾸기")
        win.transient(self)
        win.resizable(False, False)
        win.grab_set()
        frame = ttk.Frame(win, padding=18, style="Panel.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text=f"확장자 {path.suffix}는 유지됩니다.", style="Section.TLabel").pack(anchor="w")
        value = tk.StringVar(value=path.stem)
        entry = ttk.Entry(frame, textvariable=value, width=46)
        entry.pack(fill=tk.X, pady=10)
        actions = ttk.Frame(frame, style="Panel.TFrame")
        actions.pack(fill=tk.X)

        def commit(_event=None):
            try:
                destination = self._rename_path(path, value.get())
            except Exception as exc:
                messagebox.showerror("이름 바꾸기", str(exc), parent=win)
                return "break"
            idx = self.folder_files.index(path)
            self.folder_files[idx] = destination
            if self.source_path == path:
                self.source_path = destination
            self._thumb_photos.pop(str(path), None)
            self._thumb_loaded.discard(str(path))
            self._file_stat_cache.pop(str(path), None)
            win.destroy()
            self._resort_playlist(keep_current=True)
            self.status.configure(text=f"이름 변경: {destination.name}")
            return "break"

        ttk.Button(actions, text="취소", command=win.destroy).pack(side=tk.RIGHT)
        ttk.Button(actions, text="이름 바꾸기", style="Accent.TButton", command=commit).pack(side=tk.RIGHT, padx=6)
        entry.bind("<Return>", commit)
        entry.bind("<Escape>", lambda _e: win.destroy())
        entry.focus_set()
        entry.selection_range(0, tk.END)

    def delete_selected_files(self) -> None:
        paths = self._selected_playlist_paths()
        if not paths:
            return
        if send2trash is None:
            messagebox.showerror("휴지통으로 삭제", "Send2Trash 구성 요소가 없습니다.", parent=self)
            return
        label = paths[0].name if len(paths) == 1 else f"선택한 파일 {len(paths)}개"
        if not messagebox.askyesno("휴지통으로 삭제", f"{label}을(를) 휴지통으로 이동할까요?", parent=self):
            return
        failures: List[str] = []
        for path in paths:
            try:
                send2trash(str(path))
            except Exception as exc:
                failures.append(f"{path.name}: {exc}")
        removed = {path for path in paths if not path.exists()}
        self.folder_files = [path for path in self.folder_files if path not in removed]
        self._playlist_selection.clear()
        self.index = min(self.index, len(self.folder_files) - 1)
        self._populate_list_names_only()
        if self.index >= 0:
            self._select_list_index(self.index)
            self._load_current()
        else:
            self.display_image = self.pil_image = None
            self.redraw()
        self._update_header()
        self.status.configure(text=f"파일 {len(removed)}개를 휴지통으로 이동했습니다")
        if failures:
            messagebox.showwarning("일부 파일 삭제 실패", "\n".join(failures), parent=self)

    def open_selected_file_location(self) -> None:
        paths = self._selected_playlist_paths()
        if not paths:
            return
        path = paths[-1].resolve()
        try:
            subprocess.Popen(["explorer.exe", f"/select,{path}"], shell=False)
        except OSError as exc:
            messagebox.showerror("파일 위치 열기", str(exc), parent=self)

    def show_playlist_context_menu(self, event) -> str:
        item = self._playlist_item_at_event(event)
        if item is not None and item[0] == "image" and item[2] is not None:
            idx = item[2]
            if idx not in self._playlist_selection:
                self._playlist_selection = {idx}
                self._selection_anchor = idx
                self.goto_index(idx, from_list=True)
                self._restore_playlist_selection_visuals()
        paths = self._selected_playlist_paths()
        menu = tk.Menu(self, tearoff=0)
        if len(paths) == 1:
            menu.add_command(label="열기", command=lambda: self.goto_index(self.folder_files.index(paths[0])))
            menu.add_command(label="이름 바꾸기\tF2", command=self.rename_selected_file)
            menu.add_separator()
        menu.add_command(label=f"파일 복사\tCtrl+C", command=self.copy_selected_files, state=tk.NORMAL if paths else tk.DISABLED)
        menu.add_command(label="휴지통으로 삭제\tDelete", command=self.delete_selected_files, state=tk.NORMAL if paths else tk.DISABLED)
        menu.add_command(label="파일 위치 열기", command=self.open_selected_file_location, state=tk.NORMAL if paths else tk.DISABLED)
        if len(paths) == 1:
            menu.add_separator()
            formats = tk.Menu(menu, tearoff=0)
            for label, suffix in (("PNG", ".png"), ("JPEG", ".jpg"), ("WebP", ".webp"), ("BMP", ".bmp"), ("TIFF", ".tiff")):
                formats.add_command(label=label, command=lambda ext=suffix: self.save_as_format(ext))
            menu.add_cascade(label="다른 형식으로 저장", menu=formats)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
        return "break"

    def _drag_init_playlist(self, _event, index: Optional[int] = None):
        if self._selection_press_snapshot:
            self._playlist_selection = set(self._selection_press_snapshot)
            self._selection_press_snapshot = None
            self._restore_playlist_selection_visuals()
        if index is not None and index not in self._playlist_selection:
            self._playlist_selection = {index}
            self._selection_anchor = index
            self.goto_index(index, from_list=True)
            self._highlight_icon_selection()
        paths = tuple(str(path.resolve()) for path in self._selected_playlist_paths())
        if not paths or COPY is None or DND_FILES is None:
            return None
        self.status.configure(text=f"선택한 파일 {len(paths)}개를 창 밖으로 복사할 수 있습니다")
        return (COPY, DND_FILES, paths)

    def _drag_end_playlist(self, event):
        action = str(getattr(event, "action", "") or "").lower()
        if action == str(COPY).lower():
            self.status.configure(text=f"파일 {len(self._selected_playlist_paths())}개 복사 드래그 완료")
        self.after_idle(self._restore_playlist_selection_visuals)

    # ----- progressive list / thumbs ---------------------------------------

    def _cancel_thumb_jobs(self) -> None:
        if self._thumb_job is not None:
            try:
                self.after_cancel(self._thumb_job)
            except Exception:
                pass
            self._thumb_job = None
        self._thumb_queue.clear()

    def _populate_list_names_only(self) -> None:
        """Instant list fill: names (+ placeholder icons). No image decode."""
        w = self._list_widget
        if w is None:
            return
        ph = self._placeholder_photo
        t = self._theme()
        self._playlist_items = self._visible_playlist_items()
        items = self._playlist_items
        shown = sum(1 for kind, _path, _idx in items if kind == "image")
        total = len(self.folder_files)
        self._playlist_count_var.set(str(total) if shown == total else f"{shown}/{total}")

        if isinstance(w, tk.Listbox):
            w.delete(0, tk.END)
            for kind, p, _idx in items:
                text = p.name if kind == "image" else f"▸  {self._playlist_folder_label(kind, p)}"
                w.insert(tk.END, text)
            return

        if self.list_mode == "icons" and self._grid_inner is not None:
            for child in self._grid_inner.winfo_children():
                child.destroy()
            self._icon_cells.clear()
            self._folder_cells.clear()
            self._icon_grid_order.clear()
            cell = self._icon_cell_size()
            for kind, p, image_idx in items:
                if kind == "image" and image_idx is not None:
                    i = image_idx
                    lbl = tk.Label(
                        self._grid_inner, image=ph, bg=t["panel"], bd=1,
                        relief=tk.FLAT, cursor="hand2", width=cell, height=cell,
                    )
                    lbl.image = ph  # type: ignore[attr-defined]
                    lbl.bind("<Button-1>", lambda e, idx=i: self._on_icon_click(e, idx))
                    lbl.bind("<ButtonRelease-1>", self._on_playlist_button_release)
                    lbl.bind("<Double-Button-1>", lambda _e: "break")
                    lbl.bind("<Button-3>", lambda e, idx=i: self._show_icon_context_menu(e, idx))
                    self._register_playlist_drag_source(lbl, i)
                    self._icon_cells[i] = lbl
                else:
                    key = f"{kind}:{p}"
                    label_text = self._short_folder_name(self._playlist_folder_label(kind, p))
                    folder_image = self._icons["computer_large"] if kind == "drive" else self._icons["folder_large"]
                    lbl = tk.Label(
                        self._grid_inner, image=folder_image, text=label_text,
                        compound=tk.TOP, bg=t["panel"], fg=t["fg"], bd=1,
                        relief=tk.FLAT, cursor="hand2", width=cell, height=cell,
                        font=("Segoe UI", 9),
                    )
                    lbl.image = folder_image  # type: ignore[attr-defined]
                    lbl.bind("<Button-1>", lambda e, path=p: self._on_folder_icon_click(e, path))
                    self._folder_cells[key] = lbl
                self._bind_grid_wheel(lbl)
                self._icon_grid_order.append(lbl)
            self._layout_icon_grid()
            self._highlight_icon_selection()
            self._restore_cached_thumbnails()
            return

        assert isinstance(w, ttk.Treeview)
        for item in w.get_children():
            w.delete(item)
        for row, (kind, p, image_idx) in enumerate(items):
            if kind != "image":
                icon = self._icons["computer"] if kind == "drive" else self._icons["folder"]
                w.insert(
                    "", tk.END, iid=f"folder:{row}",
                    text=self._playlist_folder_label(kind, p), image=icon,
                )
                continue
            assert image_idx is not None
            iid = str(image_idx)
            img = ph if self.list_mode == "small" else None
            if img is not None:
                w.insert("", tk.END, iid=iid, text=p.name, image=img)
            else:
                w.insert("", tk.END, iid=iid, text=p.name)
        self._restore_cached_thumbnails()

    def _show_icon_context_menu(self, event, idx: int) -> str:
        if idx not in self._playlist_selection:
            self._playlist_selection = {idx}
            self._selection_anchor = idx
            self.goto_index(idx, from_list=True)
            self._highlight_icon_selection()
        return self.show_playlist_context_menu(event)

    @staticmethod
    def _short_folder_name(name: str, limit: int = 10) -> str:
        return name if len(name) <= limit else f"{name[:limit - 1]}…"

    @staticmethod
    def _playlist_folder_label(kind: str, path: Path) -> str:
        if kind == "drive":
            return path.drive or str(path)
        if kind.startswith("special:"):
            return kind.split(":", 1)[1]
        return path.name or path.drive or str(path)

    def _restore_cached_thumbnails(self) -> None:
        """Reattach cached PhotoImages after rebuilding playlist widgets."""
        if self.list_mode == "names":
            return
        for idx in self._visible_playlist_indices():
            if not (0 <= idx < len(self.folder_files)):
                continue
            cached_photo = self._thumb_photos.get(str(self.folder_files[idx]))
            if cached_photo is not None:
                self._apply_thumb_to_row(idx, cached_photo)

    def _on_icon_click(self, event, idx: int) -> None:
        self._interrupt_slideshow()
        ctrl = bool(int(getattr(event, "state", 0)) & 0x0004)
        shift = bool(int(getattr(event, "state", 0)) & 0x0001)
        if shift and self._selection_anchor is not None:
            lo, hi = sorted((self._selection_anchor, idx))
            self._playlist_selection = set(range(lo, hi + 1))
        elif ctrl:
            if idx in self._playlist_selection:
                self._playlist_selection.discard(idx)
            else:
                self._playlist_selection.add(idx)
            self._selection_anchor = idx
        elif idx in self._playlist_selection and len(self._playlist_selection) > 1:
            # A normal press on an already-selected image is usually the
            # beginning of a multi-file drag. Keep the whole selection.
            self._selection_anchor = idx
        else:
            self._playlist_selection = {idx}
            self._selection_anchor = idx
        if not self._playlist_selection:
            self._playlist_selection = {idx}
        self.goto_index(idx, from_list=True)
        self._highlight_icon_selection()
        self._queue_thumbs_priority()

    def _on_folder_icon_click(self, _event, path: Path) -> None:
        self._navigate_playlist_folder(path)

    def _navigate_playlist_folder(self, path: Path):
        self._search_var.set("")
        self._playlist_selection.clear()
        self._selection_anchor = None
        self._selected_folder_path = None
        self.navigate_to_folder(path)
        return "break"

    def _highlight_icon_selection(self) -> None:
        t = self._theme()
        for i, lbl in self._icon_cells.items():
            if i in self._playlist_selection:
                lbl.configure(bg=t["select"], relief=tk.SOLID, bd=2)
            else:
                lbl.configure(bg=t["panel"], relief=tk.FLAT, bd=1)
        selected_folder = str(self._selected_folder_path) if self._selected_folder_path else None
        for key, lbl in self._folder_cells.items():
            if selected_folder and key.endswith(f":{selected_folder}"):
                lbl.configure(bg=t["select"], relief=tk.SOLID, bd=2)
            else:
                lbl.configure(bg=t["panel"], relief=tk.FLAT, bd=1)

    def _queue_thumbs_priority(self) -> None:
        """Queue only current neighbours and visible rows; never flood a NAS."""
        if self.list_mode == "names" or not self.folder_files:
            return
        n = len(self.folder_files)
        order: List[int] = []
        if 0 <= self.index < n:
            for idx in (self.index, self.index + 1, self.index - 1, self.index + 2, self.index - 2):
                if 0 <= idx < n and idx not in order:
                    order.append(idx)
        # append visible estimate
        for i in self._visible_indices():
            if i not in order:
                order.append(i)
        self._thumb_queue = [i for i in order if str(self.folder_files[i]) not in self._thumb_loaded]
        self._kick_thumb_worker()

    def _queue_thumbs_visible(self) -> None:
        if self.list_mode == "names":
            return
        seen = set(self._thumb_queue)
        for i in self._visible_indices():
            key = str(self.folder_files[i]) if 0 <= i < len(self.folder_files) else ""
            if key and key not in self._thumb_loaded and i not in seen:
                self._thumb_queue.insert(0, i)
                seen.add(i)
        self._kick_thumb_worker()

    def _visible_indices(self) -> List[int]:
        w = self._list_widget
        if w is None or not self.folder_files:
            return []
        try:
            if self.list_mode == "icons" and self._grid_canvas is not None:
                # Approximate visible window of icon matrix
                cell = self._icon_cell_size() + 8
                top = int(self._grid_canvas.canvasy(0))
                bot = int(self._grid_canvas.canvasy(self._grid_canvas.winfo_height()))
                cw = max(self._grid_canvas.winfo_width(), cell)
                cols = max(1, cw // cell)
                first_row = max(0, top // cell)
                last_row = max(first_row, bot // cell + 1)
                first = first_row * cols
                last = min(len(self._playlist_items), (last_row + 1) * cols)
                return [
                    idx for kind, _path, idx in self._playlist_items[first:last]
                    if kind == "image" and idx is not None
                ]
            if isinstance(w, tk.Listbox):
                first = w.nearest(0)
                last = w.nearest(w.winfo_height())
                return [
                    idx for kind, _path, idx in self._playlist_items[max(0, first):min(len(self._playlist_items), last + 2)]
                    if kind == "image" and idx is not None
                ]
            assert isinstance(w, ttk.Treeview)
            first_iid = w.identify_row(1)
            last_iid = w.identify_row(max(1, w.winfo_height() - 2))
            def row_for_iid(iid: str, fallback: int) -> int:
                if not iid:
                    return fallback
                if iid.startswith("folder:"):
                    try:
                        return int(iid.split(":", 1)[1])
                    except ValueError:
                        return fallback
                try:
                    image_idx = int(iid)
                except ValueError:
                    return fallback
                return next(
                    (row for row, (kind, _path, idx) in enumerate(self._playlist_items)
                     if kind == "image" and idx == image_idx),
                    fallback,
                )
            fi = row_for_iid(first_iid, 0)
            li = row_for_iid(last_iid, min(20, len(self._playlist_items) - 1))
            if li < fi:
                li = fi
            return [
                idx for kind, _path, idx in self._playlist_items[max(0, fi):min(len(self._playlist_items), li + 3)]
                if kind == "image" and idx is not None
            ]
        except Exception:
            return list(range(min(15, len(self.folder_files))))

    def _kick_thumb_worker(self) -> None:
        if self._thumb_job is not None:
            return
        if not self._thumb_queue:
            return
        self._thumb_job = self.after(1, self._thumb_worker_step)

    def _thumb_worker_step(self) -> None:
        self._thumb_job = None
        if self.list_mode == "names" or self._thumb_decode_active:
            return
        while self._thumb_queue:
            idx = self._thumb_queue.pop(0)
            if idx < 0 or idx >= len(self.folder_files):
                continue
            path = self.folder_files[idx]
            key = str(path)
            if key in self._thumb_loaded:
                continue
            if self._content_filter_mode == MODE_EXPLICIT:
                known_status = self._safety_known.get(key)
                if known_status is None:
                    if key not in self._safety_thumb_pending and self._safety_worker is not None:
                        self._safety_thumb_pending.add(key)
                        self._safety_worker.submit(
                            path, 20, self._playlist_gen,
                            vector_loader=self._safety_vector_loader, kind="thumbnail",
                        )
                    continue
                if known_status == BLOCKED:
                    photo = self._blocked_thumbnail(self._icon_cell_size() if self.list_mode == "icons" else 22)
                    self._thumb_loaded.add(key)
                    self._thumb_photos[key] = photo
                    self._apply_thumb_to_row(idx, photo)
                    continue
            size = self._icon_cell_size() if self.list_mode == "icons" else 22
            generation = self._playlist_gen
            self._thumb_decode_active = True

            def worker() -> None:
                image = self._make_thumb_pil(path, size)
                self._thumb_decode_results[(generation, idx)] = (path, image)

            threading.Thread(target=worker, name="CrowEyesThumbnail", daemon=True).start()
            self.after(20, self._poll_thumb_decode, generation, idx)
            return

    def _poll_thumb_decode(self, generation: int, idx: int) -> None:
        result = self._thumb_decode_results.pop((generation, idx), None)
        if result is None:
            if generation == self._playlist_gen:
                self.after(20, self._poll_thumb_decode, generation, idx)
            else:
                self._thumb_decode_active = False
            return
        self._thumb_decode_active = False
        if generation == self._playlist_gen and 0 <= idx < len(self.folder_files):
            path, image = result
            if path == self.folder_files[idx]:
                key = str(path)
                self._thumb_loaded.add(key)
                photo = ImageTk.PhotoImage(image, master=self) if image is not None else self._placeholder_photo
                if photo is not None:
                    self._thumb_photos[key] = photo
                    self._apply_thumb_to_row(idx, photo)
        if self._thumb_queue:
            self._thumb_job = self.after(1, self._thumb_worker_step)

    def _apply_thumb_to_row(self, idx: int, photo: ImageTk.PhotoImage) -> None:
        if self.list_mode == "icons":
            lbl = self._icon_cells.get(idx)
            if lbl is not None:
                lbl.configure(image=photo)
                lbl.image = photo  # type: ignore[attr-defined]
            return
        w = self._list_widget
        if not isinstance(w, ttk.Treeview):
            return
        iid = str(idx)
        if not w.exists(iid):
            return
        try:
            w.item(iid, image=photo, text=self.folder_files[idx].name)
        except tk.TclError:
            pass

    def _make_thumb_pil(self, path: Path, size: int) -> Optional[Image.Image]:
        try:
            suffix = path.suffix.lower()
            if suffix == ".svg":
                im, _logical = render_svg(path, size, size)
            elif suffix == ".eps":
                if find_ghostscript() is None:
                    return None
                im, _logical = render_eps(path, size, size)
            elif suffix == ".psd":
                # Force-load the composited preview before the PSD stream closes.
                # Pillow's PSD decoder starts on its sole composite frame and
                # raises EOFError if seek(0) is called, so do not seek here.
                with Image.open(path) as opened:
                    opened.load()
                    im = _frame_to_rgba(opened.copy())
            else:
                with Image.open(path) as opened:
                    if getattr(opened, "n_frames", 1) > 1:
                        opened.seek(0)
                    im = _frame_to_rgba(ImageOps.exif_transpose(opened))
            im.thumbnail((size, size), Image.Resampling.BILINEAR)
            t = self._theme()
            bg = Image.new("RGBA", (size, size), self._hex_to_rgba(t["panel"]))
            bg.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
            return bg
        except Exception:
            return None

    def _blocked_thumbnail(self, size: int) -> ImageTk.PhotoImage:
        try:
            with Image.open(resource_path("assets", "safety", "content_blocked_crow.webp")) as opened:
                image = opened.convert("RGBA")
            image.thumbnail((size, size), Image.Resampling.LANCZOS)
            background = Image.new("RGBA", (size, size), self._hex_to_rgba(self._theme()["panel"]))
            background.alpha_composite(
                image, ((size - image.width) // 2, (size - image.height) // 2),
            )
        except Exception:
            background = Image.new("RGBA", (size, size), self._hex_to_rgba(self._theme()["border"]))
        return ImageTk.PhotoImage(background, master=self)

    @staticmethod
    def _hex_to_rgba(hex_color: str) -> Tuple[int, int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
        return (240, 240, 240, 255)

    def _playlist_item_for_tree_iid(self, iid: str) -> Optional[Tuple[str, Path, Optional[int]]]:
        if iid.startswith("folder:"):
            try:
                row = int(iid.split(":", 1)[1])
            except ValueError:
                return None
            return self._playlist_items[row] if 0 <= row < len(self._playlist_items) else None
        try:
            idx = int(iid)
        except ValueError:
            return None
        if 0 <= idx < len(self.folder_files):
            return ("image", self.folder_files[idx], idx)
        return None

    def _playlist_item_at_event(self, event) -> Optional[Tuple[str, Path, Optional[int]]]:
        w = self._list_widget
        if isinstance(w, tk.Listbox):
            if not self._playlist_items:
                return None
            row = int(w.nearest(event.y))
            bbox = w.bbox(row)
            if bbox is None or not (bbox[1] <= event.y <= bbox[1] + bbox[3]):
                return None
            return self._playlist_items[row] if row < len(self._playlist_items) else None
        if isinstance(w, ttk.Treeview):
            iid = w.identify_row(event.y)
            return self._playlist_item_for_tree_iid(iid) if iid else None
        return None

    def _on_playlist_button_press(self, event) -> None:
        """Remember a multi-selection before Tk's class binding can collapse it."""
        item = self._playlist_item_at_event(event)
        state = int(getattr(event, "state", 0) or 0)
        modified = bool(state & 0x0005)  # Shift or Ctrl
        if (
            item is not None and item[0] == "image" and item[2] is not None
            and not modified and item[2] in self._playlist_selection
            and len(self._playlist_selection) > 1
        ):
            self._selection_press_snapshot = set(self._playlist_selection)
            self.after_idle(self._restore_press_selection)
        else:
            self._selection_press_snapshot = None

    def _restore_press_selection(self) -> None:
        snapshot = self._selection_press_snapshot
        self._selection_press_snapshot = None
        if snapshot:
            self._playlist_selection = snapshot
            self._selected_folder_path = None
            self._restore_playlist_selection_visuals()

    def _on_playlist_button_release(self, event=None):
        # Folder, drive, and Windows known-folder rows all open with one click,
        # matching the icon-grid behavior.
        item = self._playlist_item_at_event(event) if event is not None else None
        state = int(getattr(event, "state", 0) or 0) if event is not None else 0
        if item is not None and item[0] != "image" and not (state & 0x0005):
            self._navigate_playlist_folder(item[1])
            return "break"
        if (
            item is not None and item[0] == "image" and item[2] is not None
            and not (state & 0x0005) and len(self._playlist_selection) <= 1
        ):
            # Listbox ACTIVE can lag behind the clicked row in names-only
            # mode. Use the release hit-test as the authoritative target.
            self._playlist_selection = {item[2]}
            self._selection_anchor = item[2]
            self.goto_index(item[2], from_list=True)
        # Prevent Tk's release binding from reducing an extended selection.
        self.after_idle(self._restore_playlist_selection_visuals)
        return "break"

    def _on_playlist_double_click(self, event):
        item = self._playlist_item_at_event(event)
        if item is not None and item[0] != "image":
            return self._navigate_playlist_folder(item[1])
        return None

    def _restore_playlist_selection_visuals(self) -> None:
        w = self._list_widget
        if w is None:
            return
        if self.list_mode == "icons":
            self._highlight_icon_selection()
            return
        self._syncing_playlist_selection = True
        try:
            if isinstance(w, tk.Listbox):
                w.selection_clear(0, tk.END)
                for row, (kind, path, idx) in enumerate(self._playlist_items):
                    selected = (
                        kind == "image" and idx in self._playlist_selection
                    ) or (
                        kind in {"parent", "folder"} and self._selected_folder_path == path
                    )
                    if selected:
                        w.selection_set(row)
                return
            if isinstance(w, ttk.Treeview):
                selected_iids: List[str] = []
                for row, (kind, path, idx) in enumerate(self._playlist_items):
                    if kind == "image" and idx in self._playlist_selection:
                        selected_iids.append(str(idx))
                    elif kind in {"parent", "folder"} and self._selected_folder_path == path:
                        selected_iids.append(f"folder:{row}")
                w.selection_set(*selected_iids)
        finally:
            self._syncing_playlist_selection = False

    def _on_list_select(self, _event=None) -> None:
        if self._syncing_playlist_selection:
            return
        w = self._list_widget
        if w is None:
            return
        self._interrupt_slideshow()
        if isinstance(w, tk.Listbox):
            sel = w.curselection()
            if sel:
                selected_items = [self._playlist_items[int(row)] for row in sel if int(row) < len(self._playlist_items)]
                image_indices = {idx for kind, _path, idx in selected_items if kind == "image" and idx is not None}
                if image_indices:
                    self._playlist_selection = image_indices
                    self._selected_folder_path = None
                    row = int(w.index(tk.ACTIVE))
                    active = self._playlist_items[row] if 0 <= row < len(self._playlist_items) else selected_items[-1]
                    idx = (
                        active[2]
                        if active[0] == "image" and active[2] in image_indices
                        else next(reversed(sorted(image_indices)))
                    )
                    assert idx is not None
                    self._selection_anchor = idx
                    self.goto_index(idx, from_list=True)
                    self._queue_thumbs_priority()
                else:
                    self._playlist_selection.clear()
                    self._selection_anchor = None
                    self._selected_folder_path = selected_items[-1][1]
            return
        assert isinstance(w, ttk.Treeview)
        sel = w.selection()
        if sel:
            selected_items = [item for iid in sel if (item := self._playlist_item_for_tree_iid(iid)) is not None]
            image_indices = {idx for kind, _path, idx in selected_items if kind == "image" and idx is not None}
            if image_indices:
                self._playlist_selection = image_indices
                self._selected_folder_path = None
                focused = self._playlist_item_for_tree_iid(w.focus())
                idx = (
                    focused[2]
                    if focused is not None and focused[0] == "image" and focused[2] in image_indices
                    else max(image_indices)
                )
                assert idx is not None
                self._selection_anchor = idx
                self.goto_index(idx, from_list=True)
                self._queue_thumbs_priority()
            elif selected_items:
                self._playlist_selection.clear()
                self._selection_anchor = None
                self._selected_folder_path = selected_items[-1][1]

    def _select_list_index(self, idx: int) -> None:
        w = self._list_widget
        if w is None or idx < 0:
            return
        self._playlist_selection = {idx}
        self._selection_anchor = idx
        self._selected_folder_path = None
        self._playlist_selection_sync_gen += 1
        sync_gen = self._playlist_selection_sync_gen
        self._syncing_playlist_selection = True
        try:
            if self.list_mode == "icons":
                self._highlight_icon_selection()
                lbl = self._icon_cells.get(idx)
                if lbl is not None and self._grid_canvas is not None:
                    self._grid_canvas.update_idletasks()
                    # Scroll so selected cell is visible
                    y = lbl.winfo_y()
                    h = max(self._grid_inner.winfo_height(), 1) if self._grid_inner else 1
                    self._grid_canvas.yview_moveto(max(0.0, (y - 20) / h))
                return
            if isinstance(w, tk.Listbox):
                w.selection_clear(0, tk.END)
                row = next(
                    (row for row, (kind, _path, image_idx) in enumerate(self._playlist_items)
                     if kind == "image" and image_idx == idx),
                    None,
                )
                if row is not None:
                    w.selection_set(row)
                    w.see(row)
                return
            if isinstance(w, ttk.Treeview):
                iid = str(idx)
                if w.exists(iid):
                    w.selection_set(iid)
                    w.focus(iid)
                    w.see(iid)
        except tk.TclError:
            pass
        finally:
            # Tk emits <<ListboxSelect>> / <<TreeviewSelect>> after the
            # selection command returns. Keep the guard through that idle
            # cycle so slideshow navigation is not mistaken for a user click.
            self.after_idle(self._finish_playlist_selection_sync, sync_gen)

    def _finish_playlist_selection_sync(self, sync_gen: int) -> None:
        if sync_gen == self._playlist_selection_sync_gen:
            self._syncing_playlist_selection = False

    # ----- open file / folder ----------------------------------------------



    def open_folder_dialog(self) -> None:
        start = self.current_folder or (
            self.folder_files[self.index].parent if self.folder_files and self.index >= 0 else Path.home()
        )
        picker = FolderPicker(self, start=start)
        if picker.result:
            self.open_folders(picker.result)

    def _record_folder_history(self, folder: Path) -> None:
        try:
            folder = folder.resolve()
        except OSError:
            return
        if self._folder_history_index >= 0 and self._folder_history[self._folder_history_index] == folder:
            return
        del self._folder_history[self._folder_history_index + 1:]
        self._folder_history.append(folder)
        self._folder_history = self._folder_history[-60:]
        self._folder_history_index = len(self._folder_history) - 1

    def navigate_to_folder(self, folder: Path, record: bool = True) -> None:
        try:
            folder = folder.expanduser().resolve()
        except OSError as exc:
            messagebox.showerror("폴더 열기", str(exc), parent=self)
            return
        if not folder.is_dir():
            return
        self._search_var.set("")
        if record:
            self._record_folder_history(folder)
        self._history_navigation = not record
        self.open_folders([folder])

    def navigate_to_computer(self) -> None:
        """Show Windows drives and known user folders as the navigation root."""
        self._search_var.set("")
        self._playlist_gen += 1
        self._cancel_thumb_jobs()
        self._image_prefetch_queue.clear()
        self._image_prefetch_pending.clear()
        self.folder_files = []
        self._folder_dirs = []
        self.index = -1
        self.current_folder = None
        self._playlist_selection.clear()
        self._selected_folder_path = None
        self.pil_image = self.display_image = None
        self.source_path = None
        self.source_type = "none"
        self.zoom = 1.0
        self._zoom_text_var.set("크기 100%")
        self._populate_list_names_only()
        self._update_header()
        self._update_info()
        self.redraw()
        self.status.configure(text="내 컴퓨터 · 드라이브 또는 사용자 폴더를 선택하세요")

    def go_folder_back(self) -> None:
        if self._folder_history_index <= 0:
            return
        self._folder_history_index -= 1
        self.navigate_to_folder(self._folder_history[self._folder_history_index], record=False)

    def go_folder_forward(self) -> None:
        if self._folder_history_index + 1 >= len(self._folder_history):
            return
        self._folder_history_index += 1
        self.navigate_to_folder(self._folder_history[self._folder_history_index], record=False)

    def go_parent_folder(self) -> None:
        if self.current_folder is None:
            return
        parent = self.current_folder.parent
        if parent != self.current_folder:
            self.navigate_to_folder(parent)

    def refresh_folder(self) -> None:
        if self.current_folder is not None:
            self.navigate_to_folder(self.current_folder, record=False)
        else:
            self.navigate_to_computer()

    def _update_navigation_state(self) -> None:
        for button in self._navigation_buttons:
            button.configure(state=tk.NORMAL)

    def _update_breadcrumb(self) -> None:
        frame = getattr(self, "_breadcrumb_frame", None)
        if frame is None:
            return
        for child in frame.winfo_children():
            child.destroy()
        theme = self._theme()

        def link_label(text: str, target: Optional[Path], image=None) -> tk.Label:
            label = tk.Label(
                frame, text=text, image=image, compound=tk.LEFT,
                bg=theme["toolbar"], fg=theme["fg"], cursor="hand2",
                bd=0, highlightthickness=0, padx=4, pady=2,
                font=("Segoe UI", 9),
            )
            label.bind(
                "<Button-1>",
                (lambda _event: self.navigate_to_computer())
                if target is None else (lambda _event, path=target: self.navigate_to_folder(path)),
            )
            label.bind(
                "<Enter>",
                lambda _event, item=label: item.configure(
                    bg=theme["select"], fg=theme["accent_hi"], font=("Segoe UI", 9, "underline"),
                ),
            )
            label.bind(
                "<Leave>",
                lambda _event, item=label: item.configure(
                    bg=theme["toolbar"], fg=theme["fg"], font=("Segoe UI", 9),
                ),
            )
            return label

        computer = link_label(
            "내 컴퓨터", None, self._icons["computer"],
        )
        computer._croweyes_image = self._icons["computer"]  # type: ignore[attr-defined]
        computer.pack(side=tk.LEFT)
        folder = self.current_folder
        if folder is None:
            return
        chain = list(reversed((folder,) + tuple(folder.parents)))
        for part in chain:
            ttk.Label(frame, text="›", style="Breadcrumb.TLabel").pack(side=tk.LEFT, padx=4)
            label = part.name or part.drive or str(part)
            link_label(label, part).pack(side=tk.LEFT)


    def open_path(self, path: Path) -> None:
        # Avoid resolve(): on NAS paths it may trigger extra network round trips.
        path = Path(os.path.abspath(os.fspath(path.expanduser())))
        if not path.exists():
            messagebox.showerror("오류", f"찾을 수 없습니다:\n{path}")
            return

        if path.is_dir():
            self.navigate_to_folder(path)
            return

        # ---- FILE OPEN: show this file FIRST, playlist later ----
        if not is_image_file(path):
            messagebox.showwarning("파일 열기", f"지원하지 않는 형식입니다:\n{path.name}")
            return

        self._playlist_gen += 1
        gen = self._playlist_gen
        self._cancel_thumb_jobs()
        self._image_prefetch_queue.clear()
        self._image_prefetch_pending.clear()
        self._thumb_photos.clear()
        self._thumb_loaded.clear()

        self.current_folder = path.parent
        self._record_folder_history(path.parent)
        # Immediate single-item playlist so UI is responsive
        self.folder_files = [path]
        self.index = 0
        self._populate_list_names_only()
        self._select_list_index(0)
        self._load_current()  # priority display

        # Scan the containing folder only after the selected image is either
        # displayed or safely blocked. This is the critical NAS fast path.
        self._pending_playlist_build = (path.parent, path, gen)


    def goto_index(self, idx: int, from_list: bool = False) -> None:
        if not self.folder_files:
            return
        if idx < 0 or idx >= len(self.folder_files):
            return
        if idx == self.index and self.pil_image is not None and from_list:
            return
        if not from_list:
            self._interrupt_slideshow()
        self.index = idx
        if not from_list:
            self._select_list_index(idx)
        self._load_current()
        self._queue_thumbs_priority()

    def prev_image(self) -> None:
        if not self.folder_files:
            return
        # called via _action already for toolbar; slideshow tick calls directly
        self.goto_index((self.index - 1) % len(self.folder_files))

    def next_image(self) -> None:
        if not self.folder_files:
            return
        self.goto_index((self.index + 1) % len(self.folder_files))

    # ----- load / animation ------------------------------------------------

    def _stop_animation_timer(self) -> None:
        if self.anim_job is not None:
            try:
                self.after_cancel(self.anim_job)
            except Exception:
                pass
            self.anim_job = None


    def _schedule_next_frame(self) -> None:
        self._stop_animation_timer()
        if not self.is_animated or not self.anim_playing or len(self.anim_frames) < 2:
            return
        delay = self.anim_delays[self.anim_index] if self.anim_index < len(self.anim_delays) else 100
        delay = max(20, min(delay, 10000))
        self.anim_job = self.after(delay, self._advance_frame)

    def _advance_frame(self) -> None:
        if not self.is_animated or not self.anim_frames:
            return
        self.anim_index = (self.anim_index + 1) % len(self.anim_frames)
        self.pil_image = self.anim_frames[self.anim_index]
        self._rebuild_display()
        self.redraw()
        if self.anim_playing:
            self._schedule_next_frame()


    # ----- paint / transform -----------------------------------------------

    def _apply_current_transforms(self, image: Image.Image) -> Image.Image:
        img = image
        if self.flip_h:
            img = ImageOps.mirror(img)
        if self.flip_v:
            img = ImageOps.flip(img)
        if self.rotation % 360:
            img = img.rotate(-self.rotation, expand=True)
        if abs(self.brightness - 1.0) > 1e-3:
            img = ImageEnhance.Brightness(img).enhance(self.brightness)
        if abs(self.contrast - 1.0) > 1e-3:
            img = ImageEnhance.Contrast(img).enhance(self.contrast)
        return img

    def _rebuild_display(self) -> None:
        if self.pil_image is None:
            self.display_image = None
            return
        self.display_image = self._apply_current_transforms(self.pil_image)

    def _effective_bitmap_zoom(self) -> float:
        if self.source_type in {"svg", "eps"}:
            return self.zoom / max(0.0001, self.source_render_scale)
        return self.zoom

    def _logical_display_size(self) -> Tuple[float, float]:
        if self.display_image is None:
            return (1.0, 1.0)
        scale = self.source_render_scale if self.source_type in {"svg", "eps"} else 1.0
        return (self.display_image.width / scale, self.display_image.height / scale)

    def _maybe_rerender_vector(self) -> None:
        if (
            self.source_type not in {"svg", "eps"}
            or self.source_path is None
            or self._vector_render_pending
        ):
            return
        desired_scale = max(1.0, self.zoom * 1.20)
        desired_w = max(1, int(math.ceil(self.source_logical_size[0] * desired_scale)))
        desired_h = max(1, int(math.ceil(self.source_logical_size[1] * desired_scale)))
        desired_w, desired_h = _bounded_size(
            self.source_logical_size[0], self.source_logical_size[1], desired_w, desired_h,
        )
        if desired_w <= self.pil_image.width * SVG_RERENDER_GROWTH:
            return
        if self.pil_image.width * self.pil_image.height >= MAX_RENDER_PIXELS:
            return
        self._vector_render_pending = True
        self._vector_render_gen += 1
        render_generation = self._vector_render_gen
        image_generation = self._image_load_gen
        path, source_type = self.source_path, self.source_type

        def worker() -> None:
            try:
                if source_type == "svg":
                    image, logical = render_svg(path, desired_w, desired_h)
                else:
                    image, logical = render_eps(path, desired_w, desired_h)
                if render_generation == self._vector_render_gen and image_generation == self._image_load_gen:
                    self._vector_render_results[render_generation] = (
                        True, image_generation, path, image, logical,
                    )
            except Exception as exc:
                if render_generation == self._vector_render_gen and image_generation == self._image_load_gen:
                    self._vector_render_results[render_generation] = (
                        False, image_generation, path, str(exc),
                    )

        threading.Thread(target=worker, name="CrowEyesVectorRenderer", daemon=True).start()
        self.after(30, self._poll_vector_render, render_generation)

    def _poll_vector_render(self, generation: int) -> None:
        result = self._vector_render_results.pop(generation, None)
        if result is None:
            if generation == self._vector_render_gen:
                self.after(30, self._poll_vector_render, generation)
            return
        self._vector_render_pending = False
        ok, image_generation, path, *payload = result
        if image_generation != self._image_load_gen or path != self.source_path:
            return
        if not ok:
            self.status.configure(text=f"벡터 고해상도 렌더링 실패: {payload[0]}")
            return
        image, logical = payload
        self.pil_image = image
        self.anim_frames = [image]
        self.source_logical_size = (float(logical[0]), float(logical[1]))
        self.source_render_scale = image.width / max(1.0, self.source_logical_size[0])
        self._rebuild_display()
        self.redraw()
        self._update_info()
        self.after_idle(self._maybe_rerender_vector)


    def zoom_by(self, factor: float, event=None) -> None:
        if self.display_image is None:
            return
        self.zoom = max(0.02, min(32.0, self.zoom * factor))
        self._view_mode = "custom"
        # Every zoom operation recenters the image in the canvas. This keeps
        # toolbar, keyboard, and optional wheel zoom behavior consistent.
        self.offset_x = self.offset_y = 0.0
        self.redraw()
        self._maybe_rerender_vector()
        self._update_info()

    def fit_to_window(self) -> None:
        if self.display_image is None:
            return
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        iw, ih = self._logical_display_size()
        # Fill the image area while keeping aspect; center with zero pan
        self.zoom = min(cw / iw, ch / ih)
        self._view_mode = "fit"
        self.offset_x = self.offset_y = 0.0
        self.redraw()
        self._maybe_rerender_vector()
        self._update_info()

    def actual_size(self) -> None:
        self.zoom = 1.0
        self._view_mode = "actual"
        self.offset_x = self.offset_y = 0.0
        self.redraw()
        self._update_info()

    def rotate(self, degrees: int) -> None:
        self.rotation = (self.rotation + degrees) % 360
        self._rotation_text_var.set(f"{self.rotation}°")
        self._rebuild_display()
        self.fit_to_window()

    def toggle_flip_h(self) -> None:
        self.flip_h = not self.flip_h
        self._rebuild_display()
        self.redraw()

    def toggle_flip_v(self) -> None:
        self.flip_v = not self.flip_v
        self._rebuild_display()
        self.redraw()

    def _on_adjust(self, _value=None) -> None:
        self._interrupt_slideshow()
        self.brightness = float(self.bright_var.get())
        self.contrast = float(self.contrast_var.get())
        self._rebuild_display()
        self.redraw()
        self._update_info()

    def _on_mousewheel(self, event) -> None:
        self._interrupt_slideshow()
        self.canvas.focus_set()
        delta = int(getattr(event, "delta", 0) or 0)
        if not delta:
            button = int(getattr(event, "num", 0) or 0)
            delta = 120 if button == 4 else -120

        if self.settings.get("mouse_wheel_action", "navigate") == "zoom":
            factor = float(self.settings.get("wheel_zoom", 1.15))
            self.zoom_by(factor if delta > 0 else 1 / factor)
        else:
            self.prev_image() if delta > 0 else self.next_image()
        return "break"

    def _pan_start(self, event) -> None:
        self._interrupt_slideshow()
        if self._region_copy_mode:
            self._region_start = (event.x, event.y)
            if self._region_rect is not None:
                self.canvas.delete(self._region_rect)
            self._region_rect = self.canvas.create_rectangle(
                event.x, event.y, event.x, event.y,
                outline=self._theme()["accent_hi"], width=2, dash=(5, 3),
                tags=("region_selection",),
            )
            return "break"
        self.pan_start = (event.x, event.y)
        self.canvas.configure(cursor="fleur")

    def _pan_move(self, event) -> None:
        if self._region_copy_mode and self._region_start is not None:
            x0, y0 = self._region_start
            if self._region_rect is not None:
                self.canvas.coords(self._region_rect, x0, y0, event.x, event.y)
            return "break"
        if self.pan_start is None:
            return
        dx = event.x - self.pan_start[0]
        dy = event.y - self.pan_start[1]
        self.pan_start = (event.x, event.y)
        self.offset_x += dx
        self.offset_y += dy
        # Reposition the existing item while dragging; resize once only when needed.
        self.canvas.move("display_image", dx, dy)

    def _pan_end(self, event) -> None:
        if self._region_copy_mode:
            self._finish_region_copy(event.x, event.y)
            return "break"
        self.pan_start = None
        self.canvas.configure(cursor="")

    def show_image_context_menu(self, event) -> None:
        if self.display_image is None:
            return
        menu = tk.Menu(self, tearoff=0)
        t = self._theme()
        menu.configure(
            bg=t["toolbar"], fg=t["fg"], activebackground=t["select"],
            activeforeground=t["select_fg"], bd=0,
        )
        menu.add_command(
            label="클립보드로 원본 크기 복사",
            command=lambda: self.copy_image_to_clipboard("original"),
        )
        menu.add_command(
            label="클립보드로 보이는 크기 복사",
            command=lambda: self.copy_image_to_clipboard("visible"),
        )
        menu.add_separator()
        menu.add_command(label="영역 선택 후 복사", command=self.start_region_copy)
        menu.add_separator()
        formats = tk.Menu(menu, tearoff=0)
        for label, suffix in (("PNG", ".png"), ("JPEG", ".jpg"), ("WebP", ".webp"), ("BMP", ".bmp"), ("TIFF", ".tiff")):
            formats.add_command(label=label, command=lambda ext=suffix: self.save_as_format(ext))
        menu.add_cascade(label="다른 형식으로 저장", menu=formats)
        menu.add_command(label="인쇄 미리보기\tCtrl+P", command=self.print_current_image)
        menu.add_command(label="전체화면\tF11", command=self.toggle_image_fullscreen)
        menu.add_separator()
        menu.add_command(label="파일 복사\tCtrl+C", command=self.copy_selected_files)
        menu.add_command(label="이름 바꾸기\tF2", command=self.rename_selected_file)
        menu.add_command(label="휴지통으로 삭제\tDelete", command=self.delete_selected_files)
        menu.add_command(label="파일 위치 열기", command=self.open_selected_file_location)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _rendered_image_size(self) -> Tuple[int, int]:
        if self.display_image is None:
            return (1, 1)
        effective_zoom = self._effective_bitmap_zoom()
        width = max(1, int(self.display_image.width * effective_zoom))
        height = max(1, int(self.display_image.height * effective_zoom))
        if width * height > MAX_RENDER_PIXELS:
            scale = (MAX_RENDER_PIXELS / (width * height)) ** 0.5
            width, height = max(1, int(width * scale)), max(1, int(height * scale))
        return width, height

    def copy_image_to_clipboard(self, mode: str = "original") -> None:
        if self.display_image is None:
            self.status.configure(text="복사할 이미지가 없습니다")
            return
        image = self.display_image.copy()
        if mode == "visible":
            image = image.resize(self._rendered_image_size(), Image.Resampling.LANCZOS)
        try:
            self._copy_pil_to_windows_clipboard(image)
        except OSError as exc:
            messagebox.showerror("클립보드 복사 실패", str(exc), parent=self)
            return
        label = "원본 크기" if mode == "original" else "보이는 크기"
        self.status.configure(text=f"{label} 이미지가 클립보드에 복사되었습니다 · {image.width}×{image.height}")

    @staticmethod
    def _copy_pil_to_windows_clipboard(image: Image.Image) -> None:
        if os.name != "nt":
            raise OSError("이미지 클립보드 복사는 Windows에서만 지원됩니다.")
        import ctypes

        output = BytesIO()
        image.convert("RGB").save(output, "BMP")
        dib = output.getvalue()[14:]
        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
        user32.OpenClipboard.argtypes = [ctypes.c_void_p]
        user32.SetClipboardData.restype = ctypes.c_void_p
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
        handle = kernel32.GlobalAlloc(0x0002, len(dib))  # GMEM_MOVEABLE
        if not handle:
            raise OSError("클립보드 메모리를 할당하지 못했습니다.")
        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            kernel32.GlobalFree(handle)
            raise OSError("클립보드 메모리를 잠그지 못했습니다.")
        ctypes.memmove(pointer, dib, len(dib))
        kernel32.GlobalUnlock(handle)
        if not user32.OpenClipboard(None):
            kernel32.GlobalFree(handle)
            raise OSError("다른 프로그램이 클립보드를 사용 중입니다.")
        transferred = False
        try:
            user32.EmptyClipboard()
            transferred = bool(user32.SetClipboardData(8, handle))  # CF_DIB
            if not transferred:
                raise OSError("이미지를 클립보드에 기록하지 못했습니다.")
        finally:
            user32.CloseClipboard()
            if not transferred:
                kernel32.GlobalFree(handle)

    def start_region_copy(self) -> None:
        if self.display_image is None:
            return
        self._region_copy_mode = True
        self._region_start = None
        self.canvas.configure(cursor="crosshair")
        self.status.configure(text="복사할 영역을 이미지 위에서 드래그하세요 · Esc 취소")

    def _cancel_region_copy(self) -> None:
        self._region_copy_mode = False
        self._region_start = None
        if self._region_rect is not None:
            self.canvas.delete(self._region_rect)
            self._region_rect = None
        self.canvas.configure(cursor="arrow")

    def _finish_region_copy(self, end_x: int, end_y: int) -> None:
        start = self._region_start
        image = self.display_image
        if start is None or image is None:
            self._cancel_region_copy()
            return
        width, height = self._rendered_image_size()
        canvas_left = self.canvas.winfo_width() / 2 + self.offset_x - width / 2
        canvas_top = self.canvas.winfo_height() / 2 + self.offset_y - height / 2

        def to_image(x: float, y: float) -> Tuple[int, int]:
            ix = round((x - canvas_left) * image.width / width)
            iy = round((y - canvas_top) * image.height / height)
            return (max(0, min(image.width, ix)), max(0, min(image.height, iy)))

        x0, y0 = to_image(*start)
        x1, y1 = to_image(end_x, end_y)
        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))
        self._cancel_region_copy()
        if right - left < 2 or bottom - top < 2:
            self.status.configure(text="복사할 영역이 너무 작습니다")
            return
        cropped = image.crop((left, top, right, bottom))
        try:
            self._copy_pil_to_windows_clipboard(cropped)
        except OSError as exc:
            messagebox.showerror("영역 복사 실패", str(exc), parent=self)
            return
        self.status.configure(text=f"선택 영역을 클립보드에 복사했습니다 · {cropped.width}×{cropped.height}")

    def _on_motion(self, event) -> None:
        if self.display_image is None:
            return
        cw = self.canvas.winfo_width() / 2
        ch = self.canvas.winfo_height() / 2
        effective_zoom = self._effective_bitmap_zoom()
        ix = (event.x - cw - self.offset_x) / effective_zoom + self.display_image.width / 2
        iy = (event.y - ch - self.offset_y) / effective_zoom + self.display_image.height / 2
        x, y = int(ix), int(iy)
        if 0 <= x < self.display_image.width and 0 <= y < self.display_image.height:
            px = self.display_image.getpixel((x, y))
            if isinstance(px, int):
                px = (px,)
            if len(px) >= 3:
                red, green, blue = (int(px[0]), int(px[1]), int(px[2]))
            else:
                gray = int(px[0])
                red = green = blue = gray
            color_hex = f"#{red:02X}{green:02X}{blue:02X}"
            anim = f"  ·  f{self.anim_index + 1}/{len(self.anim_frames)}" if self.is_animated else ""
            self.status.configure(
                text=f"Pixel ({x}, {y})  {color_hex}{anim}"
            )

    # ----- save / slideshow ------------------------------------------------



    def _slideshow_tick(self) -> None:
        # Advance without treating as "other button" interrupt
        self.slideshow_job = None
        if not self._slideshow_active:
            return
        if len(self.folder_files) < 2:
            self._stop_slideshow()
            return
        nxt = (self.index + 1) % len(self.folder_files)
        self.index = nxt
        self._select_list_index(nxt)
        self._load_current()
        self._queue_thumbs_priority()
        ms = int(self.settings.get("slideshow_ms", 3000))
        if self._slideshow_active:
            self.slideshow_job = self.after(ms, self._slideshow_tick)
        self._update_slide_button()

    def toggle_image_fullscreen(self) -> None:
        """Show only the image canvas in true fullscreen (hide playlist/info/chrome)."""
        if self._image_fullscreen:
            self.exit_image_fullscreen()
        else:
            self.enter_image_fullscreen()

    def enter_image_fullscreen(self) -> None:
        if self._image_fullscreen:
            return
        self._image_fullscreen = True
        self._chrome_visible = False
        # Hide chrome
        self.navigation_bar.grid_remove()
        self.toolbar.grid_remove()
        self.context_bar.grid_remove()
        try:
            self.paned.forget(self.left_panel)
        except tk.TclError:
            pass
        if self._info_visible and self._right_panel is not None:
            try:
                self.paned.forget(self._right_panel)
            except tk.TclError:
                pass
        self.attributes("-fullscreen", True)
        self.after(80, self.fit_to_window)
        self.status.configure(text="이미지 전체화면  ·  Esc 또는 F11 로 종료")

    def exit_image_fullscreen(self) -> None:
        if not self._image_fullscreen:
            return
        self._image_fullscreen = False
        self.attributes("-fullscreen", False)
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.navigation_bar.grid(row=1, column=0, sticky="ew")
        if self._context_visible:
            self.context_bar.grid(row=3, column=0, sticky="ew")
        try:
            # Restore order: left, center, (right)
            # paned may still have center; re-add left at start
            panes = self.paned.panes()
            # forget all and re-add in order
            for p in list(panes):
                try:
                    self.paned.forget(p)
                except tk.TclError:
                    pass
            self.paned.add(self.left_panel, weight=0)
            if self._center_panel is not None:
                self.paned.add(self._center_panel, weight=1)
            if self._info_visible and self._right_panel is not None:
                self.paned.add(self._right_panel, weight=0)
        except tk.TclError:
            pass
        self._restore_panes()
        self._chrome_visible = True
        self._sashes_applied = False
        self.after(80, self._init_sashes)
        self.after(100, self.fit_to_window)

    def toggle_fullscreen(self) -> None:
        # Back-compat alias
        self.toggle_image_fullscreen()

    # ----- info / prefs ----------------------------------------------------




    # ----- CrowEyes 0.9 UI layer ------------------------------------------

    def _theme(self) -> dict:
        return CROWEYES_THEMES.get(
            self.settings.get("ui_theme", "croweyes_dark"),
            CROWEYES_THEMES["croweyes_dark"],
        )

    def _apply_native_window_theme(self) -> None:
        """Make the Windows title bar follow the active CrowEyes theme."""
        if os.name != "nt":
            return
        try:
            import ctypes

            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            dark = ctypes.c_int(
                1 if self.settings.get("ui_theme", "croweyes_dark") == "croweyes_dark" else 0
            )
            # Windows 10 20H1+ uses attribute 20; older builds used 19.
            for attribute in (20, 19):
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attribute, ctypes.byref(dark), ctypes.sizeof(dark)
                )
                if result == 0:
                    break
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x27)
        except (AttributeError, OSError, tk.TclError):
            pass

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self.config(menu="")
        self.toolbar = CrowEyesToolbar(self, self)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        self.navigation_bar = NavigationBar(self, self)
        self.navigation_bar.grid(row=1, column=0, sticky="ew")

        self.paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL, style="CrowEyes.TPanedwindow")
        self.paned.grid(row=2, column=0, sticky="nsew", padx=10, pady=(8, 6))

        self.left_panel = PlaylistPanel(self.paned, self)
        self._center_panel = ImageCanvasView(self.paned, self)
        self._right_panel = InfoPanel(self.paned, self)
        self.paned.add(self.left_panel, weight=0)
        self.paned.add(self._center_panel, weight=1)
        self.paned.add(self._right_panel, weight=0)

        self.context_bar = ContextControlBar(self, self)
        self.context_bar.grid(row=3, column=0, sticky="ew")
        if not self._context_visible:
            self.context_bar.grid_remove()
        if not self._playlist_visible:
            self.after(10, self.hide_playlist_panel)
        if not self._info_visible:
            self.after(10, self.hide_info_panel)
        self.after(140, self._init_sashes)
        self.bind("<Configure>", self._on_root_configure, add="+")

    def _build_modern_menus(self) -> None:
        self.config(menu="")
        bar = ttk.Frame(self, style="Chrome.TFrame", padding=(7, 2))
        bar.grid(row=0, column=0, sticky="ew")
        self._menu_frame = bar
        self._menubar = bar
        self._menus: List[tk.Menu] = []

        def cascade(label: str) -> tk.Menu:
            button = ttk.Menubutton(bar, text=label, style="Chrome.TMenubutton")
            button._croweyes_style = "Chrome.TMenubutton"  # type: ignore[attr-defined]
            menu = tk.Menu(button, tearoff=0)
            button.configure(menu=menu)
            button.pack(side=tk.LEFT, padx=(0, 2))
            self._menus.append(menu)
            return menu

        file_menu = cascade("파일")
        file_menu.add_command(label="파일 열기…", image=self._icons["open_image"], compound=tk.LEFT,
                              accelerator="Ctrl+O", command=self._action(self.open_file_dialog))
        file_menu.add_command(label="폴더로 보기…", image=self._icons["folder"], compound=tk.LEFT,
                              accelerator="Ctrl+Shift+O", command=self._action(self.open_folder_dialog))
        file_menu.add_command(label="다른 이름으로 저장…", image=self._icons["save"], compound=tk.LEFT,
                              accelerator="Ctrl+S", command=self._action(self.save_as))
        file_menu.add_command(label="인쇄…", image=self._icons["print"], compound=tk.LEFT,
                              accelerator="Ctrl+P", command=self._action(self.print_current_image))
        file_menu.add_separator()
        file_menu.add_command(label="최근 폴더", image=self._icons["folder"], compound=tk.LEFT, state=tk.DISABLED)
        file_menu.add_command(label="종료", image=self._icons["close"], compound=tk.LEFT, command=self._on_close)

        view_menu = cascade("보기")
        view_menu.add_command(label="확대", image=self._icons["zoom_in"], compound=tk.LEFT,
                              accelerator="+", command=self._action(lambda: self.zoom_by(1.15)))
        view_menu.add_command(label="축소", image=self._icons["zoom_out"], compound=tk.LEFT,
                              accelerator="-", command=self._action(lambda: self.zoom_by(1 / 1.15)))
        view_menu.add_command(label="화면 맞춤", image=self._icons["fit"], compound=tk.LEFT,
                              accelerator="Ctrl+1", command=self._action(self.fit_to_window))
        view_menu.add_command(label="1:1 원본 크기", image=self._icons["actual"], compound=tk.LEFT,
                              accelerator="Ctrl+0", command=self._action(self.actual_size))
        view_menu.add_command(label="전체화면", image=self._icons["fullscreen"], compound=tk.LEFT,
                              accelerator="F11", command=self.toggle_image_fullscreen)
        view_menu.add_separator()
        view_menu.add_command(label="정보 패널", image=self._icons["info"], compound=tk.LEFT,
                              accelerator="F8", command=self.toggle_info_panel)
        view_menu.add_command(label="플레이리스트 패널", image=self._icons["panel"], compound=tk.LEFT,
                              command=self.toggle_playlist_panel)
        view_menu.add_command(label="하단 컨텍스트 바", image=self._icons["panel"], compound=tk.LEFT,
                              command=self.toggle_context_bar)
        theme_menu = tk.Menu(view_menu, tearoff=0)
        self._menus.append(theme_menu)
        view_menu.add_cascade(label="테마", menu=theme_menu, image=self._icons["theme"], compound=tk.LEFT)
        self._theme_menu_var = tk.StringVar(
            value=self.settings.get("ui_theme", "croweyes_dark")
        )
        for key, label in THEME_LABELS.items():
            theme_menu.add_radiobutton(
                label=label, image=self._icons["theme"], compound=tk.LEFT,
                variable=self._theme_menu_var, value=key,
                command=lambda k=key: self.set_ui_theme(k),
            )

        image_menu = cascade("이미지")
        image_menu.add_command(label="오른쪽으로 회전", image=self._icons["rotate_right"], compound=tk.LEFT,
                               accelerator="Ctrl+R", command=self._action(lambda: self.rotate(90)))
        image_menu.add_command(label="왼쪽으로 회전", image=self._icons["rotate_left"], compound=tk.LEFT,
                               accelerator="Ctrl+L", command=self._action(lambda: self.rotate(-90)))
        image_menu.add_command(label="좌우 반전", image=self._icons["flip_h"], compound=tk.LEFT,
                               command=self._action(self.toggle_flip_h))
        image_menu.add_command(label="상하 반전", image=self._icons["flip_v"], compound=tk.LEFT,
                               command=self._action(self.toggle_flip_v))
        image_menu.add_separator()
        image_menu.add_command(label="밝기 초기화", image=self._icons["brightness"], compound=tk.LEFT,
                               command=lambda: self._reset_adjustment("brightness"))
        image_menu.add_command(label="대비 초기화", image=self._icons["contrast"], compound=tk.LEFT,
                               command=lambda: self._reset_adjustment("contrast"))

        slide_menu = cascade("슬라이드쇼")
        slide_menu.add_command(label="시작 / 일시정지", image=self._icons["play"], compound=tk.LEFT,
                               accelerator="F5", command=self.toggle_slideshow)
        slide_menu.add_command(label="간격 설정…", image=self._icons["settings"], compound=tk.LEFT,
                               command=self.show_preferences)

        help_menu = cascade("도움말")
        help_menu.add_command(label="단축키", image=self._icons["shortcuts"], compound=tk.LEFT,
                              command=self.show_shortcuts)
        help_menu.add_command(label="Windows 실행 차단 안내", command=self.show_windows_security_help)
        help_menu.add_command(label="프로그램 정보", image=self._icons["info"], compound=tk.LEFT,
                              command=self.show_about)

        settings_menu = cascade("설정")
        settings_menu.add_command(
            label="기본 프로그램 등록…", image=self._icons["settings"], compound=tk.LEFT,
            command=self.show_file_association_dialog,
        )
        settings_menu.add_command(
            label="Windows 기본 앱 설정 열기", image=self._icons["panel"], compound=tk.LEFT,
            command=self.open_windows_default_apps,
        )

    def _apply_theme(self) -> None:
        t = self._theme()
        canvas_bg = self.settings.get("bg_color") or t["canvas_bg"]
        self.configure(bg=t["bg"])
        self.canvas.configure(bg=canvas_bg)
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        for name, bg in (
            ("TFrame", t["bg"]), ("Toolbar.TFrame", t["toolbar"]),
            ("Chrome.TFrame", t["toolbar"]),
            ("Breadcrumb.TFrame", t["panel_alt"]),
            ("Panel.TFrame", t["panel"]), ("Viewer.TFrame", t["canvas_bg"]),
            ("BottomBar.TFrame", t["panel_alt"]),
        ):
            style.configure(name, background=bg)
        style.configure("Card.TFrame", background=t["panel"], bordercolor=t["border"],
                        borderwidth=1, relief="solid")
        style.configure("Viewer.TFrame", background=t["canvas_bg"], bordercolor=t["border"],
                        borderwidth=1, relief="solid")
        style.configure("TLabel", background=t["bg"], foreground=t["fg"], font=t["font"])
        style.configure("Brand.TLabel", background=t["toolbar"], foreground=t["fg"], font=("Segoe UI Semibold", 21))
        style.configure("Logo.TLabel", background=t["toolbar"], foreground=t["accent"], font=("Segoe UI", 17, "bold"))
        style.configure("Product.TLabel", background=t["toolbar"], foreground=t["muted"], font=("Segoe UI Semibold", 8))
        style.configure("Crumb.TLabel", background=t["toolbar"], foreground=t["muted"], font=("Segoe UI", 8))
        style.configure("Breadcrumb.TLabel", background=t["toolbar"], foreground=t["muted"], font=("Segoe UI", 9))
        style.configure(
            "Breadcrumb.TButton", background=t["toolbar"], foreground=t["fg"],
            borderwidth=0, relief="flat", padding=(4, 2), font=("Segoe UI", 9),
        )
        style.map("Breadcrumb.TButton", background=[("active", t["select"])])
        style.configure("FileTitle.TLabel", background=t["toolbar"], foreground=t["fg"], font=("Segoe UI Semibold", 9))
        style.configure("Section.TLabel", background=t["panel"], foreground=t["muted"], font=("Segoe UI Semibold", 9))
        style.configure("Badge.TLabel", background=t["select"], foreground=t["accent_hi"], padding=(7, 2), font=("Segoe UI Semibold", 8))
        style.configure("Title.TLabel", background=t["panel"], foreground=t["fg"], font=t["font_title"])
        style.configure("Muted.TLabel", background=t["toolbar"], foreground=t["muted"], font=t["font"])
        style.configure("Status.TLabel", background=t["panel_alt"], foreground=t["muted"], font=("Segoe UI", 9))
        style.configure("BottomBar.TLabel", background=t["panel_alt"], foreground=t["fg"], font=("Segoe UI", 9))
        style.configure(
            "Path.TLabel", background=t["button"], foreground=t["fg"],
            bordercolor=t["border"], borderwidth=1, relief="sunken",
            padding=(8, 3), font=("Segoe UI", 8),
        )
        style.configure("Tooltip.TLabel", background=t["panel_alt"], foreground=t["fg"], relief="solid", borderwidth=1)
        style.configure(
            "Chrome.TMenubutton", background=t["toolbar"], foreground=t["fg"],
            borderwidth=0, relief="flat", padding=(10, 4), arrowcolor=t["muted"],
            font=("Segoe UI", 9),
        )
        style.map(
            "Chrome.TMenubutton",
            background=[("pressed", t["select"]), ("active", t["button_active"])],
            foreground=[("active", t["fg"])],
        )
        button_style = {
            "background": t["button"], "foreground": t["button_fg"],
            "bordercolor": t["border"], "lightcolor": t["button_highlight"],
            "darkcolor": t["button_shadow"], "focuscolor": t["accent"],
            "borderwidth": 1, "relief": "raised",
        }
        style.configure(
            "Tool.TButton", **button_style, padding=(5, 4),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Tool.TButton",
            background=[("pressed", t["button_pressed"]), ("active", t["button_active"])],
            foreground=[("disabled", t["muted"])],
            relief=[("pressed", "sunken"), ("!pressed", "raised")],
        )
        icon_button_style = {
            "background": t["toolbar"], "foreground": t["fg"],
            "bordercolor": t["toolbar"], "lightcolor": t["toolbar"],
            "darkcolor": t["toolbar"], "focuscolor": t["toolbar"],
            # Reserve the hover border at all times. Its idle color matches
            # the toolbar, so hover changes paint only and never geometry.
            "borderwidth": 1, "relief": "flat", "padding": (5, 4),
        }
        style.configure("Icon.Tool.TButton", **icon_button_style)
        stable_icon_layout = [
            ("Button.border", {
                "sticky": "nswe", "border": "1",
                "children": [
                    ("Button.padding", {
                        "sticky": "nswe",
                        "children": [("Button.label", {"sticky": "nswe"})],
                    }),
                ],
            }),
        ]
        style.layout("Icon.Tool.TButton", stable_icon_layout)
        style.map(
            "Icon.Tool.TButton",
            background=[("pressed", t["button_pressed"]), ("active", t["select"])],
            foreground=[("disabled", t["muted"])],
            bordercolor=[("active", t["accent_hi"]), ("!active", t["toolbar"])],
            lightcolor=[("active", t["accent"]), ("!active", t["toolbar"])],
            darkcolor=[("active", t["accent"]), ("!active", t["toolbar"])],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )
        glow_icon_style = dict(icon_button_style)
        glow_icon_style.update(
            background=t["select"], bordercolor=t["accent_hi"],
            lightcolor=t["accent"], darkcolor=t["accent"], focuscolor=t["accent_hi"],
            borderwidth=1,
        )
        style.configure("Glow.Icon.Tool.TButton", **glow_icon_style)
        style.layout("Glow.Icon.Tool.TButton", stable_icon_layout)
        style.map(
            "Glow.Icon.Tool.TButton",
            background=[("pressed", t["button_pressed"]), ("active", t["select"])],
            bordercolor=[("active", t["accent_hi"])],
            lightcolor=[("active", t["accent"])], darkcolor=[("active", t["accent"])],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )
        active_icon_style = dict(icon_button_style)
        active_icon_style.update(
            background=t["accent_button"], bordercolor=t["accent_hi"],
            lightcolor=t["accent"], darkcolor=t["accent"],
        )
        style.configure("Accent.Icon.Tool.TButton", **active_icon_style)
        style.layout("Accent.Icon.Tool.TButton", stable_icon_layout)
        style.map(
            "Accent.Icon.Tool.TButton",
            background=[("pressed", t["accent_pressed"]), ("active", t["accent_button"])],
            relief=[("pressed", "flat"), ("!pressed", "flat")],
        )
        accent_button_style = dict(button_style)
        accent_button_style.update(
            background=t["accent_button"], foreground="#FFFFFF", padding=(5, 4),
        )
        style.configure("Accent.Tool.TButton", **accent_button_style)
        style.map(
            "Accent.Tool.TButton",
            background=[("pressed", t["accent_pressed"]), ("active", t["accent_button"])],
            relief=[("pressed", "sunken"), ("!pressed", "raised")],
        )
        style.configure("Pastel.TButton", **button_style, padding=(10, 6), font=t["font"])
        style.map(
            "Pastel.TButton",
            background=[("pressed", t["button_pressed"]), ("active", t["button_active"])],
            relief=[("pressed", "sunken"), ("!pressed", "raised")],
        )
        style.configure("CrowEyes.Horizontal.TScale", background=t["panel_alt"], troughcolor=t["border"],
                        bordercolor=t["border"], lightcolor=t["accent"], darkcolor=t["accent"])
        style.configure("CrowEyes.TPanedwindow", background=t["bg"], sashwidth=6)
        for entry_style in ("TEntry", "Search.TEntry", "TSpinbox"):
            style.configure(
                entry_style, fieldbackground=t["panel_alt"], background=t["panel_alt"],
                foreground=t["fg"], insertcolor=t["fg"], bordercolor=t["border"],
                lightcolor=t["button_highlight"], darkcolor=t["button_shadow"],
                padding=5,
            )
            style.map(
                entry_style,
                fieldbackground=[("disabled", t["bg"]), ("readonly", t["panel_alt"])],
                foreground=[("disabled", t["muted"]), ("readonly", t["fg"])],
            )
        style.configure("Search.TEntry", padding=(6, 2))
        style.configure("Treeview", background=t["panel"], fieldbackground=t["panel"], foreground=t["fg"],
                        bordercolor=t["border"], rowheight=30, font=t["font"])
        style.map("Treeview", background=[("selected", t["select"])], foreground=[("selected", t["select_fg"])])
        style.configure("TCombobox", fieldbackground=t["panel_alt"], background=t["button"], foreground=t["fg"],
                        arrowcolor=t["muted"], bordercolor=t["border"])
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", t["panel_alt"]), ("disabled", t["bg"])],
            foreground=[("readonly", t["fg"]), ("disabled", t["muted"])],
            selectbackground=[("readonly", t["panel_alt"])],
            selectforeground=[("readonly", t["fg"])],
        )
        style.configure(
            "TCheckbutton", background=t["panel"], foreground=t["fg"],
            indicatorcolor=t["panel_alt"], bordercolor=t["border"], focuscolor=t["accent"],
        )
        style.map(
            "TCheckbutton", background=[("active", t["panel"])],
            foreground=[("disabled", t["muted"])],
            indicatorcolor=[("selected", t["accent_button"]), ("!selected", t["panel_alt"])],
        )
        style.configure(
            "TScrollbar", background=t["button"], troughcolor=t["panel_alt"],
            bordercolor=t["border"], arrowcolor=t["fg"],
            lightcolor=t["button_highlight"], darkcolor=t["button_shadow"],
        )
        style.map("TScrollbar", background=[("active", t["button_active"]), ("pressed", t["accent_button"])])

        def restore_product_widget_styles(widget: tk.Widget) -> None:
            product_style = getattr(widget, "_croweyes_style", None)
            if product_style:
                try:
                    widget.configure(style=product_style)
                except tk.TclError:
                    pass
            for child in widget.winfo_children():
                restore_product_widget_styles(child)

        restore_product_widget_styles(self)
        self.info_text.configure(bg=t["panel_alt"], fg=t["fg"], insertbackground=t["fg"],
                                 selectbackground=t["select"], selectforeground=t["select_fg"],
                                 font=t["font"], highlightthickness=0)
        self.info_text.tag_configure("label", foreground=t["muted"], font=("Segoe UI Semibold", 8))
        self.info_text.tag_configure("value", foreground=t["fg"], font=("Segoe UI", 10), spacing3=8)
        self._info_close_btn.configure(bg=t["panel"], fg=t["muted"], activebackground=t["select"],
                                       activeforeground=t["fg"], highlightthickness=0)
        self._playlist_close_btn.configure(
            bg=t["panel"], fg=t["muted"], activebackground=t["select"],
            activeforeground=t["fg"], highlightthickness=0,
        )
        self._style_canvas_nav_button(self._canvas_prev_btn)
        self._style_canvas_nav_button(self._canvas_next_btn)
        if self._grid_canvas is not None:
            self._grid_canvas.configure(bg=t["panel"])
        for menu in getattr(self, "_menus", []):
            try:
                menu.configure(bg=t["toolbar"], fg=t["fg"], activebackground=t["select"],
                               activeforeground=t["select_fg"], bd=0)
            except tk.TclError:
                pass
        self._style_list_widget()
        self._make_placeholder()
        self.after_idle(self._apply_native_window_theme)

    def _init_sashes(self, retry: int = 0) -> None:
        if self._sashes_applied:
            return
        try:
            self.update_idletasks()
            pw = self.paned.winfo_width()
            if pw < 700 and retry < 12:
                if self._sash_init_job is None:
                    self._sash_init_job = self.after(50, self._retry_init_sashes, retry + 1)
                return
            pw = max(pw, 700)
            panes = self.paned.panes()
            if len(panes) >= 3:
                playlist_ratio = max(0.18, min(0.32, float(self.settings.get("pane_ratio_playlist", 0.22))))
                info_ratio = max(0.14, min(0.28, float(self.settings.get("pane_ratio_info", 0.18))))
                left = max(170, int(pw * playlist_ratio))
                right = max(150, int(pw * info_ratio))
                if pw - left - right < 360:
                    overflow = 360 - (pw - left - right)
                    left = max(150, left - (overflow + 1) // 2)
                    right = max(135, right - overflow // 2)
                self.paned.sashpos(0, left)
                self.paned.sashpos(1, pw - right)
            elif len(panes) == 2:
                first_is_playlist = self._playlist_visible
                self.paned.sashpos(0, max(170, int(pw * 0.22)) if first_is_playlist else min(pw - 150, int(pw * 0.82)))
            self._sashes_applied = True
        except (tk.TclError, IndexError):
            pass

    def _retry_init_sashes(self, retry: int) -> None:
        self._sash_init_job = None
        self._init_sashes(retry)

    def _restore_panes(self) -> None:
        try:
            for pane in list(self.paned.panes()):
                self.paned.forget(pane)
            if self._playlist_visible and self.left_panel is not None:
                self.paned.add(self.left_panel, weight=0)
            if self._center_panel is not None:
                self.paned.add(self._center_panel, weight=1)
            if self._info_visible and self._right_panel is not None:
                self.paned.add(self._right_panel, weight=0)
        except tk.TclError:
            pass
        self._sashes_applied = False
        self.after(40, self._init_sashes)

    def hide_playlist_panel(self) -> None:
        self._playlist_visible = False
        self._playlist_panel_var.set(False)
        self.settings["show_playlist_panel"] = False
        self._restore_panes()

    def show_playlist_panel(self) -> None:
        self._playlist_visible = True
        self._playlist_panel_var.set(True)
        self.settings["show_playlist_panel"] = True
        self._restore_panes()

    def toggle_playlist_panel(self) -> None:
        self.hide_playlist_panel() if self._playlist_visible else self.show_playlist_panel()

    def hide_info_panel(self) -> None:
        self._info_visible = False
        self._info_panel_var.set(False)
        self.settings["show_info_panel"] = False
        self._restore_panes()

    def show_info_panel(self) -> None:
        self._info_visible = True
        self._info_panel_var.set(True)
        self.settings["show_info_panel"] = True
        self._restore_panes()

    def toggle_info_panel(self) -> None:
        self.hide_info_panel() if self._info_visible else self.show_info_panel()

    def toggle_context_bar(self) -> None:
        self._context_visible = not self._context_visible
        self.settings["show_context_bar"] = self._context_visible
        if self._context_visible:
            self.context_bar.grid()
        else:
            self.context_bar.grid_remove()

    def set_ui_theme(self, theme: str) -> None:
        if theme not in CROWEYES_THEMES:
            return
        self.settings["ui_theme"] = theme
        save_settings(self.settings)
        self._cancel_thumb_jobs()
        self._thumb_photos.clear()
        self._thumb_loaded.clear()
        self._rebuild_icon_chrome()
        self._populate_list_names_only()
        self._queue_thumbs_priority()
        self.redraw()

    def _rebuild_icon_chrome(self) -> None:
        status_text = self.status.cget("text") if hasattr(self, "status") else ""
        brightness = self.brightness
        contrast = self.contrast
        if hasattr(self, "toolbar"):
            self.toolbar.destroy()
        if hasattr(self, "context_bar"):
            self.context_bar.destroy()
        if hasattr(self, "_menu_frame"):
            self._menu_frame.destroy()
        if hasattr(self, "navigation_bar"):
            self.navigation_bar.destroy()
        self._icons = CrowEyesIconSet(self, self._theme())
        self.iconphoto(True, self._icons["app"])
        self._navigation_buttons = []
        self.toolbar = CrowEyesToolbar(self, self)
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.navigation_bar = NavigationBar(self, self)
        self.navigation_bar.grid(row=1, column=0, sticky="ew")
        self.context_bar = ContextControlBar(self, self)
        self.context_bar.grid(row=3, column=0, sticky="ew")
        if not self._context_visible:
            self.context_bar.grid_remove()
        self.bright_var.set(brightness)
        self.contrast_var.set(contrast)
        self.status.configure(text=status_text)
        self._info_close_btn.configure(image=self._icons["close"])
        self._info_close_btn._croweyes_image = self._icons["close"]  # type: ignore[attr-defined]
        self._playlist_close_btn.configure(image=self._icons["close"])
        self._playlist_close_btn._croweyes_image = self._icons["close"]  # type: ignore[attr-defined]
        self._apply_theme()
        self._update_slide_button()
        self._update_safety_indicator()
        self._anim_btn.configure(state=tk.NORMAL if self.is_animated else tk.DISABLED)
        self._update_navigation_state()
        self._last_responsive_compact = None
        self.after_idle(lambda: self._update_responsive_layout(self.winfo_width()))

    def _reset_adjustment(self, which: str) -> None:
        if which == "brightness":
            self.bright_var.set(1.0)
        else:
            self.contrast_var.set(1.0)
        self._on_adjust()

    def _visible_playlist_indices(self) -> List[int]:
        query = self._search_var.get().strip().casefold()
        if query:
            self._filtered_indices = [i for i, p in enumerate(self.folder_files) if query in p.name.casefold()]
        else:
            self._filtered_indices = list(range(len(self.folder_files)))
        return self._filtered_indices

    def _visible_playlist_items(self) -> List[Tuple[str, Path, Optional[int]]]:
        """Return folder navigation rows followed by image rows."""
        items: List[Tuple[str, Path, Optional[int]]] = []
        query = self._search_var.get().strip().casefold()
        folder = self.current_folder
        if folder is None:
            seen: Set[str] = set()
            for label, target in special_folders():
                key = os.path.normcase(str(target))
                if key not in seen and (not query or query in label.casefold()):
                    seen.add(key)
                    items.append((f"special:{label}", target, None))
            for drive in list_windows_drives():
                label = drive.drive or str(drive)
                key = os.path.normcase(str(drive))
                if key not in seen and (not query or query in label.casefold()):
                    seen.add(key)
                    items.append(("drive", drive, None))
        else:
            subdirs = list(self._folder_dirs)
            if self.sort_desc:
                subdirs.reverse()
            for subdir in subdirs:
                if not query or query in subdir.name.casefold():
                    items.append(("folder", subdir, None))
        for idx in self._visible_playlist_indices():
            items.append(("image", self.folder_files[idx], idx))
        return items

    def _apply_playlist_filter(self, _event=None) -> None:
        self._cancel_thumb_jobs()
        self._populate_list_names_only()
        self._select_list_index(self.index)
        self._queue_thumbs_visible()

    def _on_canvas_resize(self, _event=None) -> None:
        if self._canvas_resize_job is not None:
            try:
                self.after_cancel(self._canvas_resize_job)
            except tk.TclError:
                pass
        self._canvas_resize_job = self.after(80, self._finish_canvas_resize)

    def _finish_canvas_resize(self) -> None:
        self._canvas_resize_job = None
        if self._view_mode == "fit" and self.display_image is not None:
            self.fit_to_window()
        else:
            self.redraw()

    def _update_header(self) -> None:
        folder = self.current_folder
        self._folder_title_var.set(folder.name if folder else "내 컴퓨터")
        if 0 <= self.index < len(self.folder_files):
            current = self.folder_files[self.index]
            self._file_title_var.set(current.name)
            self._current_path_var.set(str(current))
        else:
            self._file_title_var.set("이미지를 열어 주세요")
            self._current_path_var.set(str(folder) if folder else "경로 없음")
        self._playlist_count_var.set(str(len(self.folder_files)))
        self._update_breadcrumb()
        self._update_navigation_state()
        self._update_canvas_navigation_buttons()

    def show_shortcuts(self) -> None:
        messagebox.showinfo(
            "CrowEyes 단축키",
            "Ctrl+O  이미지 열기\nCtrl+Shift+O  폴더 열기\nCtrl+P  인쇄\n"
            "← / →  이전·다음 이미지\n+ / -  확대·축소\nCtrl+0  1:1\nCtrl+1  화면 맞춤\n"
            "Ctrl+R / Ctrl+L  회전\nF5  슬라이드쇼\nF8  정보 패널\n"
            "F11  이미지 전체화면\nSpace  GIF/WebP 재생·일시정지\n"
            "마우스 휠  이전·다음 이미지 (환경설정에서 확대·축소로 변경)",
        )

    def show_preferences(self) -> None:
        win = tk.Toplevel(self)
        win.title("CrowEyes 환경설정")
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)
        current_theme = self.settings.get("ui_theme", "croweyes_dark")
        theme_var = tk.StringVar(value=THEME_LABELS.get(current_theme, THEME_LABELS["croweyes_dark"]))
        fit_var = tk.BooleanVar(value=bool(self.settings.get("fit_on_open", True)))
        slide_var = tk.IntVar(value=int(self.settings.get("slideshow_ms", 3000)))
        playlist_var = tk.BooleanVar(value=self._playlist_visible)
        info_var = tk.BooleanVar(value=self._info_visible)
        context_var = tk.BooleanVar(value=self._context_visible)
        compact_var = tk.BooleanVar(value=bool(self.settings.get("compact_toolbar", False)))
        update_var = tk.BooleanVar(value=bool(self.settings.get("auto_check_updates", True)))
        safety_var = tk.StringVar(value=self._content_filter_mode)
        wheel_action = self.settings.get("mouse_wheel_action", "navigate")
        wheel_var = tk.StringVar(
            value=WHEEL_ACTION_LABELS.get(wheel_action, WHEEL_ACTION_LABELS["navigate"])
        )
        frame = ttk.Frame(win, style="Panel.TFrame", padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="화면", style="Title.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))
        ttk.Label(frame, text="테마").grid(row=1, column=0, sticky="w", pady=6, padx=(0, 18))
        ttk.Combobox(frame, textvariable=theme_var, values=list(THEME_LABELS.values()), state="readonly", width=20).grid(row=1, column=1, sticky="ew")
        ttk.Checkbutton(frame, text="플레이리스트 패널 표시", variable=playlist_var).grid(row=2, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(frame, text="정보 패널 표시", variable=info_var).grid(row=3, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(frame, text="하단 컨텍스트 바 표시", variable=context_var).grid(row=4, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(frame, text="컴팩트 툴바", variable=compact_var).grid(row=5, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(frame, text="열 때 화면에 맞춤", variable=fit_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Label(frame, text="마우스 휠 동작").grid(row=7, column=0, sticky="w", pady=8)
        ttk.Combobox(
            frame, textvariable=wheel_var, values=list(WHEEL_ACTION_LABELS.values()),
            state="readonly", width=20,
        ).grid(row=7, column=1, sticky="ew")
        ttk.Label(frame, text="슬라이드 간격 (ms)").grid(row=8, column=0, sticky="w", pady=8)
        ttk.Spinbox(frame, from_=200, to=60000, textvariable=slide_var, width=12).grid(row=8, column=1, sticky="w")
        ttk.Checkbutton(frame, text="프로그램 시작 시 새 버전 확인 (24시간 간격)", variable=update_var).grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(6, 0),
        )
        ttk.Separator(frame).grid(row=10, column=0, columnspan=2, sticky="ew", pady=(14, 10))
        ttk.Label(frame, text="콘텐츠 안전 (로컬 처리)", style="Title.TLabel").grid(
            row=11, column=0, columnspan=2, sticky="w",
        )
        ttk.Radiobutton(
            frame, text="끄기 (기본값)", variable=safety_var, value=MODE_OFF,
        ).grid(row=12, column=0, columnspan=2, sticky="w", pady=(6, 0))
        ttk.Radiobutton(
            frame, text="노골적인 노출 이미지 차단", variable=safety_var, value=MODE_EXPLICIT,
        ).grid(row=13, column=0, columnspan=2, sticky="w")
        ttk.Label(
            frame,
            text="이미지는 외부로 전송되지 않습니다. 판정할 수 없으면 보호를 위해 숨깁니다.",
            style="Section.TLabel",
        ).grid(row=14, column=0, columnspan=2, sticky="w", pady=(4, 4))
        ttk.Button(
            frame, text="로컬 판정 캐시 비우기",
            command=lambda: self._clear_safety_cache(win), style="Pastel.TButton",
        ).grid(row=15, column=0, columnspan=2, sticky="w", pady=(2, 0))

        def apply_settings() -> None:
            requested_safety_mode = safety_var.get()
            self.settings.update({
                "ui_theme": next((key for key, label in THEME_LABELS.items() if label == theme_var.get()), "croweyes_dark"),
                "fit_on_open": fit_var.get(),
                "slideshow_ms": int(slide_var.get()), "show_playlist_panel": playlist_var.get(),
                "show_info_panel": info_var.get(), "show_context_bar": context_var.get(),
                "compact_toolbar": compact_var.get(),
                "auto_check_updates": update_var.get(),
                "content_filter": requested_safety_mode,
                "mouse_wheel_action": next(
                    (key for key, label in WHEEL_ACTION_LABELS.items() if label == wheel_var.get()),
                    "navigate",
                ),
            })
            self._playlist_visible = playlist_var.get()
            self._info_visible = info_var.get()
            self._context_visible = context_var.get()
            self._rebuild_icon_chrome()
            self._restore_panes()
            save_settings(self.settings)
            win.destroy()
            self._set_content_filter(requested_safety_mode)
            self.redraw()

        buttons = ttk.Frame(frame, style="Panel.TFrame")
        buttons.grid(row=16, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(buttons, text="취소", command=win.destroy, style="Pastel.TButton").pack(side=tk.LEFT, padx=4)
        ttk.Button(buttons, text="저장", command=apply_settings, style="Pastel.TButton").pack(side=tk.LEFT)
        self._apply_theme()

    @staticmethod
    def _association_open_command() -> str:
        """Return the command Windows should use to open an image."""
        executable = Path(sys.executable).resolve()
        if getattr(sys, "frozen", False):
            return f'"{executable}" "%1"'
        script = Path(__file__).resolve()
        return f'"{executable}" "{script}" "%1"'

    @staticmethod
    def _registry_set(path: str, name: str, value: str) -> None:
        if winreg is None:
            raise OSError("Windows 레지스트리를 사용할 수 없습니다.")
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_SET_VALUE,
        ) as key:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)

    @staticmethod
    def _registry_value_exists(path: str, name: str = "") -> bool:
        if winreg is None:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, name)
            return True
        except OSError:
            return False

    def register_file_associations(self, extensions: List[str]) -> None:
        """Register CrowEyes as an Open With candidate for selected formats."""
        if os.name != "nt" or winreg is None:
            raise OSError("기본 프로그램 등록은 Windows에서만 지원됩니다.")

        allowed_options = ASSOCIATION_OPTIONS + (OPTIONAL_ASSOCIATION_OPTIONS if find_ghostscript() else ())
        allowed = {ext for ext, _description in allowed_options}
        selected = sorted({ext.lower() for ext in extensions if ext.lower() in allowed})
        if not selected:
            raise ValueError("등록할 이미지 확장자를 선택해 주세요.")

        command = self._association_open_command()
        executable = str(Path(sys.executable).resolve())
        classes = rf"Software\Classes\{ASSOCIATION_PROG_ID}"
        capabilities = rf"Software\{ASSOCIATION_APP_NAME}\Capabilities"
        app_class = rf"Software\Classes\Applications\CrowEyes.exe"

        self._registry_set(classes, "", "CrowEyes 이미지")
        self._registry_set(classes, "FriendlyTypeName", "CrowEyes 이미지")
        self._registry_set(classes + r"\DefaultIcon", "", f'"{executable}",0')
        self._registry_set(classes + r"\shell\open\command", "", command)
        self._registry_set(capabilities, "ApplicationName", ASSOCIATION_APP_NAME)
        self._registry_set(
            capabilities, "ApplicationDescription",
            "빠르고 간결한 CrowEyes 이미지 뷰어",
        )
        self._registry_set(capabilities, "ApplicationIcon", f'"{executable}",0')
        self._registry_set(
            r"Software\RegisteredApplications", ASSOCIATION_APP_NAME, capabilities,
        )
        self._registry_set(app_class, "FriendlyAppName", APP_NAME)
        self._registry_set(app_class + r"\shell\open\command", "", command)

        for extension in selected:
            self._registry_set(
                capabilities + r"\FileAssociations", extension, ASSOCIATION_PROG_ID,
            )
            self._registry_set(
                rf"Software\Classes\{extension}\OpenWithProgids",
                ASSOCIATION_PROG_ID, "",
            )
            self._registry_set(app_class + r"\SupportedTypes", extension, "")

        try:
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except (AttributeError, OSError):
            pass

    def set_default_associations_when_unclaimed(self, extensions: List[str]) -> Tuple[List[str], List[str]]:
        """Set CrowEyes as default only where Windows has no protected user choice.

        Windows 10/11 protects an existing UserChoice with a signed hash. We
        never bypass that protection; those formats remain unchanged.
        """
        self.register_file_associations(extensions)
        applied: List[str] = []
        protected: List[str] = []
        for extension in sorted(set(extensions)):
            user_choice = (
                rf"Software\Microsoft\Windows\CurrentVersion\Explorer\FileExts\{extension}"
                r"\UserChoice"
            )
            if self._registry_value_exists(user_choice, "ProgId"):
                protected.append(extension)
                continue
            self._registry_set(rf"Software\Classes\{extension}", "", ASSOCIATION_PROG_ID)
            applied.append(extension)
        try:
            import ctypes
            ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)
        except (AttributeError, OSError):
            pass
        return applied, protected

    def _auto_register_file_associations(self) -> None:
        extensions = list(self.settings.get("association_extensions", []))
        if not extensions:
            return
        try:
            applied, protected = self.set_default_associations_when_unclaimed(extensions)
        except (OSError, ValueError) as exc:
            self.status.configure(text=f"기본 프로그램 자동 등록 실패: {exc}")
            return
        if applied:
            self.status.configure(text=f"CrowEyes 기본 연결 {len(applied)}개 자동 적용")
        elif protected:
            self.status.configure(text="기존 Windows 기본 앱 설정을 유지했습니다")

    def open_windows_default_apps(self) -> None:
        """Open CrowEyes' Windows Default Apps page when available."""
        if os.name != "nt":
            messagebox.showinfo(
                "Windows 기본 앱", "이 기능은 Windows에서만 지원됩니다.", parent=self,
            )
            return
        try:
            os.startfile(
                f"ms-settings:defaultapps?registeredAppUser={ASSOCIATION_APP_NAME}"
            )
        except OSError:
            try:
                os.startfile("ms-settings:defaultapps")
            except OSError as exc:
                messagebox.showerror(
                    "Windows 기본 앱", f"설정 화면을 열 수 없습니다.\n\n{exc}", parent=self,
                )

    def show_file_association_dialog(self) -> None:
        """Choose formats and register them without forcing Windows UserChoice."""
        win = tk.Toplevel(self)
        win.title("CrowEyes 기본 프로그램 등록")
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)
        win.iconphoto(True, self._icons["app"])

        frame = ttk.Frame(win, style="Panel.TFrame", padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="기본 프로그램 등록", style="Title.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w",
        )
        ttk.Label(
            frame,
            text=(
                "CrowEyes로 열 이미지 형식을 선택하세요. 기존 기본 앱이 없는 형식은\n"
                "즉시 연결하고, Windows가 보호하는 기존 선택은 안전하게 유지합니다."
            ),
            style="Section.TLabel", justify=tk.LEFT,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))

        remembered = set(self.settings.get("association_extensions", []))
        association_options = ASSOCIATION_OPTIONS + (OPTIONAL_ASSOCIATION_OPTIONS if find_ghostscript() else ())
        variables: Dict[str, tk.BooleanVar] = {}
        for index, (extension, description) in enumerate(association_options):
            variable = tk.BooleanVar(value=extension in remembered)
            variables[extension] = variable
            row = 2 + index // 2
            column = index % 2
            ttk.Checkbutton(
                frame, text=f"{extension.upper():<7}  {description}", variable=variable,
            ).grid(row=row, column=column, sticky="w", padx=(0, 24), pady=3)

        def select_all(value: bool) -> None:
            for variable in variables.values():
                variable.set(value)

        action_row = 2 + (len(association_options) + 1) // 2
        selectors = ttk.Frame(frame, style="Panel.TFrame")
        selectors.grid(row=action_row, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Button(
            selectors, text="모두 선택", command=lambda: select_all(True), style="Pastel.TButton",
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            selectors, text="선택 해제", command=lambda: select_all(False), style="Pastel.TButton",
        ).pack(side=tk.LEFT)

        startup_var = tk.BooleanVar(value=bool(self.settings.get("auto_register_associations", False)))
        ttk.Checkbutton(
            frame, text="프로그램 시작 시 선택 형식의 등록 상태 자동 확인",
            variable=startup_var,
        ).grid(row=action_row + 1, column=0, columnspan=2, sticky="w", pady=(10, 0))

        def register_selected(open_settings: bool = False) -> None:
            selected = [extension for extension, variable in variables.items() if variable.get()]
            if not selected:
                messagebox.showinfo(
                    "기본 프로그램 등록", "하나 이상의 확장자를 선택해 주세요.", parent=win,
                )
                return
            try:
                applied, protected = self.set_default_associations_when_unclaimed(selected)
            except (OSError, ValueError) as exc:
                messagebox.showerror(
                    "기본 프로그램 등록", f"등록하지 못했습니다.\n\n{exc}", parent=win,
                )
                return
            self.settings["association_extensions"] = selected
            self.settings["auto_register_associations"] = startup_var.get()
            save_settings(self.settings)
            win.destroy()
            messagebox.showinfo(
                "등록 완료",
                f"즉시 연결: {len(applied)}개\n"
                f"기존 Windows 선택 유지: {len(protected)}개\n\n"
                "보호된 형식을 변경하려면 Windows 기본 앱 설정에서 CrowEyes를 선택하세요.",
                parent=self,
            )
            if open_settings and protected:
                self.open_windows_default_apps()

        buttons = ttk.Frame(frame, style="Panel.TFrame")
        buttons.grid(row=action_row + 2, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(
            buttons, text="취소", command=win.destroy, style="Pastel.TButton",
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            buttons, text="자동 등록", command=lambda: register_selected(False),
            style="Pastel.TButton",
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            buttons, text="등록 후 Windows 설정 열기", command=lambda: register_selected(True),
            style="Pastel.TButton",
        ).pack(side=tk.LEFT)
        self._apply_theme()

    def _stop_slideshow(self, quiet: bool = False) -> None:
        was_playing = self._slideshow_active
        self._slideshow_active = False
        if self.slideshow_job is not None:
            try:
                self.after_cancel(self.slideshow_job)
            except (tk.TclError, ValueError):
                pass
            self.slideshow_job = None
        if was_playing and not quiet:
            self.status.configure(text="슬라이드쇼 일시정지")
        self._update_slide_button()

    def _interrupt_slideshow(self) -> None:
        if self._is_slideshow():
            self._stop_slideshow(quiet=True)
            self.status.configure(text="다른 작업을 시작해 슬라이드쇼를 중지했습니다")

    def toggle_slideshow(self) -> None:
        if self._is_slideshow():
            self._stop_slideshow()
            return
        if len(self.folder_files) < 2:
            self.status.configure(text="슬라이드쇼에는 이미지가 2개 이상 필요합니다")
            return
        self._slideshow_active = True
        self.status.configure(text="슬라이드쇼 재생 중")
        self._slideshow_tick()
        self._update_slide_button()

    def toggle_animation(self) -> None:
        if not self.is_animated:
            self.status.configure(text="현재 이미지는 애니메이션이 아닙니다")
            return
        self.anim_playing = not self.anim_playing
        self.settings["anim_playing"] = self.anim_playing
        if self.anim_playing:
            self._schedule_next_frame()
            self.status.configure(text=f"애니메이션 재생 · {self.anim_index + 1}/{len(self.anim_frames)} 프레임")
        else:
            self._stop_animation_timer()
            self.status.configure(text=f"애니메이션 일시정지 · {self.anim_index + 1}/{len(self.anim_frames)} 프레임")
        animation_style = "Accent.Icon.Tool.TButton" if self.anim_playing else "Icon.Tool.TButton"
        self._anim_btn._croweyes_style = animation_style  # type: ignore[attr-defined]
        self._anim_btn.configure(style=animation_style)

    def open_file_dialog(self) -> None:
        selected = filedialog.askopenfilename(
            title="이미지 열기",
            filetypes=[
                ("지원 이미지", "*.bmp *.dib *.jpg *.jpeg *.jpe *.jfif *.png *.gif *.webp *.tif *.tiff *.ico *.tga *.ppm *.pgm *.pbm *.psd *.svg *.eps"),
                ("확장 형식", "*.psd *.svg *.eps"),
                ("모든 파일", "*.*"),
            ],
        )
        if selected:
            self.open_path(Path(selected))

    def save_as(self) -> None:
        if self.display_image is None:
            self.status.configure(text="저장할 이미지가 없습니다")
            return
        destination = filedialog.asksaveasfilename(
            title="다른 이름으로 저장", defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WebP", "*.webp"),
                       ("BMP", "*.bmp"), ("TIFF", "*.tiff")],
        )
        if not destination:
            return
        self._save_display_image(Path(destination))

    def save_as_format(self, suffix: str) -> None:
        if self.display_image is None:
            return
        suffix = suffix.lower()
        source = self.folder_files[self.index] if 0 <= self.index < len(self.folder_files) else Path("image")
        destination = filedialog.asksaveasfilename(
            title=f"{suffix.lstrip('.').upper()} 형식으로 저장",
            initialfile=source.stem + suffix,
            defaultextension=suffix,
            filetypes=[(suffix.lstrip(".").upper(), f"*{suffix}")],
        )
        if destination:
            self._save_display_image(Path(destination))

    def _save_display_image(self, destination: Path) -> None:
        try:
            assert self.display_image is not None
            image = self.display_image.copy()
            suffix = destination.suffix.lower()
            if suffix in {".jpg", ".jpeg"} and image.mode in {"RGBA", "LA", "P"}:
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            elif suffix == ".bmp" and image.mode not in {"RGB", "L"}:
                image = image.convert("RGB")
            image.save(destination)
            self.status.configure(text=f"저장 완료: {destination}")
        except Exception as exc:
            messagebox.showerror("저장 실패", str(exc))

    def _image_for_print(self, printable_width: int, printable_height: int) -> Image.Image:
        """Build a print-resolution image with all visible transformations applied."""
        if self.display_image is None:
            raise ValueError("인쇄할 이미지가 없습니다.")
        if self.source_type not in {"svg", "eps"} or self.source_path is None:
            return self.display_image.copy()

        # A quarter-turn swaps source-space dimensions. Rendering the vector
        # before transforms preserves detail at the selected printer resolution.
        target_w, target_h = printable_width, printable_height
        if self.rotation % 180:
            target_w, target_h = target_h, target_w
        if self.source_type == "svg":
            rendered, _logical = render_svg(self.source_path, target_w, target_h)
        else:
            rendered, _logical = render_eps(self.source_path, target_w, target_h)
        return self._apply_current_transforms(rendered)

    def print_current_image(self) -> None:
        if self.display_image is None or not (0 <= self.index < len(self.folder_files)):
            self.status.configure(text="인쇄할 이미지가 없습니다")
            return
        PrintPreview(self)

    def _print_with_options(
        self, orientation: str, paper: str, scale_mode: str,
        printer_name: str = "", copies: int = 1, output_path: Optional[str] = None,
        parent: Optional[tk.Widget] = None,
    ) -> bool:
        path = self.folder_files[self.index]
        self.status.configure(text=f"{printer_name or '기본 프린터'}로 인쇄 작업을 보내는 중…")
        self.update_idletasks()
        try:
            owner_widget = parent or self
            owner_widget.update_idletasks()
            try:
                owner_widget.lift()
                owner_widget.focus_force()
            except tk.TclError:
                pass
            owner = owner_widget.winfo_id()
            if os.name == "nt":
                import ctypes

                owner = int(ctypes.windll.user32.GetParent(owner) or owner)
            printed = print_image_windows(
                self._image_for_print, owner, path.name,
                orientation=orientation, paper=paper, scale_mode=scale_mode,
                printer_name=printer_name, copies=copies, output_path=output_path,
            )
            self.status.configure(
                text="인쇄 작업을 프린터로 보냈습니다" if printed else "인쇄를 취소했습니다"
            )
            return printed
        except Exception as exc:
            detail = str(exc) or exc.__class__.__name__
            self.status.configure(text="인쇄하지 못했습니다")
            messagebox.showerror("인쇄 실패", detail, parent=parent or self)
            return False

    def show_about(self) -> None:
        messagebox.showinfo(
            APP_TITLE,
            f"{APP_TITLE}\n\n"
            "CrowEyes는 감상과 탐색에 집중한 데스크톱 이미지 뷰어입니다.\n"
            "Pillow · tkinter · ttkbootstrap · resvg 기반\n"
            "Windows 인쇄 · PSD · SVG · EPS(Ghostscript 선택 사항)\n\n"
            f"2026년 8월 · v{APP_VERSION}\n"
            "제작: Crow Science Lab\n\n"
            "무료 배포 · Authenticode 디지털 서명 없음\n"
            "Windows 실행 차단 안내는 더 보기 메뉴에서 확인할 수 있습니다.\n\n"
            "F11 이미지 전체화면 · F8 정보 패널 · F5 슬라이드쇼",
        )

    def show_windows_security_help(self) -> None:
        """Explain unsigned-build warnings without encouraging a security bypass."""
        win = tk.Toplevel(self)
        win.title("Windows 실행 차단 안내 · CrowEyes")
        win.transient(self)
        win.grab_set()
        win.resizable(False, False)
        frame = ttk.Frame(win, style="Panel.TFrame", padding=22)
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Smart App Control · SmartScreen", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            frame,
            text=(
                "CrowEyes는 무료로 배포되는 무서명 프로그램입니다. 일부 Windows 11 PC에서는\n"
                "Smart App Control 또는 Microsoft Defender SmartScreen이 실행을 막을 수 있습니다."
            ),
            style="Section.TLabel", justify=tk.LEFT,
        ).pack(anchor="w", pady=(10, 14))
        ttk.Label(
            frame,
            text=(
                "• SmartScreen: 공식 GitHub 릴리스와 SHA-256을 확인한 뒤, 경고 화면에\n"
                "  '추가 정보 → 실행' 선택이 제공되는 경우 사용자가 직접 판단할 수 있습니다.\n\n"
                "• Smart App Control: 특정 앱만 예외로 허용할 수 없습니다. CrowEyes를 삭제한 뒤\n"
                "  다시 설치해도 해결되지 않으며, PC 전체 보안 기능을 끄는 방법은 권장하지 않습니다.\n\n"
                "• 회사·학교 관리 PC에서는 보안 설정을 변경하지 말고 관리자에게 문의하십시오."
            ),
            style="Muted.TLabel", justify=tk.LEFT,
        ).pack(anchor="w")
        actions = ttk.Frame(frame, style="Panel.TFrame")
        actions.pack(fill=tk.X, pady=(18, 0))
        ttk.Button(
            actions, text="Microsoft 공식 안내 열기",
            command=lambda: webbrowser.open(SMART_APP_CONTROL_HELP_URL),
        ).pack(side=tk.LEFT)
        ttk.Button(
            actions, text="CrowEyes 공식 릴리스 열기",
            command=lambda: webbrowser.open(GITHUB_RELEASE_PAGE_URL),
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="닫기", command=win.destroy).pack(side=tk.RIGHT)
        self._apply_theme()
        win.update_idletasks()
        win.geometry(f"+{self.winfo_rootx() + 120}+{self.winfo_rooty() + 100}")

    def check_for_updates(self, manual: bool = False) -> None:
        """Fetch GitHub's latest release off the Tk event thread."""
        self._update_gen += 1
        generation = self._update_gen
        if manual:
            self.status.configure(text="CrowEyes 업데이트를 확인하는 중…")

        def worker() -> None:
            try:
                request = urllib.request.Request(
                    GITHUB_RELEASES_URL,
                    headers={"Accept": "application/vnd.github+json", "User-Agent": f"CrowEyes/{APP_VERSION}"},
                )
                with urllib.request.urlopen(request, timeout=12) as response:
                    release = json.loads(response.read().decode("utf-8"))
                self._update_results[generation] = (True, manual, release)
            except Exception as exc:
                self._update_results[generation] = (False, manual, str(exc))

        threading.Thread(target=worker, name="CrowEyesUpdateCheck", daemon=True).start()
        self.after(60, self._poll_update_check, generation)

    def _poll_update_check(self, generation: int) -> None:
        result = self._update_results.pop(generation, None)
        if result is None:
            if generation == self._update_gen:
                self.after(60, self._poll_update_check, generation)
            return
        ok, manual, payload = result
        if generation != self._update_gen:
            return
        self.settings["last_update_check"] = time.time()
        save_settings(self.settings)
        if not ok:
            self.status.configure(text="업데이트 확인에 실패했습니다")
            if manual:
                messagebox.showerror("업데이트 확인", str(payload), parent=self)
            return
        release = payload
        tag = str(release.get("tag_name", ""))
        if not is_newer_version(tag, APP_VERSION):
            self.status.configure(text=f"CrowEyes {APP_VERSION}이 최신 버전입니다")
            if manual:
                messagebox.showinfo("업데이트 확인", f"현재 버전 {APP_VERSION}이 최신입니다.", parent=self)
            return
        self.status.configure(text=f"새 버전 {tag}을 사용할 수 있습니다")
        if messagebox.askyesno(
            "CrowEyes 업데이트",
            f"새 버전 {tag}을 사용할 수 있습니다.\n\n다운로드하고 SHA-256을 확인할까요?",
            parent=self,
        ):
            self._show_update_download(release)

    def _installed_distribution(self) -> bool:
        if not getattr(sys, "frozen", False):
            return False
        if winreg is not None:
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\CrowScienceLab\CrowEyes") as key:
                    return bool(winreg.QueryValueEx(key, "InstallPath")[0])
            except OSError:
                pass
        return "portable" not in Path(sys.executable).name.casefold()

    def _show_update_download(self, release: dict) -> None:
        installed = self._installed_distribution()
        pattern = r"CrowEyes_Setup_.+_Windows_x64\.exe" if installed else r"CrowEyes_Portable_.+_Windows_x64\.zip"
        asset = release_asset(release, pattern)
        checksums = release_asset(release, r"SHA256SUMS\.txt")
        if asset is None or checksums is None:
            messagebox.showerror("업데이트", "릴리스 파일 또는 SHA256SUMS.txt를 찾지 못했습니다.", parent=self)
            return
        win = tk.Toplevel(self)
        win.title("CrowEyes 업데이트 다운로드")
        win.transient(self)
        win.resizable(False, False)
        frame = ttk.Frame(win, padding=22, style="Panel.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)
        label_var = tk.StringVar(value=f"{asset['name']} 다운로드 준비 중…")
        ttk.Label(frame, textvariable=label_var, style="Section.TLabel", width=56).pack(anchor="w")
        progress = ttk.Progressbar(frame, length=440, mode="determinate")
        progress.pack(fill=tk.X, pady=14)
        cancel = threading.Event()
        ttk.Button(frame, text="취소", command=cancel.set).pack(anchor="e")
        queue: Dict[str, object] = {}

        def fetch_bytes(url: str) -> bytes:
            request = urllib.request.Request(url, headers={"User-Agent": f"CrowEyes/{APP_VERSION}"})
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read()

        def worker() -> None:
            try:
                hashes = parse_sha256s(fetch_bytes(str(checksums["browser_download_url"])).decode("utf-8-sig"))
                expected = hashes.get(str(asset["name"]))
                if not expected:
                    raise ValueError("선택한 파일의 SHA-256 값이 없습니다.")
                target = Path(tempfile.gettempdir()) / str(asset["name"])
                request = urllib.request.Request(str(asset["browser_download_url"]), headers={"User-Agent": f"CrowEyes/{APP_VERSION}"})
                with urllib.request.urlopen(request, timeout=45) as response, target.open("wb") as stream:
                    total = int(response.headers.get("Content-Length", "0") or 0)
                    received = 0
                    while True:
                        if cancel.is_set():
                            raise InterruptedError("다운로드를 취소했습니다.")
                        block = response.read(1024 * 256)
                        if not block:
                            break
                        stream.write(block)
                        received += len(block)
                        queue["progress"] = (received, total)
                if sha256_file(target) != expected:
                    target.unlink(missing_ok=True)
                    raise ValueError("SHA-256 검증에 실패했습니다. 파일을 실행하지 않습니다.")
                queue["done"] = target
            except Exception as exc:
                queue["error"] = str(exc)

        def poll() -> None:
            if not win.winfo_exists():
                return
            received, total = queue.pop("progress", (0, 0))  # type: ignore[assignment]
            if total:
                progress.configure(maximum=total, value=received)
                label_var.set(f"{asset['name']} · {received / 1048576:.1f} / {total / 1048576:.1f} MB")
            if "error" in queue:
                error = str(queue.pop("error"))
                win.destroy()
                if not cancel.is_set():
                    messagebox.showerror("업데이트 다운로드", error, parent=self)
                return
            if "done" in queue:
                target = Path(queue.pop("done"))
                win.destroy()
                if installed:
                    if messagebox.askyesno("업데이트 준비 완료", "무결성 검증을 마쳤습니다. 설치 프로그램을 실행할까요?", parent=self):
                        subprocess.Popen([str(target)], shell=False)
                        self._on_close()
                else:
                    messagebox.showinfo(
                        "Portable 업데이트 준비 완료",
                        "검증된 ZIP을 다운로드했습니다. 실행 중인 Portable 파일은 자동 교체하지 않습니다.", parent=self,
                    )
                    subprocess.Popen(["explorer.exe", f"/select,{target}"], shell=False)
                return
            self.after(80, poll)

        threading.Thread(target=worker, name="CrowEyesUpdateDownload", daemon=True).start()
        self.after(80, poll)

    # Image decoding and folder scans run outside Tk's event thread. Only the
    # small result-application steps below touch widgets.
    def _safety_vector_loader(self, path: Path, size: int) -> Image.Image:
        if path.suffix.lower() == ".svg":
            return render_svg(path, size, size)[0]
        if path.suffix.lower() == ".eps":
            return render_eps(path, size, size)[0]
        raise OSError("지원하지 않는 벡터 형식입니다.")

    def _ensure_safety_worker(self) -> None:
        if self._safety_worker is not None:
            return
        cache_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CrowEyes"
        self._safety_manager = SafetyManager(
            resource_path("assets", "models", "nudenet-320n.onnx"),
            cache_root / "content_safety_cache.sqlite3",
        )
        self._safety_worker = SafetyWorker(self._safety_manager)
        self._safety_worker.preload()
        self._poll_safety_worker()

    def _update_safety_indicator(self) -> None:
        enabled = self._content_filter_mode == MODE_EXPLICIT
        self._content_filter_status_var.set("Safety ON" if enabled else "")
        indicator = getattr(self, "_safety_indicator", None)
        if indicator is not None:
            if enabled:
                indicator.pack(side=tk.LEFT, padx=(0, 10), before=indicator.master.winfo_children()[1])
            else:
                indicator.pack_forget()

    def _set_content_filter(self, mode: str) -> None:
        if mode not in {MODE_OFF, MODE_EXPLICIT}:
            return
        changed = mode != self._content_filter_mode
        self._content_filter_mode = mode
        self.settings["content_filter"] = mode
        save_settings(self.settings)
        self._update_safety_indicator()
        self._content_safety_status = UNKNOWN
        self._content_safety_detail = ""
        self._cancel_thumb_jobs()
        self._thumb_photos.clear()
        self._thumb_loaded.clear()
        self._safety_known.clear()
        if mode == MODE_EXPLICIT:
            self._ensure_safety_worker()
        elif self._safety_worker is not None:
            self._safety_worker.clear_pending()
        if changed:
            self._populate_list_names_only()
            if 0 <= self.index < len(self.folder_files):
                self._load_current()
            else:
                self.redraw()

    def _clear_safety_cache(self, parent: Optional[tk.Misc] = None) -> None:
        try:
            if self._safety_manager is None:
                cache_root = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CrowEyes"
                SafetyCache(cache_root / "content_safety_cache.sqlite3").clear()
            else:
                self._safety_manager.cache.clear()
            messagebox.showinfo("콘텐츠 안전", "로컬 판정 캐시를 비웠습니다.", parent=parent or self)
        except Exception as exc:
            messagebox.showerror("콘텐츠 안전", f"캐시를 비우지 못했습니다.\n\n{exc}", parent=parent or self)

    def _poll_safety_worker(self) -> None:
        self._safety_poll_job = None
        worker = self._safety_worker
        if worker is None:
            return
        for task in worker.poll():
            if task.path is not None and task.result.status in {SAFE, BLOCKED}:
                self._safety_known[str(task.path)] = task.result.status
            if task.kind == "preload":
                if task.result.status == ERROR:
                    self._content_safety_detail = task.result.detail
                    if self._content_filter_mode == MODE_EXPLICIT:
                        self.status.configure(text="콘텐츠 안전 모델을 준비하지 못했습니다")
                continue
            if task.kind == "current":
                if (
                    task.generation != self._image_load_gen
                    or task.path is None
                    or not (0 <= self.index < len(self.folder_files))
                    or task.path != self.folder_files[self.index]
                ):
                    continue
                self._content_safety_status = task.result.status
                self._content_safety_detail = task.result.detail
                if task.result.status == SAFE:
                    self._start_image_decode(task.path, task.generation)
                else:
                    self.pil_image = None
                    self.anim_frames = []
                    self.display_image = None
                    self.is_animated = False
                    self.source_path = task.path
                    self.source_type = "blocked" if task.result.status == BLOCKED else "safety_error"
                    self._show_blocked_state(error=task.result.status == ERROR)
                    self._update_header()
                    self._update_info()
                    self._start_pending_playlist()
                    self._queue_safety_neighbors()
                    if self._startup_activation_pending:
                        self._startup_activation_pending = False
                        self.after_idle(self._activate_viewer_window)
                continue
            if task.kind in {"thumbnail", "prefetch"} and task.generation == self._playlist_gen:
                if task.path is not None:
                    self._safety_thumb_pending.discard(str(task.path))
                if task.kind == "thumbnail":
                    self._cancel_thumb_jobs()
                    self._populate_list_names_only()
                    self._queue_thumbs_visible()
                elif task.result.status == SAFE:
                    self._queue_image_prefetch()
        if self._safety_worker is worker:
            self._safety_poll_job = self.after(40, self._poll_safety_worker)

    def _queue_safety_neighbors(self) -> None:
        if self._content_filter_mode != MODE_EXPLICIT or self._safety_worker is None:
            return
        for distance, priority in ((1, 1), (-1, 2), (2, 3), (-2, 4)):
            idx = self.index + distance
            if 0 <= idx < len(self.folder_files):
                path = self.folder_files[idx]
                if str(path) in self._safety_known:
                    continue
                self._safety_worker.submit(
                    path, priority, self._playlist_gen,
                    vector_loader=self._safety_vector_loader, kind="prefetch",
                )

    def _cache_decoded_image(self, path: Path, payload: tuple) -> None:
        frames = payload[0]
        if sum(frame.width * frame.height for frame in frames) > 24_000_000:
            return
        key = str(path)
        with self._decoded_cache_lock:
            self._decoded_cache[key] = payload
            if key in self._decoded_cache_order:
                self._decoded_cache_order.remove(key)
            self._decoded_cache_order.append(key)
            while len(self._decoded_cache_order) > 3:
                self._decoded_cache.pop(self._decoded_cache_order.pop(0), None)

    def _cached_decoded_image(self, path: Path) -> Optional[tuple]:
        key = str(path)
        with self._decoded_cache_lock:
            payload = self._decoded_cache.get(key)
            if payload is not None:
                if key in self._decoded_cache_order:
                    self._decoded_cache_order.remove(key)
                self._decoded_cache_order.append(key)
            return payload

    def _queue_image_prefetch(self) -> None:
        if not self.folder_files or self.index < 0:
            return
        for distance in (1, -1):
            idx = self.index + distance
            if not (0 <= idx < len(self.folder_files)):
                continue
            path = self.folder_files[idx]
            key = str(path)
            if self._content_filter_mode == MODE_EXPLICIT and self._safety_known.get(key) != SAFE:
                continue
            if self._cached_decoded_image(path) is None and key not in self._image_prefetch_pending:
                self._image_prefetch_pending.add(key)
                self._image_prefetch_queue.append(path)
        self._kick_image_prefetch()

    def _kick_image_prefetch(self) -> None:
        if self._image_prefetch_active or not self._image_prefetch_queue:
            return
        path = self._image_prefetch_queue.pop(0)
        key = str(path)
        self._image_prefetch_active = True
        target_width = max(256, self.canvas.winfo_width())
        target_height = max(256, self.canvas.winfo_height())

        def worker() -> None:
            try:
                payload = load_source_image(path, target_width, target_height)
                self._image_prefetch_results[key] = (True, path, payload)
            except Exception as exc:
                self._image_prefetch_results[key] = (False, path, str(exc))

        threading.Thread(target=worker, name="CrowEyesImagePrefetch", daemon=True).start()
        self.after(30, self._poll_image_prefetch, key)

    def _poll_image_prefetch(self, key: str) -> None:
        result = self._image_prefetch_results.pop(key, None)
        if result is None:
            self.after(30, self._poll_image_prefetch, key)
            return
        self._image_prefetch_pending.discard(key)
        self._image_prefetch_active = False
        ok, path, payload = result
        if ok:
            self._cache_decoded_image(path, payload)
        self._kick_image_prefetch()

    def _start_pending_playlist(self) -> None:
        pending = self._pending_playlist_build
        self._pending_playlist_build = None
        if pending is not None and pending[2] == self._playlist_gen:
            self._build_playlist_async(*pending)

    def _load_current(self) -> None:
        self._stop_animation_timer()
        if not (0 <= self.index < len(self.folder_files)):
            return
        path = self.folder_files[self.index]
        self.source_path = path
        self._current_path_var.set(str(path))
        self._image_load_gen += 1
        generation = self._image_load_gen
        self._vector_render_gen += 1
        self._vector_render_pending = False
        self.display_image = None
        self.pil_image = None
        self.anim_frames = []
        self._content_safety_status = UNKNOWN
        self._content_safety_detail = ""
        if self._content_filter_mode == MODE_EXPLICIT:
            self._show_loading_state(path.name, safety=True)
            self._ensure_safety_worker()
            assert self._safety_worker is not None
            self._safety_worker.submit(
                path, 0, generation,
                vector_loader=self._safety_vector_loader, kind="current",
            )
            return
        self._show_loading_state(path.name)
        self._start_image_decode(path, generation)

    def _start_image_decode(self, path: Path, generation: int) -> None:
        cached = self._cached_decoded_image(path)
        if cached is not None:
            self._image_load_results[generation] = (True, path, *cached)
            self.after(1, self._poll_image_load, generation)
            return
        target_width = max(256, self.canvas.winfo_width())
        target_height = max(256, self.canvas.winfo_height())

        def worker() -> None:
            try:
                frames, delays, animated, source_type, logical_size, render_scale = load_source_image(
                    path, target_width, target_height,
                )
                self._cache_decoded_image(
                    path, (frames, delays, animated, source_type, logical_size, render_scale),
                )
                if generation == self._image_load_gen:
                    self._image_load_results[generation] = (
                        True, path, frames, delays, animated,
                        source_type, logical_size, render_scale,
                    )
            except Exception as exc:
                if generation == self._image_load_gen:
                    self._image_load_results[generation] = (False, path, str(exc))

        threading.Thread(target=worker, name="CrowEyesImageLoader", daemon=True).start()
        self.after(25, self._poll_image_load, generation)

    def _poll_image_load(self, generation: int) -> None:
        result = self._image_load_results.pop(generation, None)
        if result is None:
            if generation == self._image_load_gen:
                self.after(25, self._poll_image_load, generation)
            return
        if generation != self._image_load_gen:
            return
        ok, path, *payload = result
        if not ok:
            self.pil_image = None
            self.anim_frames = []
            self.display_image = None
            self.is_animated = False
            self.source_type = "none"
            self.source_path = None
            detail = str(payload[0])
            self.status.configure(text="이미지를 열지 못했습니다")
            self._show_error_state(path.name, detail)
            self._start_pending_playlist()
            return
        frames, delays, animated, source_type, logical_size, render_scale = payload
        self.anim_frames = frames
        self.anim_delays = delays
        self.anim_index = 0
        self.is_animated = bool(animated)
        self.pil_image = frames[0]
        self.source_type = str(source_type)
        self.source_path = path
        self.source_logical_size = (float(logical_size[0]), float(logical_size[1]))
        self.source_render_scale = max(0.0001, float(render_scale))
        self.rotation = 0
        self.flip_h = self.flip_v = False
        self.bright_var.set(1.0)
        self.contrast_var.set(1.0)
        self.brightness = self.contrast = 1.0
        self.offset_x = self.offset_y = 0.0
        self.title(APP_TITLE)
        self._rebuild_display()
        if bool(self.settings.get("fit_on_open", True)):
            self.after_idle(self.fit_to_window)
        else:
            self.zoom = 1.0
            self._view_mode = "actual"
            self.redraw()
        self._update_header()
        self._update_info()
        self._rotation_text_var.set("0°")
        animation_note = f" · {len(frames)} 프레임" if animated else ""
        shown_w = int(round(self.source_logical_size[0]))
        shown_h = int(round(self.source_logical_size[1]))
        self.status.configure(text=f"{shown_w}×{shown_h}  ·  "
                                   f"{self.index + 1}/{len(self.folder_files)}{animation_note}")
        if self.is_animated and self.anim_playing:
            self._schedule_next_frame()
        self._start_pending_playlist()
        self._queue_safety_neighbors()
        self._queue_image_prefetch()
        if self._startup_activation_pending:
            self._startup_activation_pending = False
            self.after_idle(self._activate_viewer_window)

    def open_folders(self, folders: List[Path]) -> None:
        if not folders:
            return
        try:
            primary = folders[0].expanduser().resolve()
            if not self._history_navigation:
                self._record_folder_history(primary)
        except OSError:
            pass
        self._history_navigation = False
        self._playlist_gen += 1
        generation = self._playlist_gen
        self._cancel_thumb_jobs()
        self._image_prefetch_queue.clear()
        self._image_prefetch_pending.clear()
        self._thumb_photos.clear()
        self._thumb_loaded.clear()
        self._safety_known.clear()
        self._file_stat_cache.clear()
        self.current_folder = folders[0]
        self.status.configure(text="폴더의 이미지 목록을 불러오는 중…")

        def worker() -> None:
            resolved: List[Path] = []
            seen: Set[str] = set()
            clean_folders: List[Path] = []
            for folder in folders:
                try:
                    folder = Path(os.path.abspath(os.fspath(folder.expanduser())))
                except OSError:
                    continue
                if not folder.is_dir():
                    continue
                clean_folders.append(folder)
                for path in list_image_paths_fast(folder):
                    resolved_path = Path(os.path.abspath(os.fspath(path)))
                    key = str(resolved_path)
                    if key not in seen:
                        seen.add(key)
                        resolved.append(resolved_path)
            subdirs = list_subdirs(clean_folders[0]) if clean_folders else []
            if generation == self._playlist_gen:
                self._scan_results[generation] = (self._sorted(resolved), clean_folders, subdirs)

        threading.Thread(target=worker, name="CrowEyesFolderScanner", daemon=True).start()
        self.after(35, self._poll_folder_scan, generation)

    def _poll_folder_scan(self, generation: int) -> None:
        result = self._scan_results.pop(generation, None)
        if result is None:
            if generation == self._playlist_gen:
                self.after(35, self._poll_folder_scan, generation)
            return
        if generation != self._playlist_gen:
            return
        files, folders, subdirs = result
        self.folder_files = files
        self._folder_dirs = subdirs
        self.index = -1
        self.current_folder = folders[0] if folders else None
        self._populate_list_names_only()
        self._update_header()
        if not files:
            self.pil_image = self.display_image = None
            self.redraw()
            self.status.configure(text="선택한 폴더에 표시할 이미지가 없습니다")
            return
        self.goto_index(0)
        self._queue_thumbs_priority()
        self.status.configure(text=f"폴더 {len(folders)}개 · 이미지 {len(files)}개")

    def _build_playlist_async(self, folder: Path, prioritize: Path, generation: int) -> None:
        if generation != self._playlist_gen:
            return
        self.status.configure(text=f"플레이리스트 구성 중…  {folder}")

        def worker() -> None:
            files = self._sorted(list_image_paths_fast(folder))
            priority = Path(os.path.abspath(os.fspath(prioritize)))
            normalized = [Path(os.path.abspath(os.fspath(item))) for item in files]
            if priority not in normalized:
                normalized.append(priority)
                normalized = self._sorted(normalized)
            subdirs = list_subdirs(folder)
            if generation == self._playlist_gen:
                self._scan_results[generation] = (normalized, priority, subdirs)

        threading.Thread(target=worker, name="CrowEyesPlaylistScanner", daemon=True).start()
        self.after(35, self._poll_file_playlist, generation)

    def _poll_file_playlist(self, generation: int) -> None:
        result = self._scan_results.pop(generation, None)
        if result is None:
            if generation == self._playlist_gen:
                self.after(35, self._poll_file_playlist, generation)
            return
        if generation != self._playlist_gen:
            return
        files, priority, subdirs = result
        self.folder_files = files
        self._folder_dirs = subdirs
        try:
            self.index = files.index(priority)
        except ValueError:
            self.index = 0 if files else -1
        self._populate_list_names_only()
        self._select_list_index(self.index)
        self._update_header()
        self._queue_thumbs_priority()
        self.status.configure(text=f"플레이리스트 {len(files)}개")
        self.after(80, self._queue_thumbs_visible)
        self._queue_safety_neighbors()
        self._queue_image_prefetch()

    def _clear_canvas_overlay(self) -> None:
        overlay = getattr(self, "_canvas_overlay", None)
        if overlay is not None:
            try:
                overlay.destroy()
            except tk.TclError:
                pass
        self._canvas_overlay = None

    def _canvas_text_palette(self) -> Tuple[str, str, str]:
        """Return readable primary, secondary and hint colors for custom canvas backgrounds."""
        try:
            red, green, blue = self.winfo_rgb(self.canvas.cget("bg"))
            red, green, blue = red / 65535.0, green / 65535.0, blue / 65535.0
            luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
        except tk.TclError:
            luminance = 0.0
        if luminance < 0.42:
            return "#F1F3F5", "#B7C0CE", "#8994A5"
        theme = self._theme()
        return theme["fg"], theme["muted"], theme["placeholder"]

    def _draw_empty_state(self) -> None:
        self._clear_canvas_overlay()
        primary, secondary, hint = self._canvas_text_palette()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.canvas.create_image(cw / 2, ch / 2 - 70, image=self._icons["eye_large"], anchor=tk.CENTER)
        self.canvas.create_text(cw / 2, ch / 2 - 20, text="CrowEyes Image Viewer",
                                fill=primary, font=("Segoe UI Semibold", 17))
        self.canvas.create_text(cw / 2, ch / 2 + 14, text="이미지 또는 폴더를 열어 주세요",
                                fill=secondary, font=("Segoe UI", 10))
        actions = ttk.Frame(self.canvas, style="Viewer.TFrame")
        ttk.Button(actions, text="이미지 열기", image=self._icons["open_image"], compound=tk.LEFT,
                   command=self.open_file_dialog, style="Pastel.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="폴더 열기", image=self._icons["folder"], compound=tk.LEFT,
                   command=self.open_folder_dialog, style="Pastel.TButton").pack(side=tk.LEFT, padx=5)
        self._canvas_overlay = actions
        self.canvas.create_window(cw / 2, ch / 2 + 58, window=actions)
        self.canvas.create_text(cw / 2, ch / 2 + 105,
                                text="Ctrl+O  파일 열기    Ctrl+Shift+O  폴더 열기",
                                fill=hint, font=("Segoe UI", 9))

    def _show_loading_state(self, filename: str, safety: bool = False) -> None:
        self._clear_canvas_overlay()
        self.canvas.delete("all")
        t = self._theme()
        _primary, secondary, _hint = self._canvas_text_palette()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.canvas.create_text(cw / 2, ch / 2 - 12, text="◌", fill=t["accent"], font=("Segoe UI", 28))
        loading_text = "로컬에서 안전 여부 확인 중…" if safety else f"{filename} 불러오는 중…"
        self.canvas.create_text(cw / 2, ch / 2 + 24, text=loading_text,
                                fill=secondary, font=("Segoe UI", 10))
        self.status.configure(text="콘텐츠 안전 확인 중…" if safety else "이미지 불러오는 중…")

    def _load_blocked_crow(self) -> Optional[ImageTk.PhotoImage]:
        if self._blocked_crow_photo is not None:
            return self._blocked_crow_photo
        try:
            with Image.open(resource_path("assets", "safety", "content_blocked_crow.webp")) as opened:
                mascot = opened.convert("RGBA")
            mascot.thumbnail((250, 250), Image.Resampling.LANCZOS)
            self._blocked_crow_photo = ImageTk.PhotoImage(mascot, master=self)
        except (OSError, ValueError, tk.TclError):
            self._blocked_crow_photo = None
        return self._blocked_crow_photo

    def _show_blocked_state(self, error: bool = False) -> None:
        self._clear_canvas_overlay()
        self.canvas.delete("all")
        t = self._theme()
        primary, secondary, _hint = self._canvas_text_palette()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        mascot = self._load_blocked_crow()
        top = ch / 2 - 92
        if mascot is not None:
            self.canvas.create_image(cw / 2, top, image=mascot, anchor=tk.CENTER)
        else:
            self.canvas.create_image(cw / 2, top, image=self._icons["eye_large"], anchor=tk.CENTER)
        if error:
            title = "안전 여부를 확인하지 못했습니다"
            body = "보호를 위해 원본을 표시하지 않습니다. 다시 확인하거나 필터를 꺼 주세요."
            color = t["danger"]
        else:
            title = "보호된 이미지"
            body = "노골적인 노출 콘텐츠로 판단되어 화면 표시를 차단했습니다."
            color = t["accent_hi"]
        self.canvas.create_text(cw / 2, ch / 2 + 70, text=title, fill=color,
                                font=("Segoe UI Semibold", 16))
        self.canvas.create_text(cw / 2, ch / 2 + 102, text=body, fill=secondary,
                                width=max(280, cw - 140), font=("Segoe UI", 10))
        actions = ttk.Frame(self.canvas, style="Viewer.TFrame")
        ttk.Button(actions, text="다시 확인", command=self._load_current,
                   style="Pastel.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="콘텐츠 안전 설정", command=self.show_preferences,
                   style="Pastel.TButton").pack(side=tk.LEFT, padx=5)
        self._canvas_overlay = actions
        self.canvas.create_window(cw / 2, ch / 2 + 146, window=actions)
        self.status.configure(
            text="안전 판정 오류 · 원본 숨김" if error else "콘텐츠 안전 필터가 이미지를 차단했습니다"
        )
        self._update_canvas_navigation_buttons()

    def _show_error_state(self, filename: str, detail: str) -> None:
        self._clear_canvas_overlay()
        self.canvas.delete("all")
        t = self._theme()
        primary, secondary, _hint = self._canvas_text_palette()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.canvas.create_text(cw / 2, ch / 2 - 42, text="이미지를 열 수 없습니다",
                                fill=t["danger"], font=("Segoe UI Semibold", 15))
        self.canvas.create_text(cw / 2, ch / 2 - 8, text=filename, fill=primary, font=("Segoe UI", 10))
        self.canvas.create_text(cw / 2, ch / 2 + 18, text=detail[:180], width=max(240, cw - 160),
                                fill=secondary, font=("Segoe UI", 9))
        actions = ttk.Frame(self.canvas, style="Viewer.TFrame")
        ttk.Button(actions, text="다시 열기", command=self._load_current, style="Pastel.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(actions, text="다른 이미지 열기", command=self.open_file_dialog, style="Pastel.TButton").pack(side=tk.LEFT, padx=5)
        self._canvas_overlay = actions
        self.canvas.create_window(cw / 2, ch / 2 + 64, window=actions)

    def redraw(self) -> None:
        self._clear_canvas_overlay()
        self.canvas.delete("all")
        self._zoom_text_var.set(f"크기 {int(round(self.zoom * 100))}%")
        if self.display_image is None:
            self._update_canvas_navigation_buttons()
            if self._content_safety_status == BLOCKED:
                self._show_blocked_state(error=False)
            elif self._content_safety_status == ERROR:
                self._show_blocked_state(error=True)
            elif 0 <= self.index < len(self.folder_files):
                self._show_loading_state(
                    self.folder_files[self.index].name,
                    safety=self._content_filter_mode == MODE_EXPLICIT,
                )
            elif self.source_path is None:
                self._draw_empty_state()
            return
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        effective_zoom = self._effective_bitmap_zoom()
        w = max(1, int(self.display_image.width * effective_zoom))
        h = max(1, int(self.display_image.height * effective_zoom))
        if w * h > MAX_RENDER_PIXELS:
            limit_scale = (MAX_RENDER_PIXELS / (w * h)) ** 0.5
            w, h = max(1, int(w * limit_scale)), max(1, int(h * limit_scale))
        if self.is_animated and abs(self.zoom - 1.0) < 0.01:
            resample = Image.Resampling.NEAREST
        elif effective_zoom < 1.0:
            resample = Image.Resampling.BILINEAR
        else:
            resample = Image.Resampling.BICUBIC
        try:
            scaled = self.display_image.resize((w, h), resample)
        except Exception:
            scaled = self.display_image
        self.tk_image = ImageTk.PhotoImage(scaled)
        self.canvas.create_image(cw / 2 + self.offset_x, ch / 2 + self.offset_y,
                                 image=self.tk_image, anchor=tk.CENTER, tags=("display_image",))
        self._update_canvas_navigation_buttons()

    def _update_info(self) -> None:
        self.info_text.configure(state=tk.NORMAL)
        self.info_text.delete("1.0", tk.END)
        if self.pil_image is None or not (0 <= self.index < len(self.folder_files)):
            self.info_text.insert(tk.END, "이미지 정보가 없습니다", "value")
            self.info_text.configure(state=tk.DISABLED)
            return
        path = self.folder_files[self.index]
        try:
            size = path.stat().st_size
            size_text = f"{size / 1024:.1f} KB" if size < 1024 ** 2 else f"{size / 1024 ** 2:.2f} MB"
        except OSError:
            size_text = "확인할 수 없음"
        logical_w, logical_h = self.source_logical_size
        if self.source_type == "svg":
            format_text = "SVG · 벡터"
        elif self.source_type == "eps":
            format_text = "EPS · 벡터 (Ghostscript)"
        elif self.source_type == "psd":
            format_text = "PSD · 합성 미리보기"
        else:
            format_text = path.suffix.upper().lstrip(".") or "알 수 없음"
        resolution_text = f"{int(round(logical_w))} × {int(round(logical_h))}"
        if self.source_type in {"svg", "eps"}:
            resolution_text += f" · 렌더 {self.pil_image.width} × {self.pil_image.height}"
        data = [
            ("파일명", path.name), ("전체 경로", str(path)),
            ("파일 형식", format_text),
            ("파일 크기", size_text),
            ("해상도", resolution_text),
            ("현재 순서", f"{self.index + 1} / {len(self.folder_files)}"),
            ("확대율", f"{int(self.zoom * 100)}%"),
            ("밝기 · 대비", f"{self.brightness:.2f} · {self.contrast:.2f}"),
            ("애니메이션", "예" if self.is_animated else "아니요"),
            ("프레임 수", str(len(self.anim_frames)) if self.is_animated else "—"),
            ("정렬 방식", f"{SORT_LABELS.get(self.sort_by, self.sort_by)} / {'내림차순' if self.sort_desc else '오름차순'}"),
        ]
        for label, value in data:
            self.info_text.insert(tk.END, label.upper() + "\n", "label")
            self.info_text.insert(tk.END, value + "\n", "value")
        self.info_text.configure(state=tk.DISABLED)
        self._anim_btn.configure(state=tk.NORMAL if self.is_animated else tk.DISABLED)

    def _update_slide_button(self) -> None:
        if self._slide_btn is None:
            return
        playing = self._is_slideshow()
        slide_style = "Accent.Icon.Tool.TButton" if playing else "Icon.Tool.TButton"
        self._slide_btn._croweyes_style = slide_style  # type: ignore[attr-defined]
        self._slide_btn.configure(
            text="", image=self._icons["pause" if playing else "play"],
            style=slide_style,
        )

    def _on_close(self) -> None:
        self._playlist_gen += 1
        self._image_load_gen += 1
        self._vector_render_gen += 1
        self._stop_slideshow(quiet=True)
        self._stop_animation_timer()
        self._cancel_thumb_jobs()
        if self._safety_poll_job is not None:
            try:
                self.after_cancel(self._safety_poll_job)
            except tk.TclError:
                pass
            self._safety_poll_job = None
        if self._safety_worker is not None:
            self._safety_worker.stop()
        if self._image_fullscreen:
            self.exit_image_fullscreen()
        self.settings["window_geometry"] = self.geometry()
        self.settings["list_mode"] = self.list_mode
        self.settings["sort_by"] = self.sort_by
        self.settings["sort_desc"] = self.sort_desc
        self.settings["anim_playing"] = self.anim_playing
        self.settings["show_info_panel"] = self._info_visible
        self.settings["show_playlist_panel"] = self._playlist_visible
        self.settings["show_context_bar"] = self._context_visible
        if self._playlist_visible and self._info_visible:
            try:
                pane_width = max(1, self.paned.winfo_width())
                first = self.paned.sashpos(0) / pane_width
                second = self.paned.sashpos(1) / pane_width
                self.settings["pane_ratio_playlist"] = max(0.16, min(0.40, first))
                self.settings["pane_ratio_image"] = max(0.35, min(0.80, second - first))
                self.settings["pane_ratio_info"] = max(0.13, min(0.35, 1.0 - second))
            except (tk.TclError, IndexError):
                pass
        save_settings(self.settings)
        self.destroy()


def main() -> int:
    start = sys.argv[1] if len(sys.argv) > 1 else None
    app = CrowEyesImageViewer(start)
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
