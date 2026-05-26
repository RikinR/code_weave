from __future__ import annotations

"""Tree-sitter parsing and semantic extraction for source code files.

Pipeline stage: **parse** (within :mod:`index_folder`).

Reads a file, builds a Tree-sitter AST, extracts structure, call sites, and
chunks via :mod:`ast_chunking`, :mod:`call_extraction`, and
:mod:`description_extract`. Serializes a bounded AST preview with
:mod:`ast_tree`. Falls back to :mod:`text_chunking` when parsing or chunking fails.
"""
from tree_sitter import Node
from application.ingestion.ast_tree import serialize_ast_tree
from application.ingestion.call_extraction import extract_calls
from application.ingestion.description_extract import extract_class_description, extract_file_description, resolve_function_description
from application.ingestion.line_numbers import byte_offset_to_line
from infrastructure.file.reader import read_file
from infrastructure.logging.logger import get_logger
from infrastructure.parser.language_specs import get_language_spec, supports_semantic_chunking
from infrastructure.parser.path_language import infer_language
from infrastructure.parser.tree_sitter_parser import build_query_map, get_parser
logger = get_logger(__name__)
_IDENTIFIER_TYPES = frozenset({'identifier', 'field_identifier', 'type_identifier', 'property_identifier', 'simple_identifier'})

def _text_slice(code: bytes, start: int, end: int) -> str:
    return code[start:end].decode('utf-8', errors='replace')

def _name_from_declarator(decl: Node | None) -> Node | None:
    if decl is None:
        return None
    if decl.type in _IDENTIFIER_TYPES:
        return decl
    nested = decl.child_by_field_name('declarator')
    if nested is not None:
        got = _name_from_declarator(nested)
        if got is not None:
            return got
    for child in decl.children:
        if child.type in _IDENTIFIER_TYPES:
            return child
    return None

def _function_name(code: bytes, fn_node: Node) -> str | None:
    name_node = fn_node.child_by_field_name('name')
    if name_node is not None:
        return _text_slice(code, name_node.start_byte, name_node.end_byte)
    sel_node = fn_node.child_by_field_name('selector')
    if sel_node is not None:
        return _text_slice(code, sel_node.start_byte, sel_node.end_byte)
    decl = fn_node.child_by_field_name('declarator')
    id_node = _name_from_declarator(decl)
    if id_node is not None:
        return _text_slice(code, id_node.start_byte, id_node.end_byte)
    return None

def _chunk_byte_span(fn_node: Node, wrapper_types: frozenset[str]) -> tuple[int, int]:
    cur = fn_node
    start, end = (cur.start_byte, cur.end_byte)
    parent = cur.parent
    while parent is not None and parent.type in wrapper_types:
        start, end = (parent.start_byte, parent.end_byte)
        cur = parent
        parent = cur.parent
    return (start, end)

def extract_functions(code: bytes, root: Node, query, function_node_types: frozenset[str], wrapper_types: frozenset[str], *, language: str | None=None) -> list[dict]:
    """Collect function/method chunk dicts from Tree-sitter query captures."""
    result: list[dict] = []
    seen: set[int] = set()
    source_text = code.decode('utf-8', errors='replace')
    for node, cap in query.captures(root):
        if cap != 'fn_def' or node.type not in function_node_types:
            continue
        key = node.start_byte
        if key in seen:
            continue
        seen.add(key)
        name = _function_name(code, node)
        if not name:
            logger.debug('skip %s without resolvable name at byte %s', node.type, node.start_byte)
            continue
        start, end = _chunk_byte_span(node, wrapper_types)
        chunk_code = _text_slice(code, start, end)
        def_start, def_end = (node.start_byte, node.end_byte)
        logger.debug('function %r chunk %s-%s definition %s-%s', name, start, end, def_start, def_end)
        result.append({'name': name, 'code': chunk_code, 'description': resolve_function_description(source=source_text, chunk_code=chunk_code, definition_start=def_start, name=name, language=language), 'start': start, 'end': end, 'definition_start': def_start, 'definition_end': def_end, 'start_line': byte_offset_to_line(code, start), 'end_line': byte_offset_to_line(code, end)})
    result.sort(key=lambda item: item['start'])
    return result

