"""Verify FAISS vector store construction and save/load roundtrips.

Covers ``infrastructure.vector.faiss_store.FaissStore`` index-path requirements
and persistence of added vectors across reload.
"""

import pytest
from pathlib import Path
from infrastructure.vector.faiss_store import FaissStore

def test_faiss_store_requires_index_path():
    with pytest.raises(TypeError):
        FaissStore()

def test_faiss_store_roundtrip(tmp_path):
    path = tmp_path / 'test.index'
    store = FaissStore(index_path=path)
    store.load_or_create()
    dim = store.dimension
    store.add([[1.0] + [0.0] * (dim - 1)])
    store.save()
    reloaded = FaissStore(index_path=path)
    reloaded.load_or_create()
    assert reloaded.size == 1
