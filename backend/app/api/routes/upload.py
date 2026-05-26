from __future__ import annotations

"""ZIP upload endpoint that kicks off the ingestion pipeline.

Accepts a repository archive from the Flutter upload flow, enforces size limits from
``app.api.deps``, and registers a background job tracked by the pipeline UI.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from app.api.deps import MAX_UPLOAD_BYTES
from app.api.schemas.common import UploadResponse
from application.ingestion.pipeline_runner import UPLOADS_DIR, start_ingestion_background
from application.repos.processing_tracker import tracker
router = APIRouter(prefix='/api/repositories', tags=['upload'])

@router.post('/upload', response_model=UploadResponse)
async def upload_repository(file: UploadFile=File(...), name: str | None=Form(None)) -> UploadResponse:
    """Validate the ZIP, persist it on disk, and start background parse/chunk/embed work."""
    if not file.filename or not file.filename.lower().endswith('.zip'):
        raise HTTPException(status_code=400, detail='Only .zip files are supported')
    repository_name = (name or Path(file.filename).stem).strip()
    if not repository_name:
        raise HTTPException(status_code=400, detail='Repository name is required')
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f'ZIP exceeds maximum size of {MAX_UPLOAD_BYTES} bytes')
    try:
        job = tracker.create_job(repository_name)
    except OSError as exc:
        raise HTTPException(status_code=500, detail='Failed to persist ingestion job. Try the upload again.') from exc
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = UPLOADS_DIR / f'{job.id}.zip'
    zip_path.write_bytes(contents)
    start_ingestion_background(job, zip_path, max_upload_bytes=MAX_UPLOAD_BYTES)
    return UploadResponse(job_id=job.id, repository_name=repository_name)
