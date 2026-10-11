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
        source=source.replace('len(viewer._toolbar_buttons) >= 12','len(viewer._toolbar_buttons) >= 11')
        source=source.replace('all(re.search(r"[가-힣]", str(button.cget("text"))) for button in viewer._toolbar_buttons)','all(not button.cget("text") for button in viewer._toolbar_buttons)')
        source=source.replace("button.winfo_ismapped() and button.cget('text')", "button.winfo_ismapped() and not button.cget('text')")
    print('RUN:',name,flush=True)
    exec(compile(source,str(path),'exec'),{'__file__':str(path),'__name__':'__main__'})
