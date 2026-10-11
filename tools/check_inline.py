"""Exercise crop-filled thumbnails and editing on the actual main Tk canvas."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys,time
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
folder=ROOT/'tmp/inline-test';folder.mkdir(parents=True,exist_ok=True)
for i in range(3):
    image=Image.new('RGB',(640,400),'#2266aa');draw=ImageDraw.Draw(image)
    for x in range(0,640,8):
        for y in range(0,400,8):draw.rectangle((x,y,x+7,y+7),fill=(x%256,y%256,(x+y)%256))
    image.save(folder/f'photo-{i}.png')
spec=importlib.util.spec_from_file_location('inline_test',ROOT/'CrowEyes_Image_Viewer_2.0.py')
module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
module.load_settings=lambda:{**module.DEFAULT_SETTINGS,'auto_check_updates':False,'auto_register_associations':False,'window_geometry':'1280x850'}
module.save_settings=lambda values:None
module.CrowEyes20._auto_register_file_associations=lambda self:None
viewer=module.CrowEyes20(str(folder/'photo-0.png'));errors=[]
viewer.report_callback_exception=lambda *args:errors.append(str(args))
def pump(ms=150):
    end=time.monotonic()+ms/1000
    while time.monotonic()<end:viewer.update();time.sleep(.01)
pump(1000);assert viewer.display_image is not None
for mode in ('viewer','editor','viewer','editor'):
    viewer.set_workspace(mode);pump()
    assert str(viewer.left_panel) in viewer.paned.panes() and len(viewer.paned.panes())==2
    assert viewer._editor_panel is None and viewer._filmstrip is None
    assert all(b.cget('style')=='Icon.Tool.TButton' for b in viewer._toolbar_buttons)
    assert viewer.style.lookup('Icon.Tool.TButton','background')==viewer._theme()['toolbar']
assert [b._croweyes_action for b in viewer._toolbar_buttons][-5:]==['annotation','highlight','mosaic','compare','save']
base=viewer.display_image.copy()
before=set(viewer.winfo_children())
for tool in ('주석','형광펜','모자이크'):
    viewer.select_edit_tool(tool);pump()
    assert set(viewer.winfo_children())==before
    x,y=viewer.canvas.winfo_width()/2,viewer.canvas.winfo_height()/2
    viewer._pan_start(SimpleNamespace(x=x-35,y=y-25))
    viewer._pan_move(SimpleNamespace(x=x+35,y=y+25))
    viewer._pan_end(SimpleNamespace(x=x+35,y=y+25));pump()
assert [op[0] for op in viewer._annotation_ops]==['화살표','형광펜','모자이크']
assert viewer.display_image.tobytes()!=base.tobytes()
viewer.undo_edit();assert len(viewer._annotation_ops)==2
viewer.redo_edit();assert len(viewer._annotation_ops)==3
viewer.rotate(90);pump();assert len(viewer._annotation_ops)==3 and viewer.display_image.size==(400,640)
viewer.undo_edit();assert viewer.rotation==0 and len(viewer._annotation_ops)==3
viewer.restore_original();assert not viewer._annotation_ops
viewer.undo_edit();assert len(viewer._annotation_ops)==3
viewer.end_edit_tool();viewer.select_edit_tool('밝기·대비');pump()
viewer.select_edit_tool('크기·비율');pump();viewer.end_edit_tool()
viewer.select_edit_tool('크기·비율');pump()
entries=[c for c in viewer._edit_parameters.winfo_children() if isinstance(c,module.ttk.Entry)]
sizes=[];original_save=viewer.quality_dialog
viewer.quality_dialog=lambda image=None,**kwargs:sizes.append(image.size)
for entry,value in zip(entries,('1280','800')):entry.delete(0,'end');entry.insert(0,value)
save=next(c for c in viewer._edit_parameters.winfo_children() if isinstance(c,module.ttk.Button) and c.cget('text')=='저장')
save.invoke();assert sizes[-1]==(1280,800)
next(c for c in viewer._edit_parameters.winfo_children() if isinstance(c,module.ttk.Checkbutton)).invoke()
for entry,value in zip(entries,('100','200')):entry.delete(0,'end');entry.insert(0,value)
save.invoke();assert sizes[-1]==(100,200)
viewer.quality_dialog=original_save;viewer.end_edit_tool()
viewer.geometry('800x600');pump()
assert max(b.winfo_rootx()+b.winfo_width() for b in viewer._toolbar_buttons)<=viewer.winfo_rootx()+viewer.winfo_width()
viewer.set_ui_theme('bright_sky_blue');pump()
assert all(b.cget('style')=='Icon.Tool.TButton' for b in viewer._toolbar_buttons)
viewer.set_ui_theme('croweyes_dark');pump()
for name,size in [('wide',(300,100)),('tall',(100,300))]:
    source=Image.new('RGB',size,'#ff0000');source.save(folder/f'{name}.png')
    thumb=viewer._make_thumb_pil(folder/f'{name}.png',72)
    assert thumb.size==(72,72) and thumb.getpixel((0,0))[3]==0
    assert all(thumb.getpixel(point)==(255,0,0,255) for point in ((36,2),(2,36),(69,36),(36,69)))
viewer.goto_index(1);pump(700);assert not viewer._annotation_ops
viewer._on_close();assert not errors,errors
print('PASS: filled thumbnails, stable themed editor icons, shared file list, no sidebar/filmstrip, inline separate annotation tools, integrated undo/redo, transforms, small window')
