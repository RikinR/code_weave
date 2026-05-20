from __future__ import annotations
import zipfile
from pathlib import Path
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

DEFAULT_MAX_UPLOAD_BYTES = 100 * 1024 * 1024
DEFAULT_MAX_FILES = 10_000
DEFAULT_MAX_UNCOMPRESSED_RATIO = 50


class ZipExtractionError(ValueError):
    pass


def extract_zip(
    zip_path: Path,
    dest_dir: Path,
    *,
    max_bytes: int = DEFAULT_MAX_UPLOAD_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
    max_ratio: int = DEFAULT_MAX_UNCOMPRESSED_RATIO,
) -> Path:
    if not zip_path.is_file():
        raise ZipExtractionError(f"ZIP not found: {zip_path}")

    if zip_path.stat().st_size > max_bytes:
        raise ZipExtractionError(
            f"ZIP exceeds maximum size ({zip_path.stat().st_size} > {max_bytes} bytes)"
        )

    dest_dir.mkdir(parents=True, exist_ok=True)
    total_uncompressed = 0
    file_count = 0
    compressed_size = zip_path.stat().st_size or 1

    with zipfile.ZipFile(zip_path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            file_count += 1
            if file_count > max_files:
                raise ZipExtractionError(f"ZIP contains more than {max_files} files")

            total_uncompressed += info.file_size
            if total_uncompressed / compressed_size > max_ratio:
                raise ZipExtractionError("ZIP compression ratio exceeds safety limit")

            member = Path(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise ZipExtractionError(f"Unsafe path in archive: {info.filename}")

            target = (dest_dir / member).resolve()
            if not str(target).startswith(str(dest_dir.resolve())):
                raise ZipExtractionError(f"Path traversal blocked: {info.filename}")

        zf.extractall(dest_dir)

    roots = [p for p in dest_dir.iterdir() if p.name != "__MACOSX"]
    if len(roots) == 1 and roots[0].is_dir():
        logger.info("zip_extract: using single root folder %s", roots[0])
        return roots[0]

    logger.info("zip_extract: using dest_dir %s", dest_dir)
    return dest_dir
