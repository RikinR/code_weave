"""RAG prompt templates and retrieved-context formatting.

Builds system/user messages consumed by :mod:`infrastructure.llm.groq_client`.
Chunk metadata labels reuse :mod:`application.ingestion.chunk_strategy` for
consistent segment naming in prompts.
"""

from __future__ import annotations
from application.ingestion.chunk_strategy import embedding_segment_label
_STYLE_RULES = 'Writing rules:\n- Use plain prose. Do not wrap identifiers, paths, or function names in quotes or backticks.\n- Do not paste code verbatim. Summarize behavior in your own words.\n- Reference retrieved chunks by number only, e.g. [1], [2]. File paths are shown separately.\n- If context is insufficient, say what is missing.\n- Answer only from the retrieved chunks below.'
_DEFAULT_FORMAT = 'Format your answer exactly like this:\nSummary: One or two sentences answering the question.\nHow it works: Bullet points explaining the flow (use - for each point).\nRelevant chunks: List chunk numbers used, e.g. [1], [3].'
_BEGINNER_FORMAT = 'Format your answer exactly like this:\nSummary: One simple sentence a beginner can understand.\nSteps: Numbered steps (1., 2., 3.) walking through what happens.\nKey idea: One short analogy or plain-language takeaway.\nRelevant chunks: List chunk numbers used, e.g. [1], [2].'

def format_context_block(contexts: list[dict]) -> str:
    """Serialize retrieved chunk dicts into a numbered block for the LLM user message."""
    if not contexts:
        return '(no matching code chunks found)'
    blocks: list[str] = []
    for idx, ctx in enumerate(contexts, start=1):
        score = ctx.get('score')
        score_text = f'score={score:.4f}' if isinstance(score, (int, float)) else 'score=?'
        description = ctx.get('description')
        description_line = f'description: {description}' if description else None
        chunk_type = ctx.get('chunk_type') or 'function'
        segment_label = embedding_segment_label(chunk_type)
        segment_name = ctx.get('function_name', '?')
        meta_lines = [f'[{idx}] {score_text}', f"file: {ctx.get('file_path', '?')}", f'{segment_label}: {segment_name}', f"language: {ctx.get('language', '?')}"]
        if description_line:
            meta_lines.append(description_line)
        blocks.append('\n'.join([*meta_lines, '', ctx.get('content') or '']))
    return '\n\n---\n\n'.join(blocks)

def build_rag_messages(query: str, contexts: list[dict], *, beginner_mode: bool=False) -> list[dict]:
    """Build Groq chat messages (system + user) from the query and retrieved chunks."""
    context_block = format_context_block(contexts)
    if beginner_mode:
        system = f'You are a patient codebase tutor for someone new to programming. Use everyday words, short sentences, and concrete examples. Explain what each piece does before how it connects. Avoid jargon unless you define it immediately.\n\n{_BEGINNER_FORMAT}\n\n{_STYLE_RULES}'
        user_prefix = 'Explain this like I am learning to code for the first time.\n\n'
    else:
        system = f'You are a concise codebase assistant for experienced developers.\n\n{_DEFAULT_FORMAT}\n\n{_STYLE_RULES}'
        user_prefix = ''
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': f'{user_prefix}Retrieved code context:\n\n{context_block}\n\nQuestion:\n{query}'}]

def chat_temperature(*, beginner_mode: bool=False) -> float:
    """Return LLM temperature tuned for beginner vs default RAG mode."""
    return 0.45 if beginner_mode else 0.2
