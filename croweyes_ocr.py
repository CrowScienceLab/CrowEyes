"""Windows built-in, offline OCR; no model added to the core distribution."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def recognize(image, cancel=None):
    if os.name != 'nt':
        raise OSError('Windows 10/11에서 사용할 수 있습니다.')
    script = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'tools' / 'windows_ocr.ps1'
    with tempfile.TemporaryDirectory(prefix='CrowEyes-ocr-') as folder:
        path = Path(folder) / 'image.png'
        image = image.convert('RGB')
        image.thumbnail((2500,2500))
        image.save(path)
        # Execute our packaged command without changing the machine's script policy.
        command = '& {\n' + script.read_text(encoding='utf-8') + '\n} -ImagePath \'' + str(path).replace("'", "''") + "'"
        process = subprocess.Popen(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
        deadline = time.monotonic() + 60
        while True:
            try:
                out,err = process.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                if cancel and cancel.is_set():
                    process.kill()
                    process.communicate()
                    return ''
                if time.monotonic() >= deadline:
                    process.kill()
                    process.communicate()
                    raise TimeoutError('글자 인식이 60초 안에 완료되지 않았습니다. 영역을 줄여 다시 시도하세요.')
        if process.returncode:
            raise OSError(err.decode('utf-8',errors='replace'))
        return out.decode('utf-8-sig').strip()
