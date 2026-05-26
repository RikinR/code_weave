from __future__ import annotations

"""CLI entry point for background ingestion worker processes.

Pipeline stage: invoked after upload; runs **ZIP extract → … → graph** via
:mod:`pipeline_runner`. Spawned by :mod:`job_launcher` with a job id and size
limit; loads job state from :mod:`application.repos.processing_tracker` and
delegates to :func:`pipeline_runner.run_ingestion_job`.
"""
import sys
from application.ingestion.pipeline_runner import UPLOADS_DIR, run_ingestion_job
from application.repos.processing_tracker import tracker
from infrastructure.logging.logger import get_logger
logger = get_logger(__name__)

def main() -> int:
    """Load a tracked ingestion job by id and execute the full pipeline."""
    if len(sys.argv) < 2:
        logger.error('worker: job_id required')
        return 2
    job_id = sys.argv[1]
    max_upload_bytes = int(sys.argv[2]) if len(sys.argv) > 2 else 200 * 1024 * 1024
    job = tracker.get_job(job_id)
    if job is None:
        logger.error('worker: unknown job %s', job_id)
        return 1
    zip_path = tracker.zip_path_for(job_id)
    if not zip_path.is_file():
        job.fail_stage('zip_extraction', 'ZIP file missing for ingestion worker')
        return 1
    logger.info('worker: starting job %s', job_id)
    run_ingestion_job(job, zip_path, max_upload_bytes=max_upload_bytes)
    return 0 if job.status == 'completed' else 1
if __name__ == '__main__':
    raise SystemExit(main())
