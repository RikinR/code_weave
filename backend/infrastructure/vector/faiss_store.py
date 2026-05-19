from __future__ import annotations
from pathlib import Path
import faiss
import numpy as np
from infrastructure.embeddings.config import EMBEDDING_DIMENSION
from infrastructure.logging.logger import get_logger
from infrastructure.vector.config import FAISS_INDEX_PATH

logger = get_logger(__name__)


class FaissStore:
    def __init__(
        self,
        index_path: Path | None = None,
        dimension: int = EMBEDDING_DIMENSION,
    ) -> None:
        self.index_path = index_path or FAISS_INDEX_PATH
        self.dimension = dimension
        self._index: faiss.Index | None = None

    @property
    def size(self) -> int:
        if self._index is None:
            return 0
        return int(self._index.ntotal)

    def load_or_create(self) -> None:
        if self.index_path.is_file():
            logger.info("faiss: loading index from %s", self.index_path)
            self._index = faiss.read_index(str(self.index_path))
            if self._index.d != self.dimension:
                raise ValueError(
                    f"FAISS index dimension {self._index.d} != configured {self.dimension}"
                )
            logger.info("faiss: loaded %d vector(s)", self._index.ntotal)
            return

        logger.info(
            "faiss: creating new IndexFlatIP dimension=%d at %s",
            self.dimension,
            self.index_path,
        )
        self._index = faiss.IndexFlatIP(self.dimension)

    def add(self, vectors: list[list[float]]) -> list[int]:
        if not vectors:
            return []
        if self._index is None:
            raise RuntimeError("FaissStore.load_or_create() must be called before add()")

        matrix = np.asarray(vectors, dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[1] != self.dimension:
            raise ValueError(
                f"Expected vectors shape (n, {self.dimension}), got {matrix.shape}"
            )

        faiss.normalize_L2(matrix)
        start = int(self._index.ntotal)
        self._index.add(matrix)
        indices = list(range(start, start + matrix.shape[0]))
        logger.info("faiss: added %d vector(s); index size=%d", len(indices), self._index.ntotal)
        return indices

    def save(self) -> None:
        if self._index is None:
            raise RuntimeError("FaissStore.load_or_create() must be called before save()")
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self.index_path))
        logger.info("faiss: saved index (%d vectors) to %s", self._index.ntotal, self.index_path)

    def search(
        self, query_vector: list[float], k: int = 5
    ) -> tuple[list[float], list[int]]:
        if self._index is None or self._index.ntotal == 0:
            return [], []

        query = np.asarray([query_vector], dtype=np.float32)
        faiss.normalize_L2(query)
        scores, indices = self._index.search(query, min(k, int(self._index.ntotal)))
        return scores[0].tolist(), indices[0].tolist()
