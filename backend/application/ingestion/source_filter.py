from __future__ import annotations
from pathlib import Path
from infrastructure.parser.path_language import is_supported_extension

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
        ".md",
    }
)

_NON_CODE_EXTENSIONS = frozenset(
    {
        ".css",
        ".scss",
        ".sass",
        ".dockerfile",
        ".dot",
        ".ejs",
        ".gv",
        ".hbs",
        ".htm",
        ".html",
        ".json",
        ".markdown",
        ".md",
        ".mk",
        ".ql",
        ".regex",
        ".rst",
        ".sql",
        ".tf",
        ".tfvars",
        ".toml",
        ".yaml",
        ".yml",
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
        "dockerfile",
        "gemfile.lock",
        "package-lock.json",
        "pipfile",
        "poetry.lock",
        "requirements.txt",
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
    if lower.startswith("docker-compose") and lower.endswith((".yml", ".yaml")):
        return True
    if lower.startswith("compose.") and lower.endswith((".yml", ".yaml")):
        return True
    return False


def is_ingestible_source_file(path: Path) -> bool:
    if not path.is_file():
        return False
    if _path_has_skipped_dir(path):
        return False
    if _is_skipped_file_name(path.name):
        return False
    suffix = path.suffix.lower()
    if suffix in _NON_CODE_EXTENSIONS:
        return False
    if suffix == ".log":
        return False
    return is_supported_extension(path)


def iter_source_files(folder: Path):
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
            elif child.is_file() and is_ingestible_source_file(child):
                yield child
