"""Verify chat message listing is scoped to a repository.

Covers ``app.api.routes.chat`` and ``application.chat.messages.list_chat_messages``,
ensuring the messages endpoint passes the requested repository ID through.
"""

from uuid import uuid4
from fastapi.testclient import TestClient
import app.api.routes.chat as chat_routes
from app.server import create_app

def test_chat_messages_endpoint_is_scoped_to_repository(monkeypatch):
    repo_id = uuid4()
    seen: list[uuid4] = []

    def fake_require(_db, repository_id):
        return object()

    def fake_list(_db, repository_id):
        seen.append(repository_id)
        return [{'id': 'msg-1', 'role': 'user', 'content': 'repo-scoped question', 'citations': [], 'created_at': None}]
    monkeypatch.setattr(chat_routes, '_require_repository', fake_require)
    monkeypatch.setattr(chat_routes, 'list_chat_messages', fake_list)
    client = TestClient(create_app())
    response = client.get(f'/api/repositories/{repo_id}/chat/messages')
    assert response.status_code == 200
    assert response.json()[0]['content'] == 'repo-scoped question'
    assert seen == [repo_id]
