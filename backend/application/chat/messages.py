from __future__ import annotations
from uuid import UUID
from sqlalchemy.orm import Session
from infrastructure.db.models.chat_message_model import ChatMessageModel

def list_chat_messages(session: Session, repository_id: UUID) -> list[dict]:
    rows = (
        session.query(ChatMessageModel)
        .filter_by(repository_id=repository_id)
        .order_by(ChatMessageModel.created_at.asc(), ChatMessageModel.id.asc())
        .all()
    )
    return [_serialize_message(row) for row in rows]

def save_chat_message(
    session: Session,
    *,
    repository_id: UUID,
    role: str,
    content: str,
    citations: list[dict] | None = None,
) -> dict:
    row = ChatMessageModel(
        repository_id=repository_id,
        role=role,
        content=content,
        citations=citations or [],
    )
    session.add(row)
    session.flush()
    return _serialize_message(row)

def _serialize_message(row: ChatMessageModel) -> dict:
    return {
        "id": str(row.id),
        "role": row.role,
        "content": row.content,
        "citations": row.citations or [],
        "created_at": str(row.created_at) if row.created_at else None,
    }
