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
assert len(checks)==3,checks.keys()
bundled=distribution/'_internal/bundled'
assert set(json.loads((bundled/'included.json').read_text()))=={'provenance','safety','formats'}
for package in ('c2pa','numpy','onnxruntime','rawpy'):assert (bundled/package).is_dir()
assert not (bundled/'tokenizers').exists() and not (bundled/'models/clip').exists()
assert (bundled/'assets/models/nudenet-320n.onnx').is_file()
for source in (ROOT/'.bundled-runtime').rglob('*'):
    if source.is_file() and '__pycache__' not in source.parts:
        packaged=bundled/source.relative_to(ROOT/'.bundled-runtime')
        assert packaged.is_file(),packaged
        assert hashlib.file_digest(source.open('rb'),'sha256').digest()==hashlib.file_digest(packaged.open('rb'),'sha256').digest(),packaged
with zipfile.ZipFile(release/f'CrowEyes_Portable_{version}_Windows_x64.zip') as zipped:
    assert 'CrowEyes.exe' in zipped.namelist() and zipped.testzip() is None
    assert hashlib.sha256(zipped.read('CrowEyes.exe')).digest()==hashlib.file_digest((distribution/'CrowEyes.exe').open('rb'),'sha256').digest()
with zipfile.ZipFile(release/f'CrowEyes_{data["store_version"]}_x64.msix') as zipped:
    assert zipped.testzip() is None
    manifest=ElementTree.fromstring(zipped.read('AppxManifest.xml'))
    assert manifest.find('{*}Identity').attrib['Version']==data['store_version']
    assert manifest.find('{*}Identity').attrib['Name']=='170231F2.CrowEyes'
    assert hashlib.sha256(zipped.read('CrowEyes.exe')).digest()==hashlib.file_digest((distribution/'CrowEyes.exe').open('rb'),'sha256').digest()
    import ast
    tree=ast.parse((ROOT/'CrowEyes_Image_Viewer_2.0.py').read_text(encoding='utf-8'))
    options=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ASSOCIATION_OPTIONS' for t in n.targets))
    extensions={value[0] for value in options}
    manifest_extensions={node.text for node in manifest.findall('.//{*}FileType')}
    assert extensions==manifest_extensions,(extensions,manifest_extensions)
    installer=(ROOT/'installer/CrowEyes.iss').read_text(encoding='utf-8')
    assert all('ValueName: "'+ext+'"' in installer for ext in extensions)
    assert len(extensions)==29

(release/'SHA256SUMS.txt').write_text(''.join(value['sha256']+'  '+name+'\n' for name,value in sorted(checks.items())),encoding='utf-8')
sizes={}
for label,path in [('1.9e',ROOT/'dist/v1.9e/CrowEyes'),(version,distribution)]:
    if path.exists():sizes[label]=sum(p.stat().st_size for p in path.rglob('*') if p.is_file())
report=dict(version=data,status='PASS',core_bytes=sizes,artifacts=checks)
if len(sys.argv)>1:
    Path(sys.argv[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
