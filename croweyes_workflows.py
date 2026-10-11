"""On-demand editing, catalog and collection operations for CrowEyes 2.0."""
import hashlib
import io
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from PIL import Image, ImageOps


def catalog_path():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'CrowEyes' / 'catalog.sqlite3'


class Catalog:
    def __init__(self, path=None):
        self.path = Path(path or catalog_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS items(path TEXT PRIMARY KEY, taken TEXT DEFAULT "", text TEXT DEFAULT "", fingerprint TEXT DEFAULT "")')
            columns={row[1] for row in db.execute('PRAGMA table_info(items)')}
            if 'ocr_fingerprint' not in columns:
                db.execute('ALTER TABLE items ADD COLUMN ocr_fingerprint TEXT DEFAULT ""')


    def connect(self):
        return sqlite3.connect(self.path, timeout=10)

    def set(self, path, **fields):
        valid = {'taken', 'text', 'fingerprint', 'ocr_fingerprint'}
        if not fields or not fields.keys() <= valid:
            raise ValueError('Unknown catalog field')
        path = str(Path(path).resolve())
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO items(path) VALUES(?)', (path,))
            db.execute('UPDATE items SET ' + ','.join(k+'=?' for k in fields) + ' WHERE path=?', (*fields.values(), path))

    def all(self):
        with self.connect() as db:
            db.row_factory = sqlite3.Row
            return {row['path']: dict(row) for row in db.execute('SELECT * FROM items')}

    def move(self, source, target):
        with self.connect() as db:
            db.execute('UPDATE items SET path=? WHERE path=?', (str(Path(target).resolve()), str(Path(source).resolve())))

    def delete(self,paths=None,missing=False):
        with self.connect() as db:
            if missing:
                paths=[row[0] for row in db.execute('SELECT path FROM items') if not Path(row[0]).is_file()]
            before=db.total_changes
            if paths is None:db.execute('DELETE FROM items')
            else:db.executemany('DELETE FROM items WHERE path=?',[(str(Path(p).resolve()),) for p in paths])
            count=db.total_changes-before
            db.commit()
            db.execute('VACUUM')
            return count


def register_format(path):
    suffix = Path(path).suffix.lower()
    return suffix


def open_image(path, preview=False, color=True):
    suffix = register_format(path)
    if suffix in {'.heic', '.heif'}:
        from croweyes_windows_image import open_heic
        im=open_heic(path)
        if preview:
            im.thumbnail((4096,4096),Image.Resampling.LANCZOS)
    elif suffix in {'.cr2', '.cr3', '.nef', '.arw', '.dng', '.raf', '.rw2', '.orf'}:
        from croweyes_extensions import load_optional
        rawpy = load_optional('formats', 'rawpy')
        with rawpy.imread(str(path)) as raw:
            thumb = raw.extract_thumb()
            if thumb.format == rawpy.ThumbFormat.JPEG:
                im = Image.open(io.BytesIO(thumb.data))
            else:
                im = Image.fromarray(thumb.data)
            im.load()
            im = im.copy()
    else:
        with Image.open(path) as source:
            if source.width * source.height > 200_000_000:
                raise ValueError('입력 한도는 2억 픽셀입니다.')
            if preview and source.width*source.height>64_000_000 and source.format not in {'JPEG','MPO'}:
                raise ValueError('이 형식의 축소 디코딩을 지원하지 않아 메모리 보호를 위해 6,400만 픽셀로 제한합니다.')
            if preview:
                factor=min(1,4096/max(source.size))
                source.draft('RGB', (max(1,int(source.width*factor)),max(1,int(source.height*factor))))
            im = ImageOps.exif_transpose(source)
            if preview:
                im.thumbnail((4096, 4096), Image.Resampling.LANCZOS)
            im.load()
    if color and im.info.get('icc_profile'):
        from PIL import ImageCms
        try:
            source_info = dict(im.info)
            im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(im.info['icc_profile'])), ImageCms.createProfile('sRGB'), outputMode='RGBA')
            im.info.update(source_info)
            im.info['icc_profile'] = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
        except (OSError, ValueError) as exc:
            raise ValueError('ICC 프로파일을 변환할 수 없습니다: '+str(exc)) from exc
    return im


def metadata(path):
    from PIL import ExifTags
    suffix=Path(path).suffix.lower()
    if suffix in {'.heic','.heif','.cr2','.cr3','.nef','.arw','.dng','.raf','.rw2','.orf'}:
        im=open_image(path,preview=True)
        return dict(Width=im.width,Height=im.height,Format=suffix[1:].upper(),Metadata='이 형식의 EXIF/GPS 읽기는 지원하지 않습니다.',Preview='RAW는 내장 미리보기 기준' if suffix not in {'.heic','.heif'} else 'Windows 코덱')
    with Image.open(path) as im:
        exif = im.getexif()
        details = {ExifTags.TAGS.get(k, str(k)): str(v) for k, v in exif.items() if k not in {34665, 34853}}
        try:
            details.update({ExifTags.TAGS.get(k, str(k)): str(v) for k, v in exif.get_ifd(34665).items()})
            gps = exif.get_ifd(34853)
            details['GPS'] = json.dumps({ExifTags.GPSTAGS.get(k, str(k)): str(v) for k, v in gps.items()}, ensure_ascii=False) if gps else '없음'
        except (ValueError, KeyError):
            details['GPS'] = '해석 불가'
        details.update(Width=im.width, Height=im.height, ICC='있음' if im.info.get('icc_profile') else '없음', Format=im.format)
        return details


