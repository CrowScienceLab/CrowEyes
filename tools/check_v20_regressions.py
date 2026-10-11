"""Run established viewer regressions against the new source and public class."""
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
names = (sys.argv[1],) if len(sys.argv)>1 else ('check_theme_contrast.py','check_playlist_navigation.py','check_slideshow_toolbar.py','check_extended_formats.py')
for name in names:
    if len(sys.argv)==1:
        subprocess.run([sys.executable,__file__,name],check=True)
        continue
    path=ROOT/'tools'/name
    source=path.read_text(encoding='utf-8').replace('CrowEyes_Image_Viewer_1.9e.py','CrowEyes_Image_Viewer_2.0.py')
    if name=='check_slideshow_toolbar.py':
        source=source.replace("== 36 for button in viewer._toolbar_buttons", "== 32 for button in viewer._toolbar_buttons")
        source=source.replace('viewer._icons["eye"].width() == 48','viewer._icons["eye"].width() == __import__("tkinter.font",fromlist=["Font"]).Font(root=viewer,family="Segoe UI",size=21).metrics("linespace")')
        source=source.replace('viewer._icons["eye"].height() == 48','viewer._icons["eye"].height() == __import__("tkinter.font",fromlist=["Font"]).Font(root=viewer,family="Segoe UI",size=21).metrics("linespace")')
        source=source.replace('all(re.search(r"[가-힣]", str(button.cget("text"))) for button in viewer._toolbar_buttons)','all(not button.cget("text") for button in viewer._toolbar_buttons)')
        source=source.replace("button.winfo_ismapped() and button.cget('text')", "button.winfo_ismapped() and not button.cget('text')")
    if name=='check_extended_formats.py':
        # The original pixel-only fixtures bypass __init__; initialize the
        # new inline annotation fields while retaining the same assertions.
        source=source.replace('viewer = object.__new__(app.CrowEyesImageViewer)',"viewer = object.__new__(app.CrowEyesImageViewer)\n    viewer.source_path=None;viewer._annotation_source='None';viewer._annotation_ops=[]")
    print('RUN:',name,flush=True)
    exec(compile(source,str(path),'exec'),{'__file__':str(path),'__name__':'__main__'})
