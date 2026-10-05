"""Exercise the actual old and patched update comparators without starting Tk."""
import ast
import re
from pathlib import Path
from typing import Tuple

ROOT = Path(__file__).resolve().parents[1]


def load_comparator(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if (
        isinstance(node, ast.FunctionDef)
        and node.name in {"semantic_version", "is_newer_version"}
    ) or (
        isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id in {
            "APP_VERSION", "APP_UPDATE_VERSION"
        } for target in node.targets)
    )]
    namespace = {"re": re, "Tuple": Tuple}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
    return namespace


old = load_comparator(ROOT / "CrowEyes_Image_Viewer_1.9.py")
new = load_comparator(ROOT / "CrowEyes_Image_Viewer_1.9e.py")
assert old["semantic_version"]("v1.9e") == old["semantic_version"]("1.9")
assert not old["is_newer_version"]("v1.9e", "1.9")
for version in ("1.8", "1.9", "1.9d", "1.9e"):
    assert old["is_newer_version"]("v1.9.1", version), version
    assert new["is_newer_version"]("v1.9.1", version), version
assert new["APP_VERSION"] == "1.9e"
assert new["APP_UPDATE_VERSION"] == "1.9.1"
assert not new["is_newer_version"]("v1.9.1")
assert not new["is_newer_version"]("v1.9e")
assert new["is_newer_version"]("v1.9.2")
assert new["is_newer_version"]("v1.10")
source = (ROOT / "CrowEyes_Image_Viewer_1.9e.py").read_text(encoding="utf-8")
assert "is_newer_version(tag, APP_UPDATE_VERSION)" in source
print("PASS: reproduced legacy 1.9e failure; numeric tag detects upgrade; patched client does not repeat it")
