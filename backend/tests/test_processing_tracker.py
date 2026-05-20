import json
import time
from application.repos.processing_tracker import JOBS_DIR,PIPELINE_STAGES,ProcessingTracker

def test_create_job_has_all_stages():
    tracker = ProcessingTracker()
    job = tracker.create_job("demo-repo")
    snapshot = job.snapshot()
    assert len(snapshot["stages"]) == len(PIPELINE_STAGES)
    assert snapshot["status"] == "pending"

def test_stage_lifecycle():
    tracker = ProcessingTracker()
    job = tracker.create_job("demo")
    job.start_stage("zip_extraction")
    job.complete_stage("zip_extraction", "done")
    stage = job.stages["zip_extraction"]
    assert stage.status.value == "completed"
    assert stage.progress == 100.0

def test_job_persisted_and_reloaded(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "application.repos.processing_tracker.JOBS_DIR",
        tmp_path,
    )
    tracker = ProcessingTracker()
    job = tracker.create_job("persist-me")
    job.start_stage("zip_extraction")
    job.complete_stage("zip_extraction", "done")

    reloaded = ProcessingTracker()
    restored = reloaded.get_job(job.id)
    assert restored is not None
    assert restored.repository_name == "persist-me"
    assert restored.stages["zip_extraction"].status.value == "completed"

    payload = json.loads((tmp_path / f"{job.id}.json").read_text(encoding="utf-8"))
    assert payload["repository_name"] == "persist-me"

def test_running_job_not_failed_on_reload_while_live(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "application.repos.processing_tracker.JOBS_DIR",
        tmp_path,
    )
    tracker = ProcessingTracker()
    job = tracker.create_job("reload-me")
    job.start_stage("zip_extraction")
    job.complete_stage("zip_extraction", "done")
    job.start_stage("file_scanning")
    job.pulse("file_scanning", "scanning")

    reloaded = ProcessingTracker()
    restored = reloaded.get_job(job.id)
    assert restored is not None
    assert restored.status == "running"
    assert restored.error is None
    assert restored.stages["file_scanning"].status.value == "running"

def test_running_job_with_dead_worker_pid_is_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "application.repos.processing_tracker.JOBS_DIR",
        tmp_path,
    )
    tracker = ProcessingTracker()
    job = tracker.create_job("dead-worker")
    job.start_stage("embedding_generation")
    tracker.set_worker_pid(job, 999_999_999)

    fetched = tracker.get_job(job.id)
    assert fetched is not None
    assert fetched.status == "failed"
    assert fetched.error == "Interrupted by server restart"

def test_running_job_not_interrupted_while_live(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "application.repos.processing_tracker.JOBS_DIR",
        tmp_path,
    )
    tracker = ProcessingTracker()
    job = tracker.create_job("live-job")
    assert tracker.try_acquire_active(job.id)
    job.start_stage("zip_extraction")
    job.pulse("zip_extraction", "extracting")

    fetched = tracker.get_job(job.id)
    assert fetched is not None
    assert fetched.status == "running"
    assert fetched.error is None

def test_stale_running_job_interrupted_on_poll(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "application.repos.processing_tracker.JOBS_DIR",
        tmp_path,
    )
    monkeypatch.setattr(
        "application.repos.processing_tracker.STALE_JOB_SECONDS",
        30,
    )
    tracker = ProcessingTracker()
    job = tracker.create_job("stale-job")
    job.start_stage("embedding_generation")
    job.last_activity_at = time.time() - 120

    fetched = tracker.get_job(job.id)
    assert fetched is not None
    assert fetched.status == "failed"
    assert fetched.error == "Interrupted by server restart"

def test_stale_active_lock_released_for_new_job(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "application.repos.processing_tracker.JOBS_DIR",
        tmp_path,
    )
    monkeypatch.setattr(
        "application.repos.processing_tracker.STALE_JOB_SECONDS",
        30,
    )
    tracker = ProcessingTracker()
    stale = tracker.create_job("stale-holder")
    assert tracker.try_acquire_active(stale.id)
    stale.start_stage("tree_sitter_parsing")
    stale.last_activity_at = time.time() - 120

    fresh = tracker.create_job("fresh-job")
    assert tracker.try_acquire_active(fresh.id)

def test_orphan_zip_recovered_on_get_job(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    jobs = tmp_path / "jobs"
    uploads.mkdir(parents=True)
    jobs.mkdir(parents=True)
    monkeypatch.setattr("application.repos.processing_tracker.JOBS_DIR", jobs)
    monkeypatch.setattr("application.repos.processing_tracker.UPLOADS_DIR", uploads)

    job_id = "orphan-job-id"
    (uploads / f"{job_id}.zip").write_bytes(b"PK\x05\x06")
    (uploads / f"{job_id}.meta.json").write_text(
        '{"repository_name": "my-repo"}',
        encoding="utf-8",
    )

    tracker = ProcessingTracker()
    restored = tracker.get_job(job_id)
    assert restored is not None
    assert restored.repository_name == "my-repo"
    assert restored.status == "pending"
    assert restored.error is None
    assert (jobs / f"{job_id}.json").is_file()

def test_orphan_uploads_recovered_on_tracker_init(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    jobs = tmp_path / "jobs"
    uploads.mkdir(parents=True)
    jobs.mkdir(parents=True)
    monkeypatch.setattr("application.repos.processing_tracker.JOBS_DIR", jobs)
    monkeypatch.setattr("application.repos.processing_tracker.UPLOADS_DIR", uploads)

    job_id = "startup-orphan"
    (uploads / f"{job_id}.zip").write_bytes(b"PK\x05\x06")

    tracker = ProcessingTracker()
    restored = tracker.get_job(job_id)
    assert restored is not None
    assert restored.status == "pending"
    assert (jobs / f"{job_id}.json").is_file()

def test_get_job_syncs_when_worker_updates_disk(tmp_path, monkeypatch):
    """Detached workers persist job JSON; API process must reload, not serve stale cache."""
    monkeypatch.setattr(
        "application.repos.processing_tracker.JOBS_DIR",
        tmp_path,
    )
    tracker = ProcessingTracker()
    job = tracker.create_job("worker-sync")
    cached = tracker.get_job(job.id)
    assert cached is not None
    assert cached.status == "pending"

    path = tmp_path / f"{job.id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["status"] = "running"
    payload["updated_at"] = time.time() + 1
    payload["stages"][0]["status"] = "running"
    payload["stages"][0]["progress"] = 42.0
    path.write_text(json.dumps(payload), encoding="utf-8")

    refreshed = tracker.get_job(job.id)
    assert refreshed is not None
    assert refreshed.status == "running"
    assert refreshed.stages["zip_extraction"].status.value == "running"
    assert refreshed.stages["zip_extraction"].progress == 42.0

def test_zip_path_for_and_can_retry(tmp_path, monkeypatch):
    uploads = tmp_path / "uploads"
    jobs = tmp_path / "jobs"
    uploads.mkdir(parents=True)
    jobs.mkdir(parents=True)
    monkeypatch.setattr("application.repos.processing_tracker.JOBS_DIR", jobs)
    monkeypatch.setattr("application.repos.processing_tracker.UPLOADS_DIR", uploads)

    tracker = ProcessingTracker()
    job = tracker.create_job("retry-me")
    zip_path = uploads / f"{job.id}.zip"
    zip_path.write_bytes(b"PK\x05\x06")

    assert tracker.zip_path_for(job.id) == zip_path
    assert not tracker.can_retry(job.id)

    with job._lock:
        job.status = "failed"
    assert tracker.can_retry(job.id)
