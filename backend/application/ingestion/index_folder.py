from __future__ import annotations
from collections.abc import Callable
from pathlib import Path
from application.ingestion.persist import IndexBatch,get_or_create_repository,store_chunks_with_embeddings
from infrastructure.db.bootstrap import ensure_db_ready
from infrastructure.db.session import SessionLocal
from infrastructure.embeddings.local_embedder import EmbeddingError, embed_texts
from infrastructure.logging.logger import get_logger
from infrastructure.vector.config import faiss_index_path_for_repository
from infrastructure.vector.faiss_store import FaissStore

logger = get_logger(__name__)


ProgressCallback = Callable[[str, str, float], None]


def index_folder(
    folder: Path,
    repository_name: str | None = None,
    *,
    on_progress: ProgressCallback | None = None,
    sources: list[Path] | None = None,
) -> dict:
    def _progress(stage: str, message: str, percent: float) -> None:
        if on_progress is not None:
            on_progress(stage, message, percent)
    if not folder.is_dir():
        logger.warning("folder does not exist or is not a directory: %s", folder)
        return _empty_summary()

    ensure_db_ready()

    repo_name = repository_name or folder.name
    root_path = str(folder.resolve())
    if on_progress:
        on_progress("file_scanning", f"Scanning {folder}", 10.0)

    from application.ingestion.process_code import process_file
    from application.ingestion.source_filter import iter_source_files

    parsed_files: list[dict] = []
    if sources is None:
        sources = list(iter_source_files(folder))
    total_sources = max(len(sources), 1)
    for index, source in enumerate(sources, start=1):
        path = str(source)
        if on_progress:
            pct = 15.0 + (index / total_sources) * 40.0
            on_progress(
                "tree_sitter_parsing",
                f"Parsing {source.name} ({index}/{total_sources})",
                pct,
            )
        try:
            parsed_files.append(process_file(file_path=path))
        except RuntimeError as exc:
            logger.warning("index_folder: skip %s: %s", path, exc)
        except Exception:
            logger.exception("index_folder: failed to process %s", path)

    if on_progress:
        on_progress(
            "tree_sitter_parsing",
            f"Parsed {len(parsed_files)} of {len(sources)} files",
            55.0,
        )
        on_progress("chunk_generation", "Chunks prepared", 58.0)
    if not parsed_files:
        logger.info("index_folder: no parseable files under %s", folder)
        return _empty_summary(repository=repo_name)

    session = SessionLocal()
    try:
        repository = get_or_create_repository(
            session,
            name=repo_name,
            root_path=root_path,
        )
        batch = IndexBatch(repository)

        for file_result in parsed_files:
            if not file_result.get("chunks"):
                logger.debug("index_folder: no chunks for %s", file_result["file"])
                continue
            batch.add_file(session, file_result)

        batch.record_all_calls(session)

        if not batch.pending:
            session.commit()
            return {
                "repository_id": str(repository.id),
                "repository": repo_name,
                "files": batch.files_indexed,
                "classes": batch.classes_indexed,
                "functions": batch.functions_indexed,
                "chunks": 0,
                "embeddings": 0,
                "calls": batch.calls_indexed,
            }
        session.commit()
        logger.info(
            "index_folder: committed repository graph (%d files, %d functions, %d calls)",
            batch.files_indexed,
            batch.functions_indexed,
            batch.calls_indexed,
        )

        texts = [item["text"] for item in batch.pending]
        if on_progress:
            on_progress("embedding_generation", f"Embedding {len(texts)} chunks", 70.0)
        try:
            vectors = embed_texts(texts)
        except EmbeddingError:
            logger.exception(
                "index_folder: embedding failed for %s — graph data kept in Postgres",
                folder,
            )
            raise

        if on_progress:
            on_progress("vector_storage", "Writing FAISS index", 85.0)
        index_path = faiss_index_path_for_repository(repository.id)
        store = FaissStore(index_path=index_path)
        store.load_or_create()
        embedding_indices = store.add(vectors)
        store.save()
        if on_progress:
            on_progress("vector_storage", "Vectors stored", 95.0)

        chunks_stored = store_chunks_with_embeddings(session, batch, embedding_indices)
        session.commit()

        summary = {
            "repository_id": str(repository.id),
            "repository": repo_name,
            "root_path": root_path,
            "files": batch.files_indexed,
            "classes": batch.classes_indexed,
            "functions": batch.functions_indexed,
            "chunks": chunks_stored,
            "embeddings": len(embedding_indices),
            "calls": batch.calls_indexed,
            "faiss_index": str(index_path),
        }
        logger.info("index_folder: %s", summary)
        return summary
    except EmbeddingError:
        raise
    except Exception:
        session.rollback()
        logger.exception("index_folder: failed for %s", folder)
        raise
    finally:
        session.close()


def _empty_summary(repository: str | None = None) -> dict:
    return {
        "repository_id": None,
        "repository": repository,
        "files": 0,
        "classes": 0,
        "functions": 0,
        "chunks": 0,
        "embeddings": 0,
        "calls": 0,
    }
