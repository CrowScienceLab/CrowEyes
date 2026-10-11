"""Check the single navigation row, four-column defaults and fitted settings."""
import importlib.util,sys,time,json
from pathlib import Path
from PIL import Image
from tkinter import ttk
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
folder=ROOT/'tmp/review-layout';folder.mkdir(parents=True,exist_ok=True)
for i in range(12):Image.new('RGB',(640,400),(30+i*8,90,140)).save(folder/f'{i:02}.png')
spec=importlib.util.spec_from_file_location('review_layout',ROOT/'CrowEyes_Image_Viewer_2.0.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.SETTINGS_PATH=folder/'settings.json'
m.SETTINGS_PATH.write_text(json.dumps({'design_generation':10,'list_mode':'small'}))
migrated=m.load_settings();assert migrated['list_mode']=='icons' and migrated['design_generation']==11
m.SETTINGS_PATH.write_text(json.dumps({'design_generation':11,'list_mode':'names'}))
assert m.load_settings()['list_mode']=='names'
m.load_settings=lambda:{**m.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[],'window_geometry':'1280x850'}
m.save_settings=lambda values:None;m.CrowEyes20._auto_register_file_associations=lambda s:None
v=m.CrowEyes20(str(folder/'00.png'));errors=[]
v.report_callback_exception=lambda *args:errors.append(str(args))
def pump(ms=180):
    end=time.monotonic()+ms/1000
    while time.monotonic()<end:v.update();time.sleep(.01)
def visit(widget):
    for child in widget.winfo_children():
        yield child
        yield from visit(child)
pump(1200)
assert v.list_mode=='icons'
assert {int(w.grid_info()['column']) for w in v._icon_grid_order}=={0,1,2,3}
font=v.tk.splitlist(v.style.lookup('Brand.TLabel','font'))
assert '23' in font and 'bold' in font and str(v._brand_label.cget('style'))=='Brand.TLabel',font
assert not hasattr(v,'_dock_tabs') and not hasattr(v,'_info_tab') and not hasattr(v,'_pixel_label')
v._activate_dock('정보');pump()
info=v.info_text.get('1.0','end')
assert '출처' not in info and 'AI 생성' not in info,info
v.set_workspace('editor');pump();assert not v._info_visible and len(v.paned.panes())==2
for width,height in [(1280,850),(800,600)]:
    v.geometry(f'{width}x{height}');pump()
    for name,b in v._dock_tab_buttons.items():
        assert b.winfo_ismapped()
        assert b.winfo_rootx()+b.winfo_width()<=v.winfo_rootx()+v.winfo_width(),name
    assert len({b.winfo_y() for b in v._dock_tab_buttons.values()})==1
    for action in (v.show_preferences,v.performance_dialog,v.extensions_dialog):
        action();pump()
        dialogs=[w for w in v.winfo_children() if w.__class__.__name__=='FittedDialog']
        assert len(dialogs)==1
        d=dialogs[0];children=list(visit(d))
        assert not any(isinstance(w,ttk.Scrollbar) for w in children)
        assert d.winfo_rootx()>=v.winfo_rootx() and d.winfo_rooty()>=v.winfo_rooty()
        assert d.winfo_rootx()+d.winfo_width()<=v.winfo_rootx()+v.winfo_width()
        assert d.winfo_rooty()+d.winfo_height()<=v.winfo_rooty()+v.winfo_height()
        for w in children:
            if w.winfo_ismapped() and isinstance(w,(ttk.Button,ttk.Combobox,ttk.Label,ttk.Checkbutton,ttk.Radiobutton)):
                assert w.winfo_rootx()+w.winfo_width()<=d.winfo_rootx()+d.winfo_width()+1,(action.__name__,w.cget('text') if 'text' in w.keys() else str(w),'width')
                assert w.winfo_rooty()+w.winfo_height()<=d.winfo_rooty()+d.winfo_height()+1,(action.__name__,str(w),'height')
            if isinstance(w,ttk.Combobox):
                v.tk.call(w.cget('postcommand'))
        if action==v.show_preferences:
            combos=[w for w in children if isinstance(w,ttk.Combobox)]
            assert len(combos)==2 and combos[0].cget('style')!=combos[1].cget('style')
        if action==v.extensions_dialog:
            text=' '.join(w.cget('text') for w in children if isinstance(w,ttk.Label))
            assert all(term in text for term in ('C2PA','RAW','OCR','Ctrl+O','Ctrl+Z','F8','F11'))
        print(f'PASS {width}x{height}: {action.__name__} {d.winfo_width()}x{d.winfo_height()}')
        d.destroy();pump(30)
assert not errors,errors
assert not any(n in sys.modules for n in ('c2pa','onnxruntime','rawpy'))
v._on_close()
print('PASS: profile migration, four columns, brand font, one navigation row, editor closes third column, no duplicate info, fitted settings and colored selectors')
