import uuid
from sqlalchemy import Text, Integer,String,TIMESTAMP,ForeignKey,func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped,mapped_column,relationship
from infrastructure.db.base import Base

class ChunkModel(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column( UUID(as_uuid=True),ForeignKey("files.id", ondelete="CASCADE"))
    embedding_index: Mapped[int] = mapped_column(Integer,unique=True,nullable=False)
    content: Mapped[str] = mapped_column(Text,nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    chunk_type: Mapped[str | None] = mapped_column(String(50))
    token_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(TIMESTAMP,server_default=func.now())
    file = relationship("FileModel",back_populates="chunks")