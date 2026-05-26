"""ORM model for persisted RAG chat turns per repository.

Written by :mod:`application.chat.messages` after each user/assistant exchange;
``citations`` stores chunk metadata and graph node ids for UI highlights.
"""

import uuid
from sqlalchemy import ForeignKey, String, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.db.base import Base

class ChatMessageModel(Base):
    """Single chat message (user or assistant) scoped to one repository."""

    __tablename__ = 'chat_messages'
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('repositories.id', ondelete='CASCADE'), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now())
    repository = relationship('RepositoryModel', back_populates='chat_messages')
