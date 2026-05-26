from __future__ import annotations

"""Resolve stored chunks by FAISS embedding index after ingestion.

Pipeline stage: post-**embed** lookup (retrieval and graph APIs).

Maps a repository id and vector index back to chunk, function, file, and class
metadata. Uses :mod:`path_utils` for display paths relative to the repository root.
"""
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from infrastructure.db.models.chunk_model import ChunkModel
from infrastructure.db.models.file_model import FileModel
from infrastructure.db.models.function_model import FunctionModel
from application.ingestion.path_utils import relative_to_repo
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)

def get_chunk_by_embedding_index(session: Session, repository_id: UUID, embedding_index: int) -> dict | None:
    """Load chunk and related graph metadata for one FAISS vector index."""
    chunk = session.query(ChunkModel).options(joinedload(ChunkModel.function).joinedload(FunctionModel.class_), joinedload(ChunkModel.file).joinedload(FileModel.repository)).filter_by(repository_id=repository_id, embedding_index=embedding_index).one_or_none()
    if chunk is None:
        logger.warning('lookup: no chunk for repository_id=%s embedding_index=%s', repository_id, embedding_index)
        return None
    fn = chunk.function
    file_row = chunk.file
    repo = file_row.repository
    return {'chunk_id': str(chunk.id), 'repository_id': str(repo.id), 'repository_name': repo.name, 'file_id': str(file_row.id), 'file_path': relative_to_repo(file_row.file_path, repo.root_path or '', repo.name), 'language': file_row.language, 'function_id': str(fn.id), 'function_name': fn.name, 'class_id': str(fn.class_id) if fn.class_id else None, 'class_name': fn.class_.name if fn.class_ else None, 'embedding_index': chunk.embedding_index, 'content': chunk.content, 'start_line': chunk.start_line, 'end_line': chunk.end_line, 'signature': fn.signature, 'description': fn.description, 'chunk_type': chunk.chunk_type or 'function', 'chunk_strategy': chunk.chunk_strategy}
