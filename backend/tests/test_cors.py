"""Verify CORS middleware allows typical Flutter web development origins.

Covers ``app.server.create_app`` and checks that localhost and 127.0.0.1 origins
receive ``Access-Control-Allow-Origin`` on API responses.
"""

from fastapi.testclient import TestClient
from app.server import create_app

def test_cors_allows_flutter_web_localhost_origin():
    client = TestClient(create_app())
    origin = 'http://localhost:59078'
    response = client.get('/api/health', headers={'Origin': origin})
    assert response.status_code == 200
    assert response.headers.get('access-control-allow-origin') == origin

def test_cors_allows_127_0_0_1_origin():
    client = TestClient(create_app())
    origin = 'http://127.0.0.1:59078'
    response = client.get('/api/health', headers={'Origin': origin})
    assert response.status_code == 200
    assert response.headers.get('access-control-allow-origin') == origin
