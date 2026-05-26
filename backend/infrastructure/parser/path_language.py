"""File extension to Tree-sitter language id mapping.

Used during ingestion scanning to infer parser language from path and to gate
supported uploads via :func:`is_supported_extension`.
"""

from __future__ import annotations
from pathlib import Path
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)

class UnsupportedLanguageError(ValueError):
    """Raised when a file path has no known extension-to-language mapping."""

EXTENSION_TO_LANGUAGE: dict[str, str] = {'.bash': 'bash', '.c': 'c', '.cjs': 'javascript', '.cc': 'cpp', '.cl': 'commonlisp', '.cpp': 'cpp', '.cs': 'c_sharp', '.csx': 'c_sharp', '.css': 'css', '.cts': 'typescript', '.cxx': 'cpp', '.dockerfile': 'dockerfile', '.dot': 'dot', '.ejs': 'embedded_template', '.el': 'elisp', '.elm': 'elm', '.erl': 'erlang', '.ex': 'elixir', '.exs': 'elixir', '.f03': 'fortran', '.f08': 'fortran', '.f90': 'fortran', '.f95': 'fortran', '.go': 'go', '.gv': 'dot', '.hack': 'hack', '.h': 'c', '.hh': 'cpp', '.hbs': 'embedded_template', '.hpp': 'cpp', '.hs': 'haskell', '.hrl': 'erlang', '.hxx': 'cpp', '.htm': 'html', '.html': 'html', '.java': 'java', '.jl': 'julia', '.js': 'javascript', '.json': 'json', '.jsx': 'javascript', '.kt': 'kotlin', '.ksh': 'bash', '.kts': 'kotlin', '.lhs': 'haskell', '.lisp': 'commonlisp', '.lua': 'lua', '.markdown': 'markdown', '.md': 'markdown', '.mjs': 'javascript', '.mk': 'make', '.ml': 'ocaml', '.mli': 'ocaml', '.mm': 'objc', '.mts': 'typescript', '.phtml': 'php', '.php': 'php', '.pl': 'perl', '.pm': 'perl', '.py': 'python', '.pyi': 'python', '.pyw': 'python', '.ql': 'ql', '.r': 'r', '.R': 'r', '.rb': 'ruby', '.regex': 'regex', '.rs': 'rust', '.rst': 'rst', '.sass': 'css', '.scala': 'scala', '.scss': 'css', '.sc': 'scala', '.sh': 'bash', '.sql': 'sql', '.tf': 'hcl', '.tfvars': 'hcl', '.toml': 'toml', '.ts': 'typescript', '.tsx': 'tsx', '.yaml': 'yaml', '.yml': 'yaml', '.zsh': 'bash'}

def is_supported_extension(file_path: str | Path) -> bool:
    """Return whether the path suffix maps to a known Tree-sitter language."""
    suffix = Path(file_path).suffix.lower()
    return suffix in EXTENSION_TO_LANGUAGE

def infer_language(file_path: str | Path) -> str:
    """Map a file path to a Tree-sitter language id, or raise :class:`UnsupportedLanguageError`."""
    suffix = Path(file_path).suffix.lower()
    if not suffix:
        logger.warning('infer_language: no extension on %r; pass lang= explicitly', file_path)
        raise UnsupportedLanguageError(f'No file extension on {file_path!r}; pass lang= explicitly.')
    lang = EXTENSION_TO_LANGUAGE.get(suffix)
    if lang is None:
        supported = ', '.join(sorted({f"*.{ext.lstrip('.')}" for ext in EXTENSION_TO_LANGUAGE}))
        logger.warning('infer_language: unsupported suffix=%s for path=%r', suffix, file_path)
        raise UnsupportedLanguageError(f'Unsupported extension {suffix!r} for {file_path!r}. Known: {supported}')
    logger.debug('infer_language: %r -> %s', file_path, lang)
    return lang
