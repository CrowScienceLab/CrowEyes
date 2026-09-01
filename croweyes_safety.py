"""Local-only explicit nudity safety pipeline for CrowEyes.

The module deliberately avoids importing NumPy or ONNX Runtime until the
filter is enabled and a model preload/check is requested.
"""

from __future__ import annotations

from dataclasses import dataclass
from contextlib import closing
import itertools
import json
import os
from pathlib import Path
import queue
import sqlite3
import threading
import time
from typing import Callable, Iterable, List, Optional, Sequence, Tuple

from PIL import Image, ImageOps, ImageSequence


SAFETY_OFF = "off"
SAFETY_EXPLICIT = "explicit"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_SAFE = "SAFE"
STATUS_BLOCKED = "BLOCKED"
STATUS_ERROR = "ERROR"

# Concise public aliases used by the viewer UI.
MODE_OFF = SAFETY_OFF
MODE_EXPLICIT = SAFETY_EXPLICIT
UNKNOWN = STATUS_UNKNOWN
SAFE = STATUS_SAFE
BLOCKED = STATUS_BLOCKED
ERROR = STATUS_ERROR

MODEL_VERSION = "deepghs-nudenet-320n-c15d8273"
POLICY_VERSION = "croweyes-explicit-v1"
MODEL_INPUT_SIZE = 320

# Exact class order published with deepghs/nudenet_onnx (320n.onnx).
MODEL_LABELS: Tuple[str, ...] = (
    "FEMALE_GENITALIA_COVERED",
    "FACE_FEMALE",
    "BUTTOCKS_EXPOSED",
    "FEMALE_BREAST_EXPOSED",
    "FEMALE_GENITALIA_EXPOSED",
    "MALE_BREAST_EXPOSED",
    "ANUS_EXPOSED",
    "FEET_EXPOSED",
    "BELLY_COVERED",
    "FEET_COVERED",
    "ARMPITS_COVERED",
    "ARMPITS_EXPOSED",
    "FACE_MALE",
    "BELLY_EXPOSED",
    "MALE_GENITALIA_EXPOSED",
    "ANUS_COVERED",
    "FEMALE_BREAST_COVERED",
    "BUTTOCKS_COVERED",
)

# Higher thresholds on breast/buttocks favor the requested low false-positive
# policy for swimwear and close-fitting clothing. Covered classes are never
# blocking classes.
EXPLICIT_THRESHOLDS = {
    "FEMALE_BREAST_EXPOSED": 0.55,
    "FEMALE_GENITALIA_EXPOSED": 0.48,
    "MALE_GENITALIA_EXPOSED": 0.48,
    "BUTTOCKS_EXPOSED": 0.60,
    "ANUS_EXPOSED": 0.48,
}


@dataclass(frozen=True)
class SafetyResult:
    status: str
    matched_classes: Tuple[str, ...] = ()
    confidence: float = 0.0
    model_version: str = MODEL_VERSION
    policy_version: str = POLICY_VERSION
    elapsed_ms: float = 0.0
    cached: bool = False
    detail: str = ""


@dataclass(frozen=True)
class SafetyTaskResult:
    kind: str
    generation: int
    path: Optional[Path]
    result: SafetyResult


def canonical_path(path: Path) -> str:
    """Canonical cache key without network-expensive Path.resolve()."""
    return os.path.normcase(os.path.abspath(os.fspath(path.expanduser())))


