"""Bounded persistent thumbnail cache, called only from thumbnail workers."""
import hashlib
import os
from pathlib import Path
from PIL import Image
from croweyes_workflows import atomic_write
import io
_writes = 0


def cache_root():
    return Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'CrowEyes' / 'thumbnails-v2'


def key(path,size,theme):
    path=Path(path)
    stat=path.stat()
    return hashlib.sha256(f'{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:{size}:{theme}'.encode()).hexdigest()+'.png'


def get(path,size,theme):
    try:
        cached=cache_root()/key(path,size,theme)
        with Image.open(cached) as image:
            return image.copy()
    except (OSError,ValueError):
        return None


def put(path,size,theme,image):
    global _writes
    try:
        root=cache_root()
        root.mkdir(parents=True,exist_ok=True)
        buffer=io.BytesIO()
        image.save(buffer,format='PNG')
        atomic_write(root/key(path,size,theme),buffer.getvalue())
        _writes += 1
        if _writes % 32:
            return
        entries=sorted(root.glob('*.png'),key=lambda p:p.stat().st_mtime,reverse=True)
        total=0
        for entry in entries:
            total+=entry.stat().st_size
            if total>100*1024*1024:
                entry.unlink(missing_ok=True)
    except (OSError,ValueError):
        pass
