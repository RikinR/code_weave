"""Verify RAG preparation, synchronous query execution, and repository resolution.

Covers ``application.retrieval.rag_service`` citation building, answer formatting,
and error handling when a repository record is missing.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4
import pytest
from application.retrieval.rag_service import prepare_rag, run_rag_sync

def test_prepare_rag_builds_citations():
    repo_id = uuid4()
    session = MagicMock()
    repo = MagicMock()
    repo.id = repo_id
    repo.name = 'demo'
    session.get.return_value = repo
    contexts = [{'chunk_id': 'c1', 'file_path': 'app/main.py', 'function_name': 'main', 'function_id': str(uuid4()), 'class_id': None, 'score': 0.9}]
    with patch('application.retrieval.rag_service.retrieve_chunks', return_value=contexts):
        prepared = prepare_rag(session, repository_id=repo_id, query='what is main?', top_k=3)
    assert prepared.repository_name == 'demo'
    assert len(prepared.citation_payload) == 1
    assert prepared.citation_payload[0]['file_path'] == 'app/main.py'
    assert len(prepared.highlight_node_ids) == 1
    assert prepared.messages

def test_run_rag_sync_formats_answer():
    repo_id = uuid4()
    session = MagicMock()
    repo = MagicMock()
    repo.id = repo_id
    repo.name = 'demo'
    session.get.return_value = repo
    with patch('application.retrieval.rag_service.retrieve_chunks', return_value=[]), patch('application.retrieval.rag_service.chat_completion', return_value='"Hello world"'):
        result = run_rag_sync(session, repository_id=repo_id, query='hi')
    assert result['answer'] == 'Hello world'
    assert result['repository_id'] == str(repo_id)

def test_resolve_repository_missing_raises():
    from application.retrieval.rag_service import resolve_repository
    session = MagicMock()
    session.get.return_value = None
    with pytest.raises(ValueError, match='not found'):
        resolve_repository(session, repository_id=uuid4())
