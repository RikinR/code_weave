"""Verify the API health endpoint returns a successful status response.

Covers ``app.server.create_app`` and the ``/api/health`` route exposed by the
FastAPI application factory.
"""

from fastapi.testclient import TestClient
from app.server import create_app

def test_health():
    client = TestClient(create_app())
    response = client.get('/api/health')
    assert response.status_code == 200
    assert response.json()['status'] == 'ok'
