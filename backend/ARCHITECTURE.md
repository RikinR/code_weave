<p align="center">
  <img src="../images/app-logo-tight.png" alt="Code Weave" width="320" />
</p>

# Backend architecture (developer map)

High-level flow for contributors. Each Python module and Dart library under `backend/` and `frontend/lib/` has a file-level docstring or `///` header; public classes and functions document how they connect to adjacent layers (see examples in `app/server.py`, `application/ingestion/pipeline_runner.py`, `frontend/lib/core/network/api_client.dart`).

## Layers

| Layer | Path | Role |
|-------|------|------|
| **API** | `app/server.py`, `app/api/routes/` | HTTP, SSE, multipart upload |
| **Application** | `application/` | Ingestion, graph, RAG, repository services |
| **Infrastructure** | `infrastructure/` | DB, FAISS, embeddings, Tree-sitter, Groq |

## Ingestion (ZIP → indexed repo)

1. `POST /api/repositories/upload` → `processing_tracker` creates job, saves ZIP.
2. `job_launcher` spawns `application/ingestion/worker.py` (detached process).
3. `pipeline_runner.run_ingestion_job`: extract → scan → `index_folder`.
4. `index_folder`: `process_code_file` (AST semantic chunks, text fallback) / `process_text_file` (docs, `.txt`, `.css`, `.html`) → `persist.IndexBatch` → `embed_texts` → `FaissStore` → `build_architecture_graph`.
5. Job JSON under `data/jobs/`; UI uses `GET /api/jobs/{id}/events` (SSE).

## RAG chat

1. `POST /api/repositories/{id}/chat` → `rag_service.prepare_rag`.
2. `retrieve_chunks`: embed query → FAISS → `lookup` hydrates chunks from Postgres.
3. `prompt.build_rag_messages` → `groq_client` (stream) → `format_answer`.
4. Citations include graph `node_id`s for UI highlights; messages stored in `chat_message` table.

## Data on disk

- `data/uploads/{job_id}.zip` — upload archive (removed after successful ingest).
- `data/uploads/{job_id}/` — extracted tree.
- `data/jobs/{job_id}.json` — pipeline progress snapshot.
- `data/faiss/{repository_id}.index` — per-repo vector index.

## Where to change behavior

| Goal | Start here |
|------|------------|
| Supported file types / skips | `application/ingestion/source_filter.py` |
| AST chunks / call graph | `process_code.py`, `ast_chunking.py`, `language_specs.py` |
| AST serialization (ingest only; optional API field) | `ast_tree.py` |
| Node descriptions / detail API | `description_extract.py`, `node_detail.py` |
| README/config/text chunks | `text_chunking.py` (includes `.css` / `.html` as text + `indexing_notice`) |
| Chunk strategy metadata | `chunk_strategy.py`, `chunks.chunk_strategy` column |
| Embedding model | `infrastructure/embeddings/config.py` |
| Answer format / tone | `application/retrieval/prompt.py` |
| Graph layout data | `application/graph/build_graph.py` |
