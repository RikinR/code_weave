"""Application-wide logger factory.

Import :func:`get_logger` from here in any module; configuration is applied
once from :mod:`infrastructure.logging.config` at module load.
"""

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
    """Return a named logger under the configured root handlers."""
    return logging.getLogger(name)
