"""End-to-end RAG orchestration for repository chat queries.

Wires retrieval (:mod:`application.retrieval.retrieve_chunks`), prompting
(:mod:`application.retrieval.prompt`), Groq generation
(:mod:`infrastructure.llm.groq_client`), answer cleanup
(:mod:`application.retrieval.format_answer`), and graph citation node ids from
:mod:`application.graph.build_graph`.
"""

from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID
from sqlalchemy.orm import Session
from application.graph.build_graph import NODE_FUNCTION, NODE_METHOD, node_id
from application.retrieval.format_answer import format_assistant_answer
from application.retrieval.prompt import build_rag_messages, chat_temperature
from application.retrieval.retrieve_chunks import retrieve_chunks
from infrastructure.db.models.repository_model import RepositoryModel
from infrastructure.llm.groq_client import GroqError, chat_completion
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)

@dataclass(frozen=True)
class RagPrepared:
    """Intermediate RAG state after retrieval and prompt assembly, before LLM call."""

    repository_id: UUID
    repository_name: str
    query: str
    top_k: int
    beginner_mode: bool
    contexts: list[dict]
    messages: list[dict]
    temperature: float
    citation_payload: list[dict]
    highlight_node_ids: list[str]

def resolve_repository(session: Session, *, repository_id: UUID) -> RepositoryModel:
    """Load a repository row or raise ``ValueError`` when missing."""
    repo = session.get(RepositoryModel, repository_id)
    if repo is None:
        raise ValueError(f'Repository not found: {repository_id}')
    return repo

def _citations_from_contexts(contexts: list[dict]) -> tuple[list[dict], list[str]]:
    citation_payload: list[dict] = []
    highlight_node_ids: list[str] = []
    for ctx in contexts:
        fn_id = ctx.get('function_id')
        node = None
        if fn_id:
            ntype = NODE_METHOD if ctx.get('class_id') else NODE_FUNCTION
            node = node_id(ntype, UUID(str(fn_id)))
            highlight_node_ids.append(node)
        citation_payload.append({'chunk_id': ctx.get('chunk_id'), 'file_path': ctx.get('file_path'), 'function_name': ctx.get('function_name'), 'function_id': fn_id, 'node_id': node, 'score': ctx.get('score')})
    return (citation_payload, highlight_node_ids)

def prepare_rag(session: Session, *, repository_id: UUID, query: str, top_k: int=5, beginner_mode: bool=False) -> RagPrepared:
    """Retrieve chunks, build prompts, and assemble citation metadata without calling the LLM."""
    repo = resolve_repository(session, repository_id=repository_id)
    contexts = retrieve_chunks(session, repository_id, query, top_k=top_k)
    messages = build_rag_messages(query, contexts, beginner_mode=beginner_mode)
    temperature = chat_temperature(beginner_mode=beginner_mode)
    citation_payload, highlight_node_ids = _citations_from_contexts(contexts)
    return RagPrepared(repository_id=repository_id, repository_name=repo.name, query=query, top_k=top_k, beginner_mode=beginner_mode, contexts=contexts, messages=messages, temperature=temperature, citation_payload=citation_payload, highlight_node_ids=highlight_node_ids)

def run_rag_sync(session: Session, *, repository_id: UUID, query: str, top_k: int=5, beginner_mode: bool=False) -> dict:
    """Run full synchronous RAG: retrieve, generate answer, format, and return API payload."""
    prepared = prepare_rag(session, repository_id=repository_id, query=query, top_k=top_k, beginner_mode=beginner_mode)
    try:
        raw_answer = chat_completion(prepared.messages, temperature=prepared.temperature)
    except GroqError:
        logger.exception('run_rag_sync: Groq failed for query=%r', query)
        raise
    answer = format_assistant_answer(raw_answer) or 'No response from the assistant.'
    return {'query': query, 'repository_id': str(repository_id), 'repository_name': prepared.repository_name, 'top_k': top_k, 'beginner_mode': beginner_mode, 'chunks': prepared.contexts, 'answer': answer, 'citations': prepared.citation_payload, 'highlight_node_ids': prepared.highlight_node_ids}
