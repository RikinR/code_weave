from urllib.parse import quote
from uuid import uuid4
from fastapi.testclient import TestClient
import app.api.routes.graph as graph_routes
from app.server import create_app


def test_folder_node_id_with_path(monkeypatch):
    def fake_detail(_session, raw_id: str):
        assert raw_id.startswith("folder:")
        assert "|" in raw_id
        return {
            "id": raw_id,
            "type": "folder",
            "name": "app",
            "file_path": "app",
            "incoming_calls": [],
            "outgoing_calls": [],
            "related_chunks": [],
            "relationships": [],
        }

    monkeypatch.setattr(graph_routes, "get_node_detail", fake_detail)
    client = TestClient(create_app())
    node_id = f"folder:{uuid4()}|app/sub"
    response = client.get(f"/api/nodes/{quote(node_id, safe='')}")
    assert response.status_code == 200


def test_node_detail_path_with_colon(monkeypatch):
    """Node ids like function:uuid must be routable (colon breaks plain path segments)."""

    def fake_detail(_session, raw_id: str):
        return {
            "id": raw_id,
            "type": "function",
            "name": "demo",
            "file_path": "app/main.py",
            "incoming_calls": [],
            "outgoing_calls": [],
            "related_chunks": [],
            "relationships": [],
        }

    monkeypatch.setattr(graph_routes, "get_node_detail", fake_detail)
    client = TestClient(create_app())
    node_id = f"function:{uuid4()}"
    response = client.get(f"/api/nodes/{quote(node_id, safe='')}")
    assert response.status_code == 200
    assert response.json()["id"] == node_id
