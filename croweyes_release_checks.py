"""Executable self-test; writes an explicit report and exits without the viewer."""
import json
import sys
import threading
from pathlib import Path
from PIL import Image


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
        if modules:
            from croweyes_extensions import install,manifest,load_optional,model_path
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
            from croweyes_semantic import Search
            engine=Search(report.parent/'semantic.sqlite')
            ranking,errors=engine.query('a red image',[target],threading.Event(),lambda i,n:None)
            assert ranking and not errors, errors
            results['semantic']='PASS'
        results['status']='PASS'
        code=0
    except Exception as exc:
        import traceback
        results.update(status='FAIL',error=str(exc),traceback=traceback.format_exc())
        code=1
    report.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return code
