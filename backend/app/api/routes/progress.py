from __future__ import annotations

"""Ingestion job status and live progress streaming for the pipeline screen.

Exposes job snapshots, retry for failed uploads, and SSE event streams backed by
``application.repos.processing_tracker``.
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.api.deps import MAX_UPLOAD_BYTES
from app.api.schemas.common import JobSnapshot
from application.ingestion.pipeline_runner import start_ingestion_background
from application.repos.processing_tracker import sse_event_stream, tracker
router = APIRouter(prefix='/api/jobs', tags=['jobs'])

@router.get('/{job_id}', response_model=JobSnapshot)
def get_job(job_id: str) -> JobSnapshot:
    """Return the current stage-level snapshot for a single ingestion job."""
    job = tracker.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Job not found')
    return JobSnapshot(**job.snapshot())

@router.post('/{job_id}/retry', response_model=JobSnapshot)
def retry_job(job_id: str) -> JobSnapshot:
    """Restart a failed job from the saved ZIP when the upload file still exists."""
    job = tracker.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail='Job not found')
    if job.status != 'failed':
        raise HTTPException(status_code=400, detail='Only failed jobs can be retried')
    zip_path = tracker.zip_path_for(job_id)
    if not zip_path.is_file():
        raise HTTPException(status_code=400, detail='Original ZIP is no longer available. Upload the repository again.')
    tracker.reset_for_retry(job)
    start_ingestion_background(job, zip_path, max_upload_bytes=MAX_UPLOAD_BYTES)
    return JobSnapshot(**job.snapshot())

@router.get('/{job_id}/events')
async def job_events(job_id: str) -> StreamingResponse:
    """Stream stage updates and log lines to the Flutter pipeline via Server-Sent Events."""
    if tracker.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail='Job not found')
    return StreamingResponse(sse_event_stream(job_id), media_type='text/event-stream', headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive', 'X-Accel-Buffering': 'no'})
