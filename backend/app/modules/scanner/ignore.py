import os
from pathlib import Path

DEFAULT_IGNORE_DIR_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        ".mypy_cache",
        ".pytest_cache",
        ".eggs",
        "dist",
        "build",
        ".idea",
        ".vscode",
        "__MACOSX",
        ".tox",
        "htmlcov",
    }
)

DEFAULT_IGNORE_SUFFIXES: tuple[str, ...] = (".pyc", ".pyo", ".so", ".dll", ".exe", ".bin")


def should_skip_dir(name: str) -> bool:
    return name in DEFAULT_IGNORE_DIR_NAMES or name.startswith(".")


def should_skip_file(path: Path) -> bool:
    suf = path.suffix.lower()
    if suf in DEFAULT_IGNORE_SUFFIXES:
        return True
    return False


def is_probably_text(path: Path) -> bool:
    text_ext = {".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".md", ".html", ".css", ".sh", ""}
    return path.suffix.lower() in text_ext or path.suffix == ""
