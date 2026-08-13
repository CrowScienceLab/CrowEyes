#!/usr/bin/env python3
"""CrowEyes Image Viewer 1.0.

A modern Windows image viewer built with Pillow, tkinter, and ttkbootstrap.
Copyright 2026 Crow Science Lab.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Dict, List, Optional, Set, Tuple

try:
    import winreg
except ImportError:  # pragma: no cover - Windows publishing target
    winreg = None  # type: ignore[assignment]

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


_ORIGINAL_TK_INIT = tk.Tk.__init__


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
APP_VERSION = "1.0"
APP_TITLE = f"{APP_NAME} {APP_VERSION}"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SUPPORTED_EXT = {
    ".bmp", ".dib", ".jpg", ".jpeg", ".jpe", ".jfif", ".png", ".gif",
    ".webp", ".tif", ".tiff", ".ico", ".tga", ".ppm", ".pgm", ".pbm",
}

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
)
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
    "design_generation": 3,
    # Initial pane ratios: playlist / image / info
    "pane_ratio_playlist": 0.20,
    "pane_ratio_image": 0.65,
    "pane_ratio_info": 0.15,
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

    legacy_theme_map = {
        "pastel": "bright_sky_blue", "pastel_peach": "bright_sky_blue",
        "light": "bright_sky_blue", "dark": "croweyes_dark",
    }
    if not loaded_keys or "ui_theme" in loaded_keys or data.get("design_generation") == 3:
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


def special_folders() -> List[Tuple[str, Path]]:
    """Common Windows user folders for quick access."""
    home = Path.home()
    candidates = [
        ("홈", home),
        ("바탕 화면", home / "Desktop"),
        ("문서", home / "Documents"),
        ("사진", home / "Pictures"),
        ("다운로드", home / "Downloads"),
        ("음악", home / "Music"),
        ("비디오", home / "Videos"),
    ]
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
    """Tiny antialiased line icons rendered in memory; no asset files required."""

    def __init__(self, root: tk.Misc, colors: dict) -> None:
        self.root = root
        self.colors = colors
        self.images: Dict[str, ImageTk.PhotoImage] = {}
        toolbar_icons = (
            "previous", "next", "fit", "zoom_in", "zoom_out", "rotate_right",
            "rotate_left", "fullscreen", "play", "pause", "info", "settings",
            "more", "actual", "gif", "folder", "open_image", "save", "flip_h",
            "flip_v", "brightness", "contrast", "theme", "panel", "shortcuts",
            "slideshow", "close",
        )
        for name in toolbar_icons:
            self.images[name] = self._render(name, 18)
        self.images["eye"] = self._render("eye", 28)
        self.images["eye_large"] = self._render("eye", 64)
        self.images["app"] = self._render("eye", 32, app_badge=True)

    def __getitem__(self, name: str) -> ImageTk.PhotoImage:
        return self.images[name]

    @staticmethod
    def _rgb(value: str) -> Tuple[int, int, int, int]:
        value = value.lstrip("#")
        return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), 255)

    def _render(self, name: str, size: int, app_badge: bool = False) -> ImageTk.PhotoImage:
        scale = 4
        side = size * scale
        image = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        fg = self._rgb(self.colors["fg"])
        muted = self._rgb(self.colors["muted"])
        accent = self._rgb(self.colors["accent"])
        panel = self._rgb(self.colors["panel_alt"])
        line = max(5, int(size * 0.085 * scale))
        s = scale

        def poly(points, fill=fg, width=line) -> None:
            draw.line([(int(x * s), int(y * s)) for x, y in points], fill=fill, width=width, joint="curve")

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
                poly([(size * .62, size * .22), (size * .34, size * .50), (size * .62, size * .78)])
            else:
                poly([(size * .38, size * .22), (size * .66, size * .50), (size * .38, size * .78)])
        elif name in {"zoom_in", "zoom_out"}:
            ellipse((size * .16, size * .13, size * .65, size * .62))
            poly([(size * .60, size * .58), (size * .84, size * .82)])
            poly([(size * .28, size * .38), (size * .53, size * .38)])
            if name == "zoom_in":
                poly([(size * .405, size * .25), (size * .405, size * .51)])
        elif name in {"fit", "fullscreen"}:
            inset = size * (.15 if name == "fullscreen" else .22)
            reach = size * (.38 if name == "fullscreen" else .40)
            for sx, sy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                x = inset if sx == 1 else size - inset
                y = inset if sy == 1 else size - inset
                poly([(x + sx * reach, y), (x, y), (x, y + sy * reach)])
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
            rectangle((size * .16, size * .16, size * .84, size * .84), radius=size * .08)
            poly([(size * .42, size * .37), (size * .52, size * .29), (size * .52, size * .70)], accent)
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
        elif name == "save":
            rectangle((size * .15, size * .13, size * .85, size * .87), radius=size * .05)
            rectangle((size * .29, size * .13, size * .69, size * .38), outline=accent)
            rectangle((size * .28, size * .58, size * .72, size * .87), outline=fg)
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

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip: Optional[tk.Toplevel] = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self.tip or not self.text:
            return
        x = self.widget.winfo_rootx() + 8
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 7
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        ttk.Label(self.tip, text=self.text, style="Tooltip.TLabel", padding=(9, 5)).pack()

    def _hide(self, _event=None) -> None:
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None


def _tool_button(
    parent: tk.Widget,
    text: str,
    tooltip: str,
    command,
    width: int = 3,
    image: Optional[ImageTk.PhotoImage] = None,
) -> ttk.Button:
    button = ttk.Button(
        parent, text=text, image=image, compound=tk.LEFT,
        command=command, width=width, style="Tool.TButton",
    )
    button._croweyes_image = image  # type: ignore[attr-defined]
    # ttkbootstrap may normalize an as-yet undefined custom style to TButton.
    # _apply_theme restores this marker after all product styles are defined.
    button._croweyes_style = "Tool.TButton"  # type: ignore[attr-defined]
    ToolTip(button, tooltip)
    return button


class CrowEyesToolbar(ttk.Frame):
    """Brand/header area and the viewer's primary commands."""

    def __init__(self, master: tk.Widget, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(master, style="Toolbar.TFrame", padding=(14, 9))
        self.viewer = viewer
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0)
        self.columnconfigure(2, weight=1)

        brand = ttk.Frame(self, style="Toolbar.TFrame")
        brand.grid(row=0, column=0, sticky="w")
        ttk.Label(brand, image=viewer._icons["eye"], style="Logo.TLabel").pack(side=tk.LEFT, padx=(0, 9))
        brand_text = ttk.Frame(brand, style="Toolbar.TFrame")
        brand_text.pack(side=tk.LEFT)
        ttk.Label(brand_text, text="CrowEyes", style="Brand.TLabel").pack(anchor="w")
        ttk.Label(brand_text, text="IMAGE VIEWER  ·  1.0", style="Product.TLabel").pack(anchor="w")
        if not bool(viewer.settings.get("compact_toolbar", False)):
            crumbs = ttk.Frame(brand, style="Toolbar.TFrame")
            crumbs.pack(side=tk.LEFT, padx=(18, 0))
            ttk.Label(crumbs, textvariable=viewer._folder_title_var, style="Crumb.TLabel").pack(anchor="w")
            ttk.Label(crumbs, textvariable=viewer._file_title_var, style="FileTitle.TLabel").pack(anchor="w")

        primary = ttk.Frame(self, style="Toolbar.TFrame")
        primary.grid(row=0, column=1)
        specs = [
            ("previous", "이전 이미지 (←)", viewer._action(viewer.prev_image)),
            ("next", "다음 이미지 (→)", viewer._action(viewer.next_image)),
            ("fit", "화면 맞춤 (Ctrl+1)", viewer._action(viewer.fit_to_window)),
            ("actual", "원본 크기 (Ctrl+0)", viewer._action(viewer.actual_size)),
            ("zoom_in", "확대", viewer._action(lambda: viewer.zoom_by(1.15))),
            ("zoom_out", "축소", viewer._action(lambda: viewer.zoom_by(1 / 1.15))),
            ("rotate_right", "오른쪽으로 회전 (Ctrl+R)", viewer._action(lambda: viewer.rotate(90))),
            ("fullscreen", "이미지 전체화면 (F11)", viewer.toggle_image_fullscreen),
        ]
        for icon_name, tip, command in specs:
            _tool_button(primary, "", tip, command, image=viewer._icons[icon_name]).pack(side=tk.LEFT, padx=2)

        actions = ttk.Frame(self, style="Toolbar.TFrame")
        actions.grid(row=0, column=2, sticky="e")
        viewer._slide_btn = _tool_button(
            actions, "", "슬라이드쇼 재생/일시정지 (F5)", viewer.toggle_slideshow,
            image=viewer._icons["play"],
        )
        viewer._slide_btn.pack(side=tk.LEFT, padx=2)
        _tool_button(actions, "", "정보 패널 표시/숨기기 (F8)", viewer.toggle_info_panel,
                     image=viewer._icons["info"]).pack(side=tk.LEFT, padx=2)
        _tool_button(actions, "", "환경설정 (Ctrl+,)", viewer._action(viewer.show_preferences),
                     image=viewer._icons["settings"]).pack(side=tk.LEFT, padx=2)
        more = ttk.Menubutton(actions, image=viewer._icons["more"], width=3, style="Tool.TButton")
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
        more["menu"] = menu
        more.pack(side=tk.LEFT, padx=(2, 0))
        ToolTip(more, "더 보기")


