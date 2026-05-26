"""Process-wide cache of loaded FAISS indexes keyed by repository id.

Avoids re-reading ``data/faiss/{id}.index`` on every RAG query. Invalidated when
indexes are deleted via :mod:`application.repos.repository_service` or when the
file is missing on disk.
"""

from __future__ import annotations
import threading
from uuid import UUID
from infrastructure.logging.logger import get_logger
from infrastructure.vector.config import faiss_index_path_for_repository
from infrastructure.vector.faiss_store import FaissStore
logger = get_logger(__name__)
_lock = threading.Lock()
_cache: dict[str, tuple[float, FaissStore]] = {}

def get_loaded_store(repository_id: UUID) -> FaissStore | None:
    """Return a cached :class:`FaissStore` for the repository, or ``None`` if no index exists."""
    index_path = faiss_index_path_for_repository(repository_id)
    if not index_path.is_file():
        invalidate(repository_id)
        return None
    try:
        mtime = index_path.stat().st_mtime
    except OSError:
        logger.exception('faiss_cache: cannot stat %s', index_path)
        return None
    key = str(repository_id)
    with _lock:
        entry = _cache.get(key)
        if entry is not None and entry[0] == mtime:
            return entry[1]
    store = FaissStore(index_path=index_path)
    store.load_or_create()
    with _lock:
        _cache[key] = (mtime, store)
    logger.debug('faiss_cache: loaded index for %s (%d vectors)', key, store.size)
    return store

def invalidate(repository_id: UUID) -> None:
    """Drop any in-memory index for ``repository_id`` (e.g. after delete or rebuild)."""
    with _lock:
        removed = _cache.pop(str(repository_id), None)
    if removed is not None:
        logger.debug('faiss_cache: invalidated %s', repository_id)
