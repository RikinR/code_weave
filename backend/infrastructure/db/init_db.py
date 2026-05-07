from infrastructure.db.base import Base
from infrastructure.db.session import engine
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.db.models.file_model import FileModel
from infrastructure.db.models.chunk_model import ChunkModel
from infrastructure.db.models.function_model import FunctionModel
from infrastructure.db.models.function_calls_model import FunctionCallModel
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


def init_db() -> None:
    logger.info("init_db: creating tables from metadata")
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        logger.critical(
            "init_db: failed to create schema — database unavailable or misconfigured",
            exc_info=True,
        )
        raise
    logger.info("init_db: tables created successfully")

