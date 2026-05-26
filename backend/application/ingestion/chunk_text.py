"""Format chunk dicts into embedding input text.

Pipeline stage: **embed** (within :mod:`persist` / :mod:`index_folder`).

Combines file path, segment label from :mod:`chunk_strategy`, description, and
source code into the string passed to the embedder.
"""
from application.ingestion.chunk_strategy import embedding_segment_label


def chunk_to_embedding_text(file_path: str, chunk: dict) -> str:
    """Build the text payload embedded and stored for one chunk."""
    name = chunk.get('name') or 'unknown'
    code = chunk.get('code') or ''
    description = chunk.get('description')
    chunk_type = chunk.get('chunk_type') or 'function'
    label = embedding_segment_label(chunk_type)
    parts = [f'file: {file_path}', f'{label}: {name}']
    if description:
        parts.append(f'description: {description}')
    parts.append('')
    parts.append(code)
    return '\n'.join(parts)
