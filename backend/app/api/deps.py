from __future__ import annotations

"""Shared FastAPI dependencies and environment-driven API settings.

Provides the SQLAlchemy session factory used by route handlers, plus CORS and upload
limits read from the environment for ``app.server`` and ingestion routes.
"""
import os
from collections.abc import Generator
from sqlalchemy.orm import Session
from infrastructure.db.session import SessionLocal
MAX_UPLOAD_BYTES = int(os.getenv('MAX_UPLOAD_BYTES', str(200 * 1024 * 1024)))
CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080').split(',')
CORS_ALLOW_LOCALHOST_REGEX = os.getenv('CORS_ALLOW_LOCALHOST_REGEX', 'true').lower() in ('1', 'true', 'yes')
CORS_LOCALHOST_REGEX = 'https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?'

def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped database session and close it when the handler finishes."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
