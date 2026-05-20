# Code Weave

**Upload a codebase as a ZIP, index it with Tree-sitter, explore it through an interactive architecture graph, and ask questions with repository-scoped RAG chat.**

Code Weave is a full-stack project built for demonstrating end-to-end code intelligence: parsing, structural graph extraction, local embeddings, vector search, and LLM-grounded answers with citations. A Python/FastAPI backend owns ingestion and retrieval; a Flutter Web client provides upload, live pipeline progress, a VS Code–style explorer, and streaming Q&A.

![System architecture: Flutter Web UI, FastAPI API, detached worker, PostgreSQL, FAISS, local embeddings, and Groq](images/architecture-overview.png)

---

## What this project demonstrates

| Area | What you can evaluate |
|------|------------------------|
| **Code understanding** | Multi-language AST parsing (Tree-sitter), function/class extraction, static call-graph edges |
| **RAG pipeline** | Custom chunking, local embeddings, FAISS retrieval, prompt assembly, Groq streaming — **no LangChain / LlamaIndex / managed vector DB** |
| **Systems design** | Detached ingestion worker, disk-backed job state, SSE progress, per-repo FAISS indexes |
| **Full-stack UX** | ZIP upload → live pipeline → explorer tree + architecture graph → chat with citations and graph highlights |

---

## RAG built from scratch

The retrieval stack is implemented in-house rather than delegated to a framework:

| Component | Implementation |
|-----------|----------------|
| **Chunking** | One chunk per extracted function/method; embedding text = `file + function name + source` (`application/ingestion/chunk_text.py`) |
| **Embeddings** | `sentence-transformers` via a thin wrapper (`infrastructure/embeddings/local_embedder.py`); default model `BAAI/bge-small-en-v1.5` (384-dim) |
| **Vector store** | Per-repository **FAISS** `IndexFlatIP` with L2-normalized vectors (`infrastructure/vector/faiss_store.py`) |
| **Metadata** | Chunk rows + `embedding_index` in **PostgreSQL** for lookup after FAISS search |
| **Retrieval** | Query embed → FAISS top-k → hydrate chunks from DB (`application/retrieval/retrieve_chunks.py`) |
| **Generation** | Custom system/user prompt from retrieved context (`application/retrieval/prompt.py`) → **Groq** chat API (streaming SSE) |

**Not used:** LangChain, LlamaIndex, Pinecone, Chroma, Weaviate, or any hosted embedding/vector SaaS. The only external AI dependency for answers is Groq; embeddings run entirely on the host.

![RAG pipeline: embed query, FAISS top-k, hydrate chunks from Postgres, build prompt, Groq streaming](images/rag-pipeline.png)

![Data stores: PostgreSQL metadata and per-repo FAISS indexes on disk](images/data-stores.png)

---

## Features

- **ZIP upload** — Upload a repository archive; size limit configurable (`MAX_UPLOAD_BYTES`, default 100 MB).
- **Live ingestion pipeline** — Staged progress (extract → scan → parse → embed → graph) streamed over SSE; UI auto-navigates to explorer on success.
- **Detached worker** — Ingestion runs in a subprocess so API hot-reload does not kill long jobs; progress persisted to `backend/data/jobs/{job_id}.json`.
- **Multi-language parsing** — Tree-sitter with per-language query specs (Python, TypeScript/JavaScript, Java, Go, Rust, C/C++, and more).
- **Architecture graph** — Nodes: repository → folders → files → classes → functions/methods. Edges: `contains` (hierarchy) + `calls` (static call graph).
- **Explorer UI** — Project tree, left-to-right architecture canvas, syntax-highlighted node details, RAG chat panel.
- **RAG chat** — Repository-scoped Q&A with streaming tokens, chunk citations (file, function, score), and optional graph node highlights.
- **Beginner mode** — Simpler tutor-style system prompt for explanations.
- **Repository management** — List, inspect, delete indexed repos (DB + FAISS + upload artifacts).

![Ingestion pipeline stages from ZIP extraction through indexing complete](images/ingestion-pipeline.png)

![Explorer UI: project tree, architecture graph, node details, and RAG chat](images/explore-ui-mock.png)

![Architecture graph hierarchy: repository → folder → file → class → function, with call edges](images/graph-hierarchy.png)

---

## Tech stack

| Layer | Technologies |
|-------|----------------|
| **API** | FastAPI, Uvicorn, Pydantic, python-multipart |
| **Database** | PostgreSQL, SQLAlchemy 2 |
| **Parsing** | Tree-sitter, tree-sitter-languages |
| **Embeddings** | sentence-transformers (local CPU) |
| **Vector search** | FAISS (faiss-cpu), per-repo flat index |
| **LLM** | Groq API (default: `llama-3.3-70b-versatile`) |
| **Frontend** | Flutter Web, Provider, Dio, go_router |
| **Highlighting** | flutter_highlight |
| **Tests** | pytest (backend), flutter_test (frontend) |

![Tech stack: Flutter Web, FastAPI, PostgreSQL, Tree-sitter, sentence-transformers, FAISS, Groq](images/tech-stack.png)

---

## Project structure

