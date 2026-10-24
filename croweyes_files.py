"""Windows file visibility and ordering; never rewrite image content."""
import ctypes
import os
import re
from pathlib import Path

HIDDEN = 0x2
NORMAL = 0x80


def file_attributes(path):
    if os.name != 'nt':
        raise OSError('Windows 파일 속성은 Windows에서만 지원합니다.')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    get = kernel.GetFileAttributesW
    get.argtypes = [ctypes.c_wchar_p]
    get.restype = ctypes.c_uint32
    value = get(str(Path(path).absolute()))
    if value == 0xFFFFFFFF:
        raise ctypes.WinError(ctypes.get_last_error())
    return value


def is_hidden(path):
    if os.name != 'nt':
        return Path(path).name.startswith('.')
    try:
        return bool(file_attributes(path) & HIDDEN)
    except OSError:
        # A disappearing/unreadable file must not abort a folder scan.
        return True


def entry_hidden(entry):
    if os.name != 'nt':
        return entry.name.startswith('.')
    try:
        # Windows scandir already has these attributes: no image I/O.
        return bool(entry.stat(follow_symlinks=False).st_file_attributes & HIDDEN)
    except OSError:
        return True


def set_hidden(path, hidden):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise OSError('일반 파일만 숨김 속성을 변경할 수 있습니다.')
    attributes = file_attributes(path)
    updated = (attributes | HIDDEN) & ~NORMAL if hidden else attributes & ~HIDDEN
    updated = updated or NORMAL
    if updated == attributes:
        return
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    put = kernel.SetFileAttributesW
    put.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32]
    put.restype = ctypes.c_int
    if not put(str(path.absolute()), updated):
        raise ctypes.WinError(ctypes.get_last_error())


def natural_key(value):
    return tuple((1, int(p), len(p)) if p.isdigit() else (0, p.casefold())
                 for p in re.split(r'(\d+)', value))
