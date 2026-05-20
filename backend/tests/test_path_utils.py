from pathlib import Path
from application.ingestion.path_utils import relative_to_repo, resolve_repo_path
from application.graph.build_graph import _folder_path_parts, _repo_relative_path
from infrastructure.db.models.repository_model import RepositoryModel

def test_relative_to_repo_from_absolute_under_root(tmp_path: Path):
    root = tmp_path / "rag_prac"
    app_dir = root / "app"
    app_dir.mkdir(parents=True)
    main_py = app_dir / "main.py"
    main_py.write_text("print('hi')", encoding="utf-8")

    rel = relative_to_repo(str(main_py), root, "rag_prac")
    assert rel == "app/main.py"

def test_relative_to_repo_strips_upload_prefix():
    abs_path = "/data/uploads/job-id/rag_prac/app/db.py"
    rel = relative_to_repo(abs_path, "/unused/root", "rag_prac")
    assert rel == "app/db.py"

def test_resolve_repo_path_joins_relative(tmp_path: Path):
    root = tmp_path / "rag_prac"
    root.mkdir()
    abs_path = resolve_repo_path("app/main.py", root)
    assert abs_path == root / "app" / "main.py"

def test_folder_parts_use_relative_only():
    parts = _folder_path_parts("app/pipeline.py")
    assert parts == ["app"]

def test_repo_relative_path_legacy_absolute():
    repo = RepositoryModel(
        name="rag_prac",
        root_path="/data/uploads/uuid/rag_prac",
    )
    legacy = "/data/uploads/uuid/rag_prac/app/main.py"
    rel = _repo_relative_path(legacy, repo)
    assert rel == "app/main.py"
