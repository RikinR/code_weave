from __future__ import annotations

"""Heuristic extraction of docstrings and descriptions from source text.

Pipeline stage: **parse** (used by :mod:`process_code` and :mod:`text_chunking`).

Pulls module, class, and function documentation from AST docstrings, leading
comments, and lightweight code-pattern inference. Generic placeholders can be
refined later by :mod:`summarize_description`.
"""
import ast
import re
_MAX_LEN = 1000
_GENERIC_LOCATION_RE = re.compile('^(Function|Method|Class|Source file|Folder|Indexed repository)\\s+.+', re.IGNORECASE)

def _truncate(text: str) -> str:
    cleaned = re.sub('\\s+', ' ', text.strip())
    if len(cleaned) <= _MAX_LEN:
        return cleaned
    return cleaned[:_MAX_LEN - 3].rstrip() + '...'

def is_generic_description(description: str | None) -> bool:
    """Return True when a stored description is too vague to show users."""
    if not description or not description.strip():
        return True
    text = description.strip()
    if len(text) < 24:
        return True
    if _GENERIC_LOCATION_RE.match(text) and ' in ' in text and ('.' in text.split(' in ', 1)[-1]):
        return True
    if re.match('^This function \\w+\\.$', text, re.IGNORECASE):
        return True
    lowered = text.lower()
    if lowered.startswith('this function ') and len(text.split()) <= 5:
        return True
    name_tail = text.split()[-1].rstrip('.') if text.endswith('.') else ''
    if lowered.startswith('this function ') and name_tail and name_tail.endswith('s'):
        base = name_tail[:-1]
        if base and base in lowered:
            return True
    return False

def _leading_docstring(code: str) -> str | None:
    for pattern in ('^\\s*"""(.*?)"""', "^\\s*'''(.*?)'''", '^\\s*/\\*\\*(.*?)\\*/'):
        match = re.match(pattern, code, re.DOTALL)
        if match:
            text = match.group(1)
            if pattern.endswith('\\*/'):
                text = re.sub('^\\s*\\*\\s?', '', text, flags=re.MULTILINE)
            return _truncate(text)
    return None

def extract_preceding_comments(source: str, before_byte: int) -> str | None:
    """Collect block or line comments immediately above a definition byte offset."""
    if before_byte <= 0:
        return None
    prefix = source[:before_byte]
    lines = prefix.splitlines()
    if not lines:
        return None
    collected: list[str] = []
    idx = len(lines) - 1
    while idx >= 0 and (not lines[idx].strip()):
        idx -= 1
    if idx < 0:
        return None
    line = lines[idx].strip()
    if line.endswith('*/'):
        block_lines = [line]
        idx -= 1
        while idx >= 0:
            block_lines.insert(0, lines[idx].strip())
            if lines[idx].strip().startswith('/**') or lines[idx].strip().startswith('/*'):
                break
            idx -= 1
        block = '\n'.join(block_lines)
        match = re.search('/\\*\\*(.*?)\\*/', block, re.DOTALL)
        if match:
            text = re.sub('^\\s*\\*\\s?', '', match.group(1), flags=re.MULTILINE)
            return _truncate(text.strip())
        return None
    while idx >= 0:
        stripped = lines[idx].strip()
        if stripped.startswith('//'):
            collected.insert(0, stripped[2:].strip())
            idx -= 1
            continue
        if stripped.startswith('#'):
            collected.insert(0, stripped.lstrip('#').strip())
            idx -= 1
            continue
        break
    if collected:
        return _truncate(' '.join(collected))
    return None

def _camel_to_words(name: str) -> str:
    spaced = re.sub('([a-z0-9])([A-Z])', '\\1 \\2', name)
    spaced = re.sub('[_-]+', ' ', spaced)
    return spaced.strip().lower()

def infer_description_from_code(code: str, *, name: str, language: str | None=None) -> str | None:
    """Infer a short behavioral description from code patterns when no docstring exists."""
    if not code.strip():
        return None
    doc = extract_function_description(code, language=language) or _leading_docstring(code)
    if doc:
        return doc
    if re.search('^\\s*class\\s+\\w+', code, re.MULTILINE):
        return _infer_class_description(code, name=name, language=language)
    behaviors: list[str] = []
    if re.search('\\bjwt\\.decode\\s*\\(', code, re.IGNORECASE):
        behaviors.append('Decodes a JWT access token and returns its payload claims, or None when the token is invalid or expired.')
    elif re.search('\\bjwt\\.encode\\s*\\(', code, re.IGNORECASE):
        behaviors.append('Creates a signed JWT from a claims dictionary using the configured secret and algorithm.')
    if re.search('\\btry\\s*:', code) and re.search('\\bexcept\\b', code):
        if not behaviors:
            behaviors.append('Runs token or parsing logic inside try/except and returns None (or a safe default) on failure.')
    props = _meaningful_property_paths(code)
    if props:
        joined = ', '.join(props[:3])
        behaviors.append(f'Uses {joined} from settings or inputs.')
    if re.search('\\.sort\\s*\\(', code):
        behaviors.append('Sorts a list using a comparator or key derived from item fields.')
    if re.search('\\b(?:map|forEach|filter|reduce)\\s*\\(', code):
        behaviors.append('Iterates over a collection to transform or filter elements.')
    if re.search('\\breturn\\b', code) and (not behaviors):
        behaviors.append('Computes and returns a value from its parameters.')
    if behaviors:
        return _truncate(' '.join(behaviors))
    name_words = _camel_to_words(name.lstrip('_'))
    if name_words and len(name_words.split()) >= 2:
        return _truncate(f'Implements {_natural_name(name_words)}.')
    return None

