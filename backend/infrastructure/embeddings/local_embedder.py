"""On-device text embedding via sentence-transformers.

Used during ingestion (:mod:`application.ingestion.persist`) to vectorize chunks
and at query time by :mod:`application.retrieval.retrieve_chunks`. Vectors are
L2-normalized for inner-product search in FAISS.
"""

from __future__ import annotations
from infrastructure.embeddings.config import EMBEDDING_DIMENSION, LOCAL_EMBEDDING_MODEL
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)
_BATCH_SIZE = 64
_model = None

class EmbeddingError(RuntimeError):
    """Raised when the embedding model cannot load or encode text."""

def _get_model():
    global _model
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise EmbeddingError('sentence-transformers is not installed. Run: pip install sentence-transformers') from exc
    logger.info('local_embedder: loading model %s', LOCAL_EMBEDDING_MODEL)
    try:
        _model = SentenceTransformer(LOCAL_EMBEDDING_MODEL)
    except Exception as exc:
        raise EmbeddingError(f'Failed to load embedding model {LOCAL_EMBEDDING_MODEL!r}: {exc}') from exc
    dim = _model.get_sentence_embedding_dimension()
    if dim != EMBEDDING_DIMENSION:
        raise EmbeddingError(f'Model {LOCAL_EMBEDDING_MODEL!r} produces dimension {dim}, but EMBEDDING_DIMENSION is {EMBEDDING_DIMENSION}. Update backend/.env to match.')
    logger.info('local_embedder: model ready (dimension=%d)', dim)
    return _model

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Return L2-normalized embedding vectors for each input string."""
    if not texts:
        return []
    model = _get_model()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), _BATCH_SIZE):
        batch = texts[start:start + _BATCH_SIZE]
        logger.debug('embed_texts: model=%s batch=%d..%d of %d', LOCAL_EMBEDDING_MODEL, start, start + len(batch), len(texts))
        try:
            encoded = model.encode(batch, normalize_embeddings=True, show_progress_bar=False, convert_to_numpy=True)
        except Exception as exc:
            logger.error('embed_texts: encoding failed', exc_info=True)
            raise EmbeddingError(f'Local embedding encode failed: {exc}') from exc
        vectors.extend((row.tolist() for row in encoded))
    logger.info('embed_texts: embedded %d text(s) locally with model=%s dim=%d', len(vectors), LOCAL_EMBEDDING_MODEL, EMBEDDING_DIMENSION)
    return vectors
