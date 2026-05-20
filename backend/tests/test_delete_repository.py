from pathlib import Path
from uuid import uuid4
from application.repos.repository_service import _remove_faiss_index,_remove_upload_artifacts, purge_repository_artifacts
from infrastructure.db.models.repository_model import RepositoryModel

def test_remove_faiss_index(tmp_path, monkeypatch):
    repo_id = uuid4()
    index_dir = tmp_path / "faiss"
    index_dir.mkdir()
    index_file = index_dir / f"{repo_id}.index"
    index_file.write_bytes(b"fake")

    monkeypatch.setattr(
        "application.repos.repository_service.faiss_index_path_for_repository",
        lambda rid: index_dir / f"{rid}.index",
    )

    assert _remove_faiss_index(repo_id) is True
    assert not index_file.exists()

def test_remove_upload_artifacts_deletes_job_folder(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    job_id = "job-abc"
    job_dir = uploads / job_id / "rag_prac"
    job_dir.mkdir(parents=True)
    (job_dir / "app.py").write_text("x", encoding="utf-8")
    (uploads / f"{job_id}.zip").write_bytes(b"zip")

    monkeypatch.setattr(
        "application.repos.repository_service.UPLOADS_DIR",
        uploads,
    )

    root_path = str(job_dir)
    assert _remove_upload_artifacts(root_path) is True
    assert not job_dir.exists()
    assert not (uploads / job_id).exists()
    assert not (uploads / f"{job_id}.zip").exists()

def test_remove_upload_artifacts_skips_outside_uploads(tmp_path, monkeypatch):
    external = tmp_path / "test_data" / "my_repo"
    external.mkdir(parents=True)
    monkeypatch.setattr(
        "application.repos.repository_service.UPLOADS_DIR",
        tmp_path / "uploads",
    )
    assert _remove_upload_artifacts(str(external)) is False
    assert external.exists()

def test_purge_repository_artifacts_combined(tmp_path, monkeypatch):
    repo_id = uuid4()
    index_dir = tmp_path / "faiss"
    index_dir.mkdir()
    (index_dir / f"{repo_id}.index").write_bytes(b"idx")

    uploads = tmp_path / "uploads"
    job_dir = uploads / "job1" / "proj"
    job_dir.mkdir(parents=True)

    monkeypatch.setattr(
        "application.repos.repository_service.faiss_index_path_for_repository",
        lambda rid: index_dir / f"{rid}.index",
    )
    monkeypatch.setattr(
        "application.repos.repository_service.UPLOADS_DIR",
        uploads,
    )

    repo = RepositoryModel(name="proj", root_path=str(job_dir))
    repo.id = repo_id
    result = purge_repository_artifacts(repo)
    assert result["faiss_index"] is True
    assert result["upload_tree"] is True
    assert not job_dir.exists()