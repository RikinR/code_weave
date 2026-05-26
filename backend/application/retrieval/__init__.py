"""RAG pipeline: retrieve chunks, prompt LLM, format answers.

Orchestrated by :mod:`application.retrieval.rag_service` from the chat API.
Retrieval uses :mod:`infrastructure.vector.faiss_cache` and
:mod:`application.ingestion.lookup`; generation uses
:mod:`infrastructure.llm.groq_client`.
"""
