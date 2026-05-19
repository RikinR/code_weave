import uuid
from sqlalchemy import Integer, TIMESTAMP, ForeignKey, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from infrastructure.db.base import Base

class FunctionCallModel(Base):
    __tablename__ = "function_calls"
    __table_args__ = (
        UniqueConstraint(
            "caller_function_id",
            "callee_function_id",
            "call_site_byte",
            name="uq_function_calls_caller_callee_site",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    caller_function_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("functions.id", ondelete="CASCADE"), nullable=False)
    callee_function_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("functions.id", ondelete="CASCADE"), nullable=False)
    call_site_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[str] = mapped_column(TIMESTAMP, server_default=func.now())
    caller = relationship(
        "FunctionModel",
        foreign_keys=[caller_function_id],
        back_populates="outgoing_calls",
    )
    callee = relationship(
        "FunctionModel",
        foreign_keys=[callee_function_id],
        back_populates="incoming_calls",
    )
