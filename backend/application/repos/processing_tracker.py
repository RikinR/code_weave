from __future__ import annotations
import asyncio
import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

STALE_JOB_SECONDS = 120

INTERRUPTED_BY_RESTART_ERROR = "Interrupted by server restart"

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
JOBS_DIR = DATA_ROOT / "jobs"
UPLOADS_DIR = DATA_ROOT / "uploads"

class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

PIPELINE_STAGES: tuple[str, ...] = (
    "zip_extraction",
    "file_scanning",
    "language_detection",
    "tree_sitter_parsing",
    "ast_generation",
    "class_extraction",
    "function_extraction",
    "call_extraction",
    "chunk_generation",
    "embedding_generation",
    "vector_storage",
    "architecture_graph",
    "indexing_complete",
)

@dataclass
class StageState:
    key: str
    label: str
    status: StageStatus = StageStatus.PENDING
    progress: float = 0.0
    logs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "status": self.status.value,
            "progress": self.progress,
            "logs": list(self.logs),
        }

_STAGE_LABELS: dict[str, str] = {
    "zip_extraction": "ZIP extraction",
    "file_scanning": "File scanning",
    "language_detection": "Language detection",
    "tree_sitter_parsing": "Tree-sitter parsing",
    "ast_generation": "AST generation",
    "class_extraction": "Class extraction",
    "function_extraction": "Function extraction",
    "call_extraction": "Call extraction",
    "chunk_generation": "Chunk generation",
    "embedding_generation": "Embedding generation",
    "vector_storage": "Vector storage",
    "architecture_graph": "Architecture graph",
    "indexing_complete": "Indexing complete",
}

