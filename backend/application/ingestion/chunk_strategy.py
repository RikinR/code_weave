from __future__ import annotations

"""Chunk strategy labels for ingestion and embedding metadata.

Pipeline stage: metadata during **parse** and **persist**.

Defines how each chunk was produced (AST semantic vs text structural/sliding).
Used when storing :class:`ChunkModel` rows in :mod:`persist` and when formatting
embedding text in :mod:`chunk_text`.
"""
from enum import StrEnum

class ChunkStrategy(StrEnum):
    """How a chunk was split from source text."""

    AST_SEMANTIC = 'ast_semantic'
    TEXT_STRUCTURAL = 'text_structural'
    TEXT_SLIDING = 'text_sliding'

_CHUNK_TYPE_LABELS: dict[str, str] = {
    'function': 'function',
    'method': 'function',
    'class': 'class',
    'module': 'module',
    'document': 'section',
}

def embedding_segment_label(chunk_type: str | None) -> str:
    """Map a chunk type to a human-readable segment label for embedding text."""
    return _CHUNK_TYPE_LABELS.get(chunk_type or 'function', 'function')

def chunk_strategy_from_chunk(chunk: dict) -> str:
    """Infer :class:`ChunkStrategy` from chunk metadata produced by parse/chunk modules."""
    explicit = chunk.get('chunk_strategy')
    if explicit:
        return str(explicit)
    chunk_type = chunk.get('chunk_type') or 'function'
    if chunk_type == 'document':
        return ChunkStrategy.TEXT_STRUCTURAL
    if chunk_type in ('class', 'module'):
        return ChunkStrategy.AST_SEMANTIC
    if chunk_type in ('function', 'method'):
        return ChunkStrategy.AST_SEMANTIC
    return ChunkStrategy.TEXT_SLIDING
