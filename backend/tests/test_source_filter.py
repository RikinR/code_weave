from pathlib import Path

from application.ingestion.source_filter import (
    classify_ingestible_file,
    is_ingestible_source_file,
    iter_ingestible_files,
)


def _touch(root: Path, rel: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("content\n", encoding="utf-8")
    return path


def test_code_files_still_ingestible(tmp_path: Path):
    py_file = _touch(tmp_path, "app/main.py")
    assert classify_ingestible_file(py_file) == "code"
    assert is_ingestible_source_file(py_file)


def test_readme_and_requirements_are_context(tmp_path: Path):
    readme = _touch(tmp_path, "README.md")
    reqs = _touch(tmp_path, "requirements.txt")
    assert classify_ingestible_file(readme) == "context"
    assert classify_ingestible_file(reqs) == "context"


def test_dockerfile_without_extension_is_context(tmp_path: Path):
    dockerfile = _touch(tmp_path, "Dockerfile")
    assert classify_ingestible_file(dockerfile) == "context"


def test_lock_files_remain_skipped(tmp_path: Path):
    lock = _touch(tmp_path, "poetry.lock")
    assert classify_ingestible_file(lock) is None


def test_iter_ingestible_files_includes_code_and_context(tmp_path: Path):
    _touch(tmp_path, "README.md")
    _touch(tmp_path, "app/main.py")
    _touch(tmp_path, "poetry.lock")

    paths = {p.name for p in iter_ingestible_files(tmp_path)}
    assert paths == {"README.md", "main.py"}
