from __future__ import annotations
from application.ingestion.description_extract import infer_description_from_code,is_generic_description
from infrastructure.llm.config import GROQ_API_KEY
from infrastructure.llm.groq_client import GroqError, chat_completion
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_MAX_CODE_CHARS = 4000


def generate_function_description(
    *,
    code: str,
    name: str,
    file_path: str | None = None,
    language: str | None = None,
    signature: str | None = None,
) -> str | None:
    """Produce a detailed behavioral summary from source code."""
    if not code or not code.strip():
        return None

    if GROQ_API_KEY:
        try:
            return _summarize_with_llm(
                code=code,
                name=name,
                file_path=file_path,
                language=language,
                signature=signature,
            )
        except GroqError as exc:
            logger.warning("summarize_description: LLM failed for %s: %s", name, exc)

    return infer_description_from_code(code, name=name, language=language)


def ensure_function_description(
    stored: str | None,
    *,
    code: str | None,
    name: str,
    file_path: str | None = None,
    language: str | None = None,
    signature: str | None = None,
) -> str | None:
    if stored and not is_generic_description(stored):
        return stored
    if not code:
        return stored
    generated = generate_function_description(
        code=code,
        name=name,
        file_path=file_path,
        language=language,
        signature=signature,
    )
    return generated or stored


def _summarize_with_llm(
    *,
    code: str,
    name: str,
    file_path: str | None,
    language: str | None,
    signature: str | None,
) -> str:
    trimmed = code if len(code) <= _MAX_CODE_CHARS else code[:_MAX_CODE_CHARS] + "\n// ..."
    meta = [
        f"Function: {name}",
        f"File: {file_path or 'unknown'}",
        f"Language: {language or 'unknown'}",
    ]
    if signature:
        meta.append(f"Signature: {signature}")

    messages = [
        {
            "role": "system",
            "content": (
                "You summarize what a code function does for developers exploring a codebase. "
                "Write 1-2 sentences in plain English. Focus on behavior: inputs, outputs, "
                "data accessed (e.g. nested properties), and side effects. "
                "Do not repeat the function name verbatim as the whole answer. "
                "Do not wrap identifiers in quotes. No markdown."
            ),
        },
        {
            "role": "user",
            "content": "\n".join(meta) + f"\n\nCode:\n{trimmed}",
        },
    ]
    result = chat_completion(messages, temperature=0.1, max_tokens=180).strip()
    if not result:
        raise GroqError("empty summary")
    return result
