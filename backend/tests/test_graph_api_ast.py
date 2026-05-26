"""Verify graph node-detail API responses include AST and indexing metadata.

Covers ``app.api.routes.graph`` and ``app.server.create_app``, asserting AST
trees, indexing modes, and notices for AST and plain-text file nodes.
"""

from urllib.parse import quote
from uuid import uuid4
from fastapi.testclient import TestClient
import app.api.routes.graph as graph_routes
from app.server import create_app

def test_node_detail_includes_ast_and_indexing_fields(monkeypatch):
    file_id = uuid4()

    def fake_detail(_session, raw_id: str):
        return {
            'id': raw_id,
            'type': 'file',
            'name': 'main.py',
            'file_path': 'app/main.py',
            'language': 'python',
            'indexing_mode': 'ast',
            'indexing_notice': None,
            'ast_tree': {'root': {'type': 'module', 'start_line': 1, 'end_line': 5, 'children': []}, 'truncated': False, 'node_count': 1},
            'description': 'Entry module',
            'explanation': 'Entry module',
            'code': 'def run(): pass',
            'start_line': 1,
            'end_line': 1,
            'incoming_calls': [],
            'outgoing_calls': [],
            'related_chunks': [],
            'relationships': [],
        }

    monkeypatch.setattr(graph_routes, 'get_node_detail', fake_detail)
    client = TestClient(create_app())
    node_id = f'file:{file_id}'
    response = client.get(f'/api/nodes/{quote(node_id, safe="")}')
    assert response.status_code == 200
    body = response.json()
    assert body['indexing_mode'] == 'ast'
    assert body['ast_tree']['root']['type'] == 'module'
    assert body['ast_tree']['node_count'] == 1

def test_node_detail_css_text_indexing_notice(monkeypatch):

    def fake_detail(_session, raw_id: str):
        return {
            'id': raw_id,
            'type': 'file',
            'name': 'styles.css',
            'file_path': 'styles.css',
            'language': 'css',
            'indexing_mode': 'unsupported_extension',
            'indexing_notice': 'Indexed as plain text (.md/.txt-style chunks). Tree-sitter AST chunking is not used for .css files.',
            'ast_tree': None,
            'description': None,
            'explanation': 'Source file (css).',
            'code': 'body { }',
            'start_line': 1,
            'end_line': 1,
            'incoming_calls': [],
            'outgoing_calls': [],
            'related_chunks': [],
            'relationships': [],
        }

    monkeypatch.setattr(graph_routes, 'get_node_detail', fake_detail)
    client = TestClient(create_app())
    response = client.get(f'/api/nodes/{quote(f"file:{uuid4()}", safe="")}')
    assert response.status_code == 200
    body = response.json()
    assert body['indexing_mode'] == 'unsupported_extension'
    assert '.css' in body['indexing_notice']
    assert body['ast_tree'] is None
