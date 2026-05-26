"""Vector similarity search over indexed repository chunks.

Embeds the user query locally, searches the repository FAISS index, and
hydrates Postgres chunk rows via :mod:`application.ingestion.lookup` for RAG
context assembly in :mod:`application.retrieval.rag_service`.
"""

from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session
from application.ingestion.lookup import get_chunk_by_embedding_index
from infrastructure.embeddings.local_embedder import embed_texts
from infrastructure.logging.logger import get_logger
from infrastructure.vector.faiss_cache import get_loaded_store
logger = get_logger(__name__)

def retrieve_chunks(session: Session, repository_id: UUID, query: str, top_k: int=5) -> list[dict]:
    """Return top matching chunk dicts with similarity scores for a natural-language query."""
    vectors = embed_texts([query])
    if not vectors:
        return []
    store = get_loaded_store(repository_id)
    if store is None or store.size == 0:
        logger.warning('retrieve_chunks: no FAISS index for %s', repository_id)
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
        ctx['score'] = float(score)
        results.append(ctx)
    logger.info('retrieve_chunks: query=%r hits=%d (requested top_k=%d)', query[:80], len(results), top_k)
    return results
