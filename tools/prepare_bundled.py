"""Merge the three reviewed, hash-pinned runtimes; share identical dependencies."""
import hashlib
import json
from pathlib import Path,PurePosixPath
import zipfile

ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'extensions.json').read_text())
version=json.loads((ROOT/'version.json').read_text())['version']
target=ROOT/'.bundled-runtime'
target.mkdir(exist_ok=True)
seen={}
included={}
for kind in ('provenance','safety','formats'):
    item=manifest[kind]
    archive=ROOT/'release'/f'review-v{version}'/item['filename']
    with archive.open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==item['sha256']
    with zipfile.ZipFile(archive) as zipped:
        for entry in zipped.infolist():
            name=PurePosixPath(entry.filename.replace('\\','/'))
            assert not name.is_absolute() and '..' not in name.parts and ':' not in str(name)
            if entry.is_dir():continue
            data=zipped.read(entry)
            digest=hashlib.sha256(data).hexdigest()
            if str(name) in seen:
                assert seen[str(name)]==digest,str(name)
                continue
            seen[str(name)]=digest
            output=target/str(name);output.parent.mkdir(parents=True,exist_ok=True);output.write_bytes(data)
    included[kind]=item
(target/'included.json').write_text(json.dumps(included,indent=2),encoding='utf-8')
print('Bundled bytes:',sum(p.stat().st_size for p in target.rglob('*') if p.is_file()))