class SafetyCache:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self._lock = threading.RLock()

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=4.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS safety_cache (
                path TEXT PRIMARY KEY,
                size INTEGER NOT NULL,
                mtime_ns INTEGER NOT NULL,
                model_version TEXT NOT NULL,
                policy_version TEXT NOT NULL,
                result TEXT NOT NULL,
                confidence REAL NOT NULL,
                matched_classes TEXT NOT NULL,
                checked_at REAL NOT NULL
            )
            """
        )
        return connection

    @staticmethod
    def signature(path: Path) -> Tuple[str, int, int]:
        stat = path.stat()
        return canonical_path(path), int(stat.st_size), int(stat.st_mtime_ns)

    def get(self, path: Path) -> Optional[SafetyResult]:
        try:
            key, size, mtime_ns = self.signature(path)
        except OSError:
            return None
        with self._lock, closing(self._connect()) as connection:
            row = connection.execute(
                """
                SELECT result, confidence, matched_classes
                FROM safety_cache
                WHERE path=? AND size=? AND mtime_ns=?
                  AND model_version=? AND policy_version=?
                """,
                (key, size, mtime_ns, MODEL_VERSION, POLICY_VERSION),
            ).fetchone()
        if row is None:
            return None
        try:
            matched = tuple(str(item) for item in json.loads(row[2]))
        except (TypeError, ValueError, json.JSONDecodeError):
            matched = ()
        return SafetyResult(
            status=str(row[0]), matched_classes=matched,
            confidence=float(row[1]), cached=True,
        )

    def put(self, path: Path, result: SafetyResult) -> None:
        if result.status not in {STATUS_SAFE, STATUS_BLOCKED}:
            return
        key, size, mtime_ns = self.signature(path)
        with self._lock, closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT INTO safety_cache
                    (path, size, mtime_ns, model_version, policy_version,
                     result, confidence, matched_classes, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(path) DO UPDATE SET
                    size=excluded.size,
                    mtime_ns=excluded.mtime_ns,
                    model_version=excluded.model_version,
                    policy_version=excluded.policy_version,
                    result=excluded.result,
                    confidence=excluded.confidence,
                    matched_classes=excluded.matched_classes,
                    checked_at=excluded.checked_at
                """,
                (
                    key, size, mtime_ns, MODEL_VERSION, POLICY_VERSION,
                    result.status, result.confidence,
                    json.dumps(result.matched_classes, ensure_ascii=True), time.time(),
                ),
            )
            connection.commit()

    def clear(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.execute("DELETE FROM safety_cache")
            connection.commit()


def _sample_positions(frame_count: int, limit: int = 5) -> List[int]:
    if frame_count <= 1:
        return [0]
    count = min(limit, frame_count)
    if count == 1:
        return [0]
    return sorted({round(i * (frame_count - 1) / (count - 1)) for i in range(count)})


def _small_rgb(image: Image.Image, size: int = MODEL_INPUT_SIZE) -> Image.Image:
    image = ImageOps.exif_transpose(image).convert("RGB")
    image.thumbnail((size, size), Image.Resampling.LANCZOS, reducing_gap=3.0)
    return image


def load_safety_samples(
    path: Path,
    vector_loader: Optional[Callable[[Path, int], Image.Image]] = None,
    max_frames: int = 5,
) -> List[Image.Image]:
    """Create bounded local previews; no image bytes leave the computer."""
    suffix = path.suffix.lower()
    if suffix in {".svg", ".eps"}:
        if vector_loader is None:
            raise OSError(f"{suffix} 안전 판정용 렌더러가 없습니다.")
        return [_small_rgb(vector_loader(path, MODEL_INPUT_SIZE))]

    samples: List[Image.Image] = []
    with Image.open(path) as source:
        frame_count = max(1, int(getattr(source, "n_frames", 1) or 1))
        positions = _sample_positions(frame_count, max_frames)
        for index in positions:
            if frame_count > 1:
                source.seek(index)
            if index == 0 and (source.format or "").upper() in {"JPEG", "MPO"}:
                try:
                    source.draft("RGB", (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE))
                except Exception:
                    pass
            samples.append(_small_rgb(source.copy()))
    if not samples:
        raise OSError("안전 판정용 이미지를 만들지 못했습니다.")
    return samples


class SafetyManager:
    def __init__(self, model_path: Path, cache_path: Path) -> None:
        self.model_path = model_path
        self.cache = SafetyCache(cache_path)
        self._session = None
        self._input_name = ""
        self._session_lock = threading.RLock()

    @property
    def model_loaded(self) -> bool:
        return self._session is not None

    def cached_result(self, path: Path) -> Optional[SafetyResult]:
        return self.cache.get(path)

    def prepare_model(self) -> SafetyResult:
        start = time.perf_counter()
        try:
            self._ensure_session()
            return SafetyResult(
                status=STATUS_SAFE,
                elapsed_ms=(time.perf_counter() - start) * 1000.0,
                detail="모델 준비 완료",
            )
        except Exception as exc:
            return SafetyResult(
                status=STATUS_ERROR,
                elapsed_ms=(time.perf_counter() - start) * 1000.0,
                detail=str(exc),
            )

    def _ensure_session(self):
        with self._session_lock:
            if self._session is not None:
                return self._session
            if not self.model_path.is_file():
                raise FileNotFoundError(f"콘텐츠 안전 모델이 없습니다: {self.model_path}")
            import onnxruntime as ort  # Lazy: never imported while filter is OFF.

            options = ort.SessionOptions()
            options.intra_op_num_threads = max(1, min(2, os.cpu_count() or 1))
            options.inter_op_num_threads = 1
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            self._session = ort.InferenceSession(
                os.fspath(self.model_path), sess_options=options,
                providers=["CPUExecutionProvider"],
            )
            inputs = self._session.get_inputs()
            if len(inputs) != 1:
                raise OSError("지원하지 않는 안전 모델 입력 구조입니다.")
            self._input_name = inputs[0].name
            return self._session

    @staticmethod
    def _tensor(image: Image.Image):
        import numpy as np

        image = image.convert("RGB")
        width, height = image.size
        scale = min(MODEL_INPUT_SIZE / max(1, width), MODEL_INPUT_SIZE / max(1, height))
        resized = image.resize(
            (max(1, round(width * scale)), max(1, round(height * scale))),
            Image.Resampling.BILINEAR,
        )
        canvas = Image.new("RGB", (MODEL_INPUT_SIZE, MODEL_INPUT_SIZE), (114, 114, 114))
        canvas.paste(
            resized,
            ((MODEL_INPUT_SIZE - resized.width) // 2, (MODEL_INPUT_SIZE - resized.height) // 2),
        )
        array = np.asarray(canvas, dtype=np.float32) / 255.0
        return np.transpose(array, (2, 0, 1))[None, ...]

    def _scores(self, image: Image.Image) -> dict:
        import numpy as np

        session = self._ensure_session()
        outputs = session.run(None, {self._input_name: self._tensor(image)})
        if not outputs:
            raise OSError("안전 모델 출력이 없습니다.")
        raw = np.asarray(outputs[0])
        if raw.ndim == 3:
            raw = raw[0]
        if raw.shape[0] == 4 + len(MODEL_LABELS):
            class_scores = raw[4:, :]
        elif raw.shape[-1] == 4 + len(MODEL_LABELS):
            class_scores = raw[:, 4:].T
        else:
            raise OSError(f"지원하지 않는 안전 모델 출력 구조입니다: {tuple(raw.shape)}")
        maxima = np.max(class_scores, axis=1)
        return {label: float(maxima[index]) for index, label in enumerate(MODEL_LABELS)}

    def check(
        self,
        path: Path,
        vector_loader: Optional[Callable[[Path, int], Image.Image]] = None,
    ) -> SafetyResult:
        start = time.perf_counter()
        cached = self.cache.get(path)
        if cached is not None:
            return SafetyResult(
                status=cached.status,
                matched_classes=cached.matched_classes,
                confidence=cached.confidence,
                cached=True,
                elapsed_ms=(time.perf_counter() - start) * 1000.0,
            )
        try:
            samples = load_safety_samples(path, vector_loader=vector_loader)
            maxima = {name: 0.0 for name in EXPLICIT_THRESHOLDS}
            for sample in samples:
                scores = self._scores(sample)
                for name in maxima:
                    maxima[name] = max(maxima[name], scores.get(name, 0.0))
            matched = tuple(
                name for name, threshold in EXPLICIT_THRESHOLDS.items()
                if maxima[name] >= threshold
            )
            confidence = max(maxima.values(), default=0.0)
            result = SafetyResult(
                status=STATUS_BLOCKED if matched else STATUS_SAFE,
                matched_classes=matched,
                confidence=confidence,
                elapsed_ms=(time.perf_counter() - start) * 1000.0,
            )
            self.cache.put(path, result)
            return result
        except Exception as exc:
            return SafetyResult(
                status=STATUS_ERROR,
                confidence=0.0,
                elapsed_ms=(time.perf_counter() - start) * 1000.0,
                detail=str(exc),
            )


class SafetyWorker:
    """One bounded daemon worker with a priority queue and result polling."""

    def __init__(self, manager: SafetyManager) -> None:
        self.manager = manager
        self._tasks: "queue.PriorityQueue[tuple]" = queue.PriorityQueue()
        self._results: "queue.Queue[SafetyTaskResult]" = queue.Queue()
        self._counter = itertools.count()
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, name="CrowEyesSafetyWorker", daemon=True,
        )
        self._thread.start()

    def preload(self) -> None:
        self._tasks.put((-10, next(self._counter), "preload", 0, None, None))

    def submit(
        self,
        path: Path,
        priority: int,
        generation: int,
        vector_loader: Optional[Callable[[Path, int], Image.Image]] = None,
        kind: str = "current",
    ) -> None:
        self._tasks.put((priority, next(self._counter), kind, generation, path, vector_loader))

    def poll(self) -> List[SafetyTaskResult]:
        results: List[SafetyTaskResult] = []
        while True:
            try:
                results.append(self._results.get_nowait())
            except queue.Empty:
                return results

    def clear_pending(self) -> None:
        while True:
            try:
                self._tasks.get_nowait()
                self._tasks.task_done()
            except queue.Empty:
                return

    def stop(self) -> None:
        self._stop.set()
        self.clear_pending()
        self._tasks.put((9999, next(self._counter), "stop", 0, None, None))

    def _run(self) -> None:
        while not self._stop.is_set():
            priority, sequence, kind, generation, path, vector_loader = self._tasks.get()
            try:
                if kind == "stop":
                    return
                if kind == "preload":
                    result = self.manager.prepare_model()
                else:
                    assert path is not None
                    result = self.manager.check(path, vector_loader=vector_loader)
                self._results.put(SafetyTaskResult(kind, generation, path, result))
            finally:
                self._tasks.task_done()
