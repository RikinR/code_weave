from application.ingestion.chunk_text import chunk_to_embedding_text


def test_function_chunk_embedding_text():
    text = chunk_to_embedding_text(
        "app/main.py",
        {
            "name": "run",
            "code": "def run(): pass",
            "description": "Starts the app",
            "chunk_type": "function",
        },
    )
    assert "function: run" in text
    assert "description: Starts the app" in text


def test_document_chunk_embedding_text():
    text = chunk_to_embedding_text(
        "README.md",
        {
            "name": "Setup",
            "code": "pip install -r requirements.txt",
            "description": "Install dependencies",
            "chunk_type": "document",
        },
    )
    assert "section: Setup" in text
    assert "function:" not in text
