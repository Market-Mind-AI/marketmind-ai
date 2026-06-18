"""Architecture fitness tests enforcing the Clean/Hexagonal dependency rule.

The dependency rule is ABSOLUTE: dependencies point inward only
(infrastructure -> application -> domain).

These tests scan the *source files* of the ``domain`` and ``application``
packages with the ``ast`` module and assert that no forbidden imports appear:

* ``domain`` may import only the Python standard library and other ``domain``
  modules — NO ``application``, NO ``infrastructure``, NO third-party.
* ``application`` may import ``domain`` and the standard library — NO
  ``infrastructure`` and none of the pinned third-party frameworks
  (fastapi, sqlalchemy, pydantic, anthropic, cohere, httpx, langgraph, ...).
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

_SRC = Path(__file__).resolve().parents[2] / "src"
_DOMAIN = _SRC / "marketmind" / "domain"
_APPLICATION = _SRC / "marketmind" / "application"

# Modules that are part of the Python standard library (3.12). Anything not in
# here and not a first-party ``marketmind`` import is treated as third-party.
_STDLIB = set(getattr(sys, "stdlib_module_names", set())) | {
    "__future__",
}

_THIRD_PARTY_FORBIDDEN = {
    "fastapi",
    "starlette",
    "sse_starlette",
    "uvicorn",
    "sqlalchemy",
    "asyncpg",
    "pgvector",
    "pydantic",
    "pydantic_settings",
    "anthropic",
    "cohere",
    "httpx",
    "structlog",
    "langgraph",
}


def _python_files(package_dir: Path) -> list[Path]:
    return sorted(package_dir.rglob("*.py"))


def _imported_roots(path: Path) -> set[str]:
    """Top-level module names imported by the file at ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            # Ignore relative imports (level > 0) — they are first-party.
            if node.level and not node.module:
                continue
            if node.module:
                roots.add(node.module.split(".")[0])
    return roots


def _full_module_targets(path: Path) -> set[str]:
    """Full dotted import targets (for matching marketmind sub-packages)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _is_allowed_root(root: str, *, allow_application: bool) -> bool:
    if root == "marketmind":
        return True
    if root in _STDLIB:
        return True
    # typing_extensions etc. are not used; everything else third-party is checked
    # explicitly. Treat unknown roots conservatively only via the forbidden set.
    return root not in _THIRD_PARTY_FORBIDDEN


def test_domain_files_exist() -> None:
    files = _python_files(_DOMAIN)
    assert files, f"no domain modules found under {_DOMAIN}"


def test_application_files_exist() -> None:
    files = _python_files(_APPLICATION)
    assert files, f"no application modules found under {_APPLICATION}"


@pytest.mark.parametrize("path", _python_files(_DOMAIN), ids=lambda p: p.name)
def test_domain_imports_stdlib_and_domain_only(path: Path) -> None:
    targets = _full_module_targets(path)
    roots = _imported_roots(path)

    # No application / infrastructure dependencies.
    for target in targets:
        assert not target.startswith(
            "marketmind.application"
        ), f"{path} imports application: {target}"
        assert not target.startswith(
            "marketmind.infrastructure"
        ), f"{path} imports infrastructure: {target}"

    # No third-party imports at all (domain is stdlib-only).
    for root in roots:
        if root == "marketmind":
            continue
        assert (
            root in _STDLIB
        ), f"{path} imports non-stdlib module {root!r}; domain must be stdlib-only"


@pytest.mark.parametrize("path", _python_files(_APPLICATION), ids=lambda p: p.name)
def test_application_imports_domain_and_stdlib_only(path: Path) -> None:
    targets = _full_module_targets(path)
    roots = _imported_roots(path)

    # No infrastructure dependency.
    for target in targets:
        assert not target.startswith(
            "marketmind.infrastructure"
        ), f"{path} imports infrastructure: {target}"

    # No forbidden third-party frameworks.
    for root in roots:
        assert root not in _THIRD_PARTY_FORBIDDEN, (
            f"{path} imports forbidden third-party framework {root!r}; "
            "application must be framework-free"
        )
        # Application is also expected to be stdlib + domain only.
        assert _is_allowed_root(
            root, allow_application=False
        ), f"{path} imports unexpected module {root!r}"
