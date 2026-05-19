from __future__ import annotations


def format_context_block(contexts: list[dict]) -> str:
    if not contexts:
        return "(no matching code chunks found)"

    blocks: list[str] = []
    for idx, ctx in enumerate(contexts, start=1):
        score = ctx.get("score")
        score_text = f"score={score:.4f}" if isinstance(score, (int, float)) else "score=?"
        blocks.append(
            "\n".join(
                [
                    f"[{idx}] {score_text}",
                    f"file: {ctx.get('file_path', '?')}",
                    f"function: {ctx.get('function_name', '?')}",
                    f"language: {ctx.get('language', '?')}",
                    "",
                    ctx.get("content") or "",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def build_rag_messages(query: str, contexts: list[dict]) -> list[dict]:
    context_block = format_context_block(contexts)
    return [
        {
            "role": "system",
            "content": (
                "You are a codebase assistant. Answer using only the retrieved "
                "function chunks below. If the context is insufficient, say what "
                "is missing. Cite file paths and function names when relevant."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Retrieved code context:\n\n{context_block}\n\n"
                f"Question:\n{query}"
            ),
        },
    ]
