"""Hash-pinned, optional extension archives; no packages loaded at viewer startup."""
import hashlib
import importlib
import json
import os
import shutil
import sys
import tempfile
import zipfile
import uuid
from pathlib import Path, PurePosixPath

_handles = []


def bundled_root():
    return (Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'bundled') if getattr(sys,'frozen',False) else Path(__file__).resolve().parent/'.bundled-runtime'


def bundled(kind):
    path=bundled_root()/'included.json'
    return path.is_file() and kind in json.loads(path.read_text(encoding='utf-8'))


def root():
    version = json.loads((Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))/'version.json').read_text())['version']
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'CrowEyes' / 'extensions' / version


def manifest():
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    path = base / 'extensions.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def available(kind):
    if bundled(kind):return True
    try:
        installed = root() / kind / 'installed.json'
        return installed.is_file() and json.loads(installed.read_text()) == manifest().get(kind)
    except (OSError, ValueError):
        return False


def install(archive, kind):
    expected = manifest().get(kind)
    if not expected:
        raise ValueError('이 빌드용 공식 선택 모듈 정보가 없습니다.')
    archive = Path(archive)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != expected['sha256']:
        raise ValueError('이 버전의 공식 선택 모듈과 SHA-256이 일치하지 않습니다.')
    root().mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='install-', dir=root()))
    try:
        with zipfile.ZipFile(archive) as zipped:
            entries = zipped.infolist()
            if sum(e.file_size for e in entries) > 1_000_000_000:
                raise ValueError('선택 모듈 크기 한도 초과')
            for entry in entries:
                name = PurePosixPath(entry.filename.replace('\\', '/'))
                if name.is_absolute() or '..' in name.parts or ':' in str(name) or (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError('잘못된 선택 모듈 경로')
            zipped.extractall(staging)
        (staging / 'installed.json').write_text(json.dumps(expected), encoding='utf-8')
        target = root() / kind
        if target.exists():
            # Keep recoverable prior installation rather than deleting it.
            backup = root() / ('previous-' + kind + '-' + uuid.uuid4().hex)
            target.rename(backup)
        staging.rename(target)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def load_optional(kind, module):
    if bundled(kind):
        path=bundled_root()
        if str(path) not in sys.path:
            sys.path.insert(0,str(path))
            if os.name=='nt':
                for folder in [path,*path.glob('*.libs'),path/'onnxruntime'/'capi',path/'rawpy',path/'c2pa']:
                    if folder.is_dir():_handles.append(os.add_dll_directory(str(folder)))
        return importlib.import_module(module)
    if not getattr(sys, 'frozen', False):
        return importlib.import_module(module)
    path = root() / kind
    if not available(kind):
        raise ImportError('선택 모듈 관리에서 ' + kind + ' 모듈을 설치하세요.')
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
        if os.name == 'nt':
            for folder in [path, *path.rglob('*.libs'), path / 'onnxruntime' / 'capi', path / 'rawpy']:
                if folder.is_dir():
                    _handles.append(os.add_dll_directory(str(folder)))
    return importlib.import_module(module)


def model_path():
    if bundled('safety'):return bundled_root()/'assets'/'models'/'nudenet-320n.onnx'
    return root() / 'safety' / 'assets' / 'models' / 'nudenet-320n.onnx'
