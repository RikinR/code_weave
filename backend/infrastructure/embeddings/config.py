"""Local sentence-transformer embedding configuration.

``LOCAL_EMBEDDING_MODEL`` and ``EMBEDDING_DIMENSION`` must stay aligned with
:mod:`infrastructure.vector.faiss_store` index dimension and with ingestion
embedding in :mod:`application.ingestion.persist`.
"""

import os
from dotenv import load_dotenv
from infrastructure.logging.logger import get_logger
load_dotenv()
logger = get_logger(__name__)
LOCAL_EMBEDDING_MODEL = os.getenv('LOCAL_EMBEDDING_MODEL', 'BAAI/bge-small-en-v1.5')
_MODEL_DEFAULT_DIMS: dict[str, int] = {'all-MiniLM-L6-v2': 384, 'BAAI/bge-small-en-v1.5': 384, 'BAAI/bge-base-en-v1.5': 768, 'sentence-transformers/all-MiniLM-L6-v2': 384}
_default_dim = _MODEL_DEFAULT_DIMS.get(LOCAL_EMBEDDING_MODEL, 384)
EMBEDDING_DIMENSION = int(os.getenv('EMBEDDING_DIMENSION', str(_default_dim)))
if LOCAL_EMBEDDING_MODEL in _MODEL_DEFAULT_DIMS:
    expected = _MODEL_DEFAULT_DIMS[LOCAL_EMBEDDING_MODEL]
    if EMBEDDING_DIMENSION != expected:
        logger.warning('EMBEDDING_DIMENSION=%s does not match default %s for model %s', EMBEDDING_DIMENSION, expected, LOCAL_EMBEDDING_MODEL)
logger.debug('embeddings: model=%s dimension=%d', LOCAL_EMBEDDING_MODEL, EMBEDDING_DIMENSION)