def encode(image, suffix, quality=90, target_kib=0, preserve_exif=False):
    suffix = suffix.lower()
    formats = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP', '.bmp': 'BMP', '.tif': 'TIFF', '.tiff': 'TIFF', '.avif': 'AVIF'}
    fmt = formats.get(suffix)
    if not fmt:
        raise ValueError('지원하지 않는 출력 형식')
    from croweyes_editing import validate_size
    validate_size(*image.size)
    rgba = image.convert('RGBA')
    clean = Image.new('RGBA', rgba.size)
    clean.paste(rgba)
    if fmt in {'JPEG', 'BMP'}:
        rgb = Image.new('RGB', clean.size, 'white')
        rgb.paste(clean, mask=clean.getchannel('A'))
        clean = rgb
    options = {}
    # Never copy invalidated C2PA manifests. Keep only explicitly opted-in EXIF.
    if preserve_exif and image.info.get('exif') and fmt in {'JPEG', 'PNG', 'WEBP', 'TIFF'}:
        exif=Image.Exif()
        exif.load(image.info['exif'])
        exif[274]=1
        exif[256],exif[257]=image.size
        if 34665 in exif:
            ifd=exif.get_ifd(34665)
            ifd[40962],ifd[40963]=image.size
        options['exif'] = exif.tobytes()
    if image.info.get('icc_profile') and fmt in {'JPEG', 'PNG', 'WEBP', 'TIFF'}:
        options['icc_profile'] = image.info['icc_profile']

    def attempt(q):
        stream = io.BytesIO()
        clean.save(stream, format=fmt, **options, **({'quality': int(q)} if fmt in {'JPEG', 'WEBP', 'AVIF'} else {}))
        return stream.getvalue()

    result = attempt(quality)
    if target_kib:
        if fmt not in {'JPEG', 'WEBP', 'AVIF'}:
            raise ValueError('목표 용량은 JPEG/WebP/AVIF에서 지원합니다.')
        budget = int(target_kib) * 1024
        lo, hi, best = 1, int(quality), None
        while lo <= hi:
            mid = (lo + hi) // 2
            data = attempt(mid)
            if len(data) <= budget:
                best, lo = data, mid + 1
            else:
                hi = mid - 1
        if best is None:
            raise ValueError('최저 품질에서도 목표 용량을 넘습니다. 이미지 크기를 줄이세요.')
        result = best
    return result


def atomic_write(destination, data):
    destination = Path(destination)
    fd, temporary = tempfile.mkstemp(prefix='.croweyes-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    finally:
        Path(temporary).unlink(missing_ok=True)


def batch(paths, output, width, height, suffix, quality, prefix, cancel, progress, keep_ratio=True):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for index, source in enumerate(paths):
        if cancel.is_set():
            break
        source = Path(source)
        try:
            image = open_image(source)
            if width and height:
                if keep_ratio:
                    image.thumbnail((width, height), Image.Resampling.LANCZOS)
                else:
                    image = image.resize((width, height), Image.Resampling.LANCZOS)
            stem = (prefix + f'{index+1:04d}') if prefix else source.stem
            if Path(stem).name != stem or any(c in stem for c in '/\\:'):
                raise ValueError('파일 이름에 경로를 사용할 수 없습니다.')
            target = output / (stem + suffix)
            n = 1
            while target.exists() or target.resolve() == source.resolve():
                target = output / (stem + f' ({n})' + suffix)
                n += 1
            data = encode(image, suffix, quality)
            if cancel.is_set():
                break
            atomic_write(target, data)
            records.append({'source': str(source), 'output': str(target), 'status': '완료'})
        except Exception as exc:
            records.append({'source': str(source), 'status': '실패', 'error': str(exc)})
        progress(index+1, len(paths))
    report = output / ('CrowEyes-batch-' + next(tempfile._get_candidate_names()) + '.json')
    atomic_write(report, json.dumps({'cancelled': cancel.is_set(), 'results': records}, ensure_ascii=False, indent=2).encode('utf-8'))
    return report, records


def difference_hash(image):
    gray = image.convert('L').resize((9, 8), Image.Resampling.LANCZOS)
    values = list(gray.getdata())
    return sum((values[y*9+x] > values[y*9+x+1]) << (y*8+x) for y in range(8) for x in range(8))


def duplicates(paths, similar, cancel, progress):
    seen, hashes, matches = {}, [], []
    if similar and len(paths) > 2000:
        raise ValueError('유사 이미지 비교는 한 번에 최대 2,000장입니다.')
    for i, path in enumerate(paths):
        if cancel.is_set():
            break
        try:
            if similar:
                h = difference_hash(open_image(path, preview=True))
                matches.extend((str(old), str(path), (h ^ oh).bit_count()) for old, oh in hashes if (h ^ oh).bit_count() <= 5)
                hashes.append((path, h))
            else:
                with Path(path).open('rb') as file:
                    h = hashlib.file_digest(file, 'sha256').hexdigest()
                if h in seen:
                    matches.append((str(seen[h]), str(path), 0))
                else:
                    seen[h] = path
        except (OSError, ValueError):
            pass
        progress(i+1, len(paths))
    return matches
