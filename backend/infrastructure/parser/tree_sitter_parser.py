from typing import Protocol, cast

from tree_sitter import Parser
from tree_sitter_languages import get_language
from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


class _ParserSetLanguage(Protocol):
    def set_language(self, language: object) -> None: ...


def get_parser(lang: str):
    logger.info(f"Getting parser for:{lang}")
    language = get_language(lang)
    parser = Parser()
    cast(_ParserSetLanguage, parser).set_language(language)
    return parser


def get_query(lang: str, queries: str):
    logger.info(f"Getting Query for:{lang} and queries {queries}")
    language = get_language(lang)
    return language.query(queries)

PYTHON_QUERIES = {
    "functions": """
    (function_definition) @fn_def
""",
    "class_methods": """
    (class_definition
      name: (identifier) @class_name
      body: (block
        (function_definition
          name: (identifier) @method_name) @method_def))
""",
    "attributes": """
    (class_definition
      body: (block
        (expression_statement
          (assignment
            left: (attribute
              attribute: (identifier) @attr_name)))))
    """,
}