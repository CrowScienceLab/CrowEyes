"""Shared resource limits for Pillow image readers."""

from PIL import Image


MAX_INPUT_PIXELS = 200_000_000
MAX_PREVIEW_PIXELS = 64_000_000
JPEG_FORMATS = frozenset({"JPEG", "MPO"})
ANIMATION_FORMATS = frozenset({"GIF", "WEBP"})

# Pillow raises at twice this value. Keep its early header checks enabled
# across plugins while allowing CrowEyes to draft previews up to 200 MP.
Image.MAX_IMAGE_PIXELS = MAX_INPUT_PIXELS // 2


def check_image_size(image, *, preview=False):
    pixels = image.width * image.height
    if pixels > MAX_INPUT_PIXELS:
        raise ValueError("입력 한도는 2억 픽셀입니다.")
    if preview and pixels > MAX_PREVIEW_PIXELS and image.format not in JPEG_FORMATS:
        raise ValueError("이 형식의 축소 디코딩을 지원하지 않아 메모리 보호를 위해 6,400만 픽셀로 제한합니다.")


def animation_frame_count(image):
    if image.format not in ANIMATION_FORMATS:
        return 1
    pixels = image.width * image.height
    count = image.n_frames
    if count > 1:
        if pixels > 40_000_000:
            raise ValueError("고해상도 애니메이션은 지원하지 않습니다.")
        if count > 1000 or pixels * count * 4 > 256 * 1024 * 1024:
            raise ValueError("애니메이션이 메모리 한도(256MB 또는 1,000프레임)를 초과합니다.")
    return count
