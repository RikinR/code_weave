from pathlib import Path

from application.ingestion.process_context import (
    chunk_markdown,
    chunk_requirements,
    chunk_sliding_window,
    chunk_yaml,
    process_context_file,
)


def test_chunk_markdown_splits_on_headings():
    text = "# Intro\n\nHello world.\n\n## Setup\n\nRun pip install.\n"
    chunks = chunk_markdown(text)
    assert len(chunks) == 2
    assert chunks[0]["name"] == "Intro"
    assert "Hello world" in chunks[0]["code"]
    assert chunks[1]["name"] == "Setup"
    assert chunks[1]["chunk_type"] == "document"


def test_chunk_yaml_splits_top_level_keys():
    text = "service:\n  name: api\n\nversion: 1\n"
    chunks = chunk_yaml(text)
    assert len(chunks) >= 2
    names = {c["name"] for c in chunks}
    assert "service" in names
    assert "version" in names


def test_chunk_requirements_groups_lines():
    text = "fastapi>=0.1\nuvicorn>=0.2\n\npytest>=7\n"
    chunks = chunk_requirements(text)
    assert len(chunks) >= 1
    assert "fastapi" in chunks[0]["code"]


def test_sliding_window_fallback():
    text = "a" * 5000
    chunks = chunk_sliding_window(text, max_chars=2000, overlap=200)
    assert len(chunks) >= 2
    assert chunks[0]["name"] == "part-1"


def test_process_context_file_returns_document_chunks(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text("# Title\n\nProject overview.\n", encoding="utf-8")
    result = process_context_file(str(readme))
    assert result["language"] == "markdown"
    assert len(result["chunks"]) >= 1
    assert result["structure"] == {}
    assert result["calls"] == []
