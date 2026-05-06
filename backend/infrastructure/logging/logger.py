import logging
import logging.config

from infrastructure.logging.config import LOGGING_CONFIG


def _apply_logging_config() -> None:
    logging.config.dictConfig(LOGGING_CONFIG)
    root = logging.getLogger()
    root.disabled = False
    root.setLevel(logging.DEBUG)
    for handler in root.handlers:
        handler.setLevel(logging.DEBUG)


_apply_logging_config()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)