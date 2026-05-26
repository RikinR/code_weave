from __future__ import annotations

"""Repository-scoped RAG chat endpoints for the Flutter Q&A UI.

Streams or returns LLM answers over retrieved code chunks, persists message history,
and emits citation metadata so the explorer can highlight relevant graph nodes.
"""
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.common import ChatCitation, ChatMessageResponse, ChatRequest
from application.chat.messages import list_chat_messages, save_chat_message
from application.retrieval.rag_service import prepare_rag, run_rag_sync
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.db.session import SessionLocal
from infrastructure.llm.groq_client import GroqError, chat_completion_stream
from application.retrieval.format_answer import format_assistant_answer
router = APIRouter(prefix='/api/repositories', tags=['chat'])

def _require_repository(db: Session, repository_id: UUID) -> RepositoryModel:
    """Load a repository row or raise 404 before running chat or history handlers."""
    repo = db.get(RepositoryModel, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail='Repository not found')
    return repo

@router.get('/{repository_id}/chat/messages', response_model=list[ChatMessageResponse])
def repository_chat_messages(repository_id: UUID, db: Session=Depends(get_db)) -> list[ChatMessageResponse]:
    """Return prior user and assistant messages for the repository chat thread."""
    _require_repository(db, repository_id)
    rows = list_chat_messages(db, repository_id)
    return [ChatMessageResponse(**row) for row in rows]

@router.post('/{repository_id}/chat')
def repository_chat(repository_id: UUID, body: ChatRequest, db: Session=Depends(get_db)) -> StreamingResponse:
    """Run RAG retrieval then stream Groq tokens as Server-Sent Events (meta, token, answer)."""
    _require_repository(db, repository_id)
    prepared = prepare_rag(db, repository_id=repository_id, query=body.query, top_k=body.top_k, beginner_mode=body.beginner_mode)
    citations = [ChatCitation(**c) for c in prepared.citation_payload]
    citation_payload = [c.model_dump() for c in citations]
    save_chat_message(db, repository_id=repository_id, role='user', content=body.query)
    db.commit()

    def event_stream():
        """Yield SSE frames: citations first, then tokens, final answer, or error."""
        yield f"event: meta\ndata: {json.dumps({'citations': citation_payload, 'highlight_node_ids': prepared.highlight_node_ids})}\n\n"
        answer_parts: list[str] = []
        try:
            for token in chat_completion_stream(prepared.messages, temperature=prepared.temperature):
                answer_parts.append(token)
                payload = json.dumps({'token': token})
                yield f'event: token\ndata: {payload}\n\n'
            answer = format_assistant_answer(''.join(answer_parts).strip()) or 'No response from the assistant.'
            with SessionLocal() as persist_db:
                save_chat_message(persist_db, repository_id=repository_id, role='assistant', content=answer, citations=citation_payload)
                persist_db.commit()
            yield f"event: answer\ndata: {json.dumps({'answer': answer})}\n\n"
            yield 'event: done\ndata: {}\n\n'
        except GroqError as exc:
            err = json.dumps({'error': str(exc)})
            yield f'event: error\ndata: {err}\n\n'
    return StreamingResponse(event_stream(), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no'})

@router.post('/{repository_id}/chat/sync')
def repository_chat_sync(repository_id: UUID, body: ChatRequest, db: Session=Depends(get_db)) -> dict:
    """Blocking chat variant for tests and clients that do not consume SSE streams."""
    _require_repository(db, repository_id)
    try:
        result = run_rag_sync(db, repository_id=repository_id, query=body.query, top_k=body.top_k, beginner_mode=body.beginner_mode)
    except GroqError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    save_chat_message(db, repository_id=repository_id, role='user', content=body.query)
    save_chat_message(db, repository_id=repository_id, role='assistant', content=result['answer'], citations=result['citations'])
    db.commit()
    return {'answer': result['answer'], 'citations': result['citations'], 'highlight_node_ids': result['highlight_node_ids']}
