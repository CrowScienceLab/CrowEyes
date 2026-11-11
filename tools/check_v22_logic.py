"""Physical layout, channel arbitration and a real test-only shortcut round-trip."""
import sys,math
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from croweyes_printing import make_plan,device_rect,tile_bitmap,preview_dpi
from croweyes_updates import select_update,published_store
from PIL import Image,ImageDraw
from types import SimpleNamespace
preview=Image.new('RGB',(2100,2970));preview.info['dpi']=(254,254)
viewer=SimpleNamespace(pil_image=preview,source_render_scale=.5)
assert preview_dpi(viewer)==127
assert all(math.isclose(a,b) for a,b in zip(make_plan(preview.size,mode='actual',source_dpi=preview_dpi(viewer),tiles=4,margins=(0,0,0,0)).image_mm,(420,594)))

plan=make_plan((4200,5940),margins=(0,0,0,0),mode='percent',percent=100,source_dpi=254,tiles=4)
assert all(math.isclose(a,b) for a,b in zip(plan.image_mm,(420,594))) and not plan.clipped and len(plan.tiles)==4
assert [tuple(round(v,6) for v in t.source) for t in plan.tiles]==[(0,0,.5,.5),(.5,0,1,.5),(0,.5,.5,1),(.5,.5,1,1)]
assert device_rect(plan.tiles[0],(254,254))==(0,0,2100,2970)
small=make_plan((4200,5940),margins=(10,10,10,10),mode='percent',percent=50,source_dpi=254,tiles=4)
assert all(math.isclose(a,b) for a,b in zip(small.image_mm,(210,297)))
assert make_plan((4200,5940),mode='actual',source_dpi=254,tiles=4).clipped
assert not make_plan((4200,5940),mode='fit',tiles=4).clipped
assert make_plan((4000,2000),tiles=2).columns==2
assert make_plan((2000,4000),tiles=2).rows==2
hw=make_plan((100,100),margins=(0,0,0,0),hardware=(4,5,6,7))
assert hw.margins==(4,5,6,7)
for kwargs in [dict(percent=float('nan')),dict(source_dpi=0),dict(margins=(200,0,200,0)),dict(tiles=3)]:
    try:make_plan((100,100),**kwargs)
    except ValueError:pass
    else:raise AssertionError(kwargs)
im=Image.new('RGB',(420,594));d=ImageDraw.Draw(im)
for box,color in [((0,0,209,296),'red'),((210,0,419,296),'green'),((0,297,209,593),'blue'),((210,297,419,593),'yellow')]:d.rectangle(box,fill=color)
assert [tile_bitmap(im,t).getpixel((10,10)) for t in plan.tiles]==[(255,0,0),(0,128,0),(0,0,255),(255,255,0)]
ok=lambda v:dict(status='ok',version=v)
assert select_update('2.1',ok('2.2.0'),ok('2.2.0.0'))[0]=='store'
assert select_update('2.1',ok('2.3'),ok('2.2'))[0]=='github'
assert select_update('2.1',dict(status='error'),ok('2.2'))[0]=='store'
assert select_update('2.1',ok('2.2'),dict(status='error'))[0]=='github'
assert select_update('2.2',ok('2.2'),ok('2.1')) is None
assert select_update('2.1',ok('2.2'),dict(status='ok',available=True))[0]=='store'
assert select_update('2.1',ok('2.2'),dict(status='ok',available=False,version='2.2'))[0]=='github'
try:published_store({'store':{'published':False,'product_id':'9NNHX36VPSQZ','version':'99.0'}})
except ValueError:pass
else:raise AssertionError('unpublished Store version accepted')

from croweyes_onboarding import create_store_shortcut
import uuid
folder=ROOT/'tmp/v22-shortcut'/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=True)
with patch('croweyes_onboarding.package_family',return_value='170231F2.CrowEyes_Test'):
    shortcut=create_store_shortcut(ROOT/'assets/icons/croweyes-2.0.ico',destination=folder,icon_cache=folder/'icon.ico')
    assert shortcut.exists() and shortcut.stat().st_size>100
    try:create_store_shortcut(ROOT/'assets/icons/croweyes-2.0.ico',destination=folder,icon_cache=folder/'icon.ico')
    except FileExistsError:pass
    else:raise AssertionError('existing shortcut overwritten')
print('PASS: A2/A4 exact four-tile math, percentage, DPI, hardware margins, quadrant order, channel tie/failure routing and isolated real .lnk creation')
