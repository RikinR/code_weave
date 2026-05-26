"""Verify function description enrichment with heuristic and optional LLM fallback.

Covers ``application.ingestion.summarize_description.ensure_function_description``
when LLM summarization is disabled versus explicitly allowed.
"""

from unittest.mock import patch
from application.ingestion.summarize_description import ensure_function_description

def test_ensure_function_description_skips_llm_by_default():
    code = 'def add(a, b):\n    return a + b\n'
    with patch('application.ingestion.summarize_description.chat_completion') as mock_chat:
        result = ensure_function_description(None, code=code, name='add', language='python', allow_llm=False)
    mock_chat.assert_not_called()
    assert result is not None
    assert 'add' in result.lower() or 'return' in result.lower()

def test_ensure_function_description_uses_llm_when_allowed():
    with patch('application.ingestion.summarize_description.GROQ_API_KEY', 'test-key'), patch('application.ingestion.summarize_description.chat_completion', return_value='Adds two numbers.'):
        result = ensure_function_description(None, code='def add(a, b):\n    return a + b\n', name='add', allow_llm=True)
    assert result == 'Adds two numbers.'
