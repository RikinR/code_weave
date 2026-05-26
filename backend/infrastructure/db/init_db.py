"""ORM schema creation and lightweight column patches.

Uses :class:`infrastructure.db.base.Base` metadata to create tables and applies
additive ``ALTER TABLE`` statements for columns introduced after initial deploy.
Invoked by :func:`infrastructure.db.bootstrap.ensure_db_ready` at startup.
"""

from sqlalchemy import text
from infrastructure.db.base import Base
from infrastructure.db.session import engine
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.db.models.file_model import FileModel
from infrastructure.db.models.class_model import ClassModel
from infrastructure.db.models.chunk_model import ChunkModel
from infrastructure.db.models.function_model import FunctionModel
from infrastructure.db.models.function_calls_model import FunctionCallModel
from infrastructure.db.models.chat_message_model import ChatMessageModel
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)
_SCHEMA_PATCHES = ('ALTER TABLE files ADD COLUMN IF NOT EXISTS description TEXT', 'ALTER TABLE classes ADD COLUMN IF NOT EXISTS description TEXT', 'ALTER TABLE functions ADD COLUMN IF NOT EXISTS description TEXT', 'ALTER TABLE chunks ADD COLUMN IF NOT EXISTS chunk_strategy VARCHAR(32)', 'ALTER TABLE files ADD COLUMN IF NOT EXISTS indexing_mode VARCHAR(32)', 'ALTER TABLE files ADD COLUMN IF NOT EXISTS indexing_notice TEXT')

def _ensure_schema_columns() -> None:
    with engine.begin() as conn:
        for stmt in _SCHEMA_PATCHES:
            conn.execute(text(stmt))
    logger.info('init_db: schema columns verified')

def init_db() -> None:
    """Create all ORM tables and apply additive schema patches."""
    logger.info('init_db: creating tables from metadata')
    try:
        Base.metadata.create_all(bind=engine)
        _ensure_schema_columns()
    except Exception:
        logger.critical('init_db: failed to create schema — database unavailable or misconfigured', exc_info=True)
        raise
    logger.info('init_db: tables created successfully')
