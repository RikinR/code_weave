from __future__ import annotations
from pathlib import Path
from typing import Literal
from infrastructure.parser.path_language import is_supported_extension

FileKind = Literal["code", "context"]

_SKIP_DIR_NAMES = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".venv",
        "venv",
        "virtualenv",
        "node_modules",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        ".tox",
        ".nox",
        "dist",
        "build",
        "target",
        "logs",
        "log",
        ".idea",
        ".vscode",
        ".cursor",
        "htmlcov",
        ".eggs",
        "site-packages",
        ".npm",
        ".yarn",
        ".pnpm-store",
        "coverage",
        ".gradle",
        ".next",
        ".nuxt",
        "out",
        ".dart_tool",
        ".pub-cache",
        "vendor",
        "pods",
        "carthage",
        "deriveddata",
        ".terraform",
        ".serverless",
        "bower_components",
        "jspm_packages",
    }
)

_CONTEXT_EXTENSIONS = frozenset(
    {
        ".dockerfile",
        ".markdown",
        ".md",
        ".rst",
        ".toml",
        ".yaml",
        ".yml",
    }
)

_CONTEXT_FILE_NAMES = frozenset(
    {
        "containerfile",
        "dockerfile",
        "pipfile",
        "requirements-dev.txt",
        "requirements-prod.txt",
        "requirements.txt",
    }
)

_NON_CODE_EXTENSIONS = frozenset(
    {
        ".css",
        ".scss",
        ".sass",
        ".dot",
        ".ejs",
        ".gv",
        ".hbs",
        ".htm",
        ".html",
        ".json",
        ".ql",
        ".regex",
        ".sql",
        ".tf",
        ".tfvars",
    }
)

_SKIP_FILE_NAMES = frozenset(
    {
        ".dockerignore",
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        ".prettierignore",
        ".prettierrc",
        "cargo.lock",
        "gemfile.lock",
        "package-lock.json",
        "poetry.lock",
        "yarn.lock",
    }
)

_SKIP_NAME_PREFIXES = (".env",)


def _path_has_skipped_dir(path: Path) -> bool:
    return any(part.lower() in _SKIP_DIR_NAMES for part in path.parts)


def _is_skipped_file_name(name: str) -> bool:
    lower = name.lower()
    if lower in _SKIP_FILE_NAMES:
        return True
    if lower.startswith(_SKIP_NAME_PREFIXES):
        return True
    if lower.endswith(".log"):
        return True
    return False


def _is_context_file(path: Path) -> bool:
    lower = path.name.lower()
    if lower in _CONTEXT_FILE_NAMES:
        return True
    if path.suffix.lower() in _CONTEXT_EXTENSIONS:
        return True
    if lower.startswith("docker-compose") and lower.endswith((".yml", ".yaml")):
        return True
    if lower.startswith("compose.") and lower.endswith((".yml", ".yaml")):
        return True
    return False


def classify_ingestible_file(path: Path) -> FileKind | None:
    if not path.is_file():
        return None
    if _path_has_skipped_dir(path):
        return None
    if _is_skipped_file_name(path.name):
        return None
    if _is_context_file(path):
        return "context"
    suffix = path.suffix.lower()
    if suffix in _NON_CODE_EXTENSIONS:
        return None
    if suffix == ".log":
        return None
    if is_supported_extension(path):
        return "code"
    return None


def is_ingestible_source_file(path: Path) -> bool:
    return classify_ingestible_file(path) == "code"


def iter_ingestible_files(folder: Path):
    if not folder.is_dir():
        return

    stack: list[Path] = [folder]
    while stack:
        current = stack.pop()
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name.lower())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                if child.name.lower() in _SKIP_DIR_NAMES:
                    continue
                stack.append(child)
            elif classify_ingestible_file(child) is not None:
                yield child


def iter_source_files(folder: Path):
    for path in iter_ingestible_files(folder):
        if classify_ingestible_file(path) == "code":
            yield path
