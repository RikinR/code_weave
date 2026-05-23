from __future__ import annotations
import re

_QUOTE_PAIR_RE = re.compile(r"""^(['"])(.+?)\1$""")
_MULTI_QUOTE_RE = re.compile(r"""['"]{2,}""")
_SMART_QUOTES_RE = re.compile(r"[\u2018\u2019\u201c\u201d]")


def format_assistant_answer(text: str) -> str:
    """Normalize LLM output: strip decorative quotes and tidy whitespace."""
    if not text:
        return text

    cleaned = _SMART_QUOTES_RE.sub("", text)
    cleaned = _MULTI_QUOTE_RE.sub("", cleaned)

    lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if lines and lines[-1] != "":
                lines.append("")
            continue

        match = _QUOTE_PAIR_RE.match(stripped)
        if match and len(match.group(2)) > 2:
            stripped = match.group(2)

        stripped = re.sub(
            r"""\(\s*['"]([^'"]+)['"]\s*\)""",
            r"(\1)",
            stripped,
        )
        stripped = re.sub(
            r"""['"]([A-Za-z_][\w./-]{2,})['"]""",
            r"\1",
            stripped,
        )
        lines.append(stripped)

    result = "\n".join(lines).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result
