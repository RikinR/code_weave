"""Tree-sitter parser and query helpers for multi-language AST extraction.

Bridges :mod:`infrastructure.parser.language_specs` query definitions to native
grammars from ``tree-sitter-languages``. Used by ingestion
(:mod:`application.ingestion.process_code`) and graph-related parsing.
"""

from typing import Protocol, cast
from tree_sitter import Parser
from tree_sitter_languages import get_language
from infrastructure.logging.logger import get_logger
from infrastructure.parser.language_specs import get_language_spec
logger = get_logger(__name__)

class _ParserSetLanguage(Protocol):

    def set_language(self, language: object) -> None:
        ...

def get_parser(lang: str):
    """Return a Tree-sitter parser configured for ``lang`` (validates against language specs)."""
    logger.debug('get_parser: language=%s', lang)
    get_language_spec(lang)
    try:
        language = get_language(lang)
    except Exception as exc:
        logger.error('get_parser: native grammar load failed for language=%s', lang, exc_info=True)
        raise RuntimeError(f'Failed to load Tree-sitter grammar for {lang!r}. Ensure tree-sitter-languages includes this grammar on your platform.') from exc
    parser = Parser()
    cast(_ParserSetLanguage, parser).set_language(language)
    logger.info('get_parser: ready for language=%s', lang)
    return parser

def get_query(lang: str, queries: str):
    """Compile a Tree-sitter query string for ``lang``."""
    logger.debug('get_query: compile query for language=%s', lang)
    language = get_language(lang)
    try:
        q = language.query(queries)
    except Exception as exc:
        logger.error('get_query: invalid query for language=%s: %s', lang, exc, exc_info=True)
        raise
    return q

def build_query_map(lang: str) -> dict[str, object]:
    """Return compiled queries for all keys in the language spec (functions, classes, etc.)."""
    spec = get_language_spec(lang)
    return {key: get_query(lang, qsrc.strip()) for key, qsrc in spec.queries.items()}
