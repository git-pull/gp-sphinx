"""Tests for autodoc docutils directives."""

from __future__ import annotations

from sphinx_autodoc_docutils import setup
from sphinx_autodoc_docutils._directives import (
    _directive_classes,
    _directive_markup,
    _role_callables,
    _role_markup,
)


def test_extension_setup() -> None:
    """The extension setup function is importable."""
    assert callable(setup)


def test_directive_classes_discovers_public_directives() -> None:
    """The helper discovers directive classes defined in a module."""
    directives = _directive_classes("sphinx_autodoc_docutils._directives")
    names = {name for name, _directive in directives}
    assert "AutoDirective" in names
    assert "AutoDirectiveIndex" in names


def test_role_callables_discovers_public_roles() -> None:
    """The helper discovers role callables defined in a module."""
    roles = _role_callables("sphinx_argparse_neo.roles")
    names = {name for name, _role in roles}
    assert "cli_option_role" in names
    assert "cli_choice_role" in names


def test_directive_markup_contains_path_and_summary() -> None:
    """Rendered directive markup includes the import path and summary."""
    directive_cls = dict(_directive_classes("sphinx_autodoc_docutils._directives"))[
        "AutoDirectiveIndex"
    ]
    markup = _directive_markup(
        "sphinx_autodoc_docutils._directives.AutoDirectiveIndex",
        directive_cls,
        directive_name="autodirective-index",
    )
    assert "sphinx_autodoc_docutils._directives.AutoDirectiveIndex" in markup
    assert "Generate a summary index for all directives in a module." in markup


def test_role_markup_contains_role_name_and_path() -> None:
    """Rendered role markup includes the displayed role name and path."""
    role_fn = dict(_role_callables("sphinx_argparse_neo.roles"))["cli_option_role"]
    markup = _role_markup(
        "sphinx_argparse_neo.roles.cli_option_role", "cli-option", role_fn
    )
    assert "cli-option" in markup
    assert "sphinx_argparse_neo.roles.cli_option_role" in markup
