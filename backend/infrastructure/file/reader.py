"""Binary-safe filesystem read helper for ingestion and graph detail views.

Used when loading source bytes from extracted upload trees during indexing and
when :mod:`application.graph.node_detail` displays file or function code.
"""

from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)

def read_file(path: str) -> bytes:
    """Read and return the full contents of ``path`` as bytes."""
    logger.debug('read_file: open %s', path)
    try:
        with open(path, 'rb') as f:
            return f.read()
    except OSError as exc:
        logger.error('read_file: failed to read %s: %s', path, exc)
        raise
