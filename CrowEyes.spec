# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs


python_root = Path(sys.base_prefix)
library_bin = python_root / 'Library' / 'bin'
msgcat = python_root / 'Library' / 'lib' / 'tcl8' / '8.5' / 'msgcat-1.6.1.tm'

datas = [(str(msgcat), 'tcl8\\8.5')] if msgcat.is_file() else []
datas += collect_data_files('ttkbootstrap')
datas += [
    (str(Path('assets/icons/croweyes-eye-logo.png').resolve()), 'assets/icons'),
    (str(Path('assets/icons/croweyes.ico').resolve()), 'assets/icons'),
    (str(Path('assets/safety/content_blocked_crow.webp').resolve()), 'assets/safety'),
    (str(Path('assets/models/nudenet-320n.onnx').resolve()), 'assets/models'),
    (str(Path('THIRD_PARTY_NOTICES.md').resolve()), '.'),
    (str(Path('licenses').resolve()), 'licenses'),
]

runtime_dlls = (
    'libmpdec-4.dll', 'libcrypto-3-x64.dll', 'liblzma.dll', 'LIBBZ2.dll',
    'ffi.dll', 'libexpat.dll', 'libssl-3-x64.dll', 'tk86t.dll', 'tcl86t.dll',
)
binaries = [
    (str(library_bin / name), '.')
    for name in runtime_dlls
    if (library_bin / name).is_file()
]
binaries += collect_dynamic_libs('onnxruntime')


a = Analysis(
    ['CrowEyes_Image_Viewer_1.8.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=['resvg_py', 'send2trash'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='CrowEyes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\icons\\croweyes.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='CrowEyes',
)
