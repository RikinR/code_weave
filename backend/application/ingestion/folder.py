from pathlib import Path
from application.ingestion.process_code import process_file
from application.ingestion.source_filter import iter_source_files
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


def process_folder(folder: Path) -> list[dict]:
    result: list[dict] = []
    if not folder.is_dir():
        logger.warning("folder does not exist or is not a directory: %s", folder)
        return result

    for file in iter_source_files(folder):
        path = str(file)
        logger.debug("parse %s (language inferred from extension)", path)
        try:
            result.append(process_file(file_path=path))
        except RuntimeError as exc:
            logger.warning("skip %s: %s", path, exc)
        except Exception:
            logger.exception("failed to process %s", path)

    logger.info("processed %s file(s) from %s", len(result), folder)
    return result
