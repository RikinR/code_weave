from __future__ import annotations

"""Normalize file paths between disk, uploads, and persisted repository rows.

Pipeline stage: **persist** and post-ingestion APIs.

Converts absolute upload paths to repository-relative POSIX paths and resolves
relative paths back to on-disk locations for hashing in :mod:`persist`.
"""
from pathlib import Path, PurePosixPath
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)

def relative_to_repo(file_path: str, repo_root: str | Path, repo_name: str | None=None) -> str:
    """Return a repository-relative POSIX path for display and storage."""
    if not file_path:
        return file_path
    normalized = file_path.replace('\\', '/')
    path = Path(file_path)
    if not path.is_absolute():
        return PurePosixPath(normalized).as_posix()
    root = Path(repo_root).resolve()
    try:
        rel = path.resolve().relative_to(root)
        return rel.as_posix()
    except ValueError:
        pass
    root_posix = root.as_posix()
    if normalized.startswith(root_posix + '/'):
        return normalized[len(root_posix) + 1:]
    if repo_name:
        marker = f'/{repo_name}/'
        idx = normalized.find(marker)
        if idx >= 0:
            return normalized[idx + len(marker):]
    parts = PurePosixPath(normalized).parts
    if 'uploads' in parts:
        upload_idx = parts.index('uploads')
        tail = parts[upload_idx + 2:]
        if tail:
            return '/'.join(tail)
    logger.warning('relative_to_repo: could not relativize %r against %r; using basename', file_path, repo_root)
    return Path(file_path).name

def resolve_repo_path(file_path: str, repo_root: str | Path) -> Path:
    """Resolve ``file_path`` to an absolute path under ``repo_root`` when relative."""
    path = Path(file_path)
    if path.is_absolute():
        return path
    return Path(repo_root).resolve() / path
