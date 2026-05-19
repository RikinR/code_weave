from pathlib import Path
from uuid import UUID
from dotenv import load_dotenv
from infrastructure.embeddings.config import EMBEDDING_DIMENSION
from infrastructure.logging.logger import get_logger

load_dotenv()

logger = get_logger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
FAISS_INDEX_DIR = _BACKEND_ROOT / "data" / "faiss"
FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
FAISS_INDEX_PATH = FAISS_INDEX_DIR / "chunks.index"


def faiss_index_path_for_repository(repository_id: UUID) -> Path:
    return FAISS_INDEX_DIR / f"{repository_id}.index"


logger.debug("vector store: index_dir=%s dimension=%d", FAISS_INDEX_DIR, EMBEDDING_DIMENSION)
