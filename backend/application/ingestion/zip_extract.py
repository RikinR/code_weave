from __future__ import annotations

"""Safe ZIP archive extraction and post-extract tree cleanup.

Pipeline stage: **ZIP extract** (first stage in :mod:`pipeline_runner`).

Validates archive size and compression ratio, skips dependency/cache paths via
:mod:`source_filter` rules, extracts to a job directory, prunes noise folders,
and returns the project root for :func:`source_filter.iter_ingestible_files`.
"""
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from application.ingestion.source_filter import _is_skipped_file_name, _path_has_skipped_dir
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)
DEFAULT_MAX_UPLOAD_BYTES = 200 * 1024 * 1024
DEFAULT_MAX_FILES_AFTER_PRUNE = 10000
DEFAULT_MAX_UNCOMPRESSED_RATIO = 50

class ZipExtractionError(ValueError):
    """Raised when an archive fails safety checks or cannot be extracted."""

@dataclass(frozen=True)
class PruneResult:
    """Counts of directories and files removed during post-extract cleanup."""

    removed_dirs: int = 0
    removed_files: int = 0

def should_skip_archive_member(member: Path) -> bool:
    """Return True if a ZIP member should not be extracted (macOS metadata, caches, etc.)."""
    if not member.parts:
        return True
    if member.parts[0] == '__MACOSX':
        return True
    if _path_has_skipped_dir(member):
        return True
    name = member.name
    if name and _is_skipped_file_name(name):
        return True
    return False

def count_tree_files(root: Path) -> int:
    """Count regular files under ``root`` recursively."""
    return sum(1 for path in root.rglob('*') if path.is_file())

def prune_extracted_tree(root: Path) -> PruneResult:
    """Remove skipped directories and file names from an extracted tree."""
    from application.ingestion.source_filter import _SKIP_DIR_NAMES
    removed_dirs = 0
    removed_files = 0
    for path in sorted((p for p in root.rglob('*') if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        if path.name.lower() in _SKIP_DIR_NAMES:
            shutil.rmtree(path, ignore_errors=True)
            removed_dirs += 1
    for path in list(root.rglob('*')):
        if path.is_file() and _is_skipped_file_name(path.name):
            try:
                path.unlink()
                removed_files += 1
            except OSError:
                pass
    return PruneResult(removed_dirs=removed_dirs, removed_files=removed_files)

def _resolve_extract_root(dest_dir: Path) -> Path:
    roots = [p for p in dest_dir.iterdir() if p.name != '__MACOSX']
    if len(roots) == 1 and roots[0].is_dir():
        logger.info('zip_extract: using single root folder %s', roots[0])
        return roots[0]
    logger.info('zip_extract: using dest_dir %s', dest_dir)
    return dest_dir

def extract_zip(zip_path: Path, dest_dir: Path, *, max_bytes: int=DEFAULT_MAX_UPLOAD_BYTES, max_files_after_prune: int=DEFAULT_MAX_FILES_AFTER_PRUNE, max_ratio: int=DEFAULT_MAX_UNCOMPRESSED_RATIO) -> Path:
    """Extract ``zip_path`` into ``dest_dir`` and return the project root path.

    Enforces size, ratio, and file-count limits. Called by
    :func:`pipeline_runner.run_ingestion_job` before file scanning.
    """
    if not zip_path.is_file():
        raise ZipExtractionError(f'ZIP not found: {zip_path}')
    compressed_size = zip_path.stat().st_size
    if compressed_size > max_bytes:
        raise ZipExtractionError(f'ZIP exceeds maximum size ({compressed_size} > {max_bytes} bytes)')
    dest_dir.mkdir(parents=True, exist_ok=True)
    total_uncompressed = 0
    extracted_count = 0
    compressed_size = compressed_size or 1
    to_extract: list[zipfile.ZipInfo] = []
    with zipfile.ZipFile(zip_path, 'r') as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            member = Path(info.filename)
            if should_skip_archive_member(member):
                continue
            if member.is_absolute() or '..' in member.parts:
                raise ZipExtractionError(f'Unsafe path in archive: {info.filename}')
            target = (dest_dir / member).resolve()
            if not str(target).startswith(str(dest_dir.resolve())):
                raise ZipExtractionError(f'Path traversal blocked: {info.filename}')
            extracted_count += 1
            total_uncompressed += info.file_size
            if total_uncompressed / compressed_size > max_ratio:
                raise ZipExtractionError('ZIP compression ratio exceeds safety limit')
            to_extract.append(info)
        for info in to_extract:
            zf.extract(info, dest_dir)
    logger.info('zip_extract: extracted %d files (skipped venv/cache/env paths in archive)', extracted_count)
    root = _resolve_extract_root(dest_dir)
    prune_stats = prune_extracted_tree(root)
    if prune_stats.removed_dirs or prune_stats.removed_files:
        logger.info('zip_extract: pruned %d dirs and %d files from %s', prune_stats.removed_dirs, prune_stats.removed_files, root)
    remaining = count_tree_files(root)
    if remaining > max_files_after_prune:
        raise ZipExtractionError(f'Project still has {remaining} files after removing dependency, cache, and env folders (limit {max_files_after_prune}). Upload a smaller codebase or exclude large assets.')
    return root
