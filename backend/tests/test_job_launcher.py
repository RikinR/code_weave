import os
from unittest.mock import MagicMock, patch
from application.ingestion.job_launcher import launch_ingestion_worker, resume_recoverable_jobs
from application.repos.processing_tracker import INTERRUPTED_BY_RESTART_ERROR,ProcessingTracker

def test_launch_ingestion_worker_records_pid(tmp_path, monkeypatch):
    jobs = tmp_path / "jobs"
    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True)
    jobs.mkdir(parents=True)
    monkeypatch.setattr("application.repos.processing_tracker.JOBS_DIR", jobs)
    monkeypatch.setattr("application.repos.processing_tracker.UPLOADS_DIR", uploads)

    tracker = ProcessingTracker()
    monkeypatch.setattr("application.ingestion.job_launcher.tracker", tracker)
    job = tracker.create_job("spawn-me")
    zip_path = uploads / f"{job.id}.zip"
    zip_path.write_bytes(b"PK\x05\x06")

    mock_proc = MagicMock()
    mock_proc.pid = 4242

    with patch("application.ingestion.job_launcher.subprocess.Popen", return_value=mock_proc):
        proc = launch_ingestion_worker(job, zip_path, max_upload_bytes=1024)

    assert proc is mock_proc
    restored = tracker.get_job(job.id)
    assert restored is not None
    assert restored.worker_pid == 4242

def test_resume_recoverable_jobs_restarts_failed_interrupt(tmp_path, monkeypatch):
    jobs = tmp_path / "jobs"
    uploads = tmp_path / "uploads"
    uploads.mkdir(parents=True)
    jobs.mkdir(parents=True)
    monkeypatch.setattr("application.repos.processing_tracker.JOBS_DIR", jobs)
    monkeypatch.setattr("application.repos.processing_tracker.UPLOADS_DIR", uploads)

    tracker = ProcessingTracker()
    monkeypatch.setattr("application.ingestion.job_launcher.tracker", tracker)
    job = tracker.create_job("resume-me")
    zip_path = uploads / f"{job.id}.zip"
    zip_path.write_bytes(b"PK\x05\x06")
    with job._lock:
        job.status = "failed"
        job.error = INTERRUPTED_BY_RESTART_ERROR
    tracker._persist_job(job)

    mock_proc = MagicMock()
    mock_proc.pid = os.getpid()

    with patch(
        "application.ingestion.job_launcher.launch_ingestion_worker",
        return_value=mock_proc,
    ) as launch:
        started = resume_recoverable_jobs(max_upload_bytes=1024)

    assert started == 1
    launch.assert_called_once()
    restored = tracker.get_job(job.id)
    assert restored is not None
    assert restored.status == "pending"
