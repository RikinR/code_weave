from application.retrieval.format_answer import format_assistant_answer


def test_stored_strips_wrapped_identifiers():
    raw = 'The function "process_file" lives in "app/main.py".'
    cleaned = format_assistant_answer(raw)
    assert '"' not in cleaned
    assert "process_file" in cleaned
    assert "app/main.py" in cleaned


def test_format_answer_removes_smart_quotes():
    raw = "Summary: It calls \u2018helper\u2019 inside \u201cmain\u201d."
    cleaned = format_assistant_answer(raw)
    assert "\u2018" not in cleaned
    assert "\u201d" not in cleaned
