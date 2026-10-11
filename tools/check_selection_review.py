"""Latest review: actual rubber-band events, cursor, internal cards and toolbar."""
import importlib.util,sys,time
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
folder=ROOT/'tmp/selection-review';folder.mkdir(parents=True,exist_ok=True)
for i in range(8):Image.new('RGB',(500,350),(50+i*10,100,160)).save(folder/f'{i}.png')
spec=importlib.util.spec_from_file_location('selection_review',ROOT/'CrowEyes_Image_Viewer_2.0.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.load_settings=lambda:{**m.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[],'window_geometry':'1280x850'}
m.save_settings=lambda v:None;m.CrowEyes20._auto_register_file_associations=lambda s:None
v=m.CrowEyes20(str(folder/'0.png'));errors=[];v.report_callback_exception=lambda *a:errors.append(str(a))
def pump(ms=180):
 end=time.monotonic()+ms/1000
 while time.monotonic()<end:v.update();time.sleep(.01)
pump(1000)
assert len(v.paned.panes())==2
assert '21' in str(m.ttk.Style(v).lookup('Brand.TLabel','font'))
for w in v._breadcrumb_targets:
 assert int(w.cget('borderwidth'))==0 and w.cget('bg')==v._theme()['toolbar'],(w.cget('borderwidth'),w.cget('bg'),v._theme()['toolbar'])
w=v._breadcrumb_targets[-1];w.event_generate('<Enter>');pump();assert 'underline' in str(w.cget('font'))
w.event_generate('<Leave>');pump();assert 'underline' not in str(w.cget('font'))
assert [b._croweyes_action for b in v._toolbar_buttons][-4:]==['play','print','compare','info']
with patch.object(v,'_job') as job:
 v._navigation_tasks.winfo_children()[0].invoke()
 assert job.call_count==1
 job.call_args.args[2]({'ai':'판별 불가','credential':'없음','validation':'확인 불가'})
pump()
cards=lambda:[w for w in v.winfo_children() if w.__class__.__name__=='FittedDialog']
assert cards() and len(v.paned.panes())==2
for w in cards():w.destroy()
with patch.object(v,'_set_content_filter') as apply:
 v._navigation_tasks.winfo_children()[1].invoke();pump()
 win=cards()[-1]
 def allchildren(w):
  result=[]
  for c in w.winfo_children():result.append(c);result.extend(allchildren(c))
  return result
 widgets=allchildren(win)
 radios=[w for w in widgets if w.__class__.__name__=='Radiobutton'];assert len(radios)==2
 radios[0].invoke()
 next(w for w in widgets if w.__class__.__name__=='Button' and w.cget('text')=='적용').invoke()
 apply.assert_called_once_with('explicit')
assert len(v.paned.panes())==2
v.ocr_region();assert 'region-ocr.cur' in v.canvas.cget('cursor'),v.canvas.cget('cursor')
x,y=v.canvas.winfo_width()//2,v.canvas.winfo_height()//2
v._pan_start(SimpleNamespace(x=x-50,y=y-50));v._pan_move(SimpleNamespace(x=x+50,y=y+50))
assert float(v.canvas.itemcget(v._region_rect,'width'))==3
assert v.canvas.find_withtag('region_outline')
with patch.object(v,'_job') as job:
 v._pan_end(SimpleNamespace(x=x+50,y=y+50));assert job.call_count==1
 job.call_args.args[2]('영역 OCR 결과')
pump();assert cards() and len(v.paned.panes())==2
for w in cards():w.destroy()
assert not v.canvas.find_withtag('region_outline') and v.canvas.cget('cursor')=='arrow'
v._text('정보 색인 결과','등록 8개\n변경 없음 0개\n촬영일과 OCR 등록 완료');pump()
win=cards()[-1];assert not any(w.__class__.__name__=='Scrollbar' for w in allchildren(win))
assert not any(w.__class__.__name__=='Button' and w.cget('text')=='전체 복사' for w in allchildren(win))
assert win.winfo_reqheight()<=win.winfo_height();win.destroy()
# Start in blank gutter and drag across two rows via actual Tk widget events.
gc=v._grid_canvas;inner=v._grid_inner
cells=[v._icon_cells[i] for i in range(8)]
sx=1;sy=1
ex=cells[1].winfo_rootx()-inner.winfo_rootx()+cells[1].winfo_width()-1
ey=cells[5].winfo_rooty()-inner.winfo_rooty()+cells[5].winfo_height()-1
inner.event_generate('<ButtonPress-1>',x=sx,y=sy)
inner.event_generate('<B1-Motion>',x=ex,y=ey);pump()
assert v._playlist_selection=={0,1,4,5},v._playlist_selection
inner.event_generate('<ButtonRelease-1>',x=ex,y=ey);pump()
assert not gc.find_withtag('selection_band')
assert all(v._icon_cells[i].cget('highlightbackground')=='#32B9FF' for i in v._playlist_selection)
assert all(int(w.cget('highlightthickness'))==3 for w in v._icon_cells.values())
assert len({w.winfo_reqwidth() for w in v._icon_cells.values()})==1
# Small screens: cards remain inside CrowEyes and modes retain the canvas.
v.geometry('800x600');pump(300)
for method in (v.adult_filter_dialog,lambda:v._text('정보 색인 결과','등록 8개\n완료')):
 method();pump();win=cards()[-1]
 assert win.winfo_x()>=0 and win.winfo_y()>=0 and win.winfo_x()+win.winfo_width()<=v.winfo_width()
 assert win.winfo_reqheight()<=win.winfo_height();win.destroy()
assert not errors,errors
v._on_close()
print('PASS: plain breadcrumb hover, 21 regular brand, print order, immediate AI inspection, internal adult/OCR/index cards, native custom OCR cursor, high contrast selection, actual drag rectangle multi-selection, 800x600 fit')