def _natural_name(name_words: str) -> str:
    return name_words.replace('_', ' ')

def _infer_class_description(code: str, *, name: str, language: str | None=None) -> str | None:
    lang = (language or '').lower().replace('-', '_')
    if lang == 'python':
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    doc = ast.get_docstring(node)
                    if doc:
                        return _truncate(doc)
        except SyntaxError:
            pass
    lowered = code.lower()
    if 'deque' in lowered and 'timestamp' in lowered:
        return 'Stores recent request timestamps in a deque, used to enforce per-client rate limits.'
    if 'field(default_factory' in code or '@dataclass' in code:
        label = _natural_name(_camel_to_words(name.lstrip('_')))
        fields = re.findall('^\\s+([A-Za-z_]\\w*)\\s*:', code, re.MULTILINE)
        if fields:
            field_list = ', '.join(fields[:4])
            return _truncate(f'Data class holding {field_list} for {label or "internal"} state.')
        return _truncate(f'Data class used as a {label or "structured"} record in this module.')
    if re.search('^\\s*class\\s+\\w+', code, re.MULTILINE):
        return _truncate(f'Defines the {_natural_name(_camel_to_words(name.lstrip("_")))} type used in this file.')
    return None

def _verb_phrase(name_words: str) -> str:
    tokens = name_words.split()
    if not tokens:
        return 'performs an operation'
    first = tokens[0]
    verb_map = {'get': 'retrieves', 'set': 'updates', 'is': 'checks whether', 'has': 'checks for', 'reorder': 'reorders', 'sort': 'sorts', 'build': 'builds', 'create': 'creates', 'update': 'updates', 'delete': 'removes', 'remove': 'removes', 'parse': 'parses', 'format': 'formats', 'validate': 'validates', 'compute': 'computes', 'calculate': 'calculates', 'fetch': 'fetches', 'load': 'loads', 'save': 'stores', 'handle': 'handles', 'process': 'processes', 'extract': 'extracts', 'transform': 'transforms'}
    verb = verb_map.get(first, f'{first}s' if not first.endswith('s') else first)
    rest = ' '.join(tokens[1:])
    if rest:
        return f'{verb} {rest}'
    return verb

def _meaningful_property_paths(code: str) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    skip_roots = {'length', 'push', 'pop', 'then', 'catch', 'prototype', 'decode', 'encode', 'strip', 'lower', 'upper', 'get', 'set', 'append', 'extend'}
    for match in re.finditer('(?:\\?\\.)?\\.([A-Za-z_][\\w]*(?:\\.[A-Za-z_][\\w]*)*)', code):
        path = match.group(1)
        root = path.split('.')[0]
        if root in skip_roots:
            continue
        if path not in seen:
            seen.add(path)
            paths.append(path.replace('.', ' → '))
    return paths

def extract_function_description(code: str, language: str | None=None) -> str | None:
    """Return a function docstring from AST or leading comment block."""
    lang = (language or '').lower().replace('-', '_')
    if lang == 'python':
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    doc = ast.get_docstring(node)
                    if doc:
                        return _truncate(doc)
        except SyntaxError:
            pass
    return _leading_docstring(code)

def resolve_function_description(*, source: str, chunk_code: str, definition_start: int, name: str, language: str | None=None) -> str | None:
    """Pick the best available description for one function chunk."""
    doc = extract_function_description(chunk_code, language=language)
    if doc:
        return doc
    preceding = extract_preceding_comments(source, definition_start)
    if preceding:
        return preceding
    return infer_description_from_code(chunk_code, name=name, language=language)

def extract_file_description(code: str, language: str | None=None) -> str | None:
    """Return module-level documentation or leading comment summary."""
    lang = (language or '').lower().replace('-', '_')
    if lang == 'python':
        try:
            tree = ast.parse(code)
            doc = ast.get_docstring(tree)
            if doc:
                return _truncate(doc)
        except SyntaxError:
            pass
    head = '\n'.join(code.splitlines()[:40])
    block = _leading_docstring(head)
    if block:
        return block
    lines: list[str] = []
    for line in code.splitlines()[:20]:
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('//'):
            lines.append(stripped.lstrip('#/ ').strip())
        elif stripped and lines:
            break
    if lines:
        return _truncate(' '.join(lines))
    return None

def extract_class_description(code: str, class_name: str, language: str | None=None) -> str | None:
    """Return documentation for the named class definition."""
    lang = (language or '').lower().replace('-', '_')
    if lang == 'python':
        try:
            tree = ast.parse(code)
            for node in tree.body:
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    doc = ast.get_docstring(node)
                    if doc:
                        return _truncate(doc)
        except SyntaxError:
            pass
    pattern = f'class\\s+{re.escape(class_name)}\\b'
    match = re.search(pattern, code)
    if match:
        tail = code[match.end():]
        return _leading_docstring(tail)
    return None
