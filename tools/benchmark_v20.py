"""Interleaved source-process benchmarks on the same PC, not cold-boot claims."""
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def probe(version):
    start=time.perf_counter()
    spec=importlib.util.spec_from_file_location('benchapp',ROOT/f'CrowEyes_Image_Viewer_{version}.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    imported=time.perf_counter()
    module.SETTINGS_PATH=ROOT/'tmp'/f'benchmark-settings-{version}.json'
    module.DEFAULT_SETTINGS['auto_check_updates']=False
    module.DEFAULT_SETTINGS['content_filter']='off'
    module.DEFAULT_SETTINGS['fit_on_open']=True
    cls=module.CrowEyes20 if version=='2.0' else module.CrowEyesImageViewer
    cls._auto_register_file_associations=lambda self:None
    app=cls(str(ROOT/'tmp/v20-test/source.png'))
    app._startup_activation_pending=False
    app.withdraw()
    ready=time.perf_counter()
    deadline=ready+10
    while app.display_image is None and time.perf_counter()<deadline:
        app.update();time.sleep(.001)
    assert app.display_image is not None
    first=time.perf_counter()
    redraw=[]
    for i in range(20):
        t=time.perf_counter()
        app.zoom_by(1.02)
        app.update_idletasks()
        redraw.append((time.perf_counter()-t)*1000)
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('PageFaultCount',ctypes.c_ulong),('PeakWorkingSetSize',ctypes.c_size_t),('WorkingSetSize',ctypes.c_size_t),('QuotaPeakPagedPoolUsage',ctypes.c_size_t),('QuotaPagedPoolUsage',ctypes.c_size_t),('QuotaPeakNonPagedPoolUsage',ctypes.c_size_t),('QuotaNonPagedPoolUsage',ctypes.c_size_t),('PagefileUsage',ctypes.c_size_t),('PeakPagefileUsage',ctypes.c_size_t)]
    memory=Counters();memory.cb=ctypes.sizeof(memory)
    kernel=ctypes.WinDLL('kernel32');kernel.GetCurrentProcess.restype=ctypes.c_void_p
    psapi=ctypes.WinDLL('psapi');psapi.GetProcessMemoryInfo.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
    psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(memory),memory.cb)
    result=dict(version=version,import_ms=(imported-start)*1000,window_ms=(ready-imported)*1000,first_image_ms=(first-start)*1000,zoom_median_ms=statistics.median(redraw),working_set_mib=memory.WorkingSetSize/1024**2,heavy_modules=[name for name in ('c2pa','numpy','onnxruntime','tokenizers') if name in sys.modules])
    app._on_close()
    print(json.dumps(result))


if __name__=='__main__':
    if len(sys.argv)>1:
        probe(sys.argv[1])
    else:
        runs=[]
        for iteration in range(3):
            for version in ('1.9e','2.0'):
                process=subprocess.run([sys.executable,__file__,version],capture_output=True,text=True,check=True)
                runs.append(json.loads(process.stdout.strip().splitlines()[-1]))
        report={'method':'3 interleaved fresh Python processes per version; same 400x200 image; OS cache not cleared; not a packaged/cold-boot benchmark','runs':runs,'medians':{}}
        for version in ('1.9e','2.0'):
            report['medians'][version]={key:statistics.median(r[key] for r in runs if r['version']==version) for key in ('import_ms','window_ms','first_image_ms','zoom_median_ms','working_set_mib')}
        (ROOT/'tmp/benchmark-v20.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report['medians'],indent=2))
