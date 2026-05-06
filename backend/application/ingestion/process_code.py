from __future__ import annotations

from tree_sitter import Node
from infrastructure.file.reader import read_file
from infrastructure.parser.tree_sitter_parser import get_parser, PYTHON_QUERIES, get_query
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


def _text_slice(code: bytes, start: int, end: int) -> str:
    return code[start:end].decode("utf-8", errors="replace")


def _function_name(code: bytes, fn_node: Node) -> str | None:
    name_node = fn_node.child_by_field_name("name")
    if name_node is None:
        return None
    return _text_slice(code, name_node.start_byte, name_node.end_byte)


def _chunk_byte_span(fn_node: Node) -> tuple[int, int]:
    parent = fn_node.parent
    if parent is not None and parent.type == "decorated_definition":
        return parent.start_byte, parent.end_byte
    return fn_node.start_byte, fn_node.end_byte


def extract_functions(code: bytes, root: Node, query) -> list[dict]:
    result: list[dict] = []
    seen: set[int] = set()

    for node, cap in query.captures(root):
        if cap != "fn_def" or node.type != "function_definition":
            continue

        key = node.start_byte
        if key in seen:
            continue
        seen.add(key)

        name = _function_name(code, node)
        if not name:
            logger.debug("skip function_definition without name at byte %s", node.start_byte)
            continue

        start, end = _chunk_byte_span(node)
        chunk_code = _text_slice(code, start, end)

        logger.debug(
            "function %r chunk %s-%s definition %s-%s",
            name,
            start,
            end,
            node.start_byte,
            node.end_byte,
        )

        result.append(
            {
                "name": name,
                "code": chunk_code,
                "start": start,
                "end": end,
            }
        )

    result.sort(key=lambda item: item["start"])
    return result


def extract_structure(code,root,queries):
    result = {
        "class": None,
        "methods": [],
        "attributes": []}

    for node, cap in queries["class_methods"].captures(root):
        if cap == "class_name":
            result["class"] = code[node.start_byte:node.end_byte].decode()
            logger.debug(f"class name extracted : {code[node.start_byte:node.end_byte].decode()}")

        elif cap == "method_name":
            result["methods"].append(
                code[node.start_byte:node.end_byte].decode()
            )
            logger.debug(f"method name extracted : {code[node.start_byte:node.end_byte].decode()}")

    for node, cap in queries["attributes"].captures(root):
        if cap == "attr_name":
            result["attributes"].append(
                code[node.start_byte:node.end_byte].decode()
            )
            logger.debug(f"attributes name extracted : {code[node.start_byte:node.end_byte].decode()}")

    return result


def process_file(file_path: str, lang: str = "python"):
    logger.debug(f"calling file reader")
    raw_code = read_file(file_path)
    if isinstance(raw_code, str):
        code = raw_code.encode("utf-8")
    else:
        code = raw_code

    logger.debug(f"calling parser")
    parser = get_parser(lang)

    logger.debug(f"calling parse function")
    tree = parser.parse(code)
    
    if tree is None:
        raise ValueError("Parser returned None: Check if language is supported.")
        
    root = tree.root_node

    queries = {
        "functions": get_query(lang=lang,queries=PYTHON_QUERIES["functions"]),
        "class_methods": get_query(lang=lang,queries=PYTHON_QUERIES["class_methods"]),
        "attributes": get_query(lang=lang,queries=PYTHON_QUERIES["attributes"])
    }
    logger.debug(f"getting chunks ")
    chunks = extract_functions(code, root, queries["functions"])
    logger.debug(f"getting structure")
    structure = extract_structure(code, root, queries)

    logger.debug(f"final output: \n file: {file_path},chunks: {chunks},structure: {structure}")

    return {
        "file": file_path,
        "chunks": chunks,
        "structure": structure
    }