import uuid
from sqlalchemy import Text, Integer,String,TIMESTAMP,ForeignKey,func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped,mapped_column,relationship
from infrastructure.db.base import Base

class FunctionModel(Base):
    __tablename__ = "functions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("files.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255),nullable=False)
    start_line: Mapped[int | None] = mapped_column(Integer)
    end_line: Mapped[int | None] = mapped_column(Integer)
    signature: Mapped[str | None] = mapped_column(Text)
    docstring: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now())
    file = relationship("FileModel",back_populates="functions")