class PlaylistPanel(ttk.Frame):
    """Playlist controls and the lazily populated list container."""

    def __init__(self, master: tk.Widget, viewer: "CrowEyesImageViewer") -> None:
        super().__init__(master, style="Card.TFrame", padding=12)
        self.viewer = viewer
        header = ttk.Frame(self, style="Panel.TFrame")
        header.pack(fill=tk.X)
        ttk.Label(header, text="PLAYLIST", style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Label(header, textvariable=viewer._playlist_count_var, style="Badge.TLabel").pack(side=tk.RIGHT)

        selectors = ttk.Frame(self, style="Panel.TFrame")
        selectors.pack(fill=tk.X, pady=(10, 8))
        viewer._list_mode_display_var = tk.StringVar(value=LIST_MODE_LABELS.get(viewer.list_mode, viewer.list_mode))
        viewer._sort_display_var = tk.StringVar(value=SORT_LABELS.get(viewer.sort_by, viewer.sort_by))
        mode = ttk.Combobox(
            selectors, textvariable=viewer._list_mode_display_var,
            values=[LIST_MODE_LABELS[key] for key in LIST_MODES], state="readonly", width=13,
        )
        mode.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        mode.bind("<<ComboboxSelected>>", lambda _e: viewer.set_list_mode(
            next((key for key, label in LIST_MODE_LABELS.items() if label == viewer._list_mode_display_var.get()), "small")
        ))
        sorting = ttk.Combobox(
            selectors, textvariable=viewer._sort_display_var,
            values=[SORT_LABELS[key] for key in SORT_KEYS], state="readonly", width=10,
        )
        sorting.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        sorting.bind("<<ComboboxSelected>>", lambda _e: viewer.set_sort(
            next((key for key, label in SORT_LABELS.items() if label == viewer._sort_display_var.get()), "name")
        ))

        search = ttk.Entry(self, textvariable=viewer._search_var, style="Search.TEntry")
        search.pack(fill=tk.X, pady=(0, 10), ipady=4)
        search.bind("<KeyRelease>", viewer._apply_playlist_filter)
        ToolTip(search, "파일명 검색 — 원본 목록은 변경하지 않습니다")

        viewer.list_container = ttk.Frame(self, style="Panel.TFrame")
        viewer.list_container.pack(fill=tk.BOTH, expand=True)


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
        viewer.status = ttk.Label(self, text="이미지 또는 폴더를 열어 주세요", style="Status.TLabel", anchor="w")
        viewer.status.pack(side=tk.LEFT, fill=tk.X, expand=True)

        controls = ttk.Frame(self, style="BottomBar.TFrame")
        controls.pack(side=tk.RIGHT)
        ttk.Label(controls, textvariable=viewer._zoom_text_var, style="BottomBar.TLabel", width=7).pack(side=tk.LEFT, padx=(4, 8))
        _tool_button(controls, "", "화면 맞춤", viewer._action(viewer.fit_to_window),
                     image=viewer._icons["fit"]).pack(side=tk.LEFT, padx=2)
        _tool_button(controls, "", "원본 크기", viewer._action(viewer.actual_size),
                     image=viewer._icons["actual"]).pack(side=tk.LEFT, padx=2)
        ttk.Label(controls, text="밝기", style="BottomBar.TLabel").pack(side=tk.LEFT, padx=(10, 4))
        viewer.bright_var = tk.DoubleVar(value=1.0)
        ttk.Scale(controls, from_=0.2, to=2.0, variable=viewer.bright_var, length=90,
                  command=viewer._on_adjust, style="CrowEyes.Horizontal.TScale").pack(side=tk.LEFT)
        ttk.Label(controls, text="대비", style="BottomBar.TLabel").pack(side=tk.LEFT, padx=(10, 4))
        viewer.contrast_var = tk.DoubleVar(value=1.0)
        ttk.Scale(controls, from_=0.2, to=2.0, variable=viewer.contrast_var, length=90,
                  command=viewer._on_adjust, style="CrowEyes.Horizontal.TScale").pack(side=tk.LEFT)
        ttk.Label(controls, textvariable=viewer._rotation_text_var, style="BottomBar.TLabel", width=6).pack(side=tk.LEFT, padx=(10, 2))
        viewer._anim_btn = _tool_button(
            controls, "", "GIF/WebP 재생/일시정지 (Space)", viewer.toggle_animation,
            image=viewer._icons["gif"],
        )
        viewer._anim_btn.pack(side=tk.LEFT, padx=2)


class CrowEyesImageViewer(tb.Window):
    def __init__(self, start_path: Optional[str] = None) -> None:
        # ttkbootstrap initializes localization immediately after Tk. Some
        # Anaconda builds ship msgcat but omit its Tcl module search path.
        tk.Tk.__init__ = _tk_init_with_anaconda_msgcat
        try:
            super().__init__(themename="darkly")
        finally:
            tk.Tk.__init__ = _ORIGINAL_TK_INIT
        self.settings = load_settings()
        self._icons = CrowEyesIconSet(self, self._theme())
        self.iconphoto(True, self._icons["app"])
        self.title(APP_TITLE)
        self.geometry(self.settings.get("window_geometry", "1120x760"))
        self.minsize(860, 520)
        self._image_fullscreen = False
        self._chrome_visible = True
        self._info_visible = bool(self.settings.get("show_info_panel", True))
        self._playlist_visible = bool(self.settings.get("show_playlist_panel", True))
        self._context_visible = bool(self.settings.get("show_context_bar", True))
        self._icon_cells: Dict[int, tk.Label] = {}
        self._grid_canvas: Optional[tk.Canvas] = None
        self._grid_inner: Optional[ttk.Frame] = None
        self._right_panel: Optional[ttk.Frame] = None
        self._center_panel: Optional[ttk.Frame] = None
        self._sashes_applied = False
        self._canvas_resize_job: Optional[str] = None
        self._file_stat_cache: Dict[str, Tuple[float, int]] = {}
        self._filtered_indices: List[int] = []
        self._image_load_gen = 0
        self._image_load_results: Dict[int, tuple] = {}
        self._scan_results: Dict[int, tuple] = {}

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
        self.zoom: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.pan_start: Optional[Tuple[int, int]] = None
        self.brightness: float = 1.0
        self.contrast: float = 1.0
        self.rotation: int = 0
        self.flip_h: bool = False
        self.flip_v: bool = False
        self.slideshow_job: Optional[str] = None
        self._fit_next: bool = bool(self.settings.get("fit_on_open", True))
        self._startup_activation_pending = bool(start_path)

        self.list_mode = self.settings.get("list_mode", "small")
        self.sort_by = self.settings.get("sort_by", "name")
        self.sort_desc = bool(self.settings.get("sort_desc", False))
        self._list_mode_var = tk.StringVar(value=self.list_mode)
        self._sort_var = tk.StringVar(value=self.sort_by)
        self._search_var = tk.StringVar(value="")
        self._folder_title_var = tk.StringVar(value="폴더를 선택하지 않음")
        self._file_title_var = tk.StringVar(value="이미지를 열어 주세요")
        self._playlist_count_var = tk.StringVar(value="0")
        self._zoom_text_var = tk.StringVar(value="100%")
        self._rotation_text_var = tk.StringVar(value="0°")

        # Lazy thumbs
        self._thumb_photos: Dict[str, ImageTk.PhotoImage] = {}  # path -> photo
        self._thumb_loaded: Set[str] = set()
        self._thumb_queue: List[int] = []
        self._thumb_job: Optional[str] = None
        self._placeholder_photo: Optional[ImageTk.PhotoImage] = None

        self._list_widget: Optional[tk.Widget] = None
        self.left_panel: Optional[ttk.Frame] = None
        self.list_container: Optional[ttk.Frame] = None
        self._slide_btn: Optional[ttk.Button] = None
        self._list_scroll: Optional[ttk.Scrollbar] = None

        self._build_ui()
        self._apply_theme()
        self._bind_keys()
        self._rebuild_file_list_widget()
        # Native Tk list/canvas widgets are created after the first theme pass.
        self._apply_theme()
        self._update_slide_button()

        if start_path:
            self.open_path(Path(start_path))
            # File-association launches should accept arrow keys immediately,
            # even before the asynchronous image decoder has finished.
            self.after(80, self._activate_viewer_window)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ----- helpers: slideshow interrupt ------------------------------------

    def _is_slideshow(self) -> bool:
        return self.slideshow_job is not None



    def _action(self, fn):
        """Wrap UI actions so slideshow stops first."""
        def wrapped(*args, **kwargs):
            self._interrupt_slideshow()
            return fn(*args, **kwargs)
        return wrapped

    # ----- theme / UI ------------------------------------------------------



    def _on_root_configure(self, event) -> None:
        if event.widget is not self:
            return
        if not self._sashes_applied and self.winfo_width() > 200:
            self._init_sashes()






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

    def _bind_keys(self) -> None:
        self.bind("<Control-o>", lambda e: self._action(self.open_file_dialog)())
        self.bind("<Control-O>", lambda e: self._action(self.open_file_dialog)())
        self.bind("<Control-Shift-O>", lambda e: self._action(self.open_folder_dialog)())
        self.bind("<Control-s>", lambda e: self._action(self.save_as)())
        self.bind("<Left>", lambda e: self._action(self.prev_image)())
        self.bind("<Right>", lambda e: self._action(self.next_image)())
        self.bind("<Home>", lambda e: self._action(lambda: self.goto_index(0))())
        self.bind("<End>", lambda e: self._action(lambda: self.goto_index(len(self.folder_files) - 1))())
        self.bind("<Control-0>", lambda e: self._action(self.actual_size)())
        self.bind("<Control-1>", lambda e: self._action(self.fit_to_window)())
        self.bind("<Control-plus>", lambda e: self._action(lambda: self.zoom_by(1.15))())
        self.bind("<Control-equal>", lambda e: self._action(lambda: self.zoom_by(1.15))())
        self.bind("<Control-minus>", lambda e: self._action(lambda: self.zoom_by(1 / 1.15))())
        self.bind("<Control-r>", lambda e: self._action(lambda: self.rotate(90))())
        self.bind("<Control-l>", lambda e: self._action(lambda: self.rotate(-90))())
        self.bind("<F5>", lambda e: self.toggle_slideshow())
        self.bind("<F11>", lambda e: self.toggle_image_fullscreen())
        self.bind("<F8>", lambda e: self.toggle_info_panel())
        self.bind("<Escape>", lambda e: self._escape())
        self.bind("<Control-comma>", lambda e: self._action(self.show_preferences)())
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
        self.sort_desc = not self.sort_desc
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

    def _rebuild_file_list_widget(self) -> None:
        assert self.list_container is not None
        for child in self.list_container.winfo_children():
            child.destroy()
        self._list_widget = None
        self._list_scroll = None
        self._grid_canvas = None
        self._grid_inner = None
        self._icon_cells.clear()
        self._make_placeholder()

        wrap = ttk.Frame(self.list_container, style="Panel.TFrame")
        wrap.pack(fill=tk.BOTH, expand=True)
        scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self._list_scroll = scroll

        if self.list_mode == "names":
            lb = tk.Listbox(wrap, width=26, exportselection=False, yscrollcommand=self._on_list_yview)
            scroll.config(command=lb.yview)
            lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            lb.bind("<<ListboxSelect>>", self._on_list_select)
            lb.bind("<MouseWheel>", self._on_list_wheel, add="+")
            self._list_widget = lb
            self._style_list_widget()
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
            gc.bind("<MouseWheel>", self._on_grid_wheel, add="+")
            self._grid_canvas = gc
            self._grid_inner = inner
            self._list_widget = gc
            return

        tv = ttk.Treeview(
            wrap, show="tree", selectmode="browse",
            yscrollcommand=self._on_list_yview, style="Treeview",
        )
        scroll.config(command=tv.yview)
        tv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tv.bind("<<TreeviewSelect>>", self._on_list_select)
        tv.bind("<MouseWheel>", self._on_list_wheel, add="+")
        self._list_widget = tv

    def _on_icon_grid_resize(self, event, win_id) -> None:
        if self._grid_canvas is None:
            return
        self._grid_canvas.itemconfigure(win_id, width=event.width)
        self.after_idle(self._layout_icon_grid)

    def _on_grid_wheel(self, event) -> None:
        if self._grid_canvas is not None:
            self._grid_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            self.after(50, self._queue_thumbs_visible)

    def _icon_cell_size(self) -> int:
        return 72

    def _layout_icon_grid(self) -> None:
        if self.list_mode != "icons" or self._grid_inner is None or self._grid_canvas is None:
            return
        cell = self._icon_cell_size()
        pad = 4
        cw = max(self._grid_canvas.winfo_width(), cell + pad * 2)
        cols = max(1, cw // (cell + pad * 2))
        for position, (_idx, lbl) in enumerate(self._icon_cells.items()):
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
        indices = self._visible_playlist_indices()
        shown, total = len(indices), len(self.folder_files)
        self._playlist_count_var.set(str(total) if shown == total else f"{shown}/{total}")

        if isinstance(w, tk.Listbox):
            w.delete(0, tk.END)
            for idx in indices:
                p = self.folder_files[idx]
                w.insert(tk.END, p.name)
            return

        if self.list_mode == "icons" and self._grid_inner is not None:
            for child in self._grid_inner.winfo_children():
                child.destroy()
            self._icon_cells.clear()
            cell = self._icon_cell_size()
            for i in indices:
                p = self.folder_files[i]
                lbl = tk.Label(
                    self._grid_inner,
                    image=ph,
                    bg=t["panel"],
                    bd=1,
                    relief=tk.FLAT,
                    cursor="hand2",
                    width=cell,
                    height=cell,
                )
                lbl.image = ph  # type: ignore[attr-defined]
                lbl.bind("<Button-1>", lambda e, idx=i: self._on_icon_click(idx))
                lbl.bind("<Double-Button-1>", lambda e, idx=i: self._on_icon_click(idx))
                self._icon_cells[i] = lbl
            self._layout_icon_grid()
            self._highlight_icon_selection()
            return

        assert isinstance(w, ttk.Treeview)
        for item in w.get_children():
            w.delete(item)
        for i in indices:
            p = self.folder_files[i]
            iid = str(i)
            img = ph if self.list_mode == "small" else None
            if img is not None:
                w.insert("", tk.END, iid=iid, text=p.name, image=img)
            else:
                w.insert("", tk.END, iid=iid, text=p.name)

    def _on_icon_click(self, idx: int) -> None:
        self._interrupt_slideshow()
        self.goto_index(idx, from_list=True)
        self._queue_thumbs_priority()

    def _highlight_icon_selection(self) -> None:
        t = self._theme()
        for i, lbl in self._icon_cells.items():
            if i == self.index:
                lbl.configure(bg=t["select"], relief=tk.SOLID, bd=2)
            else:
                lbl.configure(bg=t["panel"], relief=tk.FLAT, bd=1)

    def _queue_thumbs_priority(self) -> None:
        """Priority: current index ± window, then rest of visible, then trailing."""
        if self.list_mode == "names" or not self.folder_files:
            return
        n = len(self.folder_files)
        order: List[int] = []
        if 0 <= self.index < n:
            for d in range(0, 12):
                for idx in (self.index + d, self.index - d):
                    if 0 <= idx < n and idx not in order:
                        order.append(idx)
        # append visible estimate
        for i in self._visible_indices():
            if i not in order:
                order.append(i)
        # light trailing batch
        for i in range(n):
            if i not in order:
                order.append(i)
                if len(order) > 80:  # don't flood queue; more on scroll
                    break
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
                visible = self._visible_playlist_indices()
                last = min(len(visible), (last_row + 1) * cols)
                return visible[first:last]
            if isinstance(w, tk.Listbox):
                first = w.nearest(0)
                last = w.nearest(w.winfo_height())
                visible = self._visible_playlist_indices()
                return visible[max(0, first):min(len(visible), last + 2)]
            assert isinstance(w, ttk.Treeview)
            first_iid = w.identify_row(1)
            last_iid = w.identify_row(max(1, w.winfo_height() - 2))
            try:
                fi = int(first_iid) if first_iid else 0
            except ValueError:
                fi = 0
            try:
                li = int(last_iid) if last_iid else min(20, len(self.folder_files) - 1)
            except ValueError:
                li = min(20, len(self.folder_files) - 1)
            if li < fi:
                li = fi
            return list(range(max(0, fi), min(len(self.folder_files), li + 3)))
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
        if self.list_mode == "names":
            return
        # Process a few per tick so UI stays responsive
        budget = 4 if self.list_mode == "small" else 2
        while budget > 0 and self._thumb_queue:
            idx = self._thumb_queue.pop(0)
            budget -= 1
            if idx < 0 or idx >= len(self.folder_files):
                continue
            path = self.folder_files[idx]
            key = str(path)
            if key in self._thumb_loaded:
                continue
            size = self._icon_cell_size() if self.list_mode == "icons" else 22
            photo = self._make_thumb(path, size)
            self._thumb_loaded.add(key)
            if photo is not None:
                self._thumb_photos[key] = photo
                self._apply_thumb_to_row(idx, photo)
        if self._thumb_queue:
            self._thumb_job = self.after(8, self._thumb_worker_step)

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

    def _make_thumb(self, path: Path, size: int) -> Optional[ImageTk.PhotoImage]:
        try:
            with Image.open(path) as im:
                # Cheap first-frame only
                if getattr(im, "n_frames", 1) > 1:
                    im.seek(0)
                im = ImageOps.exif_transpose(im)
                im = _frame_to_rgba(im)
                im.thumbnail((size, size), Image.Resampling.BILINEAR)
                t = self._theme()
                bg = Image.new("RGBA", (size, size), self._hex_to_rgba(t["panel"]))
                bg.paste(im, ((size - im.width) // 2, (size - im.height) // 2), im)
                return ImageTk.PhotoImage(bg)
        except Exception:
            return self._placeholder_photo

    @staticmethod
    def _hex_to_rgba(hex_color: str) -> Tuple[int, int, int, int]:
        h = hex_color.lstrip("#")
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)
        return (240, 240, 240, 255)

    def _on_list_select(self, _event=None) -> None:
        w = self._list_widget
        if w is None:
            return
        self._interrupt_slideshow()
        if isinstance(w, tk.Listbox):
            sel = w.curselection()
            if sel:
                visible = self._visible_playlist_indices()
                row = int(sel[0])
                if row < len(visible):
                    self.goto_index(visible[row], from_list=True)
                self._queue_thumbs_priority()
            return
        assert isinstance(w, ttk.Treeview)
        sel = w.selection()
        if sel:
            try:
                self.goto_index(int(sel[0]), from_list=True)
                self._queue_thumbs_priority()
            except ValueError:
                pass

    def _select_list_index(self, idx: int) -> None:
        w = self._list_widget
        if w is None or idx < 0:
            return
        if self.list_mode == "icons":
            self._highlight_icon_selection()
            lbl = self._icon_cells.get(idx)
            if lbl is not None and self._grid_canvas is not None:
                try:
                    self._grid_canvas.update_idletasks()
                    # Scroll so selected cell is visible
                    y = lbl.winfo_y()
                    h = max(self._grid_inner.winfo_height(), 1) if self._grid_inner else 1
                    self._grid_canvas.yview_moveto(max(0.0, (y - 20) / h))
                except tk.TclError:
                    pass
            return
        if isinstance(w, tk.Listbox):
            w.selection_clear(0, tk.END)
            visible = self._visible_playlist_indices()
            if idx in visible:
                row = visible.index(idx)
                w.selection_set(row)
                w.see(row)
            return
        if isinstance(w, ttk.Treeview):
            iid = str(idx)
            if w.exists(iid):
                w.selection_set(iid)
                w.focus(iid)
                w.see(iid)

    # ----- open file / folder ----------------------------------------------



    def open_folder_dialog(self) -> None:
        start = self.current_folder or (
            self.folder_files[self.index].parent if self.folder_files and self.index >= 0 else Path.home()
        )
        picker = FolderPicker(self, start=start)
        if picker.result:
            self.open_folders(picker.result)


    def open_path(self, path: Path) -> None:
        path = path.expanduser().resolve()
        if not path.exists():
            messagebox.showerror("오류", f"찾을 수 없습니다:\n{path}")
            return

        if path.is_dir():
            self.open_folders([path])
            return

        # ---- FILE OPEN: show this file FIRST, playlist later ----
        if not is_image_file(path):
            messagebox.showwarning("파일 열기", f"지원하지 않는 형식입니다:\n{path.name}")
            return

        self._playlist_gen += 1
        gen = self._playlist_gen
        self._cancel_thumb_jobs()
        self._thumb_photos.clear()
        self._thumb_loaded.clear()

        self.current_folder = path.parent
        # Immediate single-item playlist so UI is responsive
        self.folder_files = [path]
        self.index = 0
        self._populate_list_names_only()
        self._select_list_index(0)
        self._load_current()  # priority display

        # Deferred full playlist (names only, then lazy thumbs)
        self.after(30, lambda: self._build_playlist_async(path.parent, path, gen))


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

    def _rebuild_display(self) -> None:
        if self.pil_image is None:
            self.display_image = None
            return
        img = self.pil_image
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
        self.display_image = img


    def zoom_by(self, factor: float, event=None) -> None:
        if self.display_image is None:
            return
        self.zoom = max(0.02, min(32.0, self.zoom * factor))
        # Every zoom operation recenters the image in the canvas. This keeps
        # toolbar, keyboard, and optional wheel zoom behavior consistent.
        self.offset_x = self.offset_y = 0.0
        self.redraw()
        self._update_info()

    def fit_to_window(self) -> None:
        if self.display_image is None:
            return
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        iw, ih = self.display_image.size
        # Fill the image area while keeping aspect; center with zero pan
        self.zoom = min(cw / iw, ch / ih)
        self.offset_x = self.offset_y = 0.0
        self.redraw()
        self._update_info()

    def actual_size(self) -> None:
        self.zoom = 1.0
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
        self.pan_start = (event.x, event.y)
        self.canvas.configure(cursor="fleur")

    def _pan_move(self, event) -> None:
        if self.pan_start is None:
            return
        dx = event.x - self.pan_start[0]
        dy = event.y - self.pan_start[1]
        self.pan_start = (event.x, event.y)
        self.offset_x += dx
        self.offset_y += dy
        # Reposition the existing item while dragging; resize once only when needed.
        self.canvas.move("display_image", dx, dy)

    def _pan_end(self, _event) -> None:
        self.pan_start = None
        self.canvas.configure(cursor="")

    def _on_motion(self, event) -> None:
        if self.display_image is None:
            return
        cw = self.canvas.winfo_width() / 2
        ch = self.canvas.winfo_height() / 2
        ix = (event.x - cw - self.offset_x) / self.zoom + self.display_image.width / 2
        iy = (event.y - ch - self.offset_y) / self.zoom + self.display_image.height / 2
        x, y = int(ix), int(iy)
        if 0 <= x < self.display_image.width and 0 <= y < self.display_image.height:
            px = self.display_image.getpixel((x, y))
            if isinstance(px, int):
                px = (px,)
            anim = f"  ·  f{self.anim_index + 1}/{len(self.anim_frames)}" if self.is_animated else ""
            self.status.configure(
                text=f"Pixel ({x}, {y})  {px[:4] if len(px) >= 4 else px}  |  Zoom {int(self.zoom * 100)}%{anim}"
            )

    # ----- save / slideshow ------------------------------------------------



    def _slideshow_tick(self) -> None:
        # Advance without treating as "other button" interrupt
        if not self.folder_files:
            self._stop_slideshow()
            return
        nxt = (self.index + 1) % len(self.folder_files)
        self.index = nxt
        self._select_list_index(nxt)
        self._load_current()
        self._queue_thumbs_priority()
        ms = int(self.settings.get("slideshow_ms", 3000))
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
        try:
            self.config(menu="")
        except tk.TclError:
            pass
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
        self.config(menu=self._menubar)
        self.toolbar.grid()
        if self._context_visible:
            self.context_bar.grid()
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

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_modern_menus()

        self.toolbar = CrowEyesToolbar(self, self)
        self.toolbar.grid(row=0, column=0, sticky="ew")

        self.paned = ttk.Panedwindow(self, orient=tk.HORIZONTAL, style="CrowEyes.TPanedwindow")
        self.paned.grid(row=1, column=0, sticky="nsew", padx=10, pady=(8, 6))

        self.left_panel = PlaylistPanel(self.paned, self)
        self._center_panel = ImageCanvasView(self.paned, self)
        self._right_panel = InfoPanel(self.paned, self)
        self.paned.add(self.left_panel, weight=0)
        self.paned.add(self._center_panel, weight=1)
        self.paned.add(self._right_panel, weight=0)

        self.context_bar = ContextControlBar(self, self)
        self.context_bar.grid(row=2, column=0, sticky="ew")
        if not self._context_visible:
            self.context_bar.grid_remove()
        if not self._playlist_visible:
            self.after(10, self.hide_playlist_panel)
        if not self._info_visible:
            self.after(10, self.hide_info_panel)
        self.after(140, self._init_sashes)
        self.bind("<Configure>", self._on_root_configure, add="+")

    def _build_modern_menus(self) -> None:
        bar = tk.Menu(self, tearoff=0)
        self.config(menu=bar)
        self._menubar = bar
        self._menus: List[tk.Menu] = [bar]

        def cascade(label: str) -> tk.Menu:
            menu = tk.Menu(bar, tearoff=0)
            # Windows' native menubar cannot reliably render Tk PhotoImage
            # objects on top-level cascades and displays the literal "(image)".
            bar.add_cascade(label=label, menu=menu)
            self._menus.append(menu)
            return menu

        file_menu = cascade("파일")
        file_menu.add_command(label="파일 열기…", image=self._icons["open_image"], compound=tk.LEFT,
                              accelerator="Ctrl+O", command=self._action(self.open_file_dialog))
        file_menu.add_command(label="폴더로 보기…", image=self._icons["folder"], compound=tk.LEFT,
                              accelerator="Ctrl+Shift+O", command=self._action(self.open_folder_dialog))
        file_menu.add_command(label="다른 이름으로 저장…", image=self._icons["save"], compound=tk.LEFT,
                              accelerator="Ctrl+S", command=self._action(self.save_as))
        file_menu.add_separator()
        file_menu.add_command(label="최근 폴더", image=self._icons["folder"], compound=tk.LEFT, state=tk.DISABLED)
        file_menu.add_command(label="종료", image=self._icons["close"], compound=tk.LEFT, command=self._on_close)

        view_menu = cascade("보기")
        view_menu.add_command(label="확대", image=self._icons["zoom_in"], compound=tk.LEFT,
                              accelerator="Ctrl++", command=self._action(lambda: self.zoom_by(1.15)))
        view_menu.add_command(label="축소", image=self._icons["zoom_out"], compound=tk.LEFT,
                              accelerator="Ctrl+-", command=self._action(lambda: self.zoom_by(1 / 1.15)))
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
            ("Panel.TFrame", t["panel"]), ("Viewer.TFrame", t["canvas_bg"]),
            ("BottomBar.TFrame", t["panel_alt"]),
        ):
            style.configure(name, background=bg)
        style.configure("Card.TFrame", background=t["panel"], bordercolor=t["border"],
                        borderwidth=1, relief="solid")
        style.configure("Viewer.TFrame", background=t["canvas_bg"], bordercolor=t["border"],
                        borderwidth=1, relief="solid")
        style.configure("TLabel", background=t["bg"], foreground=t["fg"], font=t["font"])
        style.configure("Brand.TLabel", background=t["toolbar"], foreground=t["fg"], font=("Segoe UI Semibold", 13))
        style.configure("Logo.TLabel", background=t["toolbar"], foreground=t["accent"], font=("Segoe UI", 17, "bold"))
        style.configure("Product.TLabel", background=t["toolbar"], foreground=t["muted"], font=("Segoe UI Semibold", 7))
        style.configure("Crumb.TLabel", background=t["toolbar"], foreground=t["muted"], font=("Segoe UI", 8))
        style.configure("FileTitle.TLabel", background=t["toolbar"], foreground=t["fg"], font=("Segoe UI Semibold", 9))
        style.configure("Section.TLabel", background=t["panel"], foreground=t["muted"], font=("Segoe UI Semibold", 9))
        style.configure("Badge.TLabel", background=t["select"], foreground=t["accent_hi"], padding=(7, 2), font=("Segoe UI Semibold", 8))
        style.configure("Title.TLabel", background=t["panel"], foreground=t["fg"], font=t["font_title"])
        style.configure("Muted.TLabel", background=t["toolbar"], foreground=t["muted"], font=t["font"])
        style.configure("Status.TLabel", background=t["panel_alt"], foreground=t["muted"], font=("Segoe UI", 9))
        style.configure("BottomBar.TLabel", background=t["panel_alt"], foreground=t["fg"], font=("Segoe UI", 9))
        style.configure("Tooltip.TLabel", background=t["panel_alt"], foreground=t["fg"], relief="solid", borderwidth=1)
        button_style = {
            "background": t["button"], "foreground": t["button_fg"],
            "bordercolor": t["border"], "lightcolor": t["button_highlight"],
            "darkcolor": t["button_shadow"], "focuscolor": t["accent"],
            "borderwidth": 1, "relief": "raised",
        }
        style.configure(
            "Tool.TButton", **button_style, padding=(7, 5),
            font=("Segoe UI Semibold", 9),
        )
        style.map(
            "Tool.TButton",
            background=[("pressed", t["button_pressed"]), ("active", t["button_active"])],
            foreground=[("disabled", t["muted"])],
            relief=[("pressed", "sunken"), ("!pressed", "raised")],
        )
        accent_button_style = dict(button_style)
        accent_button_style.update(
            background=t["accent_button"], foreground="#FFFFFF", padding=(7, 5),
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

    def _init_sashes(self) -> None:
        try:
            self.update_idletasks()
            pw = max(self.paned.winfo_width(), 400)
            panes = self.paned.panes()
            if len(panes) >= 3:
                playlist_ratio = float(self.settings.get("pane_ratio_playlist", 0.20))
                image_ratio = float(self.settings.get("pane_ratio_image", 0.65))
                self.paned.sashpos(0, int(pw * playlist_ratio))
                self.paned.sashpos(1, int(pw * (playlist_ratio + image_ratio)))
            elif len(panes) == 2:
                first_is_playlist = self._playlist_visible
                self.paned.sashpos(0, int(pw * (0.20 if first_is_playlist else 0.85)))
            self._sashes_applied = True
        except (tk.TclError, IndexError):
            pass

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
        self.settings["show_playlist_panel"] = False
        self._restore_panes()

    def show_playlist_panel(self) -> None:
        self._playlist_visible = True
        self.settings["show_playlist_panel"] = True
        self._restore_panes()

    def toggle_playlist_panel(self) -> None:
        self.hide_playlist_panel() if self._playlist_visible else self.show_playlist_panel()

    def hide_info_panel(self) -> None:
        self._info_visible = False
        self.settings["show_info_panel"] = False
        self._restore_panes()

    def show_info_panel(self) -> None:
        self._info_visible = True
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
        self._rebuild_icon_chrome()
        self._populate_list_names_only()
        self.redraw()

    def _rebuild_icon_chrome(self) -> None:
        status_text = self.status.cget("text") if hasattr(self, "status") else ""
        brightness = self.brightness
        contrast = self.contrast
        if hasattr(self, "toolbar"):
            self.toolbar.destroy()
        if hasattr(self, "context_bar"):
            self.context_bar.destroy()
        try:
            self.config(menu="")
        except tk.TclError:
            pass
        self._icons = CrowEyesIconSet(self, self._theme())
        self.iconphoto(True, self._icons["app"])
        self._build_modern_menus()
        self.toolbar = CrowEyesToolbar(self, self)
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.context_bar = ContextControlBar(self, self)
        self.context_bar.grid(row=2, column=0, sticky="ew")
        if not self._context_visible:
            self.context_bar.grid_remove()
        self.bright_var.set(brightness)
        self.contrast_var.set(contrast)
        self.status.configure(text=status_text)
        self._info_close_btn.configure(image=self._icons["close"])
        self._info_close_btn._croweyes_image = self._icons["close"]  # type: ignore[attr-defined]
        self._apply_theme()
        self._update_slide_button()
        self._anim_btn.configure(state=tk.NORMAL if self.is_animated else tk.DISABLED)

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
        self.redraw()

    def _update_header(self) -> None:
        folder = self.current_folder
        self._folder_title_var.set(folder.name if folder else "폴더를 선택하지 않음")
        if 0 <= self.index < len(self.folder_files):
            self._file_title_var.set(self.folder_files[self.index].name)
        else:
            self._file_title_var.set("이미지를 열어 주세요")
        self._playlist_count_var.set(str(len(self.folder_files)))

    def show_shortcuts(self) -> None:
        messagebox.showinfo(
            "CrowEyes 단축키",
            "Ctrl+O  이미지 열기\nCtrl+Shift+O  폴더 열기\n"
            "← / →  이전·다음 이미지\nCtrl+0  1:1\nCtrl+1  화면 맞춤\n"
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

        def apply_settings() -> None:
            self.settings.update({
                "ui_theme": next((key for key, label in THEME_LABELS.items() if label == theme_var.get()), "croweyes_dark"),
                "fit_on_open": fit_var.get(),
                "slideshow_ms": int(slide_var.get()), "show_playlist_panel": playlist_var.get(),
                "show_info_panel": info_var.get(), "show_context_bar": context_var.get(),
                "compact_toolbar": compact_var.get(),
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
            self.redraw()
            save_settings(self.settings)
            win.destroy()

        buttons = ttk.Frame(frame, style="Panel.TFrame")
        buttons.grid(row=9, column=0, columnspan=2, sticky="e", pady=(16, 0))
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

    def register_file_associations(self, extensions: List[str]) -> None:
        """Register CrowEyes as an Open With candidate for selected formats."""
        if os.name != "nt" or winreg is None:
            raise OSError("기본 프로그램 등록은 Windows에서만 지원됩니다.")

        allowed = {ext for ext, _description in ASSOCIATION_OPTIONS}
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
        """Let the user choose formats, register, then hand off to Windows."""
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
                "CrowEyes로 열 이미지 형식을 선택하세요. 등록 후 Windows 설정에서\n"
                "각 확장자의 기본 앱을 CrowEyes로 선택하면 적용됩니다."
            ),
            style="Section.TLabel", justify=tk.LEFT,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 14))

        variables: Dict[str, tk.BooleanVar] = {}
        for index, (extension, description) in enumerate(ASSOCIATION_OPTIONS):
            variable = tk.BooleanVar(value=True)
            variables[extension] = variable
            row = 2 + index // 2
            column = index % 2
            ttk.Checkbutton(
                frame, text=f"{extension.upper():<7}  {description}", variable=variable,
            ).grid(row=row, column=column, sticky="w", padx=(0, 24), pady=3)

        def select_all(value: bool) -> None:
            for variable in variables.values():
                variable.set(value)

        action_row = 2 + (len(ASSOCIATION_OPTIONS) + 1) // 2
        selectors = ttk.Frame(frame, style="Panel.TFrame")
        selectors.grid(row=action_row, column=0, columnspan=2, sticky="w", pady=(12, 0))
        ttk.Button(
            selectors, text="모두 선택", command=lambda: select_all(True), style="Pastel.TButton",
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            selectors, text="선택 해제", command=lambda: select_all(False), style="Pastel.TButton",
        ).pack(side=tk.LEFT)

        def register_and_open() -> None:
            selected = [extension for extension, variable in variables.items() if variable.get()]
            if not selected:
                messagebox.showinfo(
                    "기본 프로그램 등록", "하나 이상의 확장자를 선택해 주세요.", parent=win,
                )
                return
            try:
                self.register_file_associations(selected)
            except (OSError, ValueError) as exc:
                messagebox.showerror(
                    "기본 프로그램 등록", f"등록하지 못했습니다.\n\n{exc}", parent=win,
                )
                return
            win.destroy()
            messagebox.showinfo(
                "등록 완료",
                "CrowEyes를 기본 앱 후보로 등록했습니다.\n"
                "이어서 Windows 설정에서 원하는 확장자를 CrowEyes로 선택해 주세요.",
                parent=self,
            )
            self.open_windows_default_apps()

        buttons = ttk.Frame(frame, style="Panel.TFrame")
        buttons.grid(row=action_row + 1, column=0, columnspan=2, sticky="e", pady=(16, 0))
        ttk.Button(
            buttons, text="취소", command=win.destroy, style="Pastel.TButton",
        ).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(
            buttons, text="등록 후 Windows 설정 열기", command=register_and_open,
            style="Pastel.TButton",
        ).pack(side=tk.LEFT)
        self._apply_theme()

    def _stop_slideshow(self, quiet: bool = False) -> None:
        if self.slideshow_job is not None:
            try:
                self.after_cancel(self.slideshow_job)
            except (tk.TclError, ValueError):
                pass
            self.slideshow_job = None
            if not quiet:
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
        animation_style = "Accent.Tool.TButton" if self.anim_playing else "Tool.TButton"
        self._anim_btn._croweyes_style = animation_style  # type: ignore[attr-defined]
        self._anim_btn.configure(style=animation_style)

    def open_file_dialog(self) -> None:
        selected = filedialog.askopenfilename(
            title="이미지 열기",
            filetypes=[
                ("이미지 파일", "*.bmp *.dib *.jpg *.jpeg *.png *.gif *.webp *.tif *.tiff *.ico *.tga"),
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
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg"), ("WebP", "*.webp"), ("GIF", "*.gif")],
        )
        if not destination:
            return
        try:
            image = self.display_image
            if Path(destination).suffix.lower() in {".jpg", ".jpeg"} and image.mode == "RGBA":
                image = image.convert("RGB")
            image.save(destination)
            self.status.configure(text=f"저장 완료: {destination}")
        except Exception as exc:
            messagebox.showerror("저장 실패", str(exc))

    def show_about(self) -> None:
        messagebox.showinfo(
            APP_TITLE,
            f"{APP_TITLE}\n\n"
            "CrowEyes는 감상과 탐색에 집중한 데스크톱 이미지 뷰어입니다.\n"
            "Pillow · tkinter · ttkbootstrap 기반\n\n"
            "2026년 8월 · v1.0\n"
            "제작: Crow Science Lab\n\n"
            "F11 이미지 전체화면 · F8 정보 패널 · F5 슬라이드쇼",
        )

    # Image decoding and folder scans run outside Tk's event thread. Only the
    # small result-application steps below touch widgets.
    def _load_current(self) -> None:
        self._stop_animation_timer()
        if not (0 <= self.index < len(self.folder_files)):
            return
        path = self.folder_files[self.index]
        self._image_load_gen += 1
        generation = self._image_load_gen
        self.display_image = None
        self._show_loading_state(path.name)

        def worker() -> None:
            try:
                frames, delays, animated = load_animation_frames(path)
                if generation == self._image_load_gen:
                    self._image_load_results[generation] = (True, path, frames, delays, animated)
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
            detail = str(payload[0])
            self.status.configure(text=f"열기 실패: {path.name}")
            self._show_error_state(path.name, detail)
            return
        frames, delays, animated = payload
        self.anim_frames = frames
        self.anim_delays = delays
        self.anim_index = 0
        self.is_animated = bool(animated)
        self.pil_image = frames[0]
        self.rotation = 0
        self.flip_h = self.flip_v = False
        self.bright_var.set(1.0)
        self.contrast_var.set(1.0)
        self.brightness = self.contrast = 1.0
        self.offset_x = self.offset_y = 0.0
        self.title(f"{path.name} — {APP_TITLE}")
        self._rebuild_display()
        if bool(self.settings.get("fit_on_open", True)):
            self.after_idle(self.fit_to_window)
        else:
            self.zoom = 1.0
            self.redraw()
        self._update_header()
        self._update_info()
        self._rotation_text_var.set("0°")
        animation_note = f" · {len(frames)} 프레임" if animated else ""
        self.status.configure(text=f"{path.name}  ·  {frames[0].width}×{frames[0].height}  ·  "
                                   f"{self.index + 1}/{len(self.folder_files)}{animation_note}")
        if self.is_animated and self.anim_playing:
            self._schedule_next_frame()
        if self._startup_activation_pending:
            self._startup_activation_pending = False
            self.after_idle(self._activate_viewer_window)

    def open_folders(self, folders: List[Path]) -> None:
        if not folders:
            return
        self._playlist_gen += 1
        generation = self._playlist_gen
        self._cancel_thumb_jobs()
        self._thumb_photos.clear()
        self._thumb_loaded.clear()
        self._file_stat_cache.clear()
        self.current_folder = folders[0]
        self.status.configure(text="폴더의 이미지 목록을 불러오는 중…")

        def worker() -> None:
            resolved: List[Path] = []
            seen: Set[str] = set()
            clean_folders: List[Path] = []
            for folder in folders:
                try:
                    folder = folder.expanduser().resolve()
                except OSError:
                    continue
                if not folder.is_dir():
                    continue
                clean_folders.append(folder)
                for path in list_image_paths_fast(folder):
                    try:
                        resolved_path = path.resolve()
                    except OSError:
                        continue
                    key = str(resolved_path)
                    if key not in seen:
                        seen.add(key)
                        resolved.append(resolved_path)
            if generation == self._playlist_gen:
                self._scan_results[generation] = (self._sorted(resolved), clean_folders)

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
        files, folders = result
        self.folder_files = files
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
            try:
                priority = prioritize.resolve()
            except OSError:
                priority = prioritize
            resolved: List[Path] = []
            for item in files:
                try:
                    resolved.append(item.resolve())
                except OSError:
                    continue
            if priority not in resolved:
                resolved.append(priority)
                resolved = self._sorted(resolved)
            if generation == self._playlist_gen:
                self._scan_results[generation] = (resolved, priority)

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
        files, priority = result
        self.folder_files = files
        try:
            self.index = files.index(priority)
        except ValueError:
            self.index = 0 if files else -1
        self._populate_list_names_only()
        self._select_list_index(self.index)
        self._update_header()
        self._queue_thumbs_priority()
        self.status.configure(text=f"{priority.name} · 플레이리스트 {len(files)}개")
        self.after(80, self._queue_thumbs_visible)

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

    def _show_loading_state(self, filename: str) -> None:
        self._clear_canvas_overlay()
        self.canvas.delete("all")
        t = self._theme()
        _primary, secondary, _hint = self._canvas_text_palette()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        self.canvas.create_text(cw / 2, ch / 2 - 12, text="◌", fill=t["accent"], font=("Segoe UI", 28))
        self.canvas.create_text(cw / 2, ch / 2 + 24, text=f"{filename} 불러오는 중…",
                                fill=secondary, font=("Segoe UI", 10))
        self.status.configure(text=f"이미지 불러오는 중: {filename}")

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
        if self.display_image is None:
            self._draw_empty_state()
            return
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        w = max(1, int(self.display_image.width * self.zoom))
        h = max(1, int(self.display_image.height * self.zoom))
        if w * h > 16_000_000:
            limit_scale = (16_000_000 / (w * h)) ** 0.5
            w, h = max(1, int(w * limit_scale)), max(1, int(h * limit_scale))
        if self.is_animated and abs(self.zoom - 1.0) < 0.01:
            resample = Image.Resampling.NEAREST
        elif self.zoom < 1.0:
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
        self._zoom_text_var.set(f"{int(self.zoom * 100)}%")

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
        data = [
            ("파일명", path.name), ("전체 경로", str(path)),
            ("파일 형식", path.suffix.upper().lstrip(".") or "알 수 없음"),
            ("파일 크기", size_text),
            ("해상도", f"{self.anim_frames[0].width} × {self.anim_frames[0].height}"),
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
        slide_style = "Accent.Tool.TButton" if playing else "Tool.TButton"
        self._slide_btn._croweyes_style = slide_style  # type: ignore[attr-defined]
        self._slide_btn.configure(
            text="", image=self._icons["pause" if playing else "play"],
            style=slide_style,
        )

    def _on_close(self) -> None:
        self._playlist_gen += 1
        self._image_load_gen += 1
        self._stop_slideshow(quiet=True)
        self._stop_animation_timer()
        self._cancel_thumb_jobs()
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
                self.settings["pane_ratio_playlist"] = max(0.10, min(0.40, first))
                self.settings["pane_ratio_image"] = max(0.35, min(0.80, second - first))
                self.settings["pane_ratio_info"] = max(0.10, min(0.35, 1.0 - second))
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
