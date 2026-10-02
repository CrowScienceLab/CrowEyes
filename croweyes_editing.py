"""Bounded image editing and atomic raster export."""
import math
import os
import tempfile
from pathlib import Path
from urllib.parse import urlsplit
from PIL import Image

MAX_EXPORT_PIXELS = 40_000_000
MAX_EXPORT_SIDE = 32768
EXPORT_FORMATS = {'.png': 'PNG', '.jpg': 'JPEG', '.jpeg': 'JPEG',
                  '.webp': 'WEBP', '.bmp': 'BMP', '.tif': 'TIFF', '.tiff': 'TIFF'}


def validate_update_url(url):
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or parsed.hostname != 'github.com'
            or parsed.username or parsed.password or parsed.port not in (None, 443)
            or not parsed.path.startswith('/CrowScienceLab/CrowEyes/releases/download/')):
        raise ValueError('공식 CrowEyes 릴리스 다운로드 주소가 아닙니다.')
    return url


def validate_size(width, height):
    width, height = int(width), int(height)
    if min(width, height) < 1 or max(width, height) > MAX_EXPORT_SIDE:
        raise ValueError(f'가로·세로는 1~{MAX_EXPORT_SIDE:,} 픽셀이어야 합니다.')
    if width * height > MAX_EXPORT_PIXELS:
        raise ValueError('저장 크기는 최대 4천만 픽셀입니다.')
    return width, height


def selection_box(start, end, canvas_box, image_size):
    """Map a clipped canvas drag to source pixels, including reverse drags."""
    left, top, right, bottom = canvas_box
    width, height = image_size
    if right <= left or bottom <= top:
        raise ValueError('표시된 이미지가 없습니다.')
    x0, x1 = sorted((start[0], end[0]))
    y0, y1 = sorted((start[1], end[1]))
    x0, x1 = max(left, x0), min(right, x1)
    y0, y1 = max(top, y0), min(bottom, y1)
    if x1 <= x0 or y1 <= y0:
        raise ValueError('이미지 내부의 영역을 선택하세요.')
    return (max(0, math.floor((x0-left)*width/(right-left))),
            max(0, math.floor((y0-top)*height/(bottom-top))),
            min(width, math.ceil((x1-left)*width/(right-left))),
            min(height, math.ceil((y1-top)*height/(bottom-top))))


def save_raster(image, destination):
    destination = Path(destination)
    fmt = EXPORT_FORMATS.get(destination.suffix.lower())
    if fmt is None:
        raise ValueError('PNG, JPEG, WebP, BMP, TIFF 형식으로 저장하세요.')
    validate_size(*image.size)
    # Fresh pixels avoid copying stale EXIF/C2PA claims onto edited content.
    rgba = image.convert('RGBA')
    clean = Image.new('RGBA', rgba.size)
    clean.paste(rgba)
    if fmt in {'JPEG', 'BMP'}:
        background = Image.new('RGB', clean.size, 'white')
        background.paste(clean, mask=clean.getchannel('A'))
        clean = background
    fd, temporary = tempfile.mkstemp(prefix='.croweyes-', suffix='.tmp', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            clean.save(stream, format=fmt)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)
