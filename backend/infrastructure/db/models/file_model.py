import uuid
from sqlalchemy import Text, String, TIMESTAMP, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.db.base import Base


class FileModel(Base):
    __tablename__ = "files"
    __table_args__ = (
        UniqueConstraint("repository_id", "file_path", name="uq_files_repository_path"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(50))
    file_hash: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now())
    repository = relationship("RepositoryModel", back_populates="files")
    classes = relationship("ClassModel", back_populates="file", cascade="all, delete")
    chunks = relationship("ChunkModel", back_populates="file", cascade="all, delete")
    functions = relationship("FunctionModel", back_populates="file", cascade="all, delete")
