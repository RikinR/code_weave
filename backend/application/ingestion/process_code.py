from __future__ import annotations
from tree_sitter import Node
from application.ingestion.call_extraction import extract_calls
from application.ingestion.description_extract import extract_class_description,extract_file_description,resolve_function_description
from application.ingestion.line_numbers import byte_offset_to_line
from infrastructure.file.reader import read_file
from infrastructure.logging.logger import get_logger
from infrastructure.parser.language_specs import get_language_spec
from infrastructure.parser.path_language import infer_language
from infrastructure.parser.tree_sitter_parser import build_query_map, get_parser

logger = get_logger(__name__)

_IDENTIFIER_TYPES = frozenset(
    {
        "identifier",
        "field_identifier",
        "type_identifier",
        "property_identifier",
        "simple_identifier",
    }
)


def _text_slice(code: bytes, start: int, end: int) -> str:
    return code[start:end].decode("utf-8", errors="replace")


def _name_from_declarator(decl: Node | None) -> Node | None:
    if decl is None:
        return None
    if decl.type in _IDENTIFIER_TYPES:
        return decl
    nested = decl.child_by_field_name("declarator")
    if nested is not None:
        got = _name_from_declarator(nested)
        if got is not None:
            return got
    for child in decl.children:
        if child.type in _IDENTIFIER_TYPES:
            return child
    return None


def _function_name(code: bytes, fn_node: Node) -> str | None:
    name_node = fn_node.child_by_field_name("name")
    if name_node is not None:
        return _text_slice(code, name_node.start_byte, name_node.end_byte)
    sel_node = fn_node.child_by_field_name("selector")
    if sel_node is not None:
        return _text_slice(code, sel_node.start_byte, sel_node.end_byte)
    decl = fn_node.child_by_field_name("declarator")
    id_node = _name_from_declarator(decl)
    if id_node is not None:
        return _text_slice(code, id_node.start_byte, id_node.end_byte)
    return None


def _chunk_byte_span(fn_node: Node, wrapper_types: frozenset[str]) -> tuple[int, int]:
    cur = fn_node
    start, end = cur.start_byte, cur.end_byte
    parent = cur.parent
    while parent is not None and parent.type in wrapper_types:
        start, end = parent.start_byte, parent.end_byte
        cur = parent
        parent = cur.parent
    return start, end


def extract_functions(
    code: bytes,
    root: Node,
    query,
    function_node_types: frozenset[str],
    wrapper_types: frozenset[str],
    *,
    language: str | None = None,
) -> list[dict]:
    result: list[dict] = []
    seen: set[int] = set()
    source_text = code.decode("utf-8", errors="replace")

    for node, cap in query.captures(root):
        if cap != "fn_def" or node.type not in function_node_types:
            continue

        key = node.start_byte
        if key in seen:
            continue
        seen.add(key)

        name = _function_name(code, node)
        if not name:
            logger.debug(
                "skip %s without resolvable name at byte %s",
                node.type,
                node.start_byte,
            )
            continue

        start, end = _chunk_byte_span(node, wrapper_types)
        chunk_code = _text_slice(code, start, end)
        def_start, def_end = node.start_byte, node.end_byte

        logger.debug(
            "function %r chunk %s-%s definition %s-%s",
            name,
            start,
            end,
            def_start,
            def_end,
        )

        result.append(
            {
                "name": name,
                "code": chunk_code,
                "description": resolve_function_description(
                    source=source_text,
                    chunk_code=chunk_code,
                    definition_start=def_start,
                    name=name,
                    language=language,
                ),
                "start": start,
                "end": end,
                "definition_start": def_start,
                "definition_end": def_end,
                "start_line": byte_offset_to_line(code, start),
                "end_line": byte_offset_to_line(code, end),
            }
        )

    result.sort(key=lambda item: item["start"])
    return result


def extract_structure(code: bytes, root: Node, queries: dict, *, language: str | None = None) -> dict:
    result: dict = {"class": None, "class_description": None, "methods": [], "attributes": []}

    class_methods = queries["class_methods"]
    for node, cap in class_methods.captures(root):
        if cap == "class_name":
            result["class"] = _text_slice(code, node.start_byte, node.end_byte)
            logger.debug("class name extracted: %s", result["class"])
        elif cap == "method_name":
            result["methods"].append(_text_slice(code, node.start_byte, node.end_byte))
            logger.debug(
                "method name extracted: %s",
                _text_slice(code, node.start_byte, node.end_byte),
            )

    attrs_q = queries["attributes"]
    for node, cap in attrs_q.captures(root):
        if cap == "attr_name":
            result["attributes"].append(
                _text_slice(code, node.start_byte, node.end_byte)
            )
            logger.debug(
                "attribute name extracted: %s",
                _text_slice(code, node.start_byte, node.end_byte),
            )

    if result["class"]:
        source = code.decode("utf-8", errors="replace")
        result["class_description"] = extract_class_description(
            source,
            result["class"],
            language=language,
        )

    return result


def process_file(file_path: str, lang: str | None = None) -> dict:
    logger.info("process_file: start path=%s lang=%s", file_path, lang or "(infer)")
    if lang is None:
        lang = infer_language(file_path)

    spec = get_language_spec(lang)
    raw_code = read_file(file_path)
    if isinstance(raw_code, str):
        code = raw_code.encode("utf-8")
    else:
        code = raw_code

    parser = get_parser(lang)
    tree = parser.parse(code)

    if tree is None:
        logger.error(
            "process_file: parser returned None for path=%s language=%s",
            file_path,
            lang,
        )
        raise ValueError("Parser returned None: Check if language is supported.")

    root = tree.root_node
    queries = build_query_map(lang)

    chunks = extract_functions(
        code,
        root,
        queries["functions"],
        spec.function_node_types,
        spec.wrapper_types,
        language=lang,
    )
    structure = extract_structure(code, root, queries, language=lang)
    calls = extract_calls(code, root, lang)
    source_text = code.decode("utf-8", errors="replace")
    file_description = extract_file_description(source_text, language=lang)

    if not chunks:
        logger.warning(
            "process_file: no function chunks extracted path=%s language=%s",
            file_path,
            lang,
        )

    logger.debug(
        "final output: file=%s lang=%s chunks=%s structure=%s",
        file_path,
        lang,
        chunks,
        structure,
    )

    logger.info(
        "process_file: done path=%s language=%s chunks=%d class=%r",
        file_path,
        lang,
        len(chunks),
        structure.get("class"),
    )

    return {
        "file": file_path,
        "language": lang,
        "description": file_description,
        "chunks": chunks,
        "structure": structure,
        "calls": calls,
    }
