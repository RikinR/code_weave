"""Verify description extraction from docstrings, comments, and code heuristics.

Covers ``application.ingestion.description_extract`` for Python and JavaScript
sources, including generic-description detection and resolution precedence.
"""

from application.ingestion.description_extract import extract_class_description, extract_file_description, extract_function_description, extract_preceding_comments, infer_description_from_code, is_generic_description, resolve_function_description

def test_extract_python_function_docstring():
    code = 'def greet(name):\n    """Say hello to the user."""\n    return name\n'
    assert extract_function_description(code, language='python') == 'Say hello to the user.'

def test_extract_python_module_docstring():
    code = '"""Repository ingestion helpers."""\n\ndef run():\n    pass\n'
    assert extract_file_description(code, language='python') == 'Repository ingestion helpers.'

def test_extract_class_description_from_python():
    code = 'class Worker:\n    """Runs background jobs."""\n\n    def run(self):\n        pass\n'
    assert extract_class_description(code, 'Worker', language='python') == 'Runs background jobs.'

def test_extract_preceding_jsdoc():
    source = '/** Returns priority based on dynamic key under data. */\nfunction reorderRequestBlocks(items) {\n  return items.sort((a, b) => a.data.priority - b.data.priority);\n}\n'
    before = source.index('function reorderRequestBlocks')
    assert extract_preceding_comments(source, before) == 'Returns priority based on dynamic key under data.'

def test_infer_description_from_sort_and_data_path():
    code = '\nfunction reorderRequestBlocks(items) {\n  return items.sort((a, b) => a.data.priority - b.data.priority);\n}\n'
    desc = infer_description_from_code(code, name='reorderRequestBlocks', language='javascript')
    assert desc is not None
    assert 'sort' in desc.lower()
    assert 'data' in desc.lower() or 'priority' in desc.lower()

def test_resolve_function_description_uses_preceding_comments():
    source = '// Sort request blocks by nested priority\nconst reorderRequestBlocks = (items) => items.sort((a, b) => a.data.priority - b.data.priority);\n'
    start = source.index('const reorderRequestBlocks')
    chunk = source[start:]
    assert resolve_function_description(source=source, chunk_code=chunk, definition_start=start, name='reorderRequestBlocks', language='javascript') == 'Sort request blocks by nested priority'

def test_is_generic_description():
    assert is_generic_description(None) is True
    assert is_generic_description('Function reorderRequestBlocks in src/utils/helper.js.') is True
    assert is_generic_description('Returns priority for each request block using nested data.priority values.') is False
    assert is_generic_description('This function buckets.') is True

def test_infer_class_bucket_description():
    code = 'from collections import deque\nfrom dataclasses import dataclass, field\n\n@dataclass\nclass _Bucket:\n    timestamps: deque[float] = field(default_factory=deque)\n'
    desc = infer_description_from_code(code, name='_Bucket', language='python')
    assert desc is not None
    assert 'buckets' not in desc.lower() or 'rate' in desc.lower()
    assert 'timestamp' in desc.lower() or 'deque' in desc.lower()

def test_infer_jwt_decode_description():
    code = '\ndef decode_claims(token: str) -> dict | None:\n    try:\n        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])\n    except JWTError:\n        return None\n'
    desc = infer_description_from_code(code, name='decode_claims', language='python')
    assert desc is not None
    assert 'jwt' in desc.lower() or 'token' in desc.lower()
    assert 'buckets' not in desc.lower()
