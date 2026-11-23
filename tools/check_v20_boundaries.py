"""Exercise limits and unsafe extension inputs with isolated generated files."""
import ast
import hashlib
import json
import re
import sys
import zipfile
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from typing import Tuple
from PIL import Image, ImageCms, ImageFile, ImageOps

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from croweyes_workflows import open_image,encode
from croweyes_safety import load_safety_samples
import croweyes_extensions as extensions
folder=ROOT/'tmp/boundaries'
folder.mkdir(parents=True,exist_ok=True)
image=Image.new('RGB',(9000,6000),'#3c5578')
image.save(folder/'large.jpg',quality=75)
image.close()
preview=open_image(folder/'large.jpg',preview=True)
assert max(preview.size)<=4096

profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
icc_jpeg = folder/'icc-preview.jpg'
with Image.new('RGB', (5000, 256), '#3280bd') as sample:
    sample.save(icc_jpeg, icc_profile=profile, dpi=(300, 300))
with open_image(icc_jpeg, preview=True) as preview:
    assert preview.width == 4096
    assert preview.convert('RGBA').getchannel('A').getextrema() == (255, 255)
    assert preview.info['dpi'] == (300, 300) and preview.info.get('icc_profile')

icc_png = folder/'icc-alpha.png'
with Image.new('RGBA', (3, 1), 'blue') as sample:
    sample.putalpha(Image.frombytes('L', sample.size, bytes((0, 128, 255))))
    sample.save(icc_png, icc_profile=profile)
with open_image(icc_png) as transparent:
    assert transparent.getchannel('A').tobytes() == bytes((0, 128, 255))

# A clipped JPEG tail should be repaired only for that reader. Observe
# Pillow's policy when the retry reaches the same decode path as other workers.
jpeg = folder/'recoverable.jpg'
with Image.new('RGB', (320, 240), 'blue') as sample:
    sample.save(jpeg)
    jpeg.write_bytes(jpeg.read_bytes()[:-2])
policies = []
transpose = ImageOps.exif_transpose

def observe_policy(source, **kwargs):
    policies.append(ImageFile.LOAD_TRUNCATED_IMAGES)
    return transpose(source, **kwargs)

with patch.object(ImageOps, 'exif_transpose', observe_policy):
    assert open_image(jpeg).size == (320, 240)
assert policies == [False, False], policies

# A Pillow header can report dimensions without allocating a pixel buffer.
header = SimpleNamespace(size=(20_001, 10_000), width=20_001, height=10_000, format='JPEG')
with patch.object(Image, 'open', return_value=nullcontext(header)):
    try:
        load_safety_samples(jpeg)
    except ValueError as exc:
        assert '2억 픽셀' in str(exc)
    else:
        raise AssertionError('Safety sampling accepted an oversized image')
exif=Image.Exif();exif[274]=6;exif[256]=400;exif[257]=200
sample=Image.new('RGB',(400,200),'blue');sample.info['exif']=exif.tobytes()
sample=sample.resize((80,40))
from io import BytesIO
with Image.open(BytesIO(encode(sample,'.jpg',preserve_exif=True))) as saved:
    assert saved.getexif()[274]==1 and saved.getexif()[256]==80
archive=folder/'unsafe.zip'
with zipfile.ZipFile(archive,'w') as zipped:
    zipped.writestr('../outside.txt','must not escape')
record=dict(filename=archive.name,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),version='2.0.0')
with patch.object(extensions,'manifest',lambda:{'formats':record}),patch.object(extensions,'root',lambda:folder/'modules'):
    try:extensions.install(archive,'formats')
    except ValueError as exc:assert '경로' in str(exc)
    else:raise AssertionError('Traversal accepted')
    record['sha256']='0'*64
    try:extensions.install(archive,'formats')
    except ValueError as exc:assert 'SHA-256' in str(exc)
    else:raise AssertionError('Wrong hash accepted')
assert not (folder/'outside.txt').exists()
for filename in ('tools/fixtures/legacy_update_comparator.py','CrowEyes_Image_Viewer_2.0.py'):
    tree=ast.parse((ROOT/filename).read_text(encoding='utf-8'))
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {'semantic_version','is_newer_version'}]
    scope=dict(re=re,Tuple=Tuple,APP_UPDATE_VERSION='2.0.0',APP_VERSION='2.0.0')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),filename,'exec'),scope)
    for current in ('1.9','1.9e','1.9.1'):
        assert scope['is_newer_version']('v2.0.0',current)
    assert not scope['is_newer_version']('v2.0.0','2.0.0')
    assert scope['is_newer_version']('v2.0.1','2.0.0')
print('PASS: 54MP preview, ICC preview opacity and PNG transparency, per-image JPEG recovery, safety pixel limit, export EXIF, ZIP path/hash validation, legacy update migration')