```
code_weave/
├── README.md                          # This file
├── images/                            # Diagrams for this README
├── scripts/
│   ├── setup.sh                       # macOS/Linux bootstrap
│   └── setup.ps1                      # Windows bootstrap
│
├── backend/
│   ├── app/                           # HTTP layer
│   │   ├── server.py                  # FastAPI app · lifespan · CORS
│   │   ├── main.py                    # CLI entry (legacy index helpers)
│   │   └── api/
│   │       ├── deps.py
│   │       ├── routes/                # upload · jobs · repos · graph · chat
│   │       └── schemas/
│   │
│   ├── application/                   # Domain logic
│   │   ├── ingestion/
│   │   │   ├── zip_extract.py         # Safe ZIP extraction
│   │   │   ├── source_filter.py       # Ignore patterns · extensions
│   │   │   ├── process_code.py        # Tree-sitter · functions · calls
│   │   │   ├── chunk_text.py          # Chunk → embedding string
│   │   │   ├── index_folder.py        # Orchestrate parse → persist → FAISS
│   │   │   ├── persist.py             # SQLAlchemy batch writes
│   │   │   ├── pipeline_runner.py     # Staged job orchestration
│   │   │   ├── job_launcher.py        # Detached subprocess spawn
│   │   │   └── worker.py              # Worker entrypoint
│   │   ├── retrieval/
│   │   │   ├── retrieve_chunks.py     # Embed · FAISS · DB hydrate
│   │   │   ├── prompt.py              # RAG message builder
│   │   │   └── query_repository.py    # Sync RAG helper
│   │   ├── graph/
│   │   │   ├── build_graph.py         # Hierarchy + call edges
│   │   │   └── node_detail.py         # Source · explanation for a node
│   │   └── repos/
│   │       ├── processing_tracker.py  # Job state · disk JSON
│   │       └── repository_service.py
│   │
│   ├── infrastructure/                # Adapters
│   │   ├── db/                        # Models · session · bootstrap
│   │   ├── parser/                    # tree_sitter_parser · language_specs
│   │   ├── embeddings/                # local_embedder · config
│   │   ├── vector/                    # FaissStore · per-repo paths
│   │   └── llm/                       # groq_client
│   │
│   ├── tests/                         # pytest
│   ├── data/                          # gitignored: uploads · jobs · FAISS
│   ├── .env.example
│   └── requirements.txt
│
└── frontend/
    └── lib/
        ├── main.dart
        ├── core/
        │   ├── config/api_config.dart
        │   ├── network/               # Dio client · SSE parser
        │   ├── router/app_router.dart # / · /pipeline/:id · /explorer/:id
        │   ├── theme/
        │   └── layout/
        └── features/
            ├── home/                  # Repo grid · ZIP picker
            ├── pipeline/              # Ingestion progress (SSE)
            └── explorer/              # Tree · graph canvas · details · chat
```

**Gitignored runtime paths:** `backend/.env`, `backend/data/`, `backend/logs/`, `backend/venv/`, `frontend/build/`.

---

## HTTP API (summary)

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/health` | Liveness |
| `GET` | `/api/repositories` | List indexed repositories |
| `GET` | `/api/repositories/{id}` | Repository metadata |
| `DELETE` | `/api/repositories/{id}` | Delete repo + FAISS + uploads |
| `POST` | `/api/repositories/upload` | Upload ZIP, start ingestion job |
| `GET` | `/api/jobs/{id}` | Job snapshot |
| `GET` | `/api/jobs/{id}/events` | SSE progress stream |
| `POST` | `/api/jobs/{id}/retry` | Retry failed job (if ZIP still on disk) |
| `GET` | `/api/languages/supported` | Supported Tree-sitter languages |
| `GET` | `/api/repositories/{id}/hierarchy` | Explorer tree nodes |
| `GET` | `/api/repositories/{id}/graph` | Architecture nodes + edges |
| `GET` | `/api/nodes/{node_id}` | Node detail (code, calls, metadata) |
| `POST` | `/api/repositories/{id}/chat` | Streaming RAG (SSE) |
| `POST` | `/api/repositories/{id}/chat/sync` | Non-streaming RAG |

Interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL** (local or remote)
- **Flutter SDK** (Web target; Chrome)
- **Groq API key** — [console.groq.com](https://console.groq.com)

The first embedding run downloads the Hugging Face model (~tens of MB). Allow a few minutes on a slow connection.

---

## Setup

```bash
cd code_weave
./scripts/setup.sh
```

`setup.sh` creates `backend/venv`, installs Python dependencies, copies `backend/.env.example` → `backend/.env` if missing, bootstraps the database schema, and runs `flutter pub get` when Flutter is on `PATH`.

**Configure `backend/.env`:**

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=code_weave
DB_USER=your_user
DB_PASSWORD=your_password
GROQ_API_KEY=your_groq_key
```

See `backend/.env.example` for embedding model, CORS, and upload limits.

**Windows:** run `scripts/setup.ps1` from PowerShell.

---

## Run

**Terminal 1 — API**

```bash
cd backend
source venv/bin/activate
PYTHONPATH=. uvicorn app.server:app --reload --reload-exclude 'data/**' --host 0.0.0.0 --port 8000
```

Use `data/**` (not `data/*`) so files under `backend/data/` do not trigger reload loops during uploads and job writes.

**Terminal 2 — Web UI**

```bash
cd frontend
flutter run -d chrome --dart-define=API_BASE_URL=http://127.0.0.1:8000
```

**Suggested demo flow**

1. Open the app → **Upload repository** (a small Python or TypeScript ZIP works well).  
2. Watch the **pipeline** until indexing completes (auto-navigates to explorer).  
3. In **Explorer**: browse the tree, open the **Architecture** tab, select a function, view **Details**, ask a question in **Chat** (citations and graph highlights appear in the response).  

---

## Tests

```bash
# Backend
cd backend && source venv/bin/activate
PYTHONPATH=. pytest -q

# Frontend
cd frontend && flutter test
```

Backend tests cover health/CORS, upload/ZIP extraction, job launcher, processing tracker, progress API, chat API, path utilities, node detail, and repository deletion.

---

## License

Copyright © 2026 Rikin Ranka

Licensed under the [Apache License, Version 2.0](LICENSE). You may use, modify, and distribute this project (including for your own similar work), provided you include a copy of the license and state significant changes. See [LICENSE](LICENSE) for the full terms.
