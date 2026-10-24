"""Filter transitions and UI layout cross-check without external desktop control."""
import importlib.util,sys,time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
from tkinter.font import Font
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
folder=ROOT/'tmp/ui-finish/one/two';folder.mkdir(parents=True,exist_ok=True)
for i in range(8):Image.new('RGB',(500,350),(42,91,146)).save(folder/f'{i}.png')
spec=importlib.util.spec_from_file_location('ui_finish',ROOT/'CrowEyes_Image_Viewer_2.0.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.load_settings=lambda:{**m.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[],'window_geometry':'1280x850'}
m.save_settings=lambda v:None
auto_register_original=m.CrowEyes20._auto_register_file_associations
m.CrowEyes20._auto_register_file_associations=lambda s:None
v=m.CrowEyes20(str(folder/'0.png'));errors=[];v.report_callback_exception=lambda *a:errors.append(str(a))
def pump(ms=160):
 end=time.monotonic()+ms/1000
 while time.monotonic()<end:v.update();time.sleep(.01)
def descendants(w):
 out=[]
 for c in w.winfo_children():out.append(c);out.extend(descendants(c))
 return out
def cards():return [w for w in v.winfo_children() if w.__class__.__name__=='FittedDialog']
pump(1200)
assert [b._croweyes_action for b in v._navigation_buttons]==['previous','next','up','refresh']
assert v._breadcrumb_targets[0].cget('text')=='내 컴퓨터'
assert all(w.cget('fg')=='#79BEFF' for w in v._breadcrumb_targets)
font=Font(root=v,font=m.ttk.Style(v).lookup('Brand.TLabel','font'))
assert font.actual('size')==20 and font.actual('weight')=='bold'
assert v._icons['eye'].height()==font.metrics('linespace')
assert Font(root=v,family='Segoe UI',size=9).measure(v._short_folder_name('아주 긴 한글 폴더 이름입니다'))<=64
v._on_motion(SimpleNamespace(x=v.canvas.winfo_width()/2,y=v.canvas.winfo_height()/2));pump()
assert '#2A5B92' in v.status.cget('text')
assert v._pixel_swatch.winfo_ismapped() and v._pixel_swatch.itemcget('color','fill')=='#2A5B92'
status_slot=v.status.master.winfo_width()
v.status.configure(text='일반 상태 메시지');pump()
assert not v._pixel_swatch.winfo_ismapped() and v.status.master.winfo_width()==status_slot
class Worker:
 def __init__(self):self.tasks=[];self.results=[]
 def submit(self,*a,**kw):self.tasks.append((a,kw))
 def clear_pending(self):self.tasks=[]
 def poll(self):r=self.results;self.results=[];return r
 def stop(self):pass
worker=Worker();v._safety_worker=worker
assert len(v._thumb_loaded)==8
photos=dict(v._thumb_photos);cells=dict(v._icon_cells)
v._playlist_selection={1,3};v._highlight_icon_selection()
def apply_filter(on):
 win=v.adult_filter_dialog();pump()
 widgets=descendants(win)
 next(w for w in widgets if w.__class__.__name__=='Radiobutton' and str(w.cget('text')).startswith('ON' if on else 'OFF')).invoke()
 next(w for w in widgets if w.__class__.__name__=='Button' and w.cget('text')=='적용').invoke()
 assert not win.winfo_exists()
apply_filter(True)
assert v._content_filter_mode=='explicit' and v._icon_cells==cells and v._playlist_selection=={1,3}
assert all(str(w.cget('image'))==str(v._placeholder_photo) for w in v._icon_cells.values())
on_generation=v._thumbnail_generation()
worker.results=[SimpleNamespace(kind='thumbnail',generation=on_generation,path=v.folder_files[1],result=SimpleNamespace(status=m.SAFE))]
v._poll_safety_worker();pump(80)
assert str(v._icon_cells[1].cget('image'))==str(photos[str(v.folder_files[1])])
apply_filter(False)
assert v._content_filter_mode=='off' and v._icon_cells==cells and v._playlist_selection=={1,3}
# Check before pumping: cached thumbs must already be visible with no gray flash.
assert all(str(v._icon_cells[i].cget('image'))==str(photos[str(p)]) for i,p in enumerate(v.folder_files))
worker.results=[SimpleNamespace(kind='thumbnail',generation=on_generation,path=v.folder_files[2],result=SimpleNamespace(status=m.BLOCKED))]
v._poll_safety_worker();pump(300)
assert all(str(v._icon_cells[i].cget('image'))==str(photos[str(p)]) for i,p in enumerate(v.folder_files))
# Re-applying OFF does no work and preserves the generation.
generation=v._playlist_gen;v._set_content_filter('off');assert v._playlist_gen==generation
# Deliberately hold a folder scan while toggling: image enumeration must survive.
from threading import Event
started=Event();release=Event()
def delayed_scan(path, show_hidden=False):
 started.set();release.wait(3)
 return sorted(folder.glob('*.png'))
with patch.object(m,'list_image_paths_fast',delayed_scan):
 v.open_folders([folder]);pump(100);assert started.is_set()
 scan_generation=v._playlist_gen
 v._set_content_filter('explicit');v._set_content_filter('off')
 assert v._playlist_gen==scan_generation
 release.set();pump(600)
 assert len(v.folder_files)==8 and v.display_image is not None
for geometry in ('1280x850','1000x700','800x600'):
 v.geometry(geometry);pump(220)
 for theme in ('croweyes_dark','bright_sky_blue','white_light_pink'):
  v.set_ui_theme(theme);pump(220)
  assert v._pixel_swatch.cget('bg')==v._theme()['panel_alt']
  for mode in ('viewer','editor'):
   v.set_workspace(mode);pump(180)
   for w in v._toolbar_buttons+v._navigation_buttons+list(v._navigation_tasks.winfo_children())+[v._brand_label,v.toolbar.mode_switch,v._breadcrumb_targets[0]]:
    assert w.winfo_ismapped()
    assert w.winfo_rootx()>=v.winfo_rootx() and w.winfo_rootx()+w.winfo_width()<=v.winfo_rootx()+v.winfo_width(),(geometry,theme,mode,str(w))
   assert v._brand_label.winfo_reqwidth()<=v._brand_label.winfo_width()
   assert v._brand_label.winfo_reqheight()<=v._brand_label.winfo_height(),(geometry,theme,mode,v._brand_label.winfo_reqheight(),v._brand_label.winfo_height())
   win=v._text('AI 생성 판단 · C2PA','파일: '+'아주긴사진이름'*20+'.png\n\nAI 기록: 판별 불가\n출처 기록: 없음\n검증: 확인 불가\n\n출처 정보 없음은 AI가 아니라는 뜻이 아닙니다.')
   pump()
   assert not any(w.__class__.__name__ in ('Scrollbar','Button') and (w.__class__.__name__=='Scrollbar' or w.cget('text') in ('이전','다음')) for w in descendants(win))
   assert win.winfo_reqheight()<=win.winfo_height(),(geometry,win.winfo_reqheight(),win.winfo_height())
   for w in descendants(win):
    if w.winfo_ismapped():
     assert w.winfo_rootx()+w.winfo_width()<=win.winfo_rootx()+win.winfo_width()+1
     assert w.winfo_rooty()+w.winfo_height()<=win.winfo_rooty()+win.winfo_height()+1
   win.destroy()
for theme in ('bright_sky_blue','white_light_pink','croweyes_dark'):
 v.set_ui_theme(theme);pump(180)
 for frame in (v.toolbar,v.toolbar.buttons,v.navigation_bar,v._breadcrumb_frame,v._breadcrumb_links,v._navigation_tasks):
  expected='Toolbar.TFrame' if frame in (v.toolbar,v.toolbar.buttons) else 'Chrome.TFrame'
  assert str(frame.cget('style'))==expected,(str(frame),frame.cget('style'))
  assert m.ttk.Style(v).lookup(frame.cget('style'),'background')==v._theme()['toolbar']
 assert v._breadcrumb_canvas.cget('bg')==v._theme()['toolbar']
 assert m.ttk.Style(v).lookup('Chrome.TLabel','background')==v._theme()['toolbar']
 for button in v._navigation_tasks.winfo_children():
  assert button.cget('style')=='Icon.Tool.TButton'
 for label in v._breadcrumb_links.winfo_children():
  if isinstance(label,m.ttk.Label):assert label.cget('style')=='Chrome.TLabel'
menu=v._workspace_menus['편집']
entries=[(menu.type(i),menu.entrycget(i,'label') if menu.type(i)!='separator' else '') for i in range(menu.index('end')+1)]
start=entries.index(('command','주석'));assert entries[start-1][0]=='separator'
assert [label for kind,label in entries[start:]]==['주석','형광펜','모자이크','편집 전후 비교']
assert sum(kind=='separator' for kind,label in entries)==4
assert sum(v._workspace_menus['정리'].type(i)=='separator' for i in range(v._workspace_menus['정리'].index('end')+1))==4
assert m.DEFAULT_SETTINGS['auto_check_updates'] and m.DEFAULT_SETTINGS['auto_register_associations']
with patch.object(v,'set_default_associations_when_unclaimed',return_value=(['.png'],['.jpg'])) as registrar:
 v.settings['association_extensions']=['.png','.jpg']
 auto_register_original(v)
 registrar.assert_called_once_with(['.png','.jpg'])
 assert v.settings['initial_associations_registered']
from PIL import ImageTk
ImageTk.getimage(v._icons['brand_wordmark']).save(ROOT/'tmp/brand-wordmark.png')
assert not errors,errors
v._on_close()
print('PASS: real filter setter closes ON/OFF card, immediate cached OFF thumbnails, selection/scroll widgets preserved, stale safety results ignored, no-op repeat, pixel color swatch, 20 bold outlined brand/logo height, four navigation actions, blue links, filter changes preserve active folder scan, 18 geometry/theme/mode UI bounds and one-page AI summaries')
