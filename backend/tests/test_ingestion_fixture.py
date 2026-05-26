"""Verify end-to-end ingestion classification and chunking on a mixed fixture.

Covers ``application.ingestion.source_filter``, ``process_code``,
``text_chunking``, and ``chunk_strategy`` for code, text, and skipped files.
"""

from pathlib import Path
from application.ingestion.chunk_strategy import ChunkStrategy
from application.ingestion.process_code import process_code_file
from application.ingestion.source_filter import classify_ingestible_file, iter_ingestible_files
from application.ingestion.text_chunking import process_text_file

def _touch(root: Path, rel: str, content: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path

def test_mixed_fixture_classification_and_chunking(tmp_path: Path):
    _touch(tmp_path, 'README.md', '# Title\n\nOverview.\n')
    _touch(tmp_path, 'notes.txt', 'Plain notes.\n')
    _touch(tmp_path, 'styles.css', 'body { color: red; }\n')
    _touch(tmp_path, 'app/main.py', 'def run():\n    return 1\n')
    _touch(tmp_path, 'poetry.lock', 'locked\n')
    paths = list(iter_ingestible_files(tmp_path))
    names = {p.name for p in paths}
    assert names == {'README.md', 'notes.txt', 'styles.css', 'main.py'}
    results: dict[str, dict] = {}
    for path in paths:
        kind = classify_ingestible_file(path)
        if kind == 'code':
            results[path.name] = process_code_file(str(path))
        else:
            results[path.name] = process_text_file(str(path))
    assert results['main.py']['indexing_mode'] == 'ast'
    assert results['main.py']['chunks'][0]['chunk_strategy'] == ChunkStrategy.AST_SEMANTIC
    assert results['styles.css']['indexing_mode'] == 'unsupported_extension'
    assert results['styles.css']['language'] == 'css'
    assert '.css' in (results['styles.css']['indexing_notice'] or '')
    assert results['README.md']['chunks']
    assert results['notes.txt']['chunks']
