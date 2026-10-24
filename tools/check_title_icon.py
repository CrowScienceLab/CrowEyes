"""Native title-bar icon must remain explicit after themes and menu changes."""
import importlib.util,sys,ctypes
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('icon_check',ROOT/'CrowEyes_Image_Viewer_2.0.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.load_settings=lambda:{**m.DEFAULT_SETTINGS,'auto_check_updates':False,'association_extensions':[]}
m.save_settings=lambda s:None;m.CrowEyes20._auto_register_file_associations=lambda s:None
v=m.CrowEyes20()
try:
    v.update()
    u=ctypes.WinDLL('user32',use_last_error=True)
    u.GetAncestor.argtypes=[ctypes.c_void_p,ctypes.c_uint];u.GetAncestor.restype=ctypes.c_void_p
    u.SendMessageW.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_size_t,ctypes.c_ssize_t];u.SendMessageW.restype=ctypes.c_ssize_t
    def native_icon():
        return u.SendMessageW(u.GetAncestor(v.winfo_id(),2),0x7f,0,0)
    assert native_icon(), 'Windows title-bar has no explicit small icon' 
    for theme in ('bright_sky_blue','white_light_pink','croweyes_dark'):
        v.set_ui_theme(theme);v.update()
        assert native_icon()
    v.set_workspace('editor');v.update();assert native_icon()
    print('PASS: explicit native crow icon persists across startup/themes/editor')
finally:v.destroy()
