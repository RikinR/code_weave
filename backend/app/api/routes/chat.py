from __future__ import annotations
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.common import ChatCitation, ChatMessageResponse, ChatRequest
from application.chat.messages import list_chat_messages, save_chat_message
from application.graph.build_graph import NODE_FUNCTION, NODE_METHOD, node_id
from application.retrieval.format_answer import format_assistant_answer
from application.retrieval.prompt import build_rag_messages, chat_temperature
from application.retrieval.retrieve_chunks import retrieve_chunks
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.db.session import SessionLocal
from infrastructure.llm.groq_client import GroqError, chat_completion, chat_completion_stream

router = APIRouter(prefix="/api/repositories", tags=["chat"])


def _citations_from_contexts(contexts: list[dict]) -> tuple[list[ChatCitation], list[str]]:
    citations: list[ChatCitation] = []
    highlight_ids: list[str] = []
    for ctx in contexts:
        fn_id = ctx.get("function_id")
        node = None
        if fn_id:
            ntype = NODE_METHOD if ctx.get("class_id") else NODE_FUNCTION
            node = node_id(ntype, UUID(str(fn_id)))
            highlight_ids.append(node)
        citations.append(
            ChatCitation(
                chunk_id=ctx.get("chunk_id"),
                file_path=ctx.get("file_path"),
                function_name=ctx.get("function_name"),
                function_id=fn_id,
                node_id=node,
                score=ctx.get("score"),
            )
        )
    return citations, highlight_ids


def _require_repository(db: Session, repository_id: UUID) -> RepositoryModel:
    repo = db.get(RepositoryModel, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.get("/{repository_id}/chat/messages", response_model=list[ChatMessageResponse])
def repository_chat_messages(
    repository_id: UUID,
    db: Session = Depends(get_db),
) -> list[ChatMessageResponse]:
    _require_repository(db, repository_id)
    rows = list_chat_messages(db, repository_id)
    return [ChatMessageResponse(**row) for row in rows]


@router.post("/{repository_id}/chat")
def repository_chat(
    repository_id: UUID,
    body: ChatRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    _require_repository(db, repository_id)

    contexts = retrieve_chunks(db, repository_id, body.query, top_k=body.top_k)
    messages = build_rag_messages(
        body.query,
        contexts,
        beginner_mode=body.beginner_mode,
    )
    temperature = chat_temperature(beginner_mode=body.beginner_mode)
    citations, highlight_ids = _citations_from_contexts(contexts)
    citation_payload = [c.model_dump() for c in citations]

    save_chat_message(
        db,
        repository_id=repository_id,
        role="user",
        content=body.query,
    )
    db.commit()

    def event_stream():
        yield f"event: meta\ndata: {json.dumps({'citations': citation_payload, 'highlight_node_ids': highlight_ids})}\n\n"
        answer_parts: list[str] = []
        try:
            for token in chat_completion_stream(messages, temperature=temperature):
                answer_parts.append(token)
                payload = json.dumps({"token": token})
                yield f"event: token\ndata: {payload}\n\n"
            answer = format_assistant_answer("".join(answer_parts).strip()) or (
                "No response from the assistant."
            )
            with SessionLocal() as persist_db:
                save_chat_message(
                    persist_db,
                    repository_id=repository_id,
                    role="assistant",
                    content=answer,
                    citations=citation_payload,
                )
                persist_db.commit()
            yield f"event: answer\ndata: {json.dumps({'answer': answer})}\n\n"
            yield "event: done\ndata: {}\n\n"
        except GroqError as exc:
            err = json.dumps({"error": str(exc)})
            yield f"event: error\ndata: {err}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{repository_id}/chat/sync")
def repository_chat_sync(
    repository_id: UUID,
    body: ChatRequest,
    db: Session = Depends(get_db),
) -> dict:
    _require_repository(db, repository_id)

    contexts = retrieve_chunks(db, repository_id, body.query, top_k=body.top_k)
    messages = build_rag_messages(
        body.query,
        contexts,
        beginner_mode=body.beginner_mode,
    )
    temperature = chat_temperature(beginner_mode=body.beginner_mode)
    citations, highlight_ids = _citations_from_contexts(contexts)
    citation_payload = [c.model_dump() for c in citations]
    try:
        answer = format_assistant_answer(
            chat_completion(messages, temperature=temperature)
        )
    except GroqError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    save_chat_message(
        db,
        repository_id=repository_id,
        role="user",
        content=body.query,
    )
    save_chat_message(
        db,
        repository_id=repository_id,
        role="assistant",
        content=answer,
        citations=citation_payload,
    )
    db.commit()

    return {
        "answer": answer,
        "citations": citation_payload,
        "highlight_node_ids": highlight_ids,
    }
