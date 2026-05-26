"""Repository listing, summaries, and deletion with artifact cleanup.

Coordinates Postgres cascade deletes on
:class:`infrastructure.db.models.repository_model.RepositoryModel` with
on-disk FAISS indexes (:mod:`infrastructure.vector.faiss_cache`) and upload
trees from ingestion.
"""

from __future__ import annotations
import shutil
from pathlib import Path
from uuid import UUID
from sqlalchemy import func
from sqlalchemy.orm import Session
from application.ingestion.pipeline_runner import UPLOADS_DIR
from infrastructure.db.models.chunk_model import ChunkModel
from infrastructure.db.models.file_model import FileModel
from infrastructure.db.models.function_model import FunctionModel
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.logging.logger import get_logger
from infrastructure.vector.config import faiss_index_path_for_repository
from infrastructure.vector.faiss_cache import invalidate as invalidate_faiss_cache
logger = get_logger(__name__)

def list_repositories(session: Session) -> list[dict]:
    """Return summary dicts for all repositories, newest first."""
    repos = session.query(RepositoryModel).order_by(RepositoryModel.created_at.desc()).all()
    summaries: list[dict] = []
    for repo in repos:
        summaries.append(get_repository_summary(session, repo.id))
    return summaries

def get_repository_summary(session: Session, repository_id: UUID) -> dict:
    """Return id, name, counts, and metadata for one repository."""
    repo = session.get(RepositoryModel, repository_id)
    if repo is None:
        raise ValueError(f'Repository not found: {repository_id}')
    file_count = session.query(func.count(FileModel.id)).filter_by(repository_id=repository_id).scalar() or 0
    function_count = session.query(func.count(FunctionModel.id)).join(FileModel).filter(FileModel.repository_id == repository_id).scalar() or 0
    chunk_count = session.query(func.count(ChunkModel.id)).filter_by(repository_id=repository_id).scalar() or 0
    return {'id': str(repo.id), 'name': repo.name, 'root_path': repo.root_path, 'description': repo.description, 'created_at': str(repo.created_at) if repo.created_at else None, 'file_count': int(file_count), 'function_count': int(function_count), 'chunk_count': int(chunk_count)}

def _remove_faiss_index(repository_id: UUID) -> bool:
    invalidate_faiss_cache(repository_id)
    index_path = faiss_index_path_for_repository(repository_id)
    if not index_path.is_file():
        return False
    index_path.unlink()
    logger.info('repository_service: removed FAISS index %s', index_path)
    return True

def _remove_upload_artifacts(root_path: str | None) -> bool:
    if not root_path:
        return False
    root = Path(root_path).resolve()
    uploads_root = UPLOADS_DIR.resolve()
    try:
        root.relative_to(uploads_root)
    except ValueError:
        logger.debug('repository_service: root_path %s is outside uploads; skipping disk tree removal', root)
        return False
    rel = root.relative_to(uploads_root)
    if not rel.parts:
        return False
    job_dir = uploads_root / rel.parts[0]
    if job_dir.exists():
        shutil.rmtree(job_dir)
        logger.info('repository_service: removed upload directory %s', job_dir)
    zip_path = uploads_root / f'{rel.parts[0]}.zip'
    if zip_path.is_file():
        zip_path.unlink()
        logger.info('repository_service: removed upload zip %s', zip_path)
    return True

def purge_repository_artifacts(repo: RepositoryModel) -> dict[str, bool]:
    """Remove FAISS index and upload tree artifacts for a repository without deleting DB rows."""
    repository_id = repo.id
    return {'faiss_index': _remove_faiss_index(repository_id), 'upload_tree': _remove_upload_artifacts(repo.root_path)}

def delete_repository(session: Session, repository_id: UUID) -> dict | None:
    """Delete repository rows and on-disk artifacts; return summary or ``None`` if not found."""
    repo = session.get(RepositoryModel, repository_id)
    if repo is None:
        return None
    artifacts = purge_repository_artifacts(repo)
    session.delete(repo)
    session.commit()
    logger.info('repository_service: deleted repository id=%s name=%r artifacts=%s', repository_id, repo.name, artifacts)
    return {'id': str(repository_id), 'name': repo.name, 'artifacts': artifacts}
