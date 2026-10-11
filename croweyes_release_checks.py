"""Executable self-test; writes an explicit report and exits without the viewer."""
import json
import sys
import threading
from pathlib import Path
from PIL import Image


def run_workspace(viewer_type,report_path):
    """Exercise the frozen Tk workspace without OS input or user settings."""
    import time
    from unittest.mock import patch
    report=Path(report_path);report.parent.mkdir(parents=True,exist_ok=True)
    module=sys.modules[viewer_type.__module__]
    folder=report.parent/'workspace-images';folder.mkdir(exist_ok=True)
    for i in range(6):Image.new('RGB',(640,400),(40+i*20,90,140)).save(folder/f'photo-{i}.png')
    viewer=None;errors=[]
    results={}
    try:
        with patch.object(module,'load_settings',lambda:{**module.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[],'window_geometry':'1100x800'}),patch.object(module,'save_settings',lambda values:None),patch.object(viewer_type,'_auto_register_file_associations',lambda self:None):
            viewer=viewer_type(str(folder/'photo-0.png'))
            viewer.report_callback_exception=lambda *args:errors.append(str(args))
            def pump(ms):
                end=time.monotonic()+ms/1000
                while time.monotonic()<end:viewer.update();time.sleep(.01)
            pump(1200)
            assert viewer.display_image is not None
            viewer.rotate(90);pump(100);viewer.zoom_by(1.3)
            state=viewer._state();zoom=viewer.zoom
            viewer.set_workspace('editor');pump(600)
            assert str(viewer.left_panel) in viewer.paned.panes() and viewer._editor_panel is None and viewer._filmstrip is None
            assert viewer._state()==state and viewer.zoom==zoom
            viewer.set_workspace('viewer');pump(200)
            assert len(viewer.paned.panes())==2 and viewer._state()==state
            assert list(viewer._workspace_menus)==['파일','보기','편집','정리','도구','설정']
            viewer.geometry('800x600');viewer.set_workspace('editor');pump(400)
            assert viewer.toolbar.winfo_reqheight()<250
            assert not viewer._info_visible and viewer._info_tab.winfo_ismapped()
            viewer.toggle_info_panel();pump(100);assert len(viewer.paned.panes())==3
            viewer.toggle_info_panel();pump(100);assert len(viewer.paned.panes())==2
            assert all(not b.cget('text') for b in viewer._toolbar_buttons)
            assert [b._croweyes_action for b in viewer._toolbar_buttons][-5:]==['annotation','highlight','mosaic','compare','save']
            assert all(b.cget('style')=='Icon.Tool.TButton' for b in viewer._toolbar_buttons)
            viewer.select_edit_tool('형광펜');pump(100)
            from types import SimpleNamespace
            x,y=viewer.canvas.winfo_width()/2,viewer.canvas.winfo_height()/2
            viewer._pan_start(SimpleNamespace(x=x-20,y=y-20));viewer._pan_end(SimpleNamespace(x=x+20,y=y+20))
            assert len(viewer._annotation_ops)==1
            viewer.undo_edit();assert not viewer._annotation_ops
            viewer.redo_edit();assert len(viewer._annotation_ops)==1
            viewer.end_edit_tool()
            thumbnail=viewer._make_thumb_pil(folder/'photo-0.png',72)
            assert thumbnail.size==(72,72) and thumbnail.getpixel((0,0))[3]==0
            dialog=viewer._text('OCR 결과','test');pump(100)
            assert dialog.winfo_toplevel() is viewer and dialog.winfo_rootx()>viewer.winfo_rootx()
            assert str(dialog.master)==str(viewer._dock_tasks['도구'])
            dialog.destroy()
            for page in ('정보','AI 생성 판단','성인 필터','도구'):
                viewer._activate_dock(page);pump(100)
                assert len(viewer.paned.panes())==3 and viewer._dock_pages[page].winfo_ismapped()
            viewer._activate_dock('정보');pump(100)
            viewer._on_motion(SimpleNamespace(x=viewer.canvas.winfo_width()/2,y=viewer.canvas.winfo_height()/2))
            assert 'RGB' in viewer._pixel_label.cget('text')
            viewer.set_list_mode('icons');pump(200)
            for _ in range(30):viewer._on_grid_wheel(SimpleNamespace(delta=120))
            pump(100);assert abs(viewer._grid_canvas.canvasy(0))<2
            assert not hasattr(viewer,'semantic_dialog') and not hasattr(viewer,'catalog_dialog')
            assert not [n for n in ('c2pa','numpy','onnxruntime','tokenizers') if n in sys.modules]
            viewer._on_close();viewer=None
            assert not errors,errors
        results=dict(status='PASS',checks=['frozen viewer/editor','state retention','shared file list','inline highlight and undo/redo','six menus','800x600 bounds','four right dock pages','inline OCR results','pixel RGB','grid scroll boundary','no heavy imports'],callback_errors=errors)
    except Exception as exc:
        import traceback
        results=dict(status='FAIL',error=str(exc),traceback=traceback.format_exc(),callback_errors=errors)
        if viewer:viewer.destroy()
    report.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if results['status']=='PASS' else 1


def run(report_path, modules=None):
    report=Path(report_path)
    report.parent.mkdir(parents=True,exist_ok=True)
    results={}
    try:
        results['startup_heavy_modules']=[m for m in ('c2pa','numpy','onnxruntime','tokenizers') if m in sys.modules]
        assert not results['startup_heavy_modules']
        from croweyes_workflows import encode,atomic_write,Catalog
        image=Image.new('RGB',(120,80),'red')
        target=report.parent/'test.png'
        atomic_write(target,encode(image,'.png'))
        assert Image.open(target).size==(120,80)
        from croweyes_ocr import recognize
        results['ocr_runtime']=recognize(image)
        results['core']='PASS'
        from croweyes_workflows import open_image
        if (report.parent/'heic.heic').exists():
            assert open_image(report.parent/'heic.heic').size==(120,80)
            results['native_heic']='PASS'
        from croweyes_extensions import bundled
        if modules or all(bundled(k) for k in ('provenance','safety','formats')):
            from croweyes_extensions import install,manifest,load_optional,model_path
            if modules:
                for kind,entry in manifest().items():
                    install(Path(modules)/entry['filename'],kind)
            from croweyes_provenance import inspect
            results['c2pa']=inspect(target)
            assert results['c2pa']['credential']=='없음'
            from croweyes_safety import SafetyManager
            manager=SafetyManager(model_path(),report.parent/'safety.sqlite')
            result=manager.prepare_model()
            assert manager.model_loaded, result.detail
            classified=manager.check(target)
            assert classified.status!='ERROR', classified.detail
            results['safety']='PASS'
            from croweyes_workflows import open_image
            load_optional('formats','rawpy')
            if (report.parent/'sample.CR2').exists():
                assert open_image(report.parent/'sample.CR2').size==(1936,1288)
            results['formats']='PASS'
            results['bundled_features']=[k for k in ('provenance','safety','formats') if bundled(k)]
        results['status']='PASS'
        code=0
    except Exception as exc:
        import traceback
        results.update(status='FAIL',error=str(exc),traceback=traceback.format_exc())
        code=1
    report.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
