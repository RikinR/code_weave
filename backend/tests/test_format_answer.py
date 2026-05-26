"""Verify post-processing of assistant answers for display.

Covers ``application.retrieval.format_answer.format_assistant_answer``,
including stripping wrapped identifiers and smart quotes from LLM output.
"""

from application.retrieval.format_answer import format_assistant_answer

def test_stored_strips_wrapped_identifiers():
    raw = 'The function "process_file" lives in "app/main.py".'
    cleaned = format_assistant_answer(raw)
    assert '"' not in cleaned
    assert 'process_file' in cleaned
    assert 'app/main.py' in cleaned

def test_format_answer_removes_smart_quotes():
    raw = 'Summary: It calls ‘helper’ inside “main”.'
    cleaned = format_assistant_answer(raw)
    assert '‘' not in cleaned
    assert '”' not in cleaned
