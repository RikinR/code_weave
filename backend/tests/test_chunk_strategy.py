"""Verify chunk strategy enums, inference rules, and embedding segment labels.

Covers ``application.ingestion.chunk_strategy`` helpers that map chunk types to
strategies and human-readable segment names used during embedding.
"""

from application.ingestion.chunk_strategy import ChunkStrategy, chunk_strategy_from_chunk, embedding_segment_label

def test_embedding_segment_label_function():
    assert embedding_segment_label('function') == 'function'

def test_embedding_segment_label_class_and_module():
    assert embedding_segment_label('class') == 'class'
    assert embedding_segment_label('module') == 'module'

def test_embedding_segment_label_document():
    assert embedding_segment_label('document') == 'section'

def test_chunk_strategy_from_chunk_explicit():
    chunk = {'chunk_type': 'function', 'chunk_strategy': ChunkStrategy.TEXT_SLIDING}
    assert chunk_strategy_from_chunk(chunk) == ChunkStrategy.TEXT_SLIDING

def test_chunk_strategy_from_chunk_inferred():
    assert chunk_strategy_from_chunk({'chunk_type': 'document'}) == ChunkStrategy.TEXT_STRUCTURAL
    assert chunk_strategy_from_chunk({'chunk_type': 'function'}) == ChunkStrategy.AST_SEMANTIC
    assert chunk_strategy_from_chunk({'chunk_type': 'class'}) == ChunkStrategy.AST_SEMANTIC
