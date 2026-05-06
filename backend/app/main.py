from infrastructure.logging.logger import get_logger
from application.ingestion.process_code import process_file

logger = get_logger(__name__)

if __name__ == "__main__":
    logger.debug("calling process file function for file test_data/sample.py")
    result = process_file("test_data/course_export.py")
    