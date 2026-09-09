"""Non-destructive release contract checks for CrowEyes 1.9."""

import importlib.util
import sys
import tempfile
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "CrowEyes_Image_Viewer_1.9.py"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    required = (
        'APP_VERSION = "1.9"',
        '"ui_theme": "croweyes_dark"',
        '"white_light_pink": "White + Light Pink"',
        '"AI 이미지 확률 · C2PA"',
        'c2pa_ai_probability(path)',
        '"성인용 컨텐츠 차단"',
        '"성인용 컨텐츠로 판단되어 화면 표시를 차단했습니다."',
        'self._render(name, 24)',
        'resource_path("assets", "icons", "croweyes-1.9.png")',
    )
    for marker in required:
        require(marker in source, f"missing v1.9 contract: {marker}")

    info_block = source[source.index("def _update_info"):source.index("def _update_slide_button")]
    require('(\"파일명\", path.name)' not in info_block, "duplicate filename remains in Image Info")
    require('(\"전체 경로\", str(path))' not in info_block, "duplicate directory remains in Image Info")

    icon_path = ROOT / "assets" / "icons" / "croweyes.ico"
    brand_path = ROOT / "assets" / "icons" / "croweyes-1.9.png"
    require(icon_path.is_file() and icon_path.stat().st_size > 50_000, "new ICO missing or too small")
    with Image.open(brand_path) as image:
        require(image.width >= 1024 and image.height >= 1024, "brand icon source is undersized")
    with Image.open(icon_path) as image:
        require(image.format == "ICO", "Windows icon is not ICO")

    spec = (ROOT / "CrowEyes.spec").read_text(encoding="utf-8")
    installer = (ROOT / "installer" / "CrowEyes.iss").read_text(encoding="utf-8")
    require("CrowEyes_Image_Viewer_1.9.py" in spec, "spec does not target v1.9")
    require("croweyes-1.9.png" in spec, "new brand asset is not packaged")
    require('#define MyAppVersion "1.9"' in installer, "installer version is not 1.9")
    require('Name: "{autodesktop}\\CrowEyes"' in installer, "desktop shortcut name is not CrowEyes")

    spec_obj = importlib.util.spec_from_file_location("croweyes_v19_check", SOURCE)
    require(spec_obj is not None and spec_obj.loader is not None, "cannot load v1.9 module")
    sys.path.insert(0, str(ROOT))
    module = importlib.util.module_from_spec(spec_obj)
    sys.modules[spec_obj.name] = module
    spec_obj.loader.exec_module(module)
    with tempfile.TemporaryDirectory() as temp_dir:
        plain_file = Path(temp_dir) / "plain.jpg"
        plain_file.write_bytes(b"plain-jpeg")
        require(module.c2pa_ai_probability(brand_path)[0] == 100, "valid C2PA AI declaration not detected")
        require(module.c2pa_ai_probability(plain_file)[0] == 0, "non-C2PA image must remain 0%")
        require("return 25" in source and "return 50" in source and "return 75" in source,
                "five-step C2PA evidence scale is incomplete")
    print("PASS: CrowEyes 1.9 UI, C2PA, icon, theme, and packaging contracts")


if __name__ == "__main__":
    main()
