from __future__ import annotations

"""Text and context-file chunking when AST parsing is unavailable or skipped.

Pipeline stage: **parse** (alternative to :mod:`process_code` in :mod:`index_folder`).

Handles markdown, YAML, requirements, Dockerfiles, and plain text via structural
or sliding-window splits. Also serves as fallback from :mod:`process_code` on
parse errors or empty AST chunks. Labels chunks with :mod:`chunk_strategy`.
"""
import re
from pathlib import Path
from application.ingestion.chunk_strategy import ChunkStrategy
from application.ingestion.line_numbers import byte_offset_to_line
from infrastructure.file.reader import read_file
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)
_MAX_CHUNK_CHARS = 2000
_OVERLAP_CHARS = 200
_REQUIREMENTS_LINES = 40
_HEADING_RE = re.compile('^(#{1,6})\\s+(.+)$', re.MULTILINE)
_TOP_LEVEL_KEY_RE = re.compile('^([A-Za-z0-9_.-]+)\\s*:', re.MULTILINE)
_DOCKER_FROM_RE = re.compile('^FROM\\s+', re.MULTILINE | re.IGNORECASE)
_TEXT_KIND_BY_SUFFIX: dict[str, str] = {'.md': 'markdown', '.markdown': 'markdown', '.rst': 'markdown', '.yaml': 'yaml', '.yml': 'yaml', '.toml': 'toml', '.dockerfile': 'dockerfile'}
_TEXT_KIND_BY_NAME: dict[str, str] = {'requirements.txt': 'requirements', 'requirements-dev.txt': 'requirements', 'requirements-prod.txt': 'requirements', 'pipfile': 'requirements', 'dockerfile': 'dockerfile', 'containerfile': 'dockerfile'}

def infer_text_kind(path: str | Path) -> str:
    """Classify a non-code path (markdown, yaml, requirements, dockerfile, text)."""
    file_path = Path(path)
    name = file_path.name.lower()
    if name in _TEXT_KIND_BY_NAME:
        return _TEXT_KIND_BY_NAME[name]
    suffix = file_path.suffix.lower()
    if suffix in _TEXT_KIND_BY_SUFFIX:
        return _TEXT_KIND_BY_SUFFIX[suffix]
    if name.startswith('docker-compose') and name.endswith(('.yml', '.yaml')):
        return 'yaml'
    if name.startswith('compose.') and name.endswith(('.yml', '.yaml')):
        return 'yaml'
    return 'text'

def _decode_source(raw: bytes) -> str:
    return raw.decode('utf-8', errors='replace')

def _make_chunk(source: str, name: str, start: int, end: int, *, description: str | None=None, chunk_strategy: ChunkStrategy=ChunkStrategy.TEXT_STRUCTURAL) -> dict:
    code = source[start:end].strip()
    if not code:
        return {}
    raw_bytes = source.encode('utf-8')
    first_line = code.splitlines()[0].strip() if code.splitlines() else name
    return {'name': name[:255], 'code': code, 'description': description or first_line[:500], 'start': start, 'end': end, 'start_line': byte_offset_to_line(raw_bytes, start), 'end_line': byte_offset_to_line(raw_bytes, end), 'chunk_type': 'document', 'chunk_strategy': chunk_strategy}

