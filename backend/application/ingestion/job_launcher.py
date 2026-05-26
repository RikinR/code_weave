from __future__ import annotations

"""Spawn and resume detached ingestion worker subprocesses.

Pipeline stage: job scheduling (before **ZIP extract** in the worker).

Starts :mod:`worker` as a background process for a queued upload and resumes
interrupted jobs when a slot opens. Integrates with
:mod:`application.repos.processing_tracker` for PID tracking and mutual exclusion.
"""
import os
import subprocess
import sys
from pathlib import Path
from application.repos.processing_tracker import IngestionJob, tracker
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)
BACKEND_ROOT = Path(__file__).resolve().parents[2]
WORKER_SCRIPT = Path(__file__).resolve().parent / 'worker.py'

def launch_ingestion_worker(job: IngestionJob, zip_path: Path, *, max_upload_bytes: int) -> subprocess.Popen[bytes] | None:
    """Start :mod:`worker` for ``job``; record worker PID on the tracker."""
    if not zip_path.is_file():
        logger.error('job_launcher: missing zip for job %s at %s', job.id, zip_path)
        return None
    env = os.environ.copy()
    env.setdefault('PYTHONPATH', str(BACKEND_ROOT))
    cmd = [sys.executable, str(WORKER_SCRIPT), job.id, str(max_upload_bytes)]
    try:
        proc = subprocess.Popen(cmd, cwd=str(BACKEND_ROOT), env=env, start_new_session=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if proc.pid is not None:
            tracker.set_worker_pid(job, proc.pid)
        logger.info('job_launcher: started worker pid=%s job=%s', proc.pid, job.id)
        return proc
    except OSError:
        logger.exception('job_launcher: failed to spawn worker for job %s', job.id)
        return None

def resume_recoverable_jobs(*, max_upload_bytes: int) -> int:
    """Restart at most one auto-resumable job that still has its ZIP on disk."""
    candidates: list[IngestionJob] = []
    with tracker._lock:
        jobs = list(tracker._jobs.values())
    for job in jobs:
        if tracker.should_auto_resume(job):
            candidates.append(job)
    candidates.sort(key=lambda j: j.created_at)
    started = 0
    for job in candidates:
        if not tracker.try_acquire_active(job.id):
            continue
        zip_path = tracker.zip_path_for(job.id)
        if not zip_path.is_file():
            tracker.release_active(job.id)
            continue
        tracker.reset_for_retry(job)
        if launch_ingestion_worker(job, zip_path, max_upload_bytes=max_upload_bytes):
            started += 1
            break
        tracker.release_active(job.id)
    if started:
        logger.info('job_launcher: resumed %s recoverable job(s)', started)
    return started

def maybe_resume_queued_job(*, max_upload_bytes: int) -> bool:
    """Try to resume a queued job; return True if a worker was started."""
    return resume_recoverable_jobs(max_upload_bytes=max_upload_bytes) > 0
