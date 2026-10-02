"""Editing, hostile-input, clipboard and GUI regression checks for v1.9e."""
import importlib.util
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from croweyes_editing import selection_box, validate_size, save_raster, validate_update_url

spec = importlib.util.spec_from_file_location('croweyes_v19e', ROOT/'CrowEyes_Image_Viewer_1.9e.py')
app = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = app
spec.loader.exec_module(app)
assert app.is_newer_version('v1.9e','1.9')
assert app.is_newer_version('v1.9e','1.9d')
assert not app.is_newer_version('v1.9e','1.9e')
assert app.is_newer_version('v1.10','1.9e')
assert not app.is_newer_version('v1.9','1.9e')
folder = ROOT/'tmp'/'v19e-check'
folder.mkdir(parents=True, exist_ok=True)

def rejects(fn, *args):
    try:
        fn(*args)
    except (ValueError, app.FormatSupportError):
        return
    raise AssertionError(f'Input was not rejected: {args}')

assert selection_box((75,75),(25,25),(0,0,100,100),(200,200)) == (50,50,150,150)
assert selection_box((-5,-5),(20,20),(0,0,100,100),(200,200)) == (0,0,40,40)
rejects(selection_box, (-20,-20),(-10,-10),(0,0,100,100),(200,200))
for size in ((0,10),(-1,1),(40000,1),(10000,10000)):
    rejects(validate_size, *size)
for url in ('file:///C:/test.exe', 'http://github.com/CrowScienceLab/CrowEyes/releases/download/v1/a',
            'https://github.com/evil/app/releases/download/v1/a', 'https://github.com.evil.test/a'):
    rejects(validate_update_url, url)
assert validate_update_url('https://github.com/CrowScienceLab/CrowEyes/releases/download/v1.9e/a.exe')
image = Image.new('RGBA', (200,100), (255,0,0,0))
image.putpixel((50,50), (12,34,56,255))
for suffix in ('.png','.jpg','.webp','.bmp','.tiff'):
    target = folder/f'export{suffix}'
    save_raster(image.resize((80,120)), target)
    with Image.open(target) as result:
        assert result.size == (80,120)
        if suffix in ('.jpg','.bmp'):
            assert min(result.convert('RGB').getpixel((0,0))) > 245
        if suffix == '.png':
            assert result.getpixel((0,0))[3] == 0
target = folder/'atomic.png'
target.write_bytes(b'preserve-me')
with patch.object(Image.Image, 'save', side_effect=OSError('simulated failure')):
    try:
        save_raster(image,target)
    except OSError:
        pass
assert target.read_bytes() == b'preserve-me'
assert not list(folder.glob('.croweyes-*'))
for text in ('<!DOCTYPE svg [<!ENTITY x "test">]><svg/>',
             '<svg xmlns="http://www.w3.org/2000/svg"><image href="file:///C:/secret"/></svg>',
             '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 inf 100"/>'):
    svg = folder/'unsafe.svg'
    svg.write_text(text, encoding='utf-8')
    rejects(app.inspect_svg, svg)
assert app.c2pa_ai_probability(ROOT/'test-assets/CrowEyes_C2PA_50pct_sample.jpg')[0] == 50

# Suppress only persisted settings/associations/network while using real Tk widgets.
settings = app.load_settings()
settings.update(auto_update_check=False, content_filter='off')
assert isinstance(app.is_microsoft_store_package(), bool)
with patch.object(app, 'load_settings', return_value=settings), patch.object(app, 'save_settings'), \
     patch.object(app.CrowEyesImageViewer, '_auto_register_file_associations'), \
     patch.object(app.CrowEyesImageViewer, 'check_for_updates'):
    viewer = app.CrowEyesImageViewer()
    viewer.withdraw()
    viewer.update()
    viewer.display_image = Image.new('RGBA', (200,100), 'red')
    viewer.zoom = 1.0
    viewer.redraw()
    viewer.update()
    bounds = viewer.canvas.bbox('display_image')
    assert bounds
    captured = []
    with patch.object(viewer, '_copy_pil_to_windows_clipboard', side_effect=lambda im: captured.append(im)), \
         patch.object(viewer, '_save_image_dialog', side_effect=lambda im,title: captured.append(im)):
        for action in ('copy','save'):
            viewer.start_region_copy(action)
            viewer._region_start = (bounds[0],bounds[1])
            viewer._finish_region_copy(bounds[0]+100,bounds[1]+50)
        assert [im.size for im in captured] == [(100,50),(100,50)]
    viewer.start_region_copy()
    viewer._escape()
    assert not viewer._region_copy_mode
    viewer.show_resize_dialog()
    viewer.update()
    dialogs = [w for w in viewer.winfo_children() if isinstance(w,app.tk.Toplevel)]
    assert dialogs
    dialog = dialogs[-1]
    frame = dialog.winfo_children()[0]
    entries = [w for w in frame.winfo_children() if isinstance(w,app.ttk.Entry)]
    entries[0].delete(0,'end')
    entries[0].insert(0,'80')
    assert entries[1].get() == '40', 'Aspect lock failed'
    lock = next(w for w in frame.winfo_children() if isinstance(w,app.ttk.Checkbutton))
    lock.invoke()
    entries[1].delete(0,'end')
    entries[1].insert(0,'120')
    assert entries[0].get() == '80', 'Unlocked dimensions interfered'
    destination = folder/'gui-resize.png'
    save_button = next(w for w in frame.winfo_children() if isinstance(w,app.ttk.Button) and '저장' in w.cget('text'))
    with patch.object(app.filedialog, 'asksaveasfilename', return_value=str(destination)):
        save_button.invoke()
    with Image.open(destination) as resized:
        assert resized.size == (80,120), 'GUI export dimensions are wrong'
    dialogs[-1].event_generate('<Escape>')
    viewer.update()
    viewer._on_close()
print('PASS: v1.9e crop/copy/save, non-proportional resize, alpha, atomic failure, bounds, SVG, update URL, C2PA, Tk dialog')