@dataclass
class IngestionJob:
    id: str
    repository_name: str
    status: str = "pending"
    repository_id: str | None = None
    worker_pid: int | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    last_activity_at: float = field(default_factory=time.time)
    stages: dict[str, StageState] = field(default_factory=dict)
    _disk_mtime: float = field(default=0.0, repr=False)
    _listeners: list[Callable[[dict[str, Any]], None]] = field(
        default_factory=list, repr=False
    )
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        if not self.stages:
            self.stages = {
                key: StageState(key=key, label=_STAGE_LABELS.get(key, key))
                for key in PIPELINE_STAGES
            }

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "job_id": self.id,
                "repository_name": self.repository_name,
                "status": self.status,
                "repository_id": self.repository_id,
                "worker_pid": self.worker_pid,
                "error": self.error,
                "created_at": self.created_at,
                "updated_at": self.last_activity_at,
                "stages": [self.stages[k].to_dict() for k in PIPELINE_STAGES],
            }

    @classmethod
    def from_snapshot(cls, data: dict[str, Any]) -> IngestionJob:
        job = cls(
            id=str(data["job_id"]),
            repository_name=str(data["repository_name"]),
            status=str(data.get("status", "pending")),
            repository_id=data.get("repository_id"),
            worker_pid=(
                int(data["worker_pid"])
                if data.get("worker_pid") is not None
                else None
            ),
            error=data.get("error"),
            created_at=float(data.get("created_at", time.time())),
            last_activity_at=float(
                data.get("updated_at", data.get("created_at", time.time()))
            ),
        )
        for stage_data in data.get("stages", []):
            key = stage_data["key"]
            if key not in job.stages:
                continue
            stage = job.stages[key]
            stage.status = StageStatus(stage_data.get("status", "pending"))
            stage.progress = float(stage_data.get("progress", 0.0))
            stage.logs = list(stage_data.get("logs", []))
        return job

    def subscribe(self, listener: Callable[[dict[str, Any]], None]) -> None:
        with self._lock:
            self._listeners.append(listener)

    def _touch_activity(self) -> None:
        self.last_activity_at = time.time()

    def _emit(self) -> None:
        self._touch_activity()
        payload = self.snapshot()
        tracker._on_job_updated(self)
        for listener in list(self._listeners):
            try:
                listener(payload)
            except Exception:
                logger.exception("processing_tracker: listener failed")

    def log(self, stage_key: str, message: str) -> None:
        with self._lock:
            stage = self.stages[stage_key]
            stage.logs.append(message)
            if len(stage.logs) > 200:
                stage.logs = stage.logs[-200:]
        logger.info("job=%s stage=%s %s", self.id, stage_key, message)
        self._emit()

    def start_stage(self, stage_key: str, progress: float = 0.0) -> None:
        with self._lock:
            self.status = "running"
            stage = self.stages[stage_key]
            stage.status = StageStatus.RUNNING
            stage.progress = progress
        self._emit()

    def advance_to_stage(self, stage_key: str) -> None:
        """Mark earlier stages complete and move the running marker to stage_key."""
        if stage_key not in self.stages:
            return
        with self._lock:
            self.status = "running"
            target_idx = PIPELINE_STAGES.index(stage_key)
            for i, key in enumerate(PIPELINE_STAGES):
                if i >= target_idx:
                    break
                prior = self.stages[key]
                if prior.status == StageStatus.RUNNING:
                    prior.status = StageStatus.COMPLETED
                    prior.progress = 100.0
            stage = self.stages[stage_key]
            if stage.status != StageStatus.COMPLETED:
                stage.status = StageStatus.RUNNING
        self._emit()

    def pulse(self, stage_key: str, message: str | None = None) -> None:
        """Re-emit progress during long work so SSE clients show liveness."""
        with self._lock:
            stage = self.stages.get(stage_key)
            if stage is None or stage.status != StageStatus.RUNNING:
                return
            if message and (not stage.logs or stage.logs[-1] != message):
                stage.logs.append(message)
                if len(stage.logs) > 200:
                    stage.logs = stage.logs[-200:]
        self._emit()

    def update_stage(self, stage_key: str, progress: float, message: str | None = None) -> None:
        with self._lock:
            stage = self.stages[stage_key]
            if stage.status == StageStatus.PENDING:
                stage.status = StageStatus.RUNNING
                self.status = "running"
            stage.progress = min(100.0, max(0.0, progress))
            if message:
                stage.logs.append(message)
        if message:
            logger.debug("job=%s stage=%s %.0f%% %s", self.id, stage_key, progress, message)
        self._emit()

    def complete_stage(self, stage_key: str, message: str | None = None) -> None:
        with self._lock:
            stage = self.stages[stage_key]
            stage.status = StageStatus.COMPLETED
            stage.progress = 100.0
            if message:
                stage.logs.append(message)
        self._emit()

    def fail_stage(self, stage_key: str, error: str) -> None:
        with self._lock:
            self.status = "failed"
            self.error = error
            stage = self.stages[stage_key]
            stage.status = StageStatus.FAILED
            stage.logs.append(error)
        self._emit()

    def complete_job(self, repository_id: str) -> None:
        with self._lock:
            self.status = "completed"
            self.repository_id = repository_id
        self.complete_stage("indexing_complete", "Repository ready for exploration")
        self._emit()

