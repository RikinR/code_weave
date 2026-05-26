"""Verify text-file chunking strategies for markdown, YAML, and sliding windows.

Covers ``application.ingestion.text_chunking`` chunkers and
``application.ingestion.chunk_strategy.ChunkStrategy`` assignments per format.
"""

from pathlib import Path
from application.ingestion.chunk_strategy import ChunkStrategy
from application.ingestion.text_chunking import chunk_markdown, chunk_requirements, chunk_sliding_window, chunk_yaml, infer_text_kind, process_text_file

def test_chunk_markdown_splits_on_headings():
    text = '# Intro\n\nHello world.\n\n## Setup\n\nRun pip install.\n'
    chunks = chunk_markdown(text)
    assert len(chunks) == 2
    assert chunks[0]['name'] == 'Intro'
    assert 'Hello world' in chunks[0]['code']
    assert chunks[1]['name'] == 'Setup'
    assert chunks[0]['chunk_type'] == 'document'
    assert chunks[0]['chunk_strategy'] == ChunkStrategy.TEXT_STRUCTURAL

def test_chunk_yaml_splits_top_level_keys():
    text = 'service:\n  name: api\n\nversion: 1\n'
    chunks = chunk_yaml(text)
    assert len(chunks) >= 2
    names = {c['name'] for c in chunks}
    assert 'service' in names
    assert 'version' in names
    assert all(c['chunk_strategy'] == ChunkStrategy.TEXT_STRUCTURAL for c in chunks)

def test_chunk_requirements_groups_lines():
    text = 'fastapi>=0.1\nuvicorn>=0.2\n\npytest>=7\n'
    chunks = chunk_requirements(text)
    assert len(chunks) >= 1
    assert 'fastapi' in chunks[0]['code']

def test_sliding_window_uses_sliding_strategy():
    text = 'a' * 5000
    chunks = chunk_sliding_window(text, max_chars=2000, overlap=200)
    assert len(chunks) >= 2
    assert chunks[0]['name'] == 'part-1'
    assert all(c['chunk_strategy'] == ChunkStrategy.TEXT_SLIDING for c in chunks)

def test_infer_text_kind_plain_txt():
    assert infer_text_kind('notes.txt') == 'text'

def test_process_text_file_returns_document_chunks(tmp_path: Path):
    readme = tmp_path / 'README.md'
    readme.write_text('# Title\n\nProject overview.\n', encoding='utf-8')
    result = process_text_file(str(readme))
    assert result['language'] == 'markdown'
    assert len(result['chunks']) >= 1
    assert result['structure'] == {}
    assert result['calls'] == []
    assert result['chunks'][0]['chunk_strategy'] == ChunkStrategy.TEXT_STRUCTURAL

def test_process_text_file_plain_text(tmp_path: Path):
    notes = tmp_path / 'notes.txt'
    notes.write_text('Line one.\nLine two.\n', encoding='utf-8')
    result = process_text_file(str(notes))
    assert result['language'] == 'text'
    assert len(result['chunks']) >= 1
    assert result['chunks'][0]['chunk_strategy'] == ChunkStrategy.TEXT_SLIDING
