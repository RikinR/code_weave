"""PostgreSQL database provisioning before the application serves traffic.

Called from server startup via :func:`ensure_db_ready`, which creates the
target database if missing (using a maintenance connection) and then delegates
schema creation to :mod:`infrastructure.db.init_db`.
"""

from __future__ import annotations
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from infrastructure.db.config import DATABASE_URL, DB_HOST, DB_NAME, DB_PASSWORD, DB_PORT, DB_USER
from infrastructure.db.init_db import init_db
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)
_MAINTENANCE_DATABASES = ('postgres', 'template1')

def _require_db_config() -> None:
    missing = [key for key, value in {'DB_HOST': DB_HOST, 'DB_PORT': DB_PORT, 'DB_NAME': DB_NAME, 'DB_USER': DB_USER, 'DB_PASSWORD': DB_PASSWORD}.items() if not value]
    if missing:
        raise RuntimeError(f"Database configuration incomplete. Set in backend/.env: {', '.join(missing)}")

def _maintenance_engine_url(maintenance_db: str) -> str:
    url = make_url(DATABASE_URL)
    return url.set(database=maintenance_db).render_as_string(hide_password=False)

def ensure_database_exists() -> None:
    """Create the configured database when it does not already exist."""
    _require_db_config()
    last_error: Exception | None = None
    for maintenance_db in _MAINTENANCE_DATABASES:
        admin_engine = create_engine(_maintenance_engine_url(maintenance_db), isolation_level='AUTOCOMMIT')
        try:
            with admin_engine.connect() as conn:
                exists = conn.execute(text('SELECT 1 FROM pg_database WHERE datname = :name'), {'name': DB_NAME}).scalar()
                if exists:
                    logger.info('bootstrap: database %r already exists', DB_NAME)
                    return
                logger.info('bootstrap: creating database %r', DB_NAME)
                conn.execute(text(f'CREATE DATABASE "{DB_NAME}" OWNER "{DB_USER}"'))
                logger.info('bootstrap: database %r created', DB_NAME)
                return
        except Exception as exc:
            last_error = exc
            logger.debug('bootstrap: could not use maintenance db %r: %s', maintenance_db, exc)
        finally:
            admin_engine.dispose()
    raise RuntimeError(f'Could not create or verify database {DB_NAME!r}. Ensure PostgreSQL is running and user {DB_USER!r} can connect and create databases. Last error: {last_error}') from last_error

def ensure_db_ready() -> None:
    """Ensure the database exists and ORM tables are created or patched."""
    _require_db_config()
    ensure_database_exists()
    init_db()