def extract_structure(code: bytes, root: Node, queries: dict, *, language: str | None=None) -> dict:
    """Extract class name, methods, attributes, and class description from the AST."""
    result: dict = {'class': None, 'class_description': None, 'methods': [], 'attributes': []}
    class_methods = queries['class_methods']
    for node, cap in class_methods.captures(root):
        if cap == 'class_name':
            result['class'] = _text_slice(code, node.start_byte, node.end_byte)
            logger.debug('class name extracted: %s', result['class'])
        elif cap == 'method_name':
            result['methods'].append(_text_slice(code, node.start_byte, node.end_byte))
            logger.debug('method name extracted: %s', _text_slice(code, node.start_byte, node.end_byte))
    attrs_q = queries['attributes']
    for node, cap in attrs_q.captures(root):
        if cap == 'attr_name':
            result['attributes'].append(_text_slice(code, node.start_byte, node.end_byte))
            logger.debug('attribute name extracted: %s', _text_slice(code, node.start_byte, node.end_byte))
    if result['class']:
        source = code.decode('utf-8', errors='replace')
        result['class_description'] = extract_class_description(source, result['class'], language=language)
    return result

def parse_code_file(file_path: str, lang: str | None=None) -> tuple[bytes, Node, str, object, dict]:
    """Read and parse a source file; return bytes, root node, language, spec, and queries."""
    if lang is None:
        lang = infer_language(file_path)
    spec = get_language_spec(lang)
    raw_code = read_file(file_path)
    code = raw_code.encode('utf-8') if isinstance(raw_code, str) else raw_code
    parser = get_parser(lang)
    tree = parser.parse(code)
    if tree is None:
        raise ValueError(f'Parser returned None for {file_path!r}')
    root = tree.root_node
    queries = build_query_map(lang)
    return (code, root, lang, spec, queries)

def process_code_file(file_path: str, lang: str | None=None) -> dict:
    """Parse one code file into chunks, structure, calls, and an AST tree preview.

    Primary entry used by :func:`index_folder.index_folder`. Uses AST semantic
    chunking when supported; otherwise delegates to
    :func:`text_chunking.process_text_file_as_fallback`.
    """
    from application.ingestion.text_chunking import process_text_file_as_fallback
    logger.info('process_code_file: start path=%s lang=%s', file_path, lang or '(infer)')
    try:
        code, root, lang, spec, queries = parse_code_file(file_path, lang)
    except (RuntimeError, ValueError) as exc:
        logger.warning('process_code_file: parse failed path=%s: %s', file_path, exc)
        return process_text_file_as_fallback(file_path, reason='parse_error', language_hint=lang)
    structure = extract_structure(code, root, queries, language=lang) if supports_semantic_chunking(spec) else {'class': None, 'class_description': None, 'methods': [], 'attributes': []}
    calls = extract_calls(code, root, lang) if supports_semantic_chunking(spec) else []
    source_text = code.decode('utf-8', errors='replace')
    file_description = extract_file_description(source_text, language=lang)
    if supports_semantic_chunking(spec):
        from application.ingestion.ast_chunking import chunk_ast_semantic
        chunks = chunk_ast_semantic(code, root, lang, spec, queries, language=lang)
    else:
        chunks = []
    ast_tree = serialize_ast_tree(root)
    if not chunks:
        logger.warning('process_code_file: no AST chunks path=%s language=%s — text fallback', file_path, lang)
        fallback = process_text_file_as_fallback(file_path, reason='ast_empty', language_hint=lang)
        fallback['structure'] = structure
        fallback['calls'] = calls
        fallback['ast_tree'] = ast_tree
        return fallback
    logger.info('process_code_file: done path=%s language=%s chunks=%d class=%r', file_path, lang, len(chunks), structure.get('class'))
    return {'file': file_path, 'language': lang, 'indexing_mode': 'ast', 'description': file_description, 'chunks': chunks, 'structure': structure, 'calls': calls, 'ast_tree': ast_tree}

def process_file(file_path: str, lang: str | None=None) -> dict:
    """Alias for :func:`process_code_file`."""
    return process_code_file(file_path, lang=lang)
