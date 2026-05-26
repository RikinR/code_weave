"""Verify embedding text formatting for function, class, module, and document chunks.

Covers ``application.ingestion.chunk_text.chunk_to_embedding_text`` and the
labels and descriptions included in each chunk type's embedding payload.
"""

from application.ingestion.chunk_text import chunk_to_embedding_text

def test_function_chunk_embedding_text():
    text = chunk_to_embedding_text('app/main.py', {'name': 'run', 'code': 'def run(): pass', 'description': 'Starts the app', 'chunk_type': 'function'})
    assert 'function: run' in text
    assert 'description: Starts the app' in text

def test_document_chunk_embedding_text():
    text = chunk_to_embedding_text('README.md', {'name': 'Setup', 'code': 'pip install -r requirements.txt', 'description': 'Install dependencies', 'chunk_type': 'document'})
    assert 'section: Setup' in text
    assert 'function:' not in text

def test_class_chunk_embedding_text():
    text = chunk_to_embedding_text('app/models.py', {'name': 'User', 'code': 'class User:\n    pass', 'chunk_type': 'class'})
    assert 'class: User' in text
    assert 'function:' not in text

def test_module_chunk_embedding_text():
    text = chunk_to_embedding_text('app/__init__.py', {'name': 'app', 'code': '"""Package root."""', 'chunk_type': 'module'})
    assert 'module: app' in text
    assert 'function:' not in text
