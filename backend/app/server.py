from __future__ import annotations

"""FastAPI application entry point for the Code Weave backend.

Creates the ASGI app, wires CORS for the Flutter web client, mounts REST routers
under ``app.api.routes``, and runs startup hooks (database bootstrap, embedding warmup,
resumable ingestion jobs). This layer is thin: business logic lives in
``application`` and ``infrastructure`` packages.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.deps import CORS_ALLOW_LOCALHOST_REGEX, CORS_LOCALHOST_REGEX, CORS_ORIGINS, MAX_UPLOAD_BYTES
from application.ingestion.job_launcher import resume_recoverable_jobs
from app.api.routes import chat, graph, languages, progress, repositories, upload
from app.api.schemas.common import HealthResponse
from infrastructure.db.bootstrap import ensure_db_ready
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)

def _warm_embedding_model() -> None:
    """Load the local embedding model once so the first chat query is not cold-started."""
    try:
        from infrastructure.embeddings.local_embedder import embed_texts
        embed_texts(['code weave warmup'])
        logger.info('server: embedding model warmed up')
    except Exception:
        logger.exception('server: embedding model warmup failed (chat may be slow on first query)')

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Prepare DB, warm embeddings, and resume interrupted ingestion jobs on startup."""
    logger.info('server: ensuring database is ready')
    ensure_db_ready()
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(ThreadPoolExecutor(max_workers=1), _warm_embedding_model)
    resumed = resume_recoverable_jobs(max_upload_bytes=MAX_UPLOAD_BYTES)
    if resumed:
        logger.info('server: resumed %s ingestion job(s) after startup', resumed)
    yield

def create_app() -> FastAPI:
    """Build and configure the FastAPI instance with middleware, routers, and health check."""
    app = FastAPI(title='Code Weave API', version='0.1.0', lifespan=lifespan)
    cors_kwargs: dict = {'allow_origins': [o.strip() for o in CORS_ORIGINS if o.strip()], 'allow_credentials': True, 'allow_methods': ['*'], 'allow_headers': ['*']}
    if CORS_ALLOW_LOCALHOST_REGEX:
        cors_kwargs['allow_origin_regex'] = CORS_LOCALHOST_REGEX
    app.add_middleware(CORSMiddleware, **cors_kwargs)
    app.include_router(repositories.router)
    app.include_router(upload.router)
    app.include_router(progress.router)
    app.include_router(graph.router)
    app.include_router(languages.router)
    app.include_router(chat.router)

    @app.get('/api/health', response_model=HealthResponse)
    def health() -> HealthResponse:
        """Liveness probe used by deployment scripts and the Flutter client."""
        return HealthResponse()
    return app
app = create_app()
