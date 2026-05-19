import uuid
from sqlalchemy import String, TIMESTAMP, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.db.base import Base


class ClassModel(Base):
    __tablename__ = "classes"
    __table_args__ = (UniqueConstraint("file_id", "name", name="uq_classes_file_name"),)

    id: Mapped[uuid.UUID] = mapped_column( UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now())
    file = relationship("FileModel", back_populates="classes")
    functions = relationship("FunctionModel", back_populates="class_")
