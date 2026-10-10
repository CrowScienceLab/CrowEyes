"""Exercise limits and unsafe extension inputs with isolated generated files."""
import ast
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch
from typing import Tuple
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from croweyes_workflows import open_image,encode
import croweyes_extensions as extensions
folder=ROOT/'tmp/boundaries'
folder.mkdir(parents=True,exist_ok=True)
image=Image.new('RGB',(9000,6000),'#3c5578')
image.save(folder/'large.jpg',quality=75)
image.close()
preview=open_image(folder/'large.jpg',preview=True)
assert max(preview.size)<=4096
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
for filename in ('CrowEyes_Image_Viewer_1.9.py','CrowEyes_Image_Viewer_1.9e.py','CrowEyes_Image_Viewer_2.0.py'):
    tree=ast.parse((ROOT/filename).read_text(encoding='utf-8'))
    nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in {'semantic_version','is_newer_version'}]
    scope=dict(re=re,Tuple=Tuple,APP_UPDATE_VERSION='2.0.0',APP_VERSION='2.0.0')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),filename,'exec'),scope)
    for current in ('1.9','1.9e','1.9.1'):
        assert scope['is_newer_version']('v2.0.0',current)
    assert not scope['is_newer_version']('v2.0.0','2.0.0')
    assert scope['is_newer_version']('v2.0.1','2.0.0')
print('PASS: 54MP preview limit, corrected export EXIF, ZIP traversal/hash rejection, legacy update migration')
