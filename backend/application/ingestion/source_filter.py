from __future__ import annotations

"""File discovery and classification for repository ingestion.

Pipeline stage: **scan** (after :mod:`zip_extract`, before parse).

Walks extracted trees, skips dependency and cache directories, and classifies
paths as code, context (Dockerfile, README, YAML), or plain text. Used by
:mod:`pipeline_runner` for counts and by :mod:`index_folder` to choose
:mod:`process_code` vs :mod:`text_chunking`.
"""
from pathlib import Path
from typing import Literal
from infrastructure.parser.path_language import is_supported_extension
FileKind = Literal['code', 'context', 'text']
"""Ingestion category assigned by :func:`classify_ingestible_file`."""
_SKIP_DIR_NAMES = frozenset({'.git', '.hg', '.svn', '.venv', 'venv', 'virtualenv', 'env', 'node_modules', '__pycache__', '.mypy_cache', '.pytest_cache', '.tox', '.nox', 'dist', 'build', 'target', 'logs', 'log', '.idea', '.vscode', '.cursor', 'htmlcov', '.eggs', 'site-packages', '.npm', '.yarn', '.pnpm-store', 'coverage', '.gradle', '.next', '.nuxt', 'out', '.dart_tool', '.pub-cache', 'vendor', 'pods', 'carthage', 'deriveddata', '.terraform', '.serverless', 'bower_components', 'jspm_packages', 'cache', '.cache', 'tmp', 'temp', 'bin', 'obj'})
_CONTEXT_EXTENSIONS = frozenset({'.dockerfile', '.markdown', '.md', '.rst', '.toml', '.yaml', '.yml'})
_CONTEXT_FILE_NAMES = frozenset({'containerfile', 'dockerfile', 'pipfile', 'requirements-dev.txt', 'requirements-prod.txt', 'requirements.txt'})
_TEXT_EXTENSIONS = frozenset({'.cfg', '.conf', '.ini', '.mdown', '.properties', '.text', '.txt'})
_TEXT_INDEXED_UNSUPPORTED_EXTENSIONS = frozenset({'.css', '.htm', '.html', '.sass', '.scss'})
_SKIP_EXTENSIONS = frozenset({'.dot', '.ejs', '.gv', '.hbs', '.json', '.ql', '.regex', '.sql', '.tf', '.tfvars'})

def is_text_indexed_unsupported_extension(path: Path) -> bool:
    """Return True for extensions indexed as text without Tree-sitter support (e.g. HTML)."""
    return path.suffix.lower() in _TEXT_INDEXED_UNSUPPORTED_EXTENSIONS
_SKIP_FILE_NAMES = frozenset({'.dockerignore', '.editorconfig', '.gitattributes', '.gitignore', '.prettierignore', '.prettierrc', 'cargo.lock', 'gemfile.lock', 'package-lock.json', 'poetry.lock', 'yarn.lock'})
_SKIP_NAME_PREFIXES = ('.env',)

def _path_has_skipped_dir(path: Path) -> bool:
    return any((part.lower() in _SKIP_DIR_NAMES for part in path.parts))

def _is_skipped_file_name(name: str) -> bool:
    lower = name.lower()
    if lower in _SKIP_FILE_NAMES:
        return True
    if lower.startswith(_SKIP_NAME_PREFIXES):
        return True
    if lower.endswith('.log'):
        return True
    return False

def _is_context_file(path: Path) -> bool:
    lower = path.name.lower()
    if lower in _CONTEXT_FILE_NAMES:
        return True
    if path.suffix.lower() in _CONTEXT_EXTENSIONS:
        return True
    if lower.startswith('docker-compose') and lower.endswith(('.yml', '.yaml')):
        return True
    if lower.startswith('compose.') and lower.endswith(('.yml', '.yaml')):
        return True
    return False

def _is_text_file(path: Path) -> bool:
    suffix = path.suffix.lower()
    return suffix in _TEXT_EXTENSIONS or suffix in _TEXT_INDEXED_UNSUPPORTED_EXTENSIONS

def classify_ingestible_file(path: Path) -> FileKind | None:
    """Classify a file as code, context, text, or skip (``None``)."""
    if not path.is_file():
        return None
    if _path_has_skipped_dir(path):
        return None
    if _is_skipped_file_name(path.name):
        return None
    if _is_context_file(path):
        return 'context'
    suffix = path.suffix.lower()
    if suffix in _SKIP_EXTENSIONS:
        return None
    if suffix == '.log':
        return None
    if suffix in _TEXT_INDEXED_UNSUPPORTED_EXTENSIONS:
        return 'text'
    if is_supported_extension(path):
        return 'code'
    if _is_text_file(path):
        return 'text'
    return None

def is_ingestible_source_file(path: Path) -> bool:
    """Return True when ``path`` is classified as parseable source code."""
    return classify_ingestible_file(path) == 'code'

def iter_ingestible_files(folder: Path):
    """Yield code, context, and text files under ``folder``, skipping noise paths."""
    if not folder.is_dir():
        return
    stack: list[Path] = [folder]
    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name.lower() in _SKIP_DIR_NAMES:
                    continue
                stack.append(child)
            elif classify_ingestible_file(child) is not None:
                yield child

def iter_source_files(folder: Path):
    """Yield only code files (subset of :func:`iter_ingestible_files`)."""
    for path in iter_ingestible_files(folder):
        if classify_ingestible_file(path) == 'code':
            yield path
