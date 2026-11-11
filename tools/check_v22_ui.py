"""Real Tk regression for print controls and final brand/editor chrome."""
import importlib.util,sys,time
from pathlib import Path
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
folder=ROOT/'tmp/v22-ui';folder.mkdir(parents=True,exist_ok=True)
Image.new('RGB',(840,1188),'#48a5c4').save(folder/'poster.png')
spec=importlib.util.spec_from_file_location('v22_ui',ROOT/'CrowEyes_Image_Viewer_2.0.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.load_settings=lambda:{**m.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[],'window_geometry':'1200x850'}
m.save_settings=lambda s:None;m.CrowEyes20._auto_register_file_associations=lambda s:None
v=m.CrowEyes20(str(folder/'poster.png'));errors=[];v.report_callback_exception=lambda *a:errors.append(str(a))
def pump(ms=200):
 end=time.monotonic()+ms/1000
 while time.monotonic()<end:v.update();time.sleep(.01)
def descendants(w):
 return [c for child in w.winfo_children() for c in [child,*descendants(child)]]
try:
 pump(800)
 win=m.PrintPreview(v);win.geometry('1000x600');pump(300)
 actions=[w for w in descendants(win) if w.__class__.__name__=='Button' and w.cget('text') in ('인쇄','닫기')]
 assert len(actions)==2
 for b in actions:assert b.winfo_ismapped() and b.winfo_rooty()+b.winfo_height()<=win.winfo_rooty()+win.winfo_height(), '인쇄/닫기 버튼이 창 아래로 잘림'
 assert hasattr(win,'percent_var') and hasattr(win,'margins_vars') and hasattr(win,'tiles_var')
 tabs=next(w for w in descendants(win) if w.__class__.__name__=='Notebook')
 for tab in tabs.tabs():
  tabs.select(tab);pump()
  for child in descendants(win.nametowidget(tab)):
   if child.__class__.__name__=='Label' and child.winfo_ismapped():
    assert child.winfo_height()>=child.winfo_reqheight(),f'잘린 인쇄 설명: {child.cget("text")}'
 for tiles in (1,2,4):
  win.tiles_var.set(tiles);win.redraw_preview();pump()
  assert len(win.preview.find_withtag('paper'))==tiles
  if tiles>1:assert win.preview.find_withtag('split_line')
 with patch.object(v,'_print_with_options',return_value=False) as do:
  win.percent_var.set(125);win.scale_var.set('percent');win.tiles_var.set(4);win.do_print()
  assert do.call_args.kwargs['scale_percent']==125 and do.call_args.kwargs['tiles']==4
 win.destroy();v.set_workspace('editor');pump()
 assert 'print' in [b._croweyes_action for b in v._toolbar_buttons]
 from tkinter.font import Font
 assert Font(v,font=__import__('tkinter').ttk.Style(v).lookup('Brand.TLabel','font')).actual('weight')=='normal'
 from croweyes_onboarding import show_store_onboarding
 def button(win,text):return next(w for w in descendants(win) if w.__class__.__name__=='Button' and w.cget('text')==text)
 v.settings.pop('store_onboarding_complete',None)
 intro=show_store_onboarding(v);pump()
 with patch('croweyes_onboarding.create_store_shortcut',side_effect=OSError('test failure')):
  button(intro,'바로가기 추가').invoke()
  assert intro.winfo_exists() and not v.settings.get('store_onboarding_complete')
 with patch('croweyes_onboarding.create_store_shortcut') as create:
  button(intro,'바로가기 추가').invoke();create.assert_called_once()
 assert v.settings['store_onboarding_complete'] and show_store_onboarding(v) is None
 v.settings['store_onboarding_complete']=False
 intro=show_store_onboarding(v)
 with patch('croweyes_onboarding.create_store_shortcut') as create:
  button(intro,'추가하지 않음').invoke();create.assert_not_called()
 assert v.settings['store_onboarding_complete'] and not v.settings['store_desktop_shortcut_requested']
 from croweyes_updates import UpdateCoordinator
 coordinator=UpdateCoordinator(v);coordinator.generation=7
 results={'github':dict(status='ok',version='2.1.0'),'store_feed':dict(status='error',error='test'), 'store_catalog':dict(status='ok')}
 with patch('croweyes_updates.messagebox.showinfo') as notice:
  coordinator._poll(7,True,False,results,0)
  assert '최신 버전입니다' not in notice.call_args.args[1]
 assert not errors,errors
 print('PASS: print footer/scale/margins/tiles, normal brand/editor print, Store first-run accept/decline/retry, partial update failures')
finally:v.destroy()
