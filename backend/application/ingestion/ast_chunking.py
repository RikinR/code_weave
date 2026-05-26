from __future__ import annotations

"""AST-based semantic chunking for Tree-sitter-supported languages.

Pipeline stage: **parse** (called from :mod:`process_code`).

Builds function, method, and class chunks from query captures, deduplicates
overlapping spans, and tags chunks with :class:`chunk_strategy.ChunkStrategy`.
Complements :mod:`text_chunking` for non-AST or fallback indexing.
"""
from tree_sitter import Node
from application.ingestion.chunk_strategy import ChunkStrategy
from application.ingestion.process_code import _function_name, _text_slice, extract_functions, extract_structure
from infrastructure.parser.language_specs import LanguageSpec, supports_semantic_chunking

def _overlap_ratio(start_a: int, end_a: int, start_b: int, end_b: int) -> float:
    overlap = max(0, min(end_a, end_b) - max(start_a, start_b))
    span = min(end_a - start_a, end_b - start_b)
    return overlap / span if span > 0 else 0.0

def dedupe_chunks(chunks: list[dict], *, threshold: float=0.8) -> list[dict]:
    """Drop non-function chunks that largely overlap function spans."""
    functions = [c for c in chunks if c.get('chunk_type') in ('function', 'method')]
    kept = list(functions)
    for candidate in chunks:
        if candidate in functions:
            continue
        if any(_overlap_ratio(candidate['start'], candidate['end'], existing['start'], existing['end']) >= threshold for existing in functions):
            continue
        if any(_overlap_ratio(candidate['start'], candidate['end'], existing['start'], existing['end']) >= threshold for existing in kept if existing not in functions):
            continue
        kept.append(candidate)
    return sorted(kept, key=lambda c: c.get('start', 0))

def _class_name(code: bytes, node: Node) -> str | None:
    name_node = node.child_by_field_name('name')
    if name_node is not None:
        return _text_slice(code, name_node.start_byte, name_node.end_byte)
    for child in node.children:
        if child.type in {'identifier', 'type_identifier', 'constant'}:
            return _text_slice(code, child.start_byte, child.end_byte)
    return None

def _extract_class_chunks(code: bytes, root: Node, class_node_types: frozenset[str]) -> list[dict]:
    if not class_node_types:
        return []
    chunks: list[dict] = []
    stack: list[Node] = [root]
    seen: set[int] = set()
    while stack:
        node = stack.pop()
        if node.type in class_node_types:
            key = node.start_byte
            if key not in seen:
                seen.add(key)
                name = _class_name(code, node)
                if name:
                    start, end = (node.start_byte, node.end_byte)
                    chunk_code = _text_slice(code, start, end)
                    chunks.append({'name': name, 'code': chunk_code, 'description': name, 'start': start, 'end': end, 'start_line': node.start_point[0] + 1, 'end_line': node.end_point[0] + 1, 'chunk_type': 'class', 'chunk_strategy': ChunkStrategy.AST_SEMANTIC})
        stack.extend(reversed(node.children))
    chunks.sort(key=lambda item: item['start'])
    return chunks

def _tag_function_chunks(chunks: list[dict]) -> list[dict]:
    tagged: list[dict] = []
    for chunk in chunks:
        item = dict(chunk)
        item.setdefault('chunk_type', 'function')
        item['chunk_strategy'] = ChunkStrategy.AST_SEMANTIC
        tagged.append(item)
    return tagged

def chunk_ast_semantic(code: bytes, root: Node, lang: str, spec: LanguageSpec, queries: dict, *, language: str | None=None) -> list[dict]:
    """Produce deduplicated function and class chunks from a parsed AST."""
    if not supports_semantic_chunking(spec):
        return []
    function_chunks = _tag_function_chunks(extract_functions(code, root, queries['functions'], spec.function_node_types, spec.wrapper_types, language=language or lang))
    class_chunks = _extract_class_chunks(code, root, spec.class_node_types)
    return dedupe_chunks(function_chunks + class_chunks)
