from __future__ import annotations

"""Bounded serialization of Tree-sitter ASTs for explorer UI storage.

Pipeline stage: **parse** (attached to file results in :mod:`process_code`).

Converts a syntax tree root into a JSON-friendly nested dict with depth and
node limits so large files do not explode response payloads.
"""
from tree_sitter import Node

def _node_to_dict(node: Node, *, depth: int, max_depth: int, counter: list[int], max_nodes: int) -> dict | None:
    if counter[0] >= max_nodes:
        return None
    counter[0] += 1
    start_line = node.start_point[0] + 1
    end_line = node.end_point[0] + 1
    payload: dict = {'type': node.type, 'start_line': start_line, 'end_line': end_line}
    if depth >= max_depth or not node.children:
        return payload
    children: list[dict] = []
    for child in node.children:
        child_dict = _node_to_dict(child, depth=depth + 1, max_depth=max_depth, counter=counter, max_nodes=max_nodes)
        if child_dict is not None:
            children.append(child_dict)
        if counter[0] >= max_nodes:
            break
    if children:
        payload['children'] = children
    return payload

def serialize_ast_tree(root: Node, *, max_nodes: int=2000, max_depth: int=12) -> dict:
    """Serialize ``root`` to a nested dict with truncation metadata."""
    counter = [0]
    tree = _node_to_dict(root, depth=0, max_depth=max_depth, counter=counter, max_nodes=max_nodes)
    truncated = counter[0] >= max_nodes or _tree_depth_exceeded(root, max_depth)
    return {'root': tree or {'type': root.type, 'start_line': root.start_point[0] + 1, 'end_line': root.end_point[0] + 1}, 'truncated': truncated, 'node_count': counter[0]}

def _tree_depth_exceeded(node: Node, max_depth: int, depth: int=0) -> bool:
    if depth >= max_depth and node.children:
        return True
    return any((_tree_depth_exceeded(child, max_depth, depth + 1) for child in node.children))
