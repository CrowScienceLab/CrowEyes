"""Real widget events, combined index/search and steady canvas across modes."""
import importlib.util,sys,time
from pathlib import Path
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
folder=ROOT/'tmp/search-review/one/two';folder.mkdir(parents=True,exist_ok=True)
for i in range(8):Image.new('RGB',(600,400),(50+i*10,100,160)).save(folder/f'{i}.png')
spec=importlib.util.spec_from_file_location('search_review',ROOT/'CrowEyes_Image_Viewer_2.0.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.load_settings=lambda:{**m.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[],'window_geometry':'1280x850'}
m.save_settings=lambda v:None;m.CrowEyes20._auto_register_file_associations=lambda s:None
v=m.CrowEyes20(str(folder/'0.png'));errors=[]
v.report_callback_exception=lambda *args:errors.append(str(args))
def pump(ms=160):
    end=time.monotonic()+ms/1000
    while time.monotonic()<end:v.update();time.sleep(.01)
pump(1200)
assert [b._croweyes_action for b in v._navigation_tasks.winfo_children()]==['ai_generated','shield','ocr_region','index']
assert '정보' not in v._dock_tab_buttons and '도구' not in v._dock_tab_buttons
assert v._breadcrumb_targets[0].cget('image')
assert [b._croweyes_target for b in v._breadcrumb_targets[1:]]==list(reversed((folder,*folder.parents)))
with patch.object(v,'_navigate_playlist_folder') as navigate:
    v._breadcrumb_targets[-2]._croweyes_command();navigate.assert_called_once_with(folder.parent)
def click(i,state=0):
    cell=v._icon_cells[i]
    cell.event_generate('<ButtonPress-1>',x=20,y=20,state=state)
    cell.event_generate('<ButtonRelease-1>',x=20,y=20,state=state)
    pump()
click(0);click(2,4);assert v._playlist_selection=={0,2},v._playlist_selection
click(5,1);assert v._playlist_selection=={2,3,4,5},v._playlist_selection
click(3,4);assert v._playlist_selection=={2,4,5},v._playlist_selection
assert len(v._selected_playlist_paths())==3
for geometry in ('1280x850','800x600'):
    v.geometry(geometry);pump(350)
    seen=[];binding=v.canvas.bind('<Configure>',lambda e:seen.append((e.width,e.height)),add='+')
    size=(v.canvas.winfo_width(),v.canvas.winfo_height());zoom=v.zoom;panes=tuple(v.paned.panes());sash=v.paned.sashpos(0)
    for mode in ('editor','viewer','editor','viewer'):
        v.set_workspace(mode);pump(200)
        assert (v.canvas.winfo_width(),v.canvas.winfo_height())==size,(geometry,size,seen)
        assert v.zoom==zoom and tuple(v.paned.panes())==panes and v.paned.sashpos(0)==sash
    v.canvas.unbind('<Configure>',binding)
    assert not seen,(geometry,seen)
from croweyes_workflows import Catalog
v._catalog=Catalog(ROOT/'tmp/search-review/catalog.sqlite3')
with patch('croweyes_ocr.recognize',side_effect=lambda image,cancel:'학교 공지 회의'),patch('croweyes_workflows.metadata',return_value={'DateTimeOriginal':'2026:10:11 10:30:00'}):
    v.index_all();pump(900)
assert len(v._catalog.all())==8
assert all(row['text']=='학교 공지 회의' and row['taken'].startswith('2026:10:11') for row in v._catalog.all().values())
with patch('croweyes_ocr.recognize',side_effect=AssertionError('unchanged file reindexed')):
    v.index_all();pump(800)
assert not v._tool_cancels
for query,count in [('학교',8),('2026-10-11',8),('공지 2026/10',8),('0.png',1),('없는글자',0)]:
    v._search_var.set(query);v._apply_playlist_filter();pump()
    assert len(v._visible_playlist_indices())==count,(query,v._visible_playlist_indices())
v._search_var.set('');v._apply_playlist_filter();pump()
target=v.folder_files[0]
v._playlist_selection={0}
with patch('croweyes_tools_ui.messagebox.askyesno',return_value=True):
    v.delete_index_dialog();pump()
    surface=next(w for w in v.winfo_children() if w.__class__.__name__=='FittedDialog' and any(c.__class__.__name__=='Radiobutton' for c in w.body.winfo_children()))
    options=[w for w in surface.body.winfo_children() if w.__class__.__name__=='Radiobutton']
    next(w for w in options if w.cget('value')=='selected').invoke()
    next(w for w in surface.body.winfo_children() if w.__class__.__name__=='Button').invoke();pump()
assert len(v._catalog.all())==7 and target.exists()
missing=ROOT/'tmp/search-review/missing.png';v._catalog.set(missing,text='old')
assert v._catalog.delete(missing=True)==1
assert v._catalog.delete()==7 and all(p.exists() for p in v.folder_files)
assert not errors,errors
v._on_close()
print('PASS: clickable breadcrumb, real Ctrl/Shift grid selection, four icons, no canvas resize during mode switches, combined index/cache, unified name/OCR/date search, scoped index deletion')
