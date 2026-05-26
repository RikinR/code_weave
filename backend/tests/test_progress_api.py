"""Verify progress API recovery of orphan upload jobs from leftover zip artifacts.

Covers ``app.server.create_app``, the ``/api/jobs/{job_id}`` route, and
``application.repos.processing_tracker`` plus ``pipeline_runner`` upload paths.
"""

from pathlib import Path
from fastapi.testclient import TestClient
from app.server import create_app

def test_get_job_recovers_orphan_zip(tmp_path, monkeypatch):
    uploads = tmp_path / 'uploads'
    jobs = tmp_path / 'jobs'
    uploads.mkdir(parents=True)
    jobs.mkdir(parents=True)
    monkeypatch.setattr('application.repos.processing_tracker.JOBS_DIR', jobs)
    monkeypatch.setattr('application.repos.processing_tracker.UPLOADS_DIR', uploads)
    monkeypatch.setattr('application.ingestion.pipeline_runner.UPLOADS_DIR', uploads)
    job_id = 'api-orphan-job'
    (uploads / f'{job_id}.zip').write_bytes(b'PK\x05\x06')
    (uploads / f'{job_id}.meta.json').write_text('{"repository_name": "demo"}', encoding='utf-8')
    client = TestClient(create_app())
    response = client.get(f'/api/jobs/{job_id}')
    assert response.status_code == 200
    body = response.json()
    assert body['job_id'] == job_id
    assert body['repository_name'] == 'demo'
    assert body['status'] == 'pending'
    assert Path(jobs / f'{job_id}.json').is_file()
