"""Build version-pinned optional module archives before building the core."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
VERSION=json.loads((ROOT/'version.json').read_text())['version']
VENDOR=ROOT/'.publish-venv'/'Lib'/'site-packages'
FORMAT_VENDOR=ROOT/'.optional-vendor'/'formats'
OUTPUT=ROOT/'release'/f'review-v{VERSION}'


def package(kind, sources):
    archive=OUTPUT/f'CrowEyes_Module_{kind}_{VERSION}_Windows_x64.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as zipped:
        for path,target in sources:
            if not path.exists():
                raise FileNotFoundError(path)
            for file in ([path] if path.is_file() else path.rglob('*')):
                if file.is_file() and '__pycache__' not in file.parts:
                    if file.suffix.lower() in {'.lib','.pdb','.exp','.d','.h','.pyx'}:
                        continue
                    relative=Path(target) if path.is_file() else Path(target)/file.relative_to(path)
                    zipped.write(file,str(relative))
        for file in (ROOT/'licenses').glob('*'):
            zipped.write(file,'licenses/'+file.name)
    with archive.open('rb') as file:
        digest=hashlib.file_digest(file,'sha256').hexdigest()
    return dict(filename=archive.name,sha256=digest,version=VERSION)


def dirs(base, patterns):
    return [(p,p.name) for pattern in patterns for p in base.glob(pattern)]


def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    common=dirs(VENDOR,['numpy','numpy.libs','numpy-*.dist-info'])
    records={
        'provenance':package('provenance',dirs(VENDOR,['c2pa','c2pa_python-*.dist-info'])),
        'safety':package('safety',common+dirs(VENDOR,['onnxruntime','onnxruntime-*.dist-info'])+[(ROOT/'assets/models/nudenet-320n.onnx','assets/models/nudenet-320n.onnx')]),
        'formats':package('formats',common+dirs(FORMAT_VENDOR,['rawpy','rawpy.libs','rawpy-*.dist-info'])),
        'semantic':package('semantic',common+dirs(VENDOR,['onnxruntime','onnxruntime-*.dist-info'])+dirs(ROOT/'.optional-vendor/semantic',['tokenizers','tokenizers-*.dist-info','models'])),
    }
    (ROOT/'extensions.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print(json.dumps(records,indent=2))


if __name__=='__main__':
    main()
