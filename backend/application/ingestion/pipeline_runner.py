from __future__ import annotations
import threading
from pathlib import Path
from uuid import UUID
from application.ingestion.job_launcher import launch_ingestion_worker, maybe_resume_queued_job
from application.graph.build_graph import build_architecture_graph
from application.ingestion.index_folder import index_folder
from application.ingestion.source_filter import classify_ingestible_file, iter_ingestible_files
from application.ingestion.zip_extract import ZipExtractionError, extract_zip
from application.repos.processing_tracker import IngestionJob, tracker
from infrastructure.db.session import SessionLocal
from infrastructure.logging.logger import get_logger
from infrastructure.parser.path_language import infer_language

logger = get_logger(__name__)

DATA_ROOT = Path(__file__).resolve().parents[2] / "data"
UPLOADS_DIR = DATA_ROOT / "uploads"


def run_ingestion_job(
    job: IngestionJob,
    zip_path: Path,
    *,
    max_upload_bytes: int,
) -> None:
    if not tracker.try_acquire_active(job.id):
        job.fail_stage("zip_extraction", "Another ingestion job is already running")
        return

    extract_dir = UPLOADS_DIR / job.id
    stop_heartbeat = threading.Event()

    def _heartbeat_loop() -> None:
        tick = 0
        while not stop_heartbeat.wait(3.0):
            tick += 1
            running_key = next(
                (
                    k
                    for k in reversed(job.stages.keys())
                    if job.stages[k].status.value == "running"
                ),
                None,
            )
            if running_key is None:
                continue
            elapsed = tick * 3
            job.pulse(
                running_key,
                f"Still working… ({elapsed}s elapsed on {job.stages[running_key].label})",
            )

    heartbeat_thread = threading.Thread(
        target=_heartbeat_loop, name=f"heartbeat-{job.id}", daemon=True
    )
    heartbeat_thread.start()

    try:
        job.start_stage("zip_extraction")
        job.log("zip_extraction", f"Extracting {zip_path.name}")
        root = extract_zip(zip_path, extract_dir, max_bytes=max_upload_bytes)
        job.complete_stage("zip_extraction", f"Extracted to {root}")

        job.start_stage("file_scanning")
        sources = list(iter_ingestible_files(root))
        code_count = sum(1 for p in sources if classify_ingestible_file(p) == "code")
        context_count = len(sources) - code_count
        job.log(
            "file_scanning",
            f"Found {len(sources)} ingestible files ({code_count} code, {context_count} context)",
        )
        if not sources:
            job.fail_stage("file_scanning", "No supported source or context files found in archive")
            return
        job.complete_stage("file_scanning")

        job.start_stage("language_detection")
        langs: dict[str, int] = {}
        for path in sources:
            kind = classify_ingestible_file(path)
            if kind == "context":
                from application.ingestion.process_context import infer_context_kind

                label = infer_context_kind(path)
                langs[label] = langs.get(label, 0) + 1
                continue
            try:
                lang = infer_language(path)
                langs[lang] = langs.get(lang, 0) + 1
            except Exception:
                continue
        job.log("language_detection", f"Languages: {langs}")
        job.complete_stage("language_detection")

        def on_progress(stage: str, message: str, percent: float) -> None:
            job.advance_to_stage(stage)
            job.update_stage(stage, percent, message)

        summary = index_folder(
            root,
            repository_name=job.repository_name,
            on_progress=on_progress,
            sources=sources,
        )

        for stage in (
            "tree_sitter_parsing",
            "ast_generation",
            "class_extraction",
            "function_extraction",
            "call_extraction",
            "chunk_generation",
            "embedding_generation",
            "vector_storage",
        ):
            if job.stages[stage].status.value != "completed":
                job.complete_stage(stage, "Done")

        repository_id = summary.get("repository_id")
        if not repository_id:
            job.fail_stage("embedding_generation", "Indexing produced no repository")
            return

        job.start_stage("architecture_graph")
        session = SessionLocal()
        try:
            build_architecture_graph(session, UUID(str(repository_id)))
        finally:
            session.close()
        job.complete_stage("architecture_graph", "Architecture graph ready")

        job.complete_job(str(repository_id))
    except ZipExtractionError as exc:
        job.fail_stage("zip_extraction", str(exc))
    except Exception as exc:
        logger.exception("pipeline_runner: job %s failed", job.id)
        failed = next(
            (k for k, s in job.stages.items() if s.status.value == "running"),
            "embedding_generation",
        )
        job.fail_stage(failed, str(exc))
    finally:
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1.0)
        tracker.clear_worker_pid(job)
        tracker.release_active(job.id)
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass
        maybe_resume_queued_job(max_upload_bytes=max_upload_bytes)


def start_ingestion_background(
    job: IngestionJob,
    zip_path: Path,
    *,
    max_upload_bytes: int,
) -> None:
    if not launch_ingestion_worker(job, zip_path, max_upload_bytes=max_upload_bytes):
        failed = next(
            (k for k, s in job.stages.items() if s.status.value in ("pending", "running")),
            "zip_extraction",
        )
        job.fail_stage(failed, "Failed to start ingestion worker process")
