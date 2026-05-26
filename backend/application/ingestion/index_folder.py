from __future__ import annotations

"""Folder-level indexing: parse sources, persist graph rows, embed chunks, store vectors.

Pipeline stage: **parse → persist → embed** (after :mod:`source_filter` scan).

Walks ingestible files under a repository root, dispatches code to
:mod:`process_code` and text/context to :mod:`text_chunking`, writes files,
classes, functions, and call edges through :mod:`persist`, generates embeddings,
and updates the FAISS index. Called by :mod:`pipeline_runner` after ZIP
extraction and file scanning.
"""
from collections.abc import Callable
from pathlib import Path
from application.ingestion.persist import IndexBatch, get_or_create_repository, store_chunks_with_embeddings
from infrastructure.db.bootstrap import ensure_db_ready
from infrastructure.db.session import SessionLocal
from infrastructure.embeddings.local_embedder import EmbeddingError, embed_texts
from infrastructure.logging.logger import get_logger
from infrastructure.vector.config import faiss_index_path_for_repository
from infrastructure.vector.faiss_cache import invalidate as invalidate_faiss_cache
from infrastructure.vector.faiss_store import FaissStore
logger = get_logger(__name__)
ProgressCallback = Callable[[str, str, float], None]
"""``(stage, message, percent)`` progress hook used by :mod:`pipeline_runner`."""

def index_folder(folder: Path, repository_name: str | None=None, *, on_progress: ProgressCallback | None=None, sources: list[Path] | None=None) -> dict:
    """Index all ingestible files under ``folder`` and return a summary dict.

    Parses each source, persists repository graph data, embeds chunk texts, and
    writes vectors to FAISS. When ``sources`` is omitted, rescans via
    :func:`source_filter.iter_ingestible_files`.
    """

    def _progress(stage: str, message: str, percent: float) -> None:
        if on_progress is not None:
            on_progress(stage, message, percent)
    if not folder.is_dir():
        logger.warning('folder does not exist or is not a directory: %s', folder)
        return _empty_summary()
    ensure_db_ready()
    repo_name = repository_name or folder.name
    root_path = str(folder.resolve())
    if on_progress and sources is None:
        on_progress('file_scanning', f'Scanning {folder}', 10.0)
    from application.ingestion.process_code import process_code_file
    from application.ingestion.text_chunking import process_text_file
    from application.ingestion.source_filter import classify_ingestible_file, iter_ingestible_files
    parsed_files: list[dict] = []
    if sources is None:
        sources = list(iter_ingestible_files(folder))
    total_sources = max(len(sources), 1)
    for index, source in enumerate(sources, start=1):
        path = str(source)
        file_kind = classify_ingestible_file(source)
        stage_label = 'Parsing' if file_kind == 'code' else 'Reading'
        if on_progress:
            pct = 15.0 + index / total_sources * 40.0
            on_progress('parsing', f'{stage_label} {source.name} ({index}/{total_sources})', pct)
        try:
            if file_kind in ('context', 'text'):
                parsed_files.append(process_text_file(path))
            else:
                parsed_files.append(process_code_file(path))
        except RuntimeError as exc:
            logger.warning('index_folder: skip %s: %s', path, exc)
        except Exception:
            logger.exception('index_folder: failed to process %s', path)
    chunk_count = sum((len(f.get('chunks') or []) for f in parsed_files))
    if on_progress:
        on_progress('parsing', f'Parsed {len(parsed_files)} of {len(sources)} files ({chunk_count} chunks)', 60.0)
    if not parsed_files:
        logger.info('index_folder: no parseable files under %s', folder)
        return _empty_summary(repository=repo_name)
    session = SessionLocal()
    try:
        repository = get_or_create_repository(session, name=repo_name, root_path=root_path)
        batch = IndexBatch(repository)
        files_with_chunks = [f for f in parsed_files if f.get('chunks')]
        persist_total = max(len(files_with_chunks), 1)
        for index, file_result in enumerate(files_with_chunks, start=1):
            if on_progress:
                pct = 62.0 + index / persist_total * 6.0
                on_progress('graph_persist', f"Storing {Path(file_result['file']).name} ({index}/{persist_total})", pct)
            batch.add_file(session, file_result)
        if on_progress:
            on_progress('graph_persist', 'Recording call graph edges', 69.0)
        batch.record_all_calls(session)
        if not batch.pending:
            session.commit()
            return {'repository_id': str(repository.id), 'repository': repo_name, 'files': batch.files_indexed, 'classes': batch.classes_indexed, 'functions': batch.functions_indexed, 'chunks': 0, 'embeddings': 0, 'calls': batch.calls_indexed}
        session.commit()
        logger.info('index_folder: committed repository graph (%d files, %d functions, %d calls)', batch.files_indexed, batch.functions_indexed, batch.calls_indexed)
        texts = [item['text'] for item in batch.pending]
        if on_progress:
            on_progress('embedding_generation', f'Embedding {len(texts)} chunks', 70.0)
        try:
            vectors = embed_texts(texts)
        except EmbeddingError:
            logger.exception('index_folder: embedding failed for %s — graph data kept in Postgres', folder)
            raise
        if on_progress:
            on_progress('vector_storage', 'Writing FAISS index', 85.0)
        index_path = faiss_index_path_for_repository(repository.id)
        invalidate_faiss_cache(repository.id)
        store = FaissStore(index_path=index_path)
        store.load_or_create()
        embedding_indices = store.add(vectors)
        store.save()
        invalidate_faiss_cache(repository.id)
        if on_progress:
            on_progress('vector_storage', 'Vectors stored', 100.0)
        chunks_stored = store_chunks_with_embeddings(session, batch, embedding_indices)
        session.commit()
        summary = {'repository_id': str(repository.id), 'repository': repo_name, 'root_path': root_path, 'files': batch.files_indexed, 'classes': batch.classes_indexed, 'functions': batch.functions_indexed, 'chunks': chunks_stored, 'embeddings': len(embedding_indices), 'calls': batch.calls_indexed, 'faiss_index': str(index_path)}
        logger.info('index_folder: %s', summary)
        return summary
    except EmbeddingError:
        raise
    except Exception:
        session.rollback()
        logger.exception('index_folder: failed for %s', folder)
        raise
    finally:
        session.close()

def _empty_summary(repository: str | None=None) -> dict:
    return {'repository_id': None, 'repository': repository, 'files': 0, 'classes': 0, 'functions': 0, 'chunks': 0, 'embeddings': 0, 'calls': 0}
