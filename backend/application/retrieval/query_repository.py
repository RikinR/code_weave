from __future__ import annotations
from infrastructure.db.session import SessionLocal
from infrastructure.llm.groq_client import GroqError, chat_completion
from infrastructure.logging.logger import get_logger
from application.retrieval.prompt import build_rag_messages
from application.retrieval.retrieve_chunks import get_repository_by_name, retrieve_chunks

logger = get_logger(__name__)


def query_repository(
    query: str,
    repository_name: str = "test_data",
    top_k: int = 5,
) -> dict:
    """Retrieve relevant chunks and generate an answer with Groq."""
    session = SessionLocal()
    try:
        repository = get_repository_by_name(session, repository_name)
        if repository is None:
            raise ValueError(
                f"Repository {repository_name!r} not found. "
                f"Run indexing first: python app/main.py index"
            )

        contexts = retrieve_chunks(session, repository.id, query, top_k=top_k)
        messages = build_rag_messages(query, contexts)

        try:
            answer = chat_completion(messages)
        except GroqError:
            logger.exception("query_repository: Groq failed for query=%r", query)
            raise

        return {
            "query": query,
            "repository": repository_name,
            "repository_id": str(repository.id),
            "top_k": top_k,
            "chunks": contexts,
            "answer": answer,
        }
    finally:
        session.close()


def run_manual_queries(
    queries: list[str],
    repository_name: str = "test_data",
    top_k: int = 5,
) -> list[dict]:
    results: list[dict] = []
    for query in queries:
        logger.info("run_manual_queries: %s", query)
        results.append(
            query_repository(
                query=query,
                repository_name=repository_name,
                top_k=top_k,
            )
        )
    return results
