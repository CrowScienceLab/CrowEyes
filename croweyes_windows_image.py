"""Read HEIC through installed Microsoft WIC codecs; no GPL codecs bundled."""
import subprocess
import sys
import tempfile
from pathlib import Path
from PIL import Image


def open_heic(path):
    script=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent))/'tools/windows_heic.ps1'
    with tempfile.TemporaryDirectory(prefix='CrowEyes-heic-') as folder:
        output=Path(folder)/'image.png'
        output.touch()
        quote=lambda value:"'"+str(value).replace("'","''")+"'"
        command='& {\n'+script.read_text(encoding='utf-8')+'\n} -ImagePath '+quote(Path(path).resolve())+' -OutputPath '+quote(output)
        process=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW,timeout=60)
        if process.returncode:
            raise OSError('Windows HEIF 이미지 코덱으로 읽지 못했습니다. Microsoft Store의 HEIF 이미지 확장과 해당 HEVC 코덱 설치 상태를 확인하세요.\n'+process.stderr.decode('utf-8',errors='replace'))
        with Image.open(output) as image:
            return image.copy()
