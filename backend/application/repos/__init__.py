"""Repository lifecycle and ingestion job coordination services.

:mod:`application.repos.repository_service` handles listing and deleting indexed
repos; :mod:`application.repos.processing_tracker` tracks upload pipeline jobs
and SSE progress; :mod:`application.repos.job_file_lock` serializes job JSON writes.
"""
