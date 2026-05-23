def chunk_to_embedding_text(file_path: str, chunk: dict) -> str:
    name = chunk.get("name") or "unknown"
    code = chunk.get("code") or ""
    description = chunk.get("description")
    chunk_type = chunk.get("chunk_type") or "function"
    label = "section" if chunk_type == "document" else "function"
    parts = [f"file: {file_path}", f"{label}: {name}"]
    if description:
        parts.append(f"description: {description}")
    parts.append("")
    parts.append(code)
    return "\n".join(parts)
