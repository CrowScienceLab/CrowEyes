"""Physical layout, channel isolation and a real test-only shortcut round-trip."""
import sys,math
from pathlib import Path
from unittest.mock import Mock, patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from croweyes_printing import make_plan,device_rect,tile_bitmap,preview_dpi
from croweyes_updates import UpdateCoordinator, version_key
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
assert version_key('v2.3.0') == version_key('2.3.0.0')
assert version_key('2.10.0') > version_key('2.3.0')
APP_VERSION = '2.3.0'
GITHUB_RELEASES_URL = 'https://api.github.com/repos/CrowScienceLab/CrowEyes/releases/latest'
MICROSOFT_STORE_URI = 'ms-windows-store://pdp/?productid=9NNHX36VPSQZ'
save_settings = Mock()


class UpdateViewer:
    def __init__(self, is_store):
        self._runs_as_store = is_store
        self.settings = {}
        self.status = Mock()
        self._native_owner = Mock(return_value=42)
        self._show_update_download = Mock()
        self.after = Mock()

    def finish(self):
        _, callback, *args = self.after.call_args.args
        callback(*args)


with patch('croweyes_updates.messagebox') as notice, \
     patch('croweyes_updates.fetch_json') as fetch, \
     patch('croweyes_updates.os.startfile') as open_store:
    viewer = UpdateViewer(False)
    coordinator = UpdateCoordinator(viewer)
    release = {'tag_name': 'v2.4.0'}
    fetch.return_value = release
    notice.askyesno.return_value = True
    coordinator.start()
    coordinator.start(manual=True)
    assert coordinator.result.result(timeout=2) == release
    viewer.finish()
    fetch.assert_called_once_with(GITHUB_RELEASES_URL, APP_VERSION)
    viewer._show_update_download.assert_called_once_with(release)
    open_store.assert_not_called()

    fetch.side_effect = OSError('GitHub offline')
    coordinator.start(manual=True)
    assert isinstance(coordinator.result.exception(timeout=2), OSError)
    viewer.finish()
    assert 'GitHub' in notice.showwarning.call_args.args[1]

    fetch.reset_mock()
    notice.reset_mock()
    operation = Mock(status=1)
    store_context = Mock()
    store_context.get_app_and_optional_store_package_updates_async.return_value = operation
    store_api = SimpleNamespace(StoreContext=Mock())
    store_api.StoreContext.get_default.return_value = store_context
    interop = SimpleNamespace(initialize_with_window=Mock())
    viewer = UpdateViewer(True)
    coordinator = UpdateCoordinator(viewer)
    with patch.dict(sys.modules, {'winrt.windows.services.store': store_api, 'winrt.runtime.interop': interop}):
        operation.get_results.return_value = [object()]
        coordinator.start()
        viewer.finish()
        interop.initialize_with_window.assert_called_once_with(store_context, 42)
        open_store.assert_called_once_with(MICROSOFT_STORE_URI)

        operation.get_results.return_value = []
        coordinator.start(manual=True)
        viewer.finish()
        assert '최신 버전입니다' in notice.showinfo.call_args.args[1]

        operation.status = 3
        coordinator.start(manual=True)
        viewer.finish()
        assert 'Microsoft Store' in notice.showwarning.call_args.args[1]

        operation.status = 0
        coordinator.start(manual=True)
        _, callback, *_ = viewer.after.call_args.args
        callback(0)
        operation.cancel.assert_called_once()
        assert '시간이 초과' in notice.showwarning.call_args.args[1]

    fetch.assert_not_called()
    viewer._show_update_download.assert_not_called()

from croweyes_onboarding import create_store_shortcut
import uuid
folder=ROOT/'tmp/v22-shortcut'/uuid.uuid4().hex;folder.mkdir(parents=True,exist_ok=True)
with patch('croweyes_onboarding.package_family',return_value='170231F2.CrowEyes_Test'):
    shortcut=create_store_shortcut(ROOT/'assets/icons/croweyes-2.0.ico',destination=folder,icon_cache=folder/'icon.ico')
    assert shortcut.exists() and shortcut.stat().st_size>100
    try:create_store_shortcut(ROOT/'assets/icons/croweyes-2.0.ico',destination=folder,icon_cache=folder/'icon.ico')
    except FileExistsError:pass
    else:raise AssertionError('existing shortcut overwritten')
print('PASS: A2/A4 print math, exclusive GitHub/Store routing, channel failures and timeout, isolated real .lnk creation')
