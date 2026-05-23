from application.ingestion.description_extract import (
    extract_class_description,
    extract_file_description,
    extract_function_description,
    extract_preceding_comments,
    infer_description_from_code,
    is_generic_description,
    resolve_function_description,
)


def test_extract_python_function_docstring():
    code = '''def greet(name):
    """Say hello to the user."""
    return name
'''
    assert extract_function_description(code, language="python") == "Say hello to the user."


def test_extract_python_module_docstring():
    code = '''"""Repository ingestion helpers."""

def run():
    pass
'''
    assert extract_file_description(code, language="python") == "Repository ingestion helpers."


def test_extract_class_description_from_python():
    code = '''class Worker:
    """Runs background jobs."""

    def run(self):
        pass
'''
    assert extract_class_description(code, "Worker", language="python") == "Runs background jobs."


def test_extract_preceding_jsdoc():
    source = """/** Returns priority based on dynamic key under data. */
function reorderRequestBlocks(items) {
  return items.sort((a, b) => a.data.priority - b.data.priority);
}
"""
    before = source.index("function reorderRequestBlocks")
    assert extract_preceding_comments(source, before) == (
        "Returns priority based on dynamic key under data."
    )


def test_infer_description_from_sort_and_data_path():
    code = """
function reorderRequestBlocks(items) {
  return items.sort((a, b) => a.data.priority - b.data.priority);
}
"""
    desc = infer_description_from_code(code, name="reorderRequestBlocks", language="javascript")
    assert desc is not None
    assert "reorders" in desc.lower()
    assert "data" in desc.lower() or "priority" in desc.lower()


def test_resolve_function_description_uses_preceding_comments():
    source = """// Sort request blocks by nested priority
const reorderRequestBlocks = (items) => items.sort((a, b) => a.data.priority - b.data.priority);
"""
    start = source.index("const reorderRequestBlocks")
    chunk = source[start:]
    assert resolve_function_description(
        source=source,
        chunk_code=chunk,
        definition_start=start,
        name="reorderRequestBlocks",
        language="javascript",
    ) == "Sort request blocks by nested priority"


def test_is_generic_description():
    assert is_generic_description(None) is True
    assert is_generic_description("Function reorderRequestBlocks in src/utils/helper.js.") is True
    assert is_generic_description(
        "Returns priority for each request block using nested data.priority values."
    ) is False
