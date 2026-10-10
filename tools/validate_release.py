"""Validate shared version, archive contents, hashes and core footprint."""
import hashlib
import json
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1]
data=json.loads((ROOT/'version.json').read_text())
version=data['version']
release=ROOT/'release'/f'review-v{version}'
distribution=ROOT/'dist'/f'review-v{version}'/'CrowEyes'
assert json.loads((distribution/'_internal/version.json').read_text())==data
assert json.loads((distribution/'_internal/extensions.json').read_text())==json.loads((ROOT/'extensions.json').read_text())
for name in ('c2pa','numpy','onnxruntime','rawpy','tokenizers','pillow_heif'):
    assert not (distribution/'_internal'/name).exists(),name
archives=list(release.glob('*'))
checks={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()) for p in archives if p.suffix in {'.exe','.zip','.msix'}}
assert len(checks)==7,checks.keys()
for kind,item in json.loads((ROOT/'extensions.json').read_text()).items():
    assert checks[item['filename']]['sha256']==item['sha256']
    with zipfile.ZipFile(release/item['filename']) as zipped:
        assert zipped.testzip() is None
        if kind=='formats':
            assert not any('heif' in name.lower() or 'x265' in name.lower() for name in zipped.namelist())
with zipfile.ZipFile(release/f'CrowEyes_Portable_{version}_Windows_x64.zip') as zipped:
    assert 'CrowEyes.exe' in zipped.namelist() and zipped.testzip() is None
with zipfile.ZipFile(release/f'CrowEyes_{data["store_version"]}_x64.msix') as zipped:
    assert zipped.testzip() is None
    manifest=ElementTree.fromstring(zipped.read('AppxManifest.xml'))
    assert manifest.find('{*}Identity').attrib['Version']==data['store_version']
(release/'SHA256SUMS.txt').write_text(''.join(value['sha256']+'  '+name+'\n' for name,value in sorted(checks.items())),encoding='utf-8')
sizes={}
for label,path in [('1.9e',ROOT/'dist/review-v1.9e/CrowEyes'),(version,distribution)]:
    if path.exists():sizes[label]=sum(p.stat().st_size for p in path.rglob('*') if p.is_file())
report=dict(version=data,status='PASS',core_bytes=sizes,artifacts=checks)
if len(sys.argv)>1:
    Path(sys.argv[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
