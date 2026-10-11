"""Historical numeric comparator fixture, not an application."""
import re
from typing import Tuple
APP_VERSION = '1.9'

def semantic_version(value: str) -> Tuple[int, ...]:
    match = re.search('(?:^|[^0-9])(\\d+(?:\\.\\d+){0,3})', value.strip())
    if not match:
        raise ValueError(f'올바른 버전이 아닙니다: {value}')
    return tuple((int(part) for part in match.group(1).split('.')))

def is_newer_version(latest: str, current: str=APP_VERSION) -> bool:
    left, right = (semantic_version(latest), semantic_version(current))
    width = max(len(left), len(right))
    return left + (0,) * (width - len(left)) > right + (0,) * (width - len(right))
