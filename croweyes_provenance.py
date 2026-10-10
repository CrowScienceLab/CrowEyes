"""Optional provenance inspection. Importing this module never loads C2PA."""
import json
from collections import OrderedDict
from pathlib import Path
from threading import RLock

_cache = OrderedDict()
_lock = RLock()


def inspect(path):
    from croweyes_extensions import load_optional
    reader_type = load_optional('provenance', 'c2pa').Reader
    path = Path(path)
    stat = path.stat()
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    with _lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    reader = None
    result = {'credential': '없음', 'validation': '확인 불가', 'ai': '판별 불가', 'tool': '', 'actions': []}
    try:
        reader = reader_type.try_create(path)
        if reader:
            manifest = reader.get_active_manifest()
            result['credential'] = '있음'
            result['validation'] = '정상' if reader.is_valid else '경고 또는 실패'
            declarations = set()
            actions = []

            def walk(value):
                if isinstance(value, dict):
                    for k, v in value.items():
                        if k == 'digitalSourceType' and isinstance(v, str):
                            declarations.add(v.rsplit('/', 1)[-1].lower())
                        if k == 'action' and isinstance(v, str):
                            actions.append(v)
                        walk(v)
                elif isinstance(value, list):
                    for item in value:
                        walk(item)

            # Inspect assertion fields only, never free-text descriptions/tool names.
            for assertion in (manifest or {}).get('assertions', []):
                walk(assertion.get('data', {}))
            generated = 'trainedalgorithmicmedia' in declarations
            edited = 'compositewithtrainedalgorithmicmedia' in declarations
            result['ai'] = 'AI 생성 선언' if generated else 'AI 편집 선언' if edited else 'AI 선언 확인되지 않음'
            result['actions'] = actions
            result['tool'] = str((manifest or {}).get('claim_generator', ''))
    except Exception as exc:
        result.update(credential='해석 실패', validation='검사 실패', ai='판별 불가', error=str(exc))
    finally:
        if reader:
            reader.close()
    with _lock:
        _cache[key] = result
        while len(_cache) > 128:
            _cache.popitem(last=False)
    return result
