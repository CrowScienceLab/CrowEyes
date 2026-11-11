"""Keep legacy upgrade detection covered without shipping an obsolete application."""
import ast,json,re
from pathlib import Path
from typing import Tuple
ROOT=Path(__file__).resolve().parents[1]
current=json.loads((ROOT/'version.json').read_text())['version']
def comparator(path,version):
    nodes=[n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name in {'semantic_version','is_newer_version'}]
    values={'re':re,'Tuple':Tuple,'APP_VERSION':version,'APP_UPDATE_VERSION':version}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),values)
    return values
old=comparator(ROOT/'tools/fixtures/legacy_update_comparator.py','1.9')
new=comparator(ROOT/'CrowEyes_Image_Viewer_2.0.py',current)
assert old['semantic_version']('v1.9e')==old['semantic_version']('1.9')
assert not old['is_newer_version']('v1.9e','1.9')
for previous in ('1.8','1.9','1.9d','1.9e','2.0.0','2.1.0'):
    assert old['is_newer_version']('v'+current,previous)
    assert new['is_newer_version']('v'+current,previous)
assert not new['is_newer_version']('v'+current)
assert not new['is_newer_version']('v1.9e')
print('PASS: legacy numeric client and current comparator both detect the current release; no obsolete application required')
