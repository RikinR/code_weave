"""Repository ingestion pipeline: ZIP extract → scan → parse → persist → embed → graph.

This package turns uploaded archives into searchable, graph-backed code indexes.
Orchestration lives in :mod:`pipeline_runner` and :mod:`worker`; folder indexing in
:mod:`index_folder`; per-file parsing in :mod:`process_code` and :mod:`text_chunking`;
persistence and embeddings in :mod:`persist`; and job process management in
:mod:`job_launcher`.
"""
