# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


python_root = Path(sys.base_prefix)
library_bin = python_root / 'Library' / 'bin'
msgcat = python_root / 'Library' / 'lib' / 'tcl8' / '8.5' / 'msgcat-1.6.1.tm'

datas = [(str(msgcat), 'tcl8\\8.5')] if msgcat.is_file() else []
datas += collect_data_files('ttkbootstrap')

runtime_dlls = (
    'libmpdec-4.dll', 'libcrypto-3-x64.dll', 'liblzma.dll', 'LIBBZ2.dll',
    'ffi.dll', 'libexpat.dll', 'libssl-3-x64.dll', 'tk86t.dll', 'tcl86t.dll',
)
binaries = [
    (str(library_bin / name), '.')
    for name in runtime_dlls
    if (library_bin / name).is_file()
]


a = Analysis(
    ['CrowEyes_Image_Viewer_1.0.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
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
