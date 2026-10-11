"""Verify layout changes retain image state and keep optional imports idle."""
import importlib.util
import sys
import time
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
folder=ROOT/'tmp/workspace';folder.mkdir(parents=True,exist_ok=True)
for i in range(8):Image.new('RGB',(640,400),(30+i*15,80,120)).save(folder/f'photo-{i}.png')
spec=importlib.util.spec_from_file_location('workspace_test',ROOT/'CrowEyes_Image_Viewer_2.0.py')
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
module.SETTINGS_PATH=folder/'settings.json'
module.load_settings=lambda:{**module.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[],'window_geometry':'1280x850'}
module.save_settings=lambda settings:None
viewer=module.CrowEyes20(str(folder/'photo-0.png'))
errors=[];viewer.report_callback_exception=lambda *args:errors.append(args)
def pump(ms=200):
    end=time.monotonic()+ms/1000
    while time.monotonic()<end:viewer.update();time.sleep(.01)
pump(1500)
assert viewer.display_image is not None
assert list(viewer._workspace_menus)==['파일','보기','편집','정리','도구','설정']
assert str(viewer.cget('menu'))==str(viewer.toolbar.menu_row)
assert not viewer._navigation_buttons
viewer.rotate(90);pump();viewer.zoom_by(1.5)
state=viewer._state();zoom=viewer.zoom
for _ in range(3):
    viewer.set_workspace('editor');pump()
    assert len(viewer.paned.panes())==2 and str(viewer.left_panel) in viewer.paned.panes()
    assert viewer.navigation_bar.winfo_ismapped() and viewer._filmstrip is None
    assert viewer._state()==state and viewer.zoom==zoom
    viewer.set_workspace('viewer');pump()
    assert len(viewer.paned.panes())==2 and viewer.navigation_bar.winfo_ismapped()
    assert viewer._state()==state and viewer.zoom==zoom
viewer.set_workspace('editor');pump(700)
assert viewer._editor_panel is None
viewer.enter_image_fullscreen();pump();assert len(viewer.paned.panes())==1
assert not viewer.cget('menu')
viewer.exit_image_fullscreen();pump();assert len(viewer.paned.panes())==2
assert str(viewer.cget('menu'))==str(viewer.toolbar.menu_row)
viewer.set_ui_theme('bright_sky_blue');pump()
assert viewer._workspace_mode=='editor' and len(viewer.paned.panes())==2
viewer.set_ui_theme('croweyes_dark');pump()
viewer.geometry('800x600');pump()
assert viewer.toolbar.winfo_reqheight()<250
assert [b._croweyes_action for b in viewer._toolbar_buttons][-5:]==['annotation','highlight','mosaic','compare','save']
assert all(not b.cget('text') for b in viewer._toolbar_buttons)
assert not viewer._info_visible and viewer._navigation_tasks.winfo_ismapped()
viewer.toggle_info_panel();pump();assert len(viewer.paned.panes())==3
viewer.toggle_info_panel();pump();assert len(viewer.paned.panes())==2
thumb=viewer._make_thumb_pil(folder/'photo-0.png',72)
assert thumb.size==(72,72) and thumb.getpixel((0,0))[3]==0 and thumb.getpixel((36,36))[3]==255
dialog=viewer._text('OCR 결과','CrowEyes test');pump()
assert dialog.winfo_toplevel() is viewer and dialog.master is viewer and dialog.__class__.__name__=='FittedDialog'
assert dialog.winfo_rootx()+dialog.winfo_width()<=viewer.winfo_rootx()+viewer.winfo_width()
dialog.destroy()
viewer.show_preferences();pump()
for child in viewer.winfo_children():
    if child.__class__.__name__ in ('EmbeddedDialog','FittedDialog'):
        assert child.winfo_toplevel() is viewer
        child.destroy()
from croweyes_workflows import Catalog
viewer._catalog=Catalog(folder/'index.sqlite3')
viewer.index_collection(False);pump(600)
assert len(viewer._catalog.all())==8
for child in viewer.winfo_children():
    if child.__class__.__name__ in ('EmbeddedDialog','FittedDialog'):child.destroy()
assert not hasattr(viewer,'semantic_dialog') and not hasattr(viewer,'catalog_dialog')
viewer.set_workspace('viewer');pump()
assert viewer.bright_var.get()==state[3]
assert not [name for name in ('c2pa','numpy','onnxruntime','tokenizers') if name in sys.modules]
viewer._on_close()
assert not errors,errors
print('PASS: viewer/editor modes, state retention, menus, shared file list, fullscreen, theme, 800x600, no AI imports')
