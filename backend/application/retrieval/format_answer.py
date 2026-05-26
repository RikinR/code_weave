"""Post-process raw LLM assistant text for consistent UI display.

Strips decorative quotes and normalizes whitespace after
:mod:`infrastructure.llm.groq_client` returns an answer in
:mod:`application.retrieval.rag_service`.
"""

from __future__ import annotations
import re
_QUOTE_PAIR_RE = re.compile('^([\'"])(.+?)\\1$')
_MULTI_QUOTE_RE = re.compile('[\'"]{2,}')
_SMART_QUOTES_RE = re.compile('[\\u2018\\u2019\\u201c\\u201d]')

def format_assistant_answer(text: str) -> str:
    """Clean LLM output: remove smart quotes, unwrap spurious quoting, collapse blank lines."""
    if not text:
        return text
    cleaned = _SMART_QUOTES_RE.sub('', text)
    cleaned = _MULTI_QUOTE_RE.sub('', cleaned)
    lines: list[str] = []
    for raw_line in cleaned.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            if lines and lines[-1] != '':
                lines.append('')
            continue
        match = _QUOTE_PAIR_RE.match(stripped)
        if match and len(match.group(2)) > 2:
            stripped = match.group(2)
        stripped = re.sub('\\(\\s*[\'"]([^\'"]+)[\'"]\\s*\\)', '(\\1)', stripped)
        stripped = re.sub('[\'"]([A-Za-z_][\\w./-]{2,})[\'"]', '\\1', stripped)
        lines.append(stripped)
    result = '\n'.join(lines).strip()
    result = re.sub('\\n{3,}', '\n\n', result)
    return result
