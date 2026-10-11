# -*- mode: python ; coding: utf-8 -*-
import sys
import json
from pathlib import Path
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo, StringTable, StringStruct, VarFileInfo, VarStruct

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules


python_root = Path(sys.base_prefix)
release_version=json.loads(Path('version.json').read_text())['version']
version_tuple=tuple(map(int,release_version.split('.')))+(0,)
pe_version=VSVersionInfo(ffi=FixedFileInfo(filevers=version_tuple,prodvers=version_tuple,mask=0x3f,flags=0,OS=0x40004,fileType=1,subtype=0,date=(0,0)),kids=[StringFileInfo([StringTable('040904b0',[StringStruct('CompanyName','Crow Science Lab'),StringStruct('FileDescription','CrowEyes Image Viewer'),StringStruct('FileVersion',release_version),StringStruct('ProductName','CrowEyes'),StringStruct('ProductVersion',release_version),StringStruct('OriginalFilename','CrowEyes.exe')])]),VarFileInfo([VarStruct('Translation',[1033,1200])])])
library_bin = python_root / 'Library' / 'bin'
msgcat = python_root / 'Library' / 'lib' / 'tcl8' / '8.5' / 'msgcat-1.6.1.tm'

datas = [(str(msgcat), 'tcl8\\8.5')] if msgcat.is_file() else []
datas += collect_data_files('ttkbootstrap')
datas += [
    (str(Path('assets/cursors/region-ocr.cur').resolve()), 'assets/cursors'),
    (str(Path('assets/icons/croweyes-2.0.png').resolve()), 'assets/icons'),
    (str(Path('assets/icons/croweyes-2.0.ico').resolve()), 'assets/icons'),
    (str(Path('assets/icons/croweyes.ico').resolve()), 'assets/icons'),
    (str(Path('assets/safety/content_blocked_crow.webp').resolve()), 'assets/safety'),
    (str(Path('version.json').resolve()), '.'),
    (str(Path('extensions.json').resolve()), '.'),
    (str(Path('tools/windows_ocr.ps1').resolve()), 'tools'),
    (str(Path('tools/windows_heic.ps1').resolve()), 'tools'),
    (str(Path('THIRD_PARTY_NOTICES.md').resolve()), '.'),
    (str(Path('licenses').resolve()), 'licenses'),
]
bundled_root=Path('.bundled-runtime')
datas += [(str(file.resolve()),str(Path('bundled')/file.relative_to(bundled_root).parent)) for file in bundled_root.rglob('*') if file.is_file() and '__pycache__' not in file.parts]

runtime_dlls = (
    'libmpdec-4.dll', 'libcrypto-3-x64.dll', 'liblzma.dll', 'LIBBZ2.dll',
    'ffi.dll', 'libexpat.dll', 'libssl-3-x64.dll', 'tk86t.dll', 'tcl86t.dll',
)
binaries = [
    (str(library_bin / name), '.')
    for name in runtime_dlls
    if (library_bin / name).is_file()
]

hiddenimports = ['resvg_py', 'send2trash']


a = Analysis(
    ['CrowEyes_Image_Viewer_2.0.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['c2pa', 'onnxruntime', 'numpy', 'rawpy', 'pillow_heif', 'cryptography', 'tokenizers', 'croweyes_semantic'],
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
    icon=['assets\\icons\\croweyes-2.0.ico'],
    version=pe_version,
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
