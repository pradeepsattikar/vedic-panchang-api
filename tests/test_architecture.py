"""Enforce the layered architecture: each layer may import only the layers below it.

    api  ->  services  ->  domain  ->  rules  ->  astronomy
                       ->  infra   ->  domain

``api/app.py`` is the composition root and may wire up any layer.
"""

import ast
from pathlib import Path

import pytest

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "vedic_panchang"

ALLOWED = {
    "astronomy": {"astronomy"},
    "rules": {"rules", "astronomy"},
    "domain": {"domain", "rules", "astronomy"},
    "infra": {"infra", "domain"},
    "services": {"services", "domain", "rules", "astronomy", "infra", "config", "__init__"},
    "api": {"api", "services"},
}
COMPOSITION_ROOTS = {PACKAGE / "api" / "app.py", PACKAGE / "main.py"}


def internal_imports(path: Path) -> set[str]:
    """Top-level vedic_panchang sub-packages imported by a module."""
    layers = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        else:
            continue
        for name in names:
            parts = name.split(".")
            if parts[0] == "vedic_panchang":
                layers.add(parts[1] if len(parts) > 1 else "__init__")
    return layers


def imports_module(path: Path, module: str) -> bool:
    tree = ast.parse(path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import) and any(a.name == module for a in node.names):
            return True
        if isinstance(node, ast.ImportFrom) and node.module == module:
            return True
    return False


MODULES = sorted(p for p in PACKAGE.rglob("*.py") if p not in COMPOSITION_ROOTS)


@pytest.mark.parametrize("path", MODULES, ids=lambda p: str(p.relative_to(PACKAGE)))
def test_layer_dependencies(path):
    layer = path.relative_to(PACKAGE).parts[0]
    if layer not in ALLOWED:
        return  # package root modules (config, __init__)
    forbidden = internal_imports(path) - ALLOWED[layer]
    assert not forbidden, f"{layer} must not import {sorted(forbidden)}"


@pytest.mark.parametrize("path", MODULES, ids=lambda p: str(p.relative_to(PACKAGE)))
def test_only_astronomy_layer_uses_swiss_ephemeris(path):
    if path.relative_to(PACKAGE).parts[0] != "astronomy":
        assert not imports_module(path, "swisseph")