class ProcessingTracker:
    def __init__(self) -> None:
        self._jobs: dict[str, IngestionJob] = {}
        self._active_job_id: str | None = None
        self._lock = threading.Lock()
        JOBS_DIR.mkdir(parents=True, exist_ok=True)
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        self._load_persisted_jobs()
        self._recover_orphan_uploads()

    def _job_path(self, job_id: str) -> Path:
        return JOBS_DIR / f"{job_id}.json"

    @staticmethod
    def _upload_meta_path(job_id: str) -> Path:
        return UPLOADS_DIR / f"{job_id}.meta.json"

    def save_upload_meta(self, job_id: str, repository_name: str) -> None:
        UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
        path = self._upload_meta_path(job_id)
        try:
            path.write_text(
                json.dumps({"repository_name": repository_name}),
                encoding="utf-8",
            )
        except OSError:
            logger.exception("processing_tracker: failed to persist upload meta %s", job_id)

    def _load_upload_meta(self, job_id: str) -> str | None:
        path = self._upload_meta_path(job_id)
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            name = data.get("repository_name")
            return str(name).strip() if name else None
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            logger.exception("processing_tracker: failed to read upload meta %s", job_id)
            return None

    def _persist_job(self, job: IngestionJob) -> None:
        path = self._job_path(job.id)
        tmp = path.with_suffix(".json.tmp")
        try:
            payload = json.dumps(job.snapshot(), default=str)
            tmp.write_text(payload, encoding="utf-8")
            tmp.replace(path)
            try:
                job._disk_mtime = path.stat().st_mtime
            except OSError:
                pass
        except OSError:
            logger.exception("processing_tracker: failed to persist job %s", job.id)
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass

    def sync_job_from_disk(self, job_id: str) -> IngestionJob | None:
        """Reload job JSON when a detached worker updates state on disk."""
        path = self._job_path(job_id)
        if not path.is_file():
            return self._jobs.get(job_id)

        try:
            mtime = path.stat().st_mtime
        except OSError:
            logger.exception("processing_tracker: cannot stat job file %s", job_id)
            return self._jobs.get(job_id)

        with self._lock:
            cached = self._jobs.get(job_id)
            if cached is not None and cached._disk_mtime == mtime:
                return cached

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            job = IngestionJob.from_snapshot(data)
            job._disk_mtime = mtime
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            logger.exception("processing_tracker: failed to sync job %s from disk", job_id)
            return self._jobs.get(job_id)

        with self._lock:
            prev = self._jobs.get(job_id)
            if prev is not None:
                job._listeners = list(prev._listeners)
            self._jobs[job_id] = job
        return job

    @staticmethod
    def _mark_interrupted(job: IngestionJob) -> None:
        """Align stage state when a background worker died (e.g. uvicorn --reload)."""
        with job._lock:
            job.status = "failed"
            if not job.error:
                job.error = INTERRUPTED_BY_RESTART_ERROR
            for stage in job.stages.values():
                if stage.status == StageStatus.RUNNING:
                    stage.status = StageStatus.FAILED
                    stage.logs.append("Stopped: server restarted during this step")

    def _load_persisted_jobs(self) -> None:
        for path in JOBS_DIR.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                job = IngestionJob.from_snapshot(data)
                with self._lock:
                    self._jobs[job.id] = job
            except (OSError, json.JSONDecodeError, KeyError, ValueError):
                logger.exception("processing_tracker: failed to load job %s", path.name)

    def _recover_orphan_job(self, job_id: str) -> IngestionJob | None:
        """Rebuild job state when upload artifacts exist but job JSON was lost (e.g. reload)."""
        zip_path = self.zip_path_for(job_id)
        extract_dir = UPLOADS_DIR / job_id
        if not zip_path.is_file() and not extract_dir.is_dir():
            return None

        repository_name = self._load_upload_meta(job_id) or job_id
        job = IngestionJob(id=job_id, repository_name=repository_name, status="pending")
        with self._lock:
            self._jobs[job_id] = job
        self._persist_job(job)
        logger.warning(
            "processing_tracker: recovered orphan job %s (zip=%s extract=%s)",
            job_id,
            zip_path.is_file(),
            extract_dir.is_dir(),
        )
        return job

    def _recover_orphan_uploads(self) -> None:
        if not UPLOADS_DIR.is_dir():
            return
        for zip_path in UPLOADS_DIR.glob("*.zip"):
            job_id = zip_path.stem
            if self._job_path(job_id).is_file() or job_id in self._jobs:
                continue
            self._recover_orphan_job(job_id)

    def create_job(self, repository_name: str) -> IngestionJob:
        job_id = str(uuid.uuid4())
        job = IngestionJob(id=job_id, repository_name=repository_name)
        with self._lock:
            self._jobs[job_id] = job
        self.save_upload_meta(job_id, repository_name)
        self._persist_job(job)
        if not self._job_path(job_id).is_file():
            raise OSError(f"Job state was not written to {self._job_path(job_id)}")
        return job

    def get_job(self, job_id: str) -> IngestionJob | None:
        path = self._job_path(job_id)
        if path.is_file():
            job = self.sync_job_from_disk(job_id)
            if job is not None:
                self._maybe_fail_stale_job(job)
                return job
        job = self._jobs.get(job_id)
        if job is not None:
            self._maybe_fail_stale_job(job)
            return job
        return self._recover_orphan_job(job_id)

    def zip_path_for(self, job_id: str) -> Path:
        return UPLOADS_DIR / f"{job_id}.zip"

    @staticmethod
    def is_restart_interruption(job: IngestionJob) -> bool:
        return job.error == INTERRUPTED_BY_RESTART_ERROR

    def should_auto_resume(self, job: IngestionJob) -> bool:
        if not self.zip_path_for(job.id).is_file():
            return False
        if self._worker_running(job):
            return False
        if job.status == "pending":
            return True
        if job.status == "running" and not self._is_job_live(job):
            return True
        return job.status == "failed" and self.is_restart_interruption(job)

    def can_retry(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if job is None or job.status != "failed":
            return False
        return self.zip_path_for(job_id).is_file()

    def reset_for_retry(self, job: IngestionJob) -> None:
        with job._lock:
            job.status = "pending"
            job.error = None
            job.repository_id = None
            job.worker_pid = None
            for stage in job.stages.values():
                stage.status = StageStatus.PENDING
                stage.progress = 0.0
                stage.logs.clear()
        job._emit()

    def _on_job_updated(self, job: IngestionJob) -> None:
        self._persist_job(job)

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    @staticmethod
    def _worker_running(job: IngestionJob) -> bool:
        pid = job.worker_pid
        return pid is not None and ProcessingTracker._pid_alive(pid)

    @staticmethod
    def _is_job_live(job: IngestionJob) -> bool:
        pid = job.worker_pid
        if pid is not None:
            return ProcessingTracker._pid_alive(pid)
        return (time.time() - job.last_activity_at) <= STALE_JOB_SECONDS

    def set_worker_pid(self, job: IngestionJob, pid: int) -> None:
        with job._lock:
            job.worker_pid = pid
        job._emit()

    def clear_worker_pid(self, job: IngestionJob) -> None:
        with job._lock:
            job.worker_pid = None
        job._emit()

    def _maybe_fail_stale_job(self, job: IngestionJob) -> None:
        if job.status != "running" or self._is_job_live(job):
            return
        self._mark_interrupted(job)
        self._persist_job(job)
        self.release_active(job.id)

    def try_acquire_active(self, job_id: str) -> bool:
        with self._lock:
            if self._active_job_id is not None and self._active_job_id != job_id:
                holder = self._jobs.get(self._active_job_id)
                if holder is not None and holder.status == "running" and self._is_job_live(holder):
                    return False
                self._active_job_id = None
            self._active_job_id = job_id
            return True

    def release_active(self, job_id: str) -> None:
        with self._lock:
            if self._active_job_id == job_id:
                self._active_job_id = None

tracker = ProcessingTracker()

async def sse_event_stream(job_id: str):
    job = tracker.get_job(job_id)
    if job is None:
        yield f"event: error\ndata: {{\"error\":\"unknown job\"}}\n\n"
        return

    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def on_update(payload: dict[str, Any]) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, payload)

    job.subscribe(on_update)
    last_updated_at = job.last_activity_at
    yield f"event: snapshot\ndata: {_json(job.snapshot())}\n\n"

    try:
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                synced = tracker.sync_job_from_disk(job_id)
                if synced is None:
                    break
                payload = synced.snapshot()
                if payload.get("updated_at") == last_updated_at:
                    continue

            if payload is None:
                break

            updated_at = payload.get("updated_at")
            if updated_at is not None:
                try:
                    last_updated_at = float(updated_at)
                except (TypeError, ValueError):
                    last_updated_at = time.time()
            else:
                last_updated_at = time.time()

            yield f"event: update\ndata: {_json(payload)}\n\n"
            if payload.get("status") in ("completed", "failed"):
                break
    finally:
        with job._lock:
            try:
                job._listeners.remove(on_update)
            except ValueError:
                pass

def _json(data: dict[str, Any]) -> str:
    import json

    return json.dumps(data, default=str)
