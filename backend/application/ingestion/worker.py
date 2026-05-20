from __future__ import annotations
import sys
from application.ingestion.pipeline_runner import UPLOADS_DIR, run_ingestion_job
from application.repos.processing_tracker import tracker
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

def main() -> int:
    if len(sys.argv) < 2:
        logger.error("worker: job_id required")
        return 2

    job_id = sys.argv[1]
    max_upload_bytes = int(sys.argv[2]) if len(sys.argv) > 2 else 100 * 1024 * 1024

    job = tracker.get_job(job_id)
    if job is None:
        logger.error("worker: unknown job %s", job_id)
        return 1

    zip_path = tracker.zip_path_for(job_id)
    if not zip_path.is_file():
        job.fail_stage("zip_extraction", "ZIP file missing for ingestion worker")
        return 1

    logger.info("worker: starting job %s", job_id)
    run_ingestion_job(job, zip_path, max_upload_bytes=max_upload_bytes)
    return 0 if job.status == "completed" else 1

if __name__ == "__main__":
    raise SystemExit(main())
