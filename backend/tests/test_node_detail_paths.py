"""Verify node detail display paths are normalized relative to a repository root.

Covers ``application.graph.node_detail._display_path`` and
``infrastructure.db.models.repository_model.RepositoryModel`` upload prefixes.
"""

from application.graph.node_detail import _display_path
from infrastructure.db.models.repository_model import RepositoryModel

def test_display_path_strips_absolute_upload_path():
    repo = RepositoryModel(name='rag_prac', root_path='/data/uploads/job-id/rag_prac')
    absolute = '/data/uploads/job-id/rag_prac/tests/test_faiss_store.py'
    assert _display_path(absolute, repo) == 'tests/test_faiss_store.py'

def test_display_path_keeps_relative():
    repo = RepositoryModel(name='rag_prac', root_path='/data/uploads/job-id/rag_prac')
    assert _display_path('app/faiss_store.py', repo) == 'app/faiss_store.py'
