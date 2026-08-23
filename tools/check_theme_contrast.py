"""Validate CrowEyes product-theme text and button contrast ratios."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Dict


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "CrowEyes_Image_Viewer_1.6.py"


def relative_luminance(color: str) -> float:
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    return (max(first, second) + 0.05) / (min(first, second) + 0.05)


def load_themes() -> Dict[str, dict]:
    spec = importlib.util.spec_from_file_location("croweyes_theme_source", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {SOURCE}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CROWEYES_THEMES


def main() -> int:
    themes = load_themes()
    checks = (
        ("main / window", "fg", "bg", 4.5),
        ("main / panel", "fg", "panel", 4.5),
        ("main / toolbar", "fg", "toolbar", 4.5),
        ("secondary / panel", "muted", "panel", 4.5),
        ("button / normal", "button_fg", "button", 4.5),
        ("button / hover", "button_fg", "button_active", 4.5),
        ("button / pressed", "button_fg", "button_pressed", 4.5),
        ("selection", "select_fg", "select", 4.5),
    )
    failed = False
    for theme_name, colors in themes.items():
        print(f"[{theme_name}]")
        for label, foreground_key, background_key, minimum in checks:
            ratio = contrast_ratio(colors[foreground_key], colors[background_key])
            print(f"  {label:<20} {ratio:>5.2f}:1")
            failed |= ratio < minimum

        accent_ratio = contrast_ratio("#FFFFFF", colors["accent_button"])
        accent_pressed_ratio = contrast_ratio("#FFFFFF", colors["accent_pressed"])
        bevel_ratio = max(
            contrast_ratio(colors["button"], colors["button_highlight"]),
            contrast_ratio(colors["button"], colors["button_shadow"]),
        )
        print(f"  {'accent button':<20} {accent_ratio:>5.2f}:1")
        print(f"  {'accent pressed':<20} {accent_pressed_ratio:>5.2f}:1")
        print(f"  {'button bevel edge':<20} {bevel_ratio:>5.2f}:1")
        failed |= accent_ratio < 4.5 or accent_pressed_ratio < 4.5 or bevel_ratio < 3.0

    if failed:
        print("FAIL: one or more contrast targets were not met")
        return 1
    print("PASS: all text and button-edge contrast targets were met")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
