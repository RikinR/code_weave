"""Verify in-memory FAISS store caching and invalidation per repository.

Covers ``infrastructure.vector.faiss_cache`` and its interaction with
``infrastructure.vector.faiss_store.FaissStore`` for load reuse and reload.
"""

from uuid import uuid4
from infrastructure.vector import faiss_cache
from infrastructure.vector.faiss_store import FaissStore

def _patch_index_path(monkeypatch, tmp_path):
    index_path = tmp_path / 'repo.index'

    def _path(_repository_id):
        return index_path
    monkeypatch.setattr(faiss_cache, 'faiss_index_path_for_repository', _path)
    return index_path

def test_faiss_cache_reuses_store(tmp_path, monkeypatch):
    index_path = _patch_index_path(monkeypatch, tmp_path)
    repo_id = uuid4()
    store = FaissStore(index_path=index_path)
    store.load_or_create()
    store.add([[0.1] * store.dimension])
    store.save()
    first = faiss_cache.get_loaded_store(repo_id)
    second = faiss_cache.get_loaded_store(repo_id)
    assert first is not None
    assert second is first

def test_faiss_cache_invalidate_forces_reload(tmp_path, monkeypatch):
    index_path = _patch_index_path(monkeypatch, tmp_path)
    repo_id = uuid4()
    store = FaissStore(index_path=index_path)
    store.load_or_create()
    store.add([[0.2] * store.dimension])
    store.save()
    first = faiss_cache.get_loaded_store(repo_id)
    faiss_cache.invalidate(repo_id)
    second = faiss_cache.get_loaded_store(repo_id)
    assert first is not None
    assert second is not None
    assert first is not second
