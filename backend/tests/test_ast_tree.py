"""Verify AST tree serialization shape, limits, and truncation behavior.

Covers ``application.ingestion.ast_tree.serialize_ast_tree`` and
``application.ingestion.process_code.parse_code_file`` for building parse trees.
"""

from application.ingestion.ast_tree import serialize_ast_tree
from application.ingestion.process_code import parse_code_file

def test_serialize_ast_tree_shape(tmp_path):
    py_file = tmp_path / 'sample.py'
    py_file.write_text('def hello():\n    return 1\n\nclass Box:\n    pass\n', encoding='utf-8')
    _, root, _, _, _ = parse_code_file(str(py_file))
    payload = serialize_ast_tree(root, max_nodes=100, max_depth=4)
    assert 'root' in payload
    assert payload['root']['type'] == 'module'
    assert 'start_line' in payload['root']
    assert isinstance(payload['truncated'], bool)
    assert payload['node_count'] >= 1

def test_serialize_ast_tree_respects_node_limit(tmp_path):
    py_file = tmp_path / 'big.py'
    py_file.write_text('x = 1\n' * 500, encoding='utf-8')
    _, root, _, _, _ = parse_code_file(str(py_file))
    payload = serialize_ast_tree(root, max_nodes=10, max_depth=20)
    assert payload['node_count'] <= 10
    assert payload['truncated'] is True
