from pathlib import Path
from application.ingestion.folder import process_folder
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    folder = Path("test_data/")
    logger.debug("scanning %s for parseable source files", folder)
    result = process_folder(folder)