"""Real-file workflows and Tk state regression for the 2.0 release."""
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import threading
import time
from unittest.mock import patch
from PIL import Image, ImageDraw, ImageCms

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from croweyes_workflows import batch,encode,atomic_write,Catalog,duplicates,open_image,metadata
from croweyes_annotation import render
from croweyes_provenance import inspect

folder=ROOT/'tmp/v20-test'
folder.mkdir(parents=True,exist_ok=True)
im=Image.new('RGB',(400,200),'white')
draw=ImageDraw.Draw(im)
draw.rectangle((40,40,160,160),fill='blue')
im.save(folder/'source.png')
(folder/'same.png').write_bytes((folder/'source.png').read_bytes())
im.resize((200,100)).save(folder/'similar.png')
assert len(duplicates([folder/'source.png',folder/'same.png'],False,threading.Event(),lambda i,n:None))==1
assert duplicates([folder/'source.png',folder/'similar.png'],True,threading.Event(),lambda i,n:None)
output=folder/'batch'
report,records=batch([folder/'source.png'],output,80,80,'.jpg',85,'',threading.Event(),lambda i,n:None)
assert Image.open(records[0]['output']).size==(80,40)
report,records2=batch([folder/'source.png'],output,80,120,'.png',85,'',threading.Event(),lambda i,n:None,False)
assert Image.open(records2[0]['output']).size==(80,120)
assert (folder/'source.png').read_bytes()==(folder/'same.png').read_bytes()
cancel=threading.Event();cancel.set()
report,records=batch([folder/'source.png'],output,0,0,'.png',90,'',cancel,lambda i,n:None)
assert not records and json.loads(report.read_text())['cancelled']
data=encode(im,'.jpg',95,target_kib=5)
assert len(data)<=5120
exif=Image.Exif();exif[271]='CrowEyes Test';exif[306]='2026:10:10 10:00:00'
im.save(folder/'exif.jpg',exif=exif,icc_profile=ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes())
photo=open_image(folder/'exif.jpg')
assert photo.info.get('icc_profile')
assert metadata(folder/'exif.jpg')['Make']=='CrowEyes Test'
with Image.open(io.BytesIO(encode(photo,'.jpg'))) as clean:
    assert not clean.getexif()
with Image.open(io.BytesIO(encode(photo,'.jpg',preserve_exif=True))) as preserved:
    assert preserved.getexif()[271]=='CrowEyes Test'
catalog=Catalog(folder/'catalog.sqlite')
catalog.set(folder/'source.png',text='수업 도형',taken='2026:10:11')
assert catalog.all()[str((folder/'source.png').resolve())]['text']=='수업 도형'
out=render(im,[('사각형',(10,10,100,100),'#ff0000',''),('텍스트',(10,120,150,180),'#000000','CrowEyes'),('화살표',(200,20,300,100),'#00ff00',''),('형광펜',(20,20,70,70),'#ffff00',''),('모자이크',(50,50,150,150),'#ffffff','')])
assert out.size==im.size and out.getpixel((10,10))[:3]==(255,0,0)
out.save(folder/'annotations.png')
assert inspect(ROOT/'test-assets/CrowEyes_C2PA_50pct_sample.jpg')['validation']=='정상'
spec=importlib.util.spec_from_file_location('croweyes_v20',ROOT/'CrowEyes_Image_Viewer_2.0.py')
app=importlib.util.module_from_spec(spec);sys.modules[spec.name]=app;spec.loader.exec_module(app)
assert app.APP_VERSION=='2.0.0' and app.is_newer_version('v2.0.0','1.9')
assert not app.is_newer_version('v2.0.0')
app.SETTINGS_PATH=folder/'settings.json'
app.DEFAULT_SETTINGS['auto_check_updates']=False
with patch.object(app.CrowEyes20,'_auto_register_file_associations',lambda self:None):
    viewer=app.CrowEyes20(str(folder/'source.png'))
viewer.withdraw()
deadline=time.monotonic()+8
while viewer.display_image is None and time.monotonic()<deadline:
    viewer.update();time.sleep(.01)
assert viewer.display_image is not None
viewer.rotate(90)
assert viewer.rotation==90
viewer.undo_edit();assert viewer.rotation==0
viewer.redo_edit();assert viewer.rotation==90
viewer.restore_original();assert viewer._state()==(0,False,False,1.,1.)
viewer.zoom_by(2);zoom=viewer.zoom
assert zoom>0
viewer._ensure_catalog()
for name in ('batch_dialog','annotation_dialog','compare_before_after','quality_dialog','search_dialog','extensions_dialog','performance_dialog'):
    before=set(viewer.winfo_children())
    getattr(viewer,name)();viewer.update()
    for child in set(viewer.winfo_children())-before:
        if child.winfo_class()=='Toplevel' or child.__class__.__name__=='EmbeddedDialog':child.destroy()
viewer._on_close()
print('PASS: 2.0 real exports/collision/cancellation/metadata/ICC/catalog/duplicates/annotations/C2PA/undo/redo/Tk tools')
