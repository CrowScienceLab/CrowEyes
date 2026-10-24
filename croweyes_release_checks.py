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
            assert [b._croweyes_action for b in viewer._navigation_tasks.winfo_children()]==['ai_generated','shield','ocr_region','index']
            assert viewer._breadcrumb_targets[0].cget('image')
            for i,state in [(0,0),(2,4),(4,1)]:
                cell=viewer._icon_cells[i]
                cell.event_generate('<ButtonPress-1>',x=15,y=15,state=state)
                cell.event_generate('<ButtonRelease-1>',x=15,y=15,state=state)
                pump(160)
            assert viewer._playlist_selection=={2,3,4}
            assert [b._croweyes_action for b in viewer._toolbar_buttons][-4:]==['play','print','compare','info']
            for link in viewer._breadcrumb_targets:
                assert int(link.cget('borderwidth'))==0 and link.cget('bg')==viewer._theme()['toolbar']
            inner=viewer._grid_inner
            cell=viewer._icon_cells[5]
            ex=cell.winfo_rootx()-inner.winfo_rootx()+cell.winfo_width()-1
            ey=cell.winfo_rooty()-inner.winfo_rooty()+cell.winfo_height()-1
            inner.event_generate('<ButtonPress-1>',x=1,y=1)
            inner.event_generate('<B1-Motion>',x=ex,y=ey);pump(100)
            inner.event_generate('<ButtonRelease-1>',x=ex,y=ey);pump(100)
            assert viewer._playlist_selection=={0,1,4,5}
            assert all(viewer._icon_cells[i].cget('highlightbackground')=='#32B9FF' for i in viewer._playlist_selection)
            viewer.ocr_region()
            assert 'region-ocr.cur' in viewer.canvas.cget('cursor')
            viewer._cancel_region_copy()
            win=viewer.adult_filter_dialog();pump(100)
            assert win.master is viewer and len(viewer.paned.panes())==2
            win.destroy()
            win=viewer._text('정보 색인 결과','등록 6개\\n완료');pump(100)
            assert win.winfo_reqheight()<=win.winfo_height()
            assert not any(w.__class__.__name__=='Scrollbar' for w in win.body.winfo_children())
            win.destroy()
            viewer.goto_index(0);pump(200)
            changes=[]
            binding=viewer.canvas.bind('<Configure>',lambda e:changes.append((e.width,e.height)),add='+')
            size=(viewer.canvas.winfo_width(),viewer.canvas.winfo_height());zoom=viewer.zoom
            for mode in ('editor','viewer','editor','viewer'):
                viewer.set_workspace(mode);pump(180)
                assert (viewer.canvas.winfo_width(),viewer.canvas.winfo_height())==size and viewer.zoom==zoom
            viewer.canvas.unbind('<Configure>',binding)
            assert not changes,changes
            assert viewer.list_mode=='icons'
            assert {int(w.grid_info()['column']) for w in viewer._icon_grid_order}=={0,1,2,3}
            assert not hasattr(viewer,'_info_tab') and not hasattr(viewer,'_pixel_label')
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
            assert not viewer._info_visible and viewer._navigation_tasks.winfo_ismapped()
            viewer.toggle_info_panel();pump(100);assert len(viewer.paned.panes())==3
            viewer.toggle_info_panel();pump(100);assert len(viewer.paned.panes())==2
            for action in (viewer.show_preferences,viewer.performance_dialog,viewer.extensions_dialog):
                action();pump(150)
                fitted=[w for w in viewer.winfo_children() if w.__class__.__name__=='FittedDialog']
                assert len(fitted)==1
                window=fitted[0]
                assert window.winfo_rooty()+window.winfo_height()<=viewer.winfo_rooty()+viewer.winfo_height()
                window.destroy()
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
            assert dialog.master is viewer and dialog.__class__.__name__=='FittedDialog'
            dialog.destroy()
            for page in ('정보','AI 생성 판단','성인 필터','도구'):
                viewer._activate_dock(page);pump(100)
                assert len(viewer.paned.panes())==3 and viewer._dock_pages[page].winfo_ismapped()
            viewer._activate_dock('정보');pump(100)
            viewer._on_motion(SimpleNamespace(x=viewer.canvas.winfo_width()/2,y=viewer.canvas.winfo_height()/2))
            assert 'Pixel' in viewer.status.cget('text') and not hasattr(viewer,'_pixel_label')
            viewer.set_list_mode('icons');pump(200)
            for _ in range(30):viewer._on_grid_wheel(SimpleNamespace(delta=120))
            pump(100);assert abs(viewer._grid_canvas.canvasy(0))<2
            assert not hasattr(viewer,'semantic_dialog') and not hasattr(viewer,'catalog_dialog')
            assert not [n for n in ('c2pa','numpy','onnxruntime','tokenizers') if n in sys.modules]
            # Exercise the real bundled filter, including the previously failing ON placement.
            viewer.hide_info_panel();viewer.set_workspace('viewer');pump(500)
            before=dict(viewer._thumb_photos)
            assert all(str(path) in before for path in viewer.folder_files)
            from tkinter.font import Font
            font=Font(root=viewer,font=module.ttk.Style(viewer).lookup('Brand.TLabel','font'))
            assert font.actual('size')==20 and font.actual('weight')=='bold'
            assert viewer._icons['eye'].height()==font.metrics('linespace')
            assert [b._croweyes_action for b in viewer._navigation_buttons]==['previous','next','up','refresh']
            win=viewer._text('AI 생성 판단 · C2PA','파일: photo-0.png\\nAI 기록: 판별 불가\\n출처 기록: 없음\\n검증: 확인 불가\\n출처 정보 없음은 AI가 아니라는 뜻이 아닙니다.');pump(100)
            assert not any(w.__class__.__name__=='Button' and w.cget('text') in ('이전','다음') for w in win.body.winfo_children())
            assert win.winfo_reqheight()<=win.winfo_height();win.destroy()
            def children(w):
                out=[]
                for c in w.winfo_children():out.append(c);out.extend(children(c))
                return out
            win=viewer.adult_filter_dialog();pump(100)
            widgets=children(win)
            next(w for w in widgets if w.__class__.__name__=='Radiobutton' and w.cget('text').startswith('ON')).invoke()
            next(w for w in widgets if w.__class__.__name__=='Button' and w.cget('text')=='적용').invoke()
            assert not win.winfo_exists() and viewer._content_filter_mode=='explicit'
            deadline=time.monotonic()+12
            while viewer.display_image is None and time.monotonic()<deadline:pump(100)
            assert viewer._content_safety_status==module.SAFE and viewer.display_image is not None
            win=viewer.adult_filter_dialog();pump(100)
            widgets=children(win)
            next(w for w in widgets if w.__class__.__name__=='Radiobutton' and w.cget('text').startswith('OFF')).invoke()
            next(w for w in widgets if w.__class__.__name__=='Button' and w.cget('text')=='적용').invoke()
            assert not win.winfo_exists() and viewer._content_filter_mode=='off'
            assert all(str(viewer._icon_cells[i].cget('image'))==str(before[str(path)]) for i,path in enumerate(viewer.folder_files))
            pump(200)
            viewer._on_motion(SimpleNamespace(x=viewer.canvas.winfo_width()/2,y=viewer.canvas.winfo_height()/2));pump(100)
            assert viewer._pixel_swatch.winfo_ismapped()
            assert viewer._pixel_swatch.itemcget('color','fill') in viewer.status.cget('text')
            # 2.1 packaged integration: native attributes, menus and list refresh.
            assert viewer._browser_sort_menu.index('end') is not None
            assert viewer._browser_view_menu.index('end') is not None
            from croweyes_files import is_hidden
            hidden_sample=viewer.folder_files[-1]
            viewer.change_hidden([hidden_sample],True);pump(500)
            assert is_hidden(hidden_sample) and hidden_sample not in viewer.folder_files
            viewer._show_hidden_var.set(True);viewer.toggle_show_hidden();pump(500)
            assert hidden_sample in viewer.folder_files
            viewer.change_hidden([hidden_sample],False);pump(500)
            assert not is_hidden(hidden_sample)
            viewer._on_close();viewer=None
            assert not errors,errors
        results=dict(status='PASS',checks=['frozen viewer/editor','state retention','shared file list','inline highlight and undo/redo','six menus','800x600 bounds','breadcrumb links and four action icons','Ctrl/Shift grid events','no canvas resize on workspace switch','four-column default','fitted settings without scrollbars','small internal OCR/index/filter cards','native OCR cursor in frozen build','plain breadcrumb','drag selection and strong border','print icon','single status pixel display','grid scroll boundary','no heavy startup imports','real bundled filter ON/OFF closes dialog','immediate original thumbnails on OFF','one-page AI result','pixel swatch','four navigation icons','outlined bold brand/font-matched logo'],callback_errors=errors)
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
