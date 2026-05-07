from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass(frozen=True)
class LanguageSpec:
    function_node_types: frozenset[str]
    wrapper_types: frozenset[str]
    queries: Mapping[str, str]


_EMPTY: LanguageSpec = LanguageSpec(
    function_node_types=frozenset(),
    wrapper_types=frozenset(),
    queries={"functions": "", "class_methods": "", "attributes": ""},
)

_TYPESCRIPT_LIKE: LanguageSpec = LanguageSpec(
    function_node_types=frozenset(
        {"function_declaration", "method_definition", "function"}
    ),
    wrapper_types=frozenset({"export_statement"}),
    queries={
        "functions": """
(function_declaration) @fn_def
(method_definition) @fn_def
(function) @fn_def
""",
        "class_methods": """
(class_declaration
  name: (_) @class_name
  body: (class_body
    (method_definition
      name: (_) @method_name)))
""",
        "attributes": """
(class_declaration
  body: (class_body
    (public_field_definition
      (property_identifier) @attr_name)))
""",
    },
)


def get_language_spec(lang: str) -> LanguageSpec:
    key = lang.lower().strip()
    if key not in LANGUAGE_REGISTRY:
        supported = ", ".join(sorted(LANGUAGE_REGISTRY))
        logger.error(
            "get_language_spec: unknown language=%r (supported: %s)",
            lang,
            supported,
        )
        raise KeyError(f"Unknown language {lang!r}. Supported: {supported}")
    logger.debug("get_language_spec: resolved language=%s", key)
    return LANGUAGE_REGISTRY[key]


