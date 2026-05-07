from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

def read_file(path: str) -> bytes:
    logger.debug("read_file: open %s", path)
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as exc:
        logger.error("read_file: failed to read %s: %s", path, exc)
        raise