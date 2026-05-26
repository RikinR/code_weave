"""Verify AST-based code chunking, deduplication, and empty-AST fallbacks.

Covers ``application.ingestion.process_code``, ``ast_chunking.dedupe_chunks``,
``chunk_strategy.ChunkStrategy``, and text-indexing paths for unsupported
extensions such as CSS.
"""

from pathlib import Path
from application.ingestion.ast_chunking import dedupe_chunks
from application.ingestion.chunk_strategy import ChunkStrategy
from application.ingestion.process_code import process_code_file, process_file

def test_process_code_file_extracts_python_functions(tmp_path: Path):
    py_file = tmp_path / 'main.py'
    py_file.write_text('def alpha():\n    pass\n\ndef beta():\n    pass\n', encoding='utf-8')
    result = process_code_file(str(py_file))
    assert result['indexing_mode'] == 'ast'
    names = {c['name'] for c in result['chunks']}
    assert names >= {'alpha', 'beta'}
    assert all(c['chunk_strategy'] == ChunkStrategy.AST_SEMANTIC for c in result['chunks'])
    assert result.get('ast_tree') is not None

def test_process_file_alias_matches_process_code_file(tmp_path: Path):
    py_file = tmp_path / 'main.py'
    py_file.write_text('def run():\n    return 0\n', encoding='utf-8')
    assert process_file(str(py_file))['chunks'][0]['name'] == 'run'

def test_ast_empty_falls_back_to_text(tmp_path: Path):
    py_file = tmp_path / 'empty.py'
    py_file.write_text('# only a comment\n', encoding='utf-8')
    result = process_code_file(str(py_file))
    assert result['indexing_mode'] == 'ast_empty'
    assert len(result['chunks']) >= 1
    assert result['chunks'][0]['chunk_type'] == 'document'

def test_dedupe_prefers_function_over_class():
    function = {'name': 'm', 'start': 10, 'end': 50, 'chunk_type': 'function'}
    class_chunk = {'name': 'C', 'start': 0, 'end': 100, 'chunk_type': 'class'}
    kept = dedupe_chunks([class_chunk, function])
    assert len(kept) == 1
    assert kept[0]['chunk_type'] == 'function'

def test_css_indexed_as_text_with_notice(tmp_path: Path):
    css = tmp_path / 'styles.css'
    css.write_text('body { color: red; }\n', encoding='utf-8')
    from application.ingestion.source_filter import classify_ingestible_file
    from application.ingestion.text_chunking import process_text_file
    assert classify_ingestible_file(css) == 'text'
    result = process_text_file(str(css))
    assert result['language'] == 'css'
    assert result['indexing_mode'] == 'unsupported_extension'
    assert '.css' in (result['indexing_notice'] or '')