def _split_positions(source: str, pattern: re.Pattern[str], name_group: int) -> list[tuple[int, int, str]]:
    matches = list(pattern.finditer(source))
    if not matches:
        return []
    sections: list[tuple[int, int, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        name = match.group(name_group).strip()
        sections.append((start, end, name))
    return sections

def chunk_markdown(source: str) -> list[dict]:
    """Split markdown into heading-bounded document chunks."""
    sections = _split_positions(source, _HEADING_RE, 2)
    if not sections:
        chunk = _make_chunk(source, Path('document').stem or 'document', 0, len(source))
        return [chunk] if chunk else []
    chunks: list[dict] = []
    for start, end, name in sections:
        chunk = _make_chunk(source, name, start, end)
        if chunk:
            chunks.append(chunk)
    return chunks

def chunk_yaml(source: str) -> list[dict]:
    """Split YAML/TOML-like text on top-level keys, with sliding fallback."""
    sections = _split_positions(source, _TOP_LEVEL_KEY_RE, 1)
    if len(sections) <= 1:
        return chunk_sliding_window(source)
    chunks: list[dict] = []
    for start, end, name in sections:
        chunk = _make_chunk(source, name, start, end)
        if chunk:
            chunks.append(chunk)
    return chunks

def chunk_requirements(source: str) -> list[dict]:
    """Chunk dependency list files by blank-line groups or fixed line windows."""
    lines = source.splitlines()
    if not lines:
        return []
    groups: list[tuple[int, int]] = []
    group_start = 0
    for index, line in enumerate(lines):
        if not line.strip() and index > group_start:
            groups.append((group_start, index))
            group_start = index + 1
    if group_start < len(lines):
        groups.append((group_start, len(lines)))
    if len(groups) == 1 and len(lines) > _REQUIREMENTS_LINES:
        groups = []
        for start in range(0, len(lines), _REQUIREMENTS_LINES):
            groups.append((start, min(start + _REQUIREMENTS_LINES, len(lines))))
    chunks: list[dict] = []
    for part, (start_line, end_line) in enumerate(groups, start=1):
        start = sum((len(lines[i]) + 1 for i in range(start_line)))
        end = sum((len(lines[i]) + 1 for i in range(end_line)))
        name = f'dependencies-{part}'
        chunk = _make_chunk(source, name, start, min(end, len(source)))
        if chunk:
            chunks.append(chunk)
    return chunks

def chunk_dockerfile(source: str) -> list[dict]:
    """Split Dockerfiles on ``FROM`` stage boundaries."""
    sections = _split_positions(source, _DOCKER_FROM_RE, 0)
    if not sections:
        return chunk_sliding_window(source)
    chunks: list[dict] = []
    for part, (start, end, _) in enumerate(sections, start=1):
        match = _DOCKER_FROM_RE.search(source, start)
        name = match.group(0).strip() if match else f'stage-{part}'
        chunk = _make_chunk(source, name, start, end)
        if chunk:
            chunks.append(chunk)
    return chunks

def chunk_sliding_window(source: str, *, max_chars: int=_MAX_CHUNK_CHARS, overlap: int=_OVERLAP_CHARS) -> list[dict]:
    """Split long plain text into overlapping fixed-size chunks."""
    text = source.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        chunk = _make_chunk(source, 'document', 0, len(source), chunk_strategy=ChunkStrategy.TEXT_SLIDING)
        return [chunk] if chunk else []
    chunks: list[dict] = []
    start = 0
    part = 1
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunk = _make_chunk(source, f'part-{part}', start, end, chunk_strategy=ChunkStrategy.TEXT_SLIDING)
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
        part += 1
    return chunks

def chunk_text_source(source: str, kind: str) -> list[dict]:
    """Dispatch to the appropriate text chunker for ``kind``."""
    if kind == 'markdown':
        return chunk_markdown(source)
    if kind in {'yaml', 'toml'}:
        return chunk_yaml(source)
    if kind == 'requirements':
        return chunk_requirements(source)
    if kind == 'dockerfile':
        return chunk_dockerfile(source)
    return chunk_sliding_window(source)

def _file_description(source: str, kind: str) -> str | None:
    if kind == 'markdown':
        match = _HEADING_RE.search(source)
        if match:
            return match.group(2).strip()[:500]
    first = next((line.strip() for line in source.splitlines() if line.strip()), None)
    return first[:500] if first else None

def indexing_notice_for(mode: str, *, file_path: str | None=None) -> str | None:
    """User-facing explanation when a file was indexed without AST chunking."""
    path = Path(file_path) if file_path else None
    suffix = path.suffix.lower() if path else ''
    if mode == 'unsupported_extension':
        ext_label = suffix or 'this'
        return f'Indexed as plain text (section chunks, like README). Tree-sitter AST chunking is not used for {ext_label} files.'
    if mode == 'ast_empty':
        return 'Indexed as plain text — no functions or classes were extracted from the parse tree.'
    if mode == 'parse_error':
        return 'Indexed as plain text — Tree-sitter could not parse this file.'
    return None

def _language_for_text_path(file_path: str, kind: str) -> tuple[str, str]:
    from application.ingestion.source_filter import is_text_indexed_unsupported_extension
    path = Path(file_path)
    if is_text_indexed_unsupported_extension(path):
        ext = path.suffix.lower().lstrip('.') or 'text'
        return (ext, 'unsupported_extension')
    if kind != 'text':
        return (kind, 'text')
    return ('text', 'text')

def process_text_file(file_path: str) -> dict:
    """Parse a context or text file into document chunks for :mod:`persist`."""
    kind = infer_text_kind(file_path)
    logger.info('process_text_file: start path=%s kind=%s', file_path, kind)
    raw = read_file(file_path)
    source = _decode_source(raw)
    chunks = chunk_text_source(source, kind)
    language, indexing_mode = _language_for_text_path(file_path, kind)
    if not chunks:
        logger.warning('process_text_file: no chunks for path=%s', file_path)
    return {'file': file_path, 'language': language, 'indexing_mode': indexing_mode, 'indexing_notice': indexing_notice_for(indexing_mode, file_path=file_path), 'description': _file_description(source, kind), 'chunks': chunks, 'structure': {}, 'calls': [], 'ast_tree': None}

def process_text_file_as_fallback(file_path: str, *, reason: str, language_hint: str | None=None) -> dict:
    """Index via text chunking when :mod:`process_code` cannot use the AST."""
    result = process_text_file(file_path)
    result['indexing_mode'] = reason
    if language_hint:
        result['language'] = language_hint
    result['indexing_notice'] = indexing_notice_for(reason, file_path=file_path)
    return result
