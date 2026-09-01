#!/usr/bin/env python3
"""Non-destructive release checks for CrowEyes 1.8."""

from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "CrowEyes_Image_Viewer_1.8.py"
MODEL = ROOT / "assets" / "models" / "nudenet-320n.onnx"
sys.path.insert(0, str(ROOT))

spec = importlib.util.spec_from_file_location("croweyes_v18", SOURCE)
assert spec and spec.loader
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)

import croweyes_safety as safety


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


class DeterministicManager(safety.SafetyManager):
    """Exercise policy/cache without any sensitive image fixture."""

    def __init__(self, cache_path: Path, blocked: bool) -> None:
        super().__init__(Path("unused.onnx"), cache_path)
        self.blocked = blocked

    def _scores(self, _image: Image.Image) -> dict:
        values = {name: 0.01 for name in safety.EXPLICIT_THRESHOLDS}
        if self.blocked:
            values["MALE_GENITALIA_EXPOSED"] = 0.90
        return values


def check_settings(folder: Path) -> None:
    settings_path = folder / "settings.json"
    settings_path.write_text(
        json.dumps({
            "design_generation": 9,
            "content_filter": "explicit",
            "pane_ratio_playlist": 0.05,
            "pane_ratio_image": 0.90,
            "pane_ratio_info": 0.05,
        }),
        encoding="utf-8",
    )
    old_settings, old_legacy = app.SETTINGS_PATH, app._LEGACY_SETTINGS
    try:
        app.SETTINGS_PATH, app._LEGACY_SETTINGS = settings_path, folder / "legacy.json"
        migrated = app.load_settings()
    finally:
        app.SETTINGS_PATH, app._LEGACY_SETTINGS = old_settings, old_legacy
    require(migrated["design_generation"] == 10, "v1.8 settings migration missing")
    require(migrated["content_filter"] == safety.MODE_OFF, "filter must default OFF on upgrade")
    require(migrated["pane_ratio_playlist"] >= 0.18, "playlist pane migration too narrow")
    require(migrated["pane_ratio_info"] >= 0.14, "information pane migration too narrow")


def check_policy_and_cache(folder: Path) -> None:
    image_path = folder / "synthetic.png"
    Image.new("RGB", (96, 64), "#4A90E2").save(image_path)
    cache_path = folder / "cache.sqlite3"
    safe_manager = DeterministicManager(cache_path, blocked=False)
    first = safe_manager.check(image_path)
    require(first.status == safety.SAFE, "safe policy path failed")
    cached = safe_manager.check(image_path)
    require(cached.status == safety.SAFE and cached.cached, "safe cache lookup failed")
    image_path.write_bytes(image_path.read_bytes() + b"changed")
    blocked_manager = DeterministicManager(cache_path, blocked=True)
    blocked = blocked_manager.check(image_path)
    require(blocked.status == safety.BLOCKED, "explicit class was not blocked")
    require("MALE_GENITALIA_EXPOSED" in blocked.matched_classes, "matched class missing")
    blocked_manager.cache.clear()
    require(blocked_manager.cached_result(image_path) is None, "cache clear failed")


def check_model() -> None:
    require(MODEL.is_file() and MODEL.stat().st_size == 12_150_158, "bundled model size mismatch")
    digest = hashlib.sha256(MODEL.read_bytes()).hexdigest().upper()
    require(
        digest == "C15D8273ADAD2D0A92F014CC69AB2D6C311A06777A55545F2C4EB46F51911F0F",
        "bundled model hash mismatch",
    )
    manager = safety.SafetyManager(MODEL, Path(tempfile.gettempdir()) / "croweyes-v18-model-cache.sqlite3")
    require(manager.prepare_model().status == safety.SAFE, "ONNX model failed to load")


def check_source_contract() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    for marker in (
        'APP_VERSION = "1.8"',
        '"content_filter": MODE_OFF',
        "def _poll_safety_worker",
        "def _show_blocked_state",
        "def _start_pending_playlist",
        "def _poll_thumb_decode",
        "def _queue_image_prefetch",
        'self._view_mode == "fit"',
        'resource_path("assets", "icons", "croweyes.ico")',
        'resource_path("assets", "safety", "content_blocked_crow.webp")',
    ):
        require(marker in source, f"missing v1.8 contract: {marker}")
    load_current = inspect.getsource(app.CrowEyesImageViewer._load_current)
    require("_start_image_decode" in load_current, "selected-file decoder path missing")
    require("_build_playlist_async" not in load_current, "folder scan precedes selected image")
    thumb_worker = inspect.getsource(app.CrowEyesImageViewer._thumb_worker_step)
    require("threading.Thread" in thumb_worker, "thumbnail decoding is not asynchronous")
    require("urllib" not in inspect.getsource(safety.SafetyManager), "safety manager has network code")


def check_assets() -> None:
    mascot = ROOT / "assets" / "safety" / "content_blocked_crow.webp"
    require(mascot.is_file() and mascot.stat().st_size < 50_000, "blocked mascot is not compact")
    with Image.open(mascot) as image:
        require(image.format == "WEBP", "blocked mascot is not WebP")
        require("A" in image.getbands(), "blocked mascot lacks transparency")
        require(max(image.size) <= 320, "blocked mascot dimensions are too large")
    icon = ROOT / "assets" / "icons" / "croweyes.ico"
    with Image.open(icon) as image:
        require(image.format == "ICO" and image.size == (256, 256), "application ICO is invalid")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="croweyes-v18-") as temp:
        folder = Path(temp)
        check_settings(folder)
        check_policy_and_cache(folder)
    check_model()
    check_source_contract()
    check_assets()
    print("PASS: CrowEyes 1.8 safety, async loading, layout, and asset checks")


if __name__ == "__main__":
    main()
