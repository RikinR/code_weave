"""Verify zip archive extraction, safety checks, and post-extract pruning.

Covers ``application.ingestion.zip_extract`` for normal extraction, zip-slip
rejection, venv path skipping, and ``prune_extracted_tree`` cleanup.
"""

import zipfile
from pathlib import Path
import pytest
from application.ingestion.zip_extract import ZipExtractionError, extract_zip, prune_extracted_tree

def _make_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, 'w') as zf:
        for name, data in files.items():
            zf.writestr(name, data)

def test_extract_small_zip(tmp_path: Path) -> None:
    zip_path = tmp_path / 'tiny.zip'
    dest = tmp_path / 'out'
    _make_zip(zip_path, {'proj/main.py': b"print('hi')\n", 'proj/util.py': b'x = 1\n'})
    root = extract_zip(zip_path, dest)
    assert root == dest / 'proj'
    assert (root / 'main.py').read_text() == "print('hi')\n"

def test_extract_rejects_zip_slip(tmp_path: Path) -> None:
    zip_path = tmp_path / 'evil.zip'
    dest = tmp_path / 'out'
    _make_zip(zip_path, {'../escape.txt': b'no'})
    with pytest.raises(ZipExtractionError, match='Unsafe path'):
        extract_zip(zip_path, dest)

def test_extract_skips_venv_paths_in_archive(tmp_path: Path) -> None:
    zip_path = tmp_path / 'with_venv.zip'
    dest = tmp_path / 'out'
    files = {'proj/main.py': b'def run(): pass\n'}
    for index in range(15000):
        files[f'proj/venv/lib/python3.11/site-packages/pkg/module_{index}.py'] = b'x = 1\n'
    _make_zip(zip_path, files)
    root = extract_zip(zip_path, dest)
    assert (root / 'main.py').is_file()
    assert not (root / 'venv').exists()

def test_extract_rejects_too_many_files_after_prune(tmp_path: Path) -> None:
    zip_path = tmp_path / 'huge.zip'
    dest = tmp_path / 'out'
    files = {f'proj/src/file_{index}.py': b'pass\n' for index in range(10001)}
    _make_zip(zip_path, files)
    with pytest.raises(ZipExtractionError, match='after removing dependency'):
        extract_zip(zip_path, dest, max_files_after_prune=10000)

def test_prune_removes_extracted_venv_folder(tmp_path: Path) -> None:
    root = tmp_path / 'proj'
    (root / 'venv' / 'lib').mkdir(parents=True)
    (root / 'venv' / 'lib' / 'a.py').write_text('x', encoding='utf-8')
    (root / 'main.py').write_text('y', encoding='utf-8')
    stats = prune_extracted_tree(root)
    assert stats.removed_dirs >= 1
    assert not (root / 'venv').exists()
    assert (root / 'main.py').is_file()
