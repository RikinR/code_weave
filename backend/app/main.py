from pathlib import Path

from application.ingestion.index_folder import index_folder
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

if __name__ == "__main__":
    folder = Path("test_data/")
    logger.debug("indexing %s (parse, embed, store)", folder)
    result = index_folder(folder)
    logger.info("index_folder result: %s", result)