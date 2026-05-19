def chunk_to_embedding_text(file_path: str, chunk: dict) -> str:
    name = chunk.get("name") or "unknown"
    code = chunk.get("code") or ""
    return f"file: {file_path}\nfunction: {name}\n\n{code}"
