import zipfile
from pathlib import Path
import pytest
from application.ingestion.zip_extract import ZipExtractionError, extract_zip

def _make_zip(path: Path, files: dict[str, bytes]) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)

def test_extract_small_zip(tmp_path: Path) -> None:
    zip_path = tmp_path / "tiny.zip"
    dest = tmp_path / "out"
    _make_zip(
        zip_path,
        {
            "proj/main.py": b"print('hi')\n",
            "proj/util.py": b"x = 1\n",
        },
    )

    root = extract_zip(zip_path, dest)
    assert root == dest / "proj"
    assert (root / "main.py").read_text() == "print('hi')\n"

def test_extract_rejects_zip_slip(tmp_path: Path) -> None:
    zip_path = tmp_path / "evil.zip"
    dest = tmp_path / "out"
    _make_zip(zip_path, {"../escape.txt": b"no"})

    with pytest.raises(ZipExtractionError, match="Unsafe path"):
        extract_zip(zip_path, dest)
