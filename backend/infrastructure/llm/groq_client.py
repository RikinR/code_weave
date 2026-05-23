from __future__ import annotations
from groq import Groq
from infrastructure.llm.config import GROQ_API_KEY, GROQ_MODEL
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

class GroqError(RuntimeError):
    """Groq chat completion failed."""

def _client() -> Groq:
    if not GROQ_API_KEY:
        raise GroqError(
            "GROQ_API_KEY is not set. Add it to backend/.env before running queries."
        )
    return Groq(api_key=GROQ_API_KEY)

def chat_completion(
    messages: list[dict],
    model: str | None = None,
    *,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> str:
    if not messages:
        raise GroqError("messages must not be empty")

    model_name = model or GROQ_MODEL
    logger.debug("groq: chat model=%s messages=%d", model_name, len(messages))

    try:
        response = _client().chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except Exception as exc:
        logger.error("groq: chat completion failed", exc_info=True)
        raise GroqError(f"Groq chat completion failed: {exc}") from exc

    content = response.choices[0].message.content
    if not content:
        raise GroqError("Groq returned an empty response")

    logger.info("groq: received response (%d chars)", len(content))
    return content

def chat_completion_stream(
    messages: list[dict],
    model: str | None = None,
    *,
    temperature: float = 0.2,
    max_tokens: int = 1024,
):
    if not messages:
        raise GroqError("messages must not be empty")

    model_name = model or GROQ_MODEL
    try:
        stream = _client().chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
    except Exception as exc:
        logger.error("groq: streaming failed", exc_info=True)
        raise GroqError(f"Groq streaming failed: {exc}") from exc
