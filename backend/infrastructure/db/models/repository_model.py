"""ORM model for an indexed code repository (upload target).

Root entity for files, chunks, and chat history. Created at end of ingestion
and listed or deleted via :mod:`application.repos.repository_service`.
"""

import uuid
from sqlalchemy import Text, String, TIMESTAMP, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.db.base import Base

class RepositoryModel(Base):
    """Named repository with optional on-disk root path from upload extraction."""

    __tablename__ = 'repositories'
    __table_args__ = (UniqueConstraint('name', name='uq_repositories_name'),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    root_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now())
    files = relationship('FileModel', back_populates='repository', cascade='all, delete')
    chunks = relationship('ChunkModel', back_populates='repository', cascade='all, delete')
    chat_messages = relationship('ChatMessageModel', back_populates='repository', cascade='all, delete-orphan')
