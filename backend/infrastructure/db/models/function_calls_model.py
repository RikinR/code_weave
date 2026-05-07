import uuid
from sqlalchemy import Text, Integer,String,TIMESTAMP,ForeignKey,func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped,mapped_column,relationship
from infrastructure.db.base import Base

class FunctionCallModel(Base):
    __tablename__ = "function_calls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),primary_key=True, default=uuid.uuid4)
    caller_function_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("functions.id", ondelete="CASCADE"))
    callee_function_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True),ForeignKey("functions.id", ondelete="CASCADE"))
    created_at: Mapped[str] = mapped_column(TIMESTAMP,server_default=func.now())
    caller = relationship("FunctionModel",foreign_keys=[caller_function_id])
    callee = relationship("FunctionModel",foreign_keys=[callee_function_id])