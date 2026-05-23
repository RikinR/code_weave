from __future__ import annotations
import ast
import re

_MAX_LEN = 1000

_GENERIC_LOCATION_RE = re.compile(
    r"^(Function|Method|Class|Source file|Folder|Indexed repository)\s+.+",
    re.IGNORECASE,
)


def _truncate(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= _MAX_LEN:
        return cleaned
    return cleaned[: _MAX_LEN - 3].rstrip() + "..."


def is_generic_description(description: str | None) -> bool:
    if not description or not description.strip():
        return True
    text = description.strip()
    if len(text) < 24:
        return True
    if _GENERIC_LOCATION_RE.match(text) and " in " in text and "." in text.split(" in ", 1)[-1]:
        return True
    return False


def _leading_docstring(code: str) -> str | None:
    for pattern in (
        r'^\s*"""(.*?)"""',
        r"^\s*'''(.*?)'''",
        r"^\s*/\*\*(.*?)\*/",
    ):
        match = re.match(pattern, code, re.DOTALL)
        if match:
            text = match.group(1)
            if pattern.endswith(r"\*/"):
                text = re.sub(r"^\s*\*\s?", "", text, flags=re.MULTILINE)
            return _truncate(text)
    return None


def extract_preceding_comments(source: str, before_byte: int) -> str | None:
    if before_byte <= 0:
        return None

    prefix = source[:before_byte]
    lines = prefix.splitlines()
    if not lines:
        return None

    collected: list[str] = []
    idx = len(lines) - 1

    while idx >= 0 and not lines[idx].strip():
        idx -= 1
    if idx < 0:
        return None

    line = lines[idx].strip()
    if line.endswith("*/"):
        block_lines = [line]
        idx -= 1
        while idx >= 0:
            block_lines.insert(0, lines[idx].strip())
            if lines[idx].strip().startswith("/**") or lines[idx].strip().startswith("/*"):
                break
            idx -= 1
        block = "\n".join(block_lines)
        match = re.search(r"/\*\*(.*?)\*/", block, re.DOTALL)
        if match:
            text = re.sub(r"^\s*\*\s?", "", match.group(1), flags=re.MULTILINE)
            return _truncate(text.strip())
        return None

    while idx >= 0:
        stripped = lines[idx].strip()
        if stripped.startswith("//"):
            collected.insert(0, stripped[2:].strip())
            idx -= 1
            continue
        if stripped.startswith("#"):
            collected.insert(0, stripped.lstrip("#").strip())
            idx -= 1
            continue
        break

    if collected:
        return _truncate(" ".join(collected))
    return None


def _camel_to_words(name: str) -> str:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name)
    spaced = re.sub(r"[_-]+", " ", spaced)
    return spaced.strip().lower()


def infer_description_from_code(
    code: str,
    *,
    name: str,
    language: str | None = None,
) -> str | None:
    if not code.strip():
        return None

    behaviors: list[str] = []
    name_words = _camel_to_words(name)
    if name_words:
        behaviors.append(f"This function {_verb_phrase(name_words)}.")

    props = _meaningful_property_paths(code)
    if props:
        joined = ", ".join(props[:4])
        behaviors.append(f"It works with {joined}.")

    if re.search(r"\.sort\s*\(", code):
        behaviors.append("It sorts a collection to determine order.")
    if re.search(r"\b(?:map|forEach|filter|reduce)\s*\(", code):
        behaviors.append("It iterates over collection data.")
    if re.search(r"\breturn\b", code) and not behaviors:
        behaviors.append("It computes and returns a value derived from its inputs.")

    if not behaviors:
        return None
    return _truncate(" ".join(behaviors))


def _verb_phrase(name_words: str) -> str:
    tokens = name_words.split()
    if not tokens:
        return "performs an operation"
    first = tokens[0]
    verb_map = {
        "get": "retrieves",
        "set": "updates",
        "is": "checks whether",
        "has": "checks for",
        "reorder": "reorders",
        "sort": "sorts",
        "build": "builds",
        "create": "creates",
        "update": "updates",
        "delete": "removes",
        "remove": "removes",
        "parse": "parses",
        "format": "formats",
        "validate": "validates",
        "compute": "computes",
        "calculate": "calculates",
        "fetch": "fetches",
        "load": "loads",
        "save": "stores",
        "handle": "handles",
        "process": "processes",
        "extract": "extracts",
        "transform": "transforms",
    }
    verb = verb_map.get(first, f"{first}s" if not first.endswith("s") else first)
    rest = " ".join(tokens[1:])
    if rest:
        return f"{verb} {rest}"
    return verb


def _meaningful_property_paths(code: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"(?:\?\.)?\.([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*)", code):
        path = match.group(1)
        if path.split(".")[0] in {"length", "push", "pop", "then", "catch", "prototype"}:
            continue
        if path not in seen:
            seen.add(path)
            paths.append(path.replace(".", " → "))
    return paths


def extract_function_description(code: str, language: str | None = None) -> str | None:
    lang = (language or "").lower().replace("-", "_")
    if lang == "python":
        try:
            tree = ast.parse(code)
            if tree.body:
                doc = ast.get_docstring(tree.body[0])
                if doc:
                    return _truncate(doc)
        except SyntaxError:
            pass
    return _leading_docstring(code)


def resolve_function_description(
    *,
    source: str,
    chunk_code: str,
    definition_start: int,
    name: str,
    language: str | None = None,
) -> str | None:
    doc = extract_function_description(chunk_code, language=language)
    if doc:
        return doc

    preceding = extract_preceding_comments(source, definition_start)
    if preceding:
        return preceding

    return infer_description_from_code(chunk_code, name=name, language=language)


def extract_file_description(code: str, language: str | None = None) -> str | None:
    lang = (language or "").lower().replace("-", "_")
    if lang == "python":
        try:
            tree = ast.parse(code)
            doc = ast.get_docstring(tree)
            if doc:
                return _truncate(doc)
        except SyntaxError:
            pass

    head = "\n".join(code.splitlines()[:40])
    block = _leading_docstring(head)
    if block:
        return block

    lines: list[str] = []
    for line in code.splitlines()[:20]:
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            lines.append(stripped.lstrip("#/ ").strip())
        elif stripped and lines:
            break
    if lines:
        return _truncate(" ".join(lines))
    return None


def extract_class_description(code: str, class_name: str, language: str | None = None) -> str | None:
    lang = (language or "").lower().replace("-", "_")
    if lang == "python":
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    doc = ast.get_docstring(node)
                    if doc:
                        return _truncate(doc)
        except SyntaxError:
            pass

    pattern = rf"class\s+{re.escape(class_name)}\b"
    match = re.search(pattern, code)
    if match:
        tail = code[match.end() :]
        return _leading_docstring(tail)
    return None
