from __future__ import annotations
from pathlib import Path
from application.ingestion.folder import process_folder
from application.ingestion.persist import IndexBatch,get_or_create_repository,store_chunks_with_embeddings
from infrastructure.db.bootstrap import ensure_db_ready
from infrastructure.db.session import SessionLocal
from infrastructure.embeddings.local_embedder import EmbeddingError, embed_texts
from infrastructure.logging.logger import get_logger
from infrastructure.vector.config import faiss_index_path_for_repository
from infrastructure.vector.faiss_store import FaissStore

logger = get_logger(__name__)


def index_folder(folder: Path, repository_name: str | None = None) -> dict:
    if not folder.is_dir():
        logger.warning("folder does not exist or is not a directory: %s", folder)
        return _empty_summary()

    ensure_db_ready()

    repo_name = repository_name or folder.name
    root_path = str(folder.resolve())
    parsed_files = process_folder(folder)
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

        # Commit graph metadata first so a later embedding failure does not roll it back.
        session.commit()
        logger.info(
            "index_folder: committed repository graph (%d files, %d functions, %d calls)",
            batch.files_indexed,
            batch.functions_indexed,
            batch.calls_indexed,
        )

        texts = [item["text"] for item in batch.pending]
        try:
            vectors = embed_texts(texts)
        except EmbeddingError:
            logger.exception(
                "index_folder: embedding failed for %s — graph data kept in Postgres",
                folder,
            )
            raise

        index_path = faiss_index_path_for_repository(repository.id)
        store = FaissStore(index_path=index_path)
        store.load_or_create()
        embedding_indices = store.add(vectors)
        store.save()

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
