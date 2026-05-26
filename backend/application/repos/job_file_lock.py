"""Cross-process file lock for ingestion job state on disk.

Wraps ``fcntl`` on Unix so worker and API processes do not corrupt
``data/jobs/{job_id}.json`` while :mod:`application.repos.processing_tracker`
persists snapshots.
"""

from __future__ import annotations
from contextlib import contextmanager
from pathlib import Path
try:
    import fcntl
except ImportError:
    fcntl = None

@contextmanager
def job_file_lock(path: Path):
    """Exclusive lock around read/write of a job state file (no-op when ``fcntl`` unavailable)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if fcntl is None:
        yield
        return
    with open(path, 'a+', encoding='utf-8') as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
