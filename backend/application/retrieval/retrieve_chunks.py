from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session
from application.ingestion.lookup import get_chunk_by_embedding_index
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.embeddings.local_embedder import embed_texts
from infrastructure.logging.logger import get_logger
from infrastructure.vector.config import faiss_index_path_for_repository
from infrastructure.vector.faiss_store import FaissStore

logger = get_logger(__name__)


def get_repository_by_name(session: Session, name: str) -> RepositoryModel | None:
    return session.query(RepositoryModel).filter_by(name=name).one_or_none()


def retrieve_chunks(
    session: Session,
    repository_id: UUID,
    query: str,
    top_k: int = 5,
) -> list[dict]:
    """Embed query, search FAISS, and load matching chunk rows from Postgres."""
    vectors = embed_texts([query])
    if not vectors:
        return []

    index_path = faiss_index_path_for_repository(repository_id)
    if not index_path.is_file():
        logger.warning("retrieve_chunks: no FAISS index at %s", index_path)
        return []

    store = FaissStore(index_path=index_path)
    store.load_or_create()
    if store.size == 0:
        logger.warning("retrieve_chunks: FAISS index is empty for %s", repository_id)
        return []

    scores, indices = store.search(vectors[0], k=top_k)
    results: list[dict] = []
    seen_indices: set[int] = set()

    for score, embedding_index in zip(scores, indices, strict=True):
        if embedding_index < 0 or embedding_index in seen_indices:
            continue
        seen_indices.add(embedding_index)

        ctx = get_chunk_by_embedding_index(session, repository_id, embedding_index)
        if ctx is None:
            continue
        ctx["score"] = float(score)
        results.append(ctx)

    logger.info(
        "retrieve_chunks: query=%r hits=%d (requested top_k=%d)",
        query[:80],
        len(results),
        top_k,
    )
    return results
