"""Verify extended source-filter coverage for plain-text and web asset files.

Covers ``application.ingestion.source_filter`` classification of ``.txt``,
``.ini``, ``.html``, ``.css``, and skipped formats such as JSON and lock files.
"""

from pathlib import Path
from application.ingestion.source_filter import classify_ingestible_file, iter_ingestible_files

def _touch(root: Path, rel: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('content\n', encoding='utf-8')
    return path

def test_plain_txt_classified_as_text(tmp_path: Path):
    notes = _touch(tmp_path, 'notes.txt')
    assert classify_ingestible_file(notes) == 'text'

def test_ini_and_cfg_classified_as_text(tmp_path: Path):
    assert classify_ingestible_file(_touch(tmp_path, 'app.ini')) == 'text'
    assert classify_ingestible_file(_touch(tmp_path, 'settings.cfg')) == 'text'

def test_json_remains_skipped(tmp_path: Path):
    assert classify_ingestible_file(_touch(tmp_path, 'data.json')) is None

def test_html_and_css_indexed_as_text(tmp_path: Path):
    assert classify_ingestible_file(_touch(tmp_path, 'index.html')) == 'text'
    assert classify_ingestible_file(_touch(tmp_path, 'styles.css')) == 'text'

def test_lock_files_remain_skipped(tmp_path: Path):
    assert classify_ingestible_file(_touch(tmp_path, 'poetry.lock')) is None

def test_iter_ingestible_includes_text_files(tmp_path: Path):
    _touch(tmp_path, 'README.md')
    _touch(tmp_path, 'notes.txt')
    _touch(tmp_path, 'app/main.py')
    _touch(tmp_path, 'styles.css')
    _touch(tmp_path, 'poetry.lock')
    paths = {p.name for p in iter_ingestible_files(tmp_path)}
    assert paths == {'README.md', 'notes.txt', 'main.py', 'styles.css'}
