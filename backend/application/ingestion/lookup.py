from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session, joinedload
from infrastructure.db.models.chunk_model import ChunkModel
from infrastructure.db.models.file_model import FileModel
from infrastructure.db.models.function_model import FunctionModel
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


def get_chunk_by_embedding_index(
    session: Session,
    repository_id: UUID,
    embedding_index: int,
) -> dict | None:
    chunk = (
        session.query(ChunkModel)
        .options(
            joinedload(ChunkModel.function).joinedload(FunctionModel.class_),
            joinedload(ChunkModel.file).joinedload(FileModel.repository),
        )
        .filter_by(repository_id=repository_id, embedding_index=embedding_index)
        .one_or_none()
    )
    if chunk is None:
        logger.warning(
            "lookup: no chunk for repository_id=%s embedding_index=%s",
            repository_id,
            embedding_index,
        )
        return None

    fn = chunk.function
    file_row = chunk.file
    repo = file_row.repository

    return {
        "chunk_id": str(chunk.id),
        "repository_id": str(repo.id),
        "repository_name": repo.name,
        "file_id": str(file_row.id),
        "file_path": file_row.file_path,
        "language": file_row.language,
        "function_id": str(fn.id),
        "function_name": fn.name,
        "class_id": str(fn.class_id) if fn.class_id else None,
        "class_name": fn.class_.name if fn.class_ else None,
        "embedding_index": chunk.embedding_index,
        "content": chunk.content,
        "start_line": chunk.start_line,
        "end_line": chunk.end_line,
        "signature": fn.signature,
    }


def get_repository(session: Session, repository_id: UUID) -> RepositoryModel | None:
    return session.get(RepositoryModel, repository_id)
