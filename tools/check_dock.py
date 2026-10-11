"""Verify scroll limits, on-demand dock pages and pixel sampling in real Tk."""
import importlib.util,sys,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PIL import Image
folder=ROOT/'tmp/dock-test';folder.mkdir(parents=True,exist_ok=True)
Image.new('RGB',(640,400),(42,91,146)).save(folder/'sample.png')
spec=importlib.util.spec_from_file_location('dock_test',ROOT/'CrowEyes_Image_Viewer_2.0.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.load_settings=lambda:{**m.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[],'window_geometry':'1200x850'}
m.save_settings=lambda v:None;m.CrowEyes20._auto_register_file_associations=lambda s:None
v=m.CrowEyes20(str(folder/'sample.png'));errors=[]
v.report_callback_exception=lambda *args:errors.append(str(args))
def pump(ms=150):
    end=time.monotonic()+ms/1000
    while time.monotonic()<end:v.update();time.sleep(.01)
pump(1000)
assert not v._info_visible and v._navigation_tasks.winfo_ismapped()
v.set_list_mode('icons');pump()
for _ in range(30):v._on_grid_wheel(SimpleNamespace(delta=120))
pump();assert v._grid_canvas.yview()[0]==0
assert abs(v._grid_canvas.canvasy(0))<2
v.geometry('900x600');pump()
for _ in range(30):v._on_grid_wheel(SimpleNamespace(delta=-120))
for _ in range(30):v._on_grid_wheel(SimpleNamespace(delta=120))
pump();assert abs(v._grid_canvas.canvasy(0))<2
for mode in m.LIST_MODES:
    v.set_list_mode(mode);pump();assert v._list_mode_display_var.get()==m.LIST_MODE_LABELS[mode]
for page in ('정보','AI 생성 판단','성인 필터','도구'):
    v.select_dock(page);pump()
    assert v._dock_page==page and len(v.paned.panes())==3 and v._dock_pages[page].winfo_ismapped()
assert not any(x in sys.modules for x in ('c2pa','onnxruntime','rawpy'))
v._activate_dock('정보');pump()
v._on_motion(SimpleNamespace(x=v.canvas.winfo_width()/2,y=v.canvas.winfo_height()/2))
assert '#2A5B92' in v.status.cget('text') and not hasattr(v,'_pixel_label')
v._on_motion(SimpleNamespace(x=-5000,y=-5000))
win,body=v._window('글자 인식');pump();assert str(win.master)==str(v._dock_tasks['도구'])
win.destroy()
v._text('인식된 글자','테스트 OCR 결과');pump();assert v._dock_page=='도구'
v._text('출처 정보 · C2PA','판별 불가');pump();assert v._dock_page=='AI 생성 판단'
v.hide_info_panel();v.set_workspace('editor');pump()
assert len(v.paned.panes())==2 and v._filmstrip is None
v.toolbar.mode_switch.event_generate('<Button-1>',x=25,y=20);pump();assert v._workspace_mode=='viewer'
v.toolbar.mode_switch.event_generate('<Button-1>',x=110,y=20);pump();assert v._workspace_mode=='editor'
v.enter_image_fullscreen();pump();assert not v._navigation_tasks.winfo_ismapped()
v.exit_image_fullscreen();pump();assert v._navigation_tasks.winfo_ismapped()
for theme in ('bright_sky_blue','croweyes_dark'):v.set_ui_theme(theme);pump()
assert not errors,errors
v._on_close()
print('PASS: short-grid scroll boundaries, list selectors, four dock pages, lazy models, status pixel hex, inline OCR/C2PA results, slide switch, themes/fullscreen')