LANGUAGE_REGISTRY: dict[str, LanguageSpec] = {
    "bash": LanguageSpec(
        function_node_types=frozenset({"function_definition"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "c": LanguageSpec(
        function_node_types=frozenset({"function_definition"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "c_sharp": LanguageSpec(
        function_node_types=frozenset({"method_declaration", "local_function_statement"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(method_declaration) @fn_def
(local_function_statement) @fn_def
""",
            "class_methods": """
(class_declaration
  name: (identifier) @class_name
  body: (declaration_list
    (method_declaration
      name: (identifier) @method_name)))
""",
            "attributes": """
(class_declaration
  body: (declaration_list
    (field_declaration
      (variable_declaration
        (identifier) @attr_name))))
""",
        },
    ),
    "commonlisp": _EMPTY,
    "cpp": LanguageSpec(
        function_node_types=frozenset({"function_definition"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition) @fn_def
""",
            "class_methods": """
(class_specifier
  name: (type_identifier) @class_name
  body: (field_declaration_list
    (function_definition
      declarator: (function_declarator
        (field_identifier) @method_name))))
""",
            "attributes": """
(class_specifier
  body: (field_declaration_list
    (field_declaration
      declarator: (field_identifier) @attr_name)))
""",
        },
    ),
    "css": _EMPTY,
    "dockerfile": _EMPTY,
    "dot": _EMPTY,
    "elisp": LanguageSpec(
        function_node_types=frozenset({"function_definition"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "elixir": _EMPTY,
    "elm": _EMPTY,
    "embedded_template": _EMPTY,
    "erlang": _EMPTY,
    "fortran": LanguageSpec(
        function_node_types=frozenset({"function_statement"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_statement) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "go": LanguageSpec(
        function_node_types=frozenset({"function_declaration", "method_declaration"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_declaration) @fn_def
(method_declaration) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "hack": LanguageSpec(
        function_node_types=frozenset({"function_declaration"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_declaration) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "haskell": LanguageSpec(
        function_node_types=frozenset({"function"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "hcl": _EMPTY,
    "html": _EMPTY,
    "java": LanguageSpec(
        function_node_types=frozenset({"method_declaration"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(method_declaration) @fn_def
""",
            "class_methods": """
(class_declaration
  name: (identifier) @class_name
  body: (class_body
    (method_declaration
      name: (identifier) @method_name)))
""",
            "attributes": """
(class_declaration
  body: (class_body
    (field_declaration
      (variable_declarator
        name: (identifier) @attr_name))))
""",
        },
    ),
    "javascript": LanguageSpec(
        function_node_types=frozenset(
            {"function_declaration", "method_definition", "function"}
        ),
        wrapper_types=frozenset({"export_statement"}),
        queries={
            "functions": """
(function_declaration) @fn_def
(method_definition) @fn_def
(function) @fn_def
""",
            "class_methods": """
(class_declaration
  name: (_) @class_name
  body: (class_body
    (method_definition
      name: (_) @method_name)))
""",
            "attributes": """
(class_declaration
  body: (class_body
    (field_definition
      (property_identifier) @attr_name)))
""",
        },
    ),
    "json": _EMPTY,
    "julia": LanguageSpec(
        function_node_types=frozenset({"function_definition", "short_function_definition"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition) @fn_def
(short_function_definition) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "kotlin": LanguageSpec(
        function_node_types=frozenset({"function_declaration"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_declaration) @fn_def
""",
            "class_methods": """
(class_declaration
  name: (_) @class_name
  body: (class_body
    (function_declaration
      name: (simple_identifier) @method_name)))
""",
            "attributes": "",
        },
    ),
    "lua": LanguageSpec(
        function_node_types=frozenset(
            {"function_definition_statement", "local_function_definition_statement"}
        ),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition_statement) @fn_def
(local_function_definition_statement) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "make": _EMPTY,
    "markdown": _EMPTY,
    "objc": LanguageSpec(
        function_node_types=frozenset({"method_definition"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(method_definition) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "ocaml": _EMPTY,
    "perl": LanguageSpec(
        function_node_types=frozenset({"function_definition"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "php": LanguageSpec(
        function_node_types=frozenset({"function_definition", "method_declaration"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition) @fn_def
(method_declaration) @fn_def
""",
            "class_methods": """
(class_declaration
  name: (name) @class_name
  body: (declaration_list
    (method_declaration
      name: (name) @method_name)))
""",
            "attributes": "",
        },
    ),
    "python": LanguageSpec(
        function_node_types=frozenset({"function_definition"}),
        wrapper_types=frozenset({"decorated_definition"}),
        queries={
            "functions": """
(function_definition) @fn_def
""",
            "class_methods": """
(class_definition
  name: (identifier) @class_name
  body: (block
    (function_definition
      name: (identifier) @method_name)))
""",
            "attributes": """
(class_definition
  body: (block
    (expression_statement
      (assignment
        left: (attribute
          attribute: (identifier) @attr_name)))))
""",
        },
    ),
    "ql": _EMPTY,
    "r": LanguageSpec(
        function_node_types=frozenset({"function_definition"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition) @fn_def
""",
            "class_methods": "",
            "attributes": "",
        },
    ),
    "regex": _EMPTY,
    "rst": _EMPTY,
    "ruby": LanguageSpec(
        function_node_types=frozenset({"method"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(method) @fn_def
""",
            "class_methods": """
(class
  name: (constant) @class_name
  body: (body_statement
    (method
      name: (identifier) @method_name)))
""",
            "attributes": "",
        },
    ),
    "rust": LanguageSpec(
        function_node_types=frozenset({"function_item"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_item) @fn_def
""",
            "class_methods": """
(impl_item
  type: (_) @class_name
  body: (declaration_list
    (function_item
      name: (identifier) @method_name)))
""",
            "attributes": """
(struct_item
  name: (type_identifier) @class_name
  body: (field_declaration_list
    (field_declaration
      name: (field_identifier) @attr_name)))
""",
        },
    ),
    "scala": LanguageSpec(
        function_node_types=frozenset({"function_definition"}),
        wrapper_types=frozenset(),
        queries={
            "functions": """
(function_definition) @fn_def
""",
            "class_methods": """
(class_definition
  name: (identifier) @class_name
  body: (template_body
    (function_definition
      name: (identifier) @method_name)))
""",
            "attributes": "",
        },
    ),
    "sql": _EMPTY,
    "toml": _EMPTY,
    "tsx": _TYPESCRIPT_LIKE,
    "typescript": _TYPESCRIPT_LIKE,
    "yaml": _EMPTY,
}
