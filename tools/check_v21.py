"""CrowEyes 2.1 integration regression: browser menus, sorting and real Windows hidden flags."""
import importlib.util, os, sys, time
from pathlib import Path
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
folder=ROOT/'tmp/v21-fixtures';folder.mkdir(parents=True,exist_ok=True)
for name in ('photo10.png','photo2.png','photo1.png'):
    Image.new('RGB',(180,120),'#3285b0').save(folder/name)
spec=importlib.util.spec_from_file_location('v21_review',ROOT/'CrowEyes_Image_Viewer_2.0.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.load_settings=lambda:{**m.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[],'window_geometry':'1280x850'}
m.save_settings=lambda s:None;m.CrowEyes20._auto_register_file_associations=lambda s:None
errors=[]
v=m.CrowEyes20(str(folder/'photo1.png'));v.report_callback_exception=lambda *a:errors.append(str(a))
def pump(ms=300):
    end=time.monotonic()+ms/1000
    while time.monotonic()<end:v.update();time.sleep(.01)
try:
    pump(1000)
    assert hasattr(v,'_browser_sort_menu'), '파일목록 제목 옆 정렬 메뉴 없음'
    assert hasattr(v,'_browser_view_menu'), '파일목록 제목 옆 보기 메뉴 없음'
    labels=lambda menu:[menu.entrycget(i,'label') for i in range(menu.index('end')+1) if menu.type(i)!='separator']
    assert {'이름','수정한 날짜','유형','크기','오름차순','내림차순'} <= set(labels(v._browser_sort_menu))
    assert '숨김 파일 표시' in labels(v._browser_view_menu)
    for theme in ('croweyes_dark','bright_sky_blue','white_light_pink'):
        v.set_ui_theme(theme);pump()
        for button,_ in v._browser_menu_buttons:
            assert button.winfo_ismapped()
            assert button.winfo_width()<130, '정렬/보기 메뉴 폭이 비정상적으로 큼'
        assert v._playlist_close_btn.winfo_ismapped(), '파일목록 헤더 닫기 버튼 잘림'
    v.set_ui_theme('croweyes_dark');pump()
    chosen=folder/'photo2.png';idx=v.folder_files.index(chosen.resolve());v._playlist_selection={idx};v.goto_index(idx,from_list=True)
    v.set_sort('name');pump()
    assert [p.name for p in v.folder_files]==['photo1.png','photo2.png','photo10.png']
    assert v._selected_playlist_paths()==[chosen.resolve()], '정렬 후 다른 파일이 선택됨'
    from croweyes_files import is_hidden, set_hidden, file_attributes
    before=file_attributes(chosen)
    v.change_hidden([chosen],True);pump(500)
    assert is_hidden(chosen) and chosen.exists()
    assert chosen.resolve() not in v.folder_files and v.source_path != chosen.resolve()
    assert file_attributes(chosen) & ~2 == before & ~2, '숨김 외 속성 손상'
    v._show_hidden_var.set(True);v.toggle_show_hidden();pump(500)
    assert chosen.resolve() in v.folder_files
    v.change_hidden([chosen],False);pump(500)
    assert not is_hidden(chosen) and chosen.exists()
    v._show_hidden_var.set(False);v.toggle_show_hidden();pump(500)
    assert chosen.resolve() in v.folder_files
    v.open_folders([folder]);pump(600)
    assert len(v.folder_files)==3
    with patch('tkinter.Menu.tk_popup'):
        from types import SimpleNamespace
        v.show_image_context_menu(SimpleNamespace(x_root=200,y_root=200))
    assert not errors,errors
    # Hiding the final images must clear the canvas and ignore pending loads.
    remaining=list(v.folder_files)
    v.change_hidden(remaining,True);pump(600)
    assert v.folder_files==[] and v.display_image is None and v.source_path is None
    for path in remaining:set_hidden(path,False)
    v.open_folders([folder]);pump(500)
    assert len(v.folder_files)==3
    # All image bytes survive both operations.
    import hashlib
    from croweyes_files import file_attributes
    digest=lambda:hashlib.sha256(chosen.read_bytes()).hexdigest()
    original=digest()
    set_hidden(chosen,True);set_hidden(chosen,False)
    assert digest()==original
    print('PASS: real menus/natural sort/selection/Windows hidden flag/hide-show-unhide/original retained')
finally:
    try:
        from croweyes_files import set_hidden
        for p in folder.glob('*.png'):set_hidden(p,False)
    except ImportError:pass
    v.destroy()
