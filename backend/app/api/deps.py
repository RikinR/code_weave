from __future__ import annotations
import os
from collections.abc import Generator
from sqlalchemy.orm import Session
from infrastructure.db.session import SessionLocal

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(100 * 1024 * 1024)))
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:8080,http://127.0.0.1:8080",
).split(",")

CORS_ALLOW_LOCALHOST_REGEX = os.getenv("CORS_ALLOW_LOCALHOST_REGEX", "true").lower() in (
    "1",
    "true",
    "yes",
)
CORS_LOCALHOST_REGEX = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"

def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
