"""Byte-offset to 1-based line number conversion for parsed chunks.

Pipeline stage: **parse** (used by :mod:`process_code`, :mod:`text_chunking`, and
:mod:`ast_chunking` when building chunk metadata for :mod:`persist`).
"""


def byte_offset_to_line(code: bytes, byte_offset: int) -> int:
    """Return the 1-based line number containing ``byte_offset`` in ``code``."""
    if byte_offset <= 0:
        return 1
    return code[:byte_offset].count(b'\n') + 1
