from __future__ import annotations
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.common import ChatCitation, ChatRequest
from application.graph.build_graph import NODE_FUNCTION, NODE_METHOD, node_id
from application.retrieval.prompt import build_rag_messages
from application.retrieval.retrieve_chunks import retrieve_chunks
from infrastructure.db.models.repository_model import RepositoryModel
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


@router.post("/{repository_id}/chat")
def repository_chat(
    repository_id: UUID,
    body: ChatRequest,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    repo = db.get(RepositoryModel, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    contexts = retrieve_chunks(db, repository_id, body.query, top_k=body.top_k)
    messages = build_rag_messages(
        body.query,
        contexts,
        beginner_mode=body.beginner_mode,
    )
    citations, highlight_ids = _citations_from_contexts(contexts)

    def event_stream():
        yield f"event: meta\ndata: {json.dumps({'citations': [c.model_dump() for c in citations], 'highlight_node_ids': highlight_ids})}\n\n"
        try:
            for token in chat_completion_stream(messages):
                payload = json.dumps({"token": token})
                yield f"event: token\ndata: {payload}\n\n"
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
    """Non-streaming chat fallback for clients that cannot read POST SSE reliably."""
    repo = db.get(RepositoryModel, repository_id)
    if repo is None:
        raise HTTPException(status_code=404, detail="Repository not found")

    contexts = retrieve_chunks(db, repository_id, body.query, top_k=body.top_k)
    messages = build_rag_messages(
        body.query,
        contexts,
        beginner_mode=body.beginner_mode,
    )
    citations, highlight_ids = _citations_from_contexts(contexts)
    try:
        answer = chat_completion(messages)
    except GroqError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "answer": answer,
        "citations": [c.model_dump() for c in citations],
        "highlight_node_ids": highlight_ids,
    }
