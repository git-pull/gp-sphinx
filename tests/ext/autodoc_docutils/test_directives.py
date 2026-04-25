"""Tests for autodoc docutils directives."""

from __future__ import annotations

import logging
import sys
import types

import pytest

from sphinx_autodoc_docutils import setup
from sphinx_autodoc_docutils._directives import (
    _directive_classes,
    _directive_markup,
    _registered_directives,
    _registered_roles,
    _replay_setup,
    _role_callables,
    _role_markup,
)

_RICH_DIRECTIVE_BLOCK_HEADER = ".. rst:directive::"
_RICH_ROLE_BLOCK_HEADER = ".. rst:role::"


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
    roles = _role_callables("sphinx_autodoc_argparse.roles")
    names = {name for name, _role in roles}
    assert "cli_option_role" in names
    assert "cli_choice_role" in names


def test_directive_markup_contains_path_and_summary() -> None:
    """Rendered directive markup carries the signature and summary prose."""
    directive_cls = dict(_directive_classes("sphinx_autodoc_docutils._directives"))[
        "AutoDirectiveIndex"
    ]
    markup = _directive_markup(
        "sphinx_autodoc_docutils._directives.AutoDirectiveIndex",
        directive_cls,
        directive_name="autodirective-index",
    )
    assert ".. rst:directive:: autodirective-index" in markup
    assert "Generate a summary index for all directives a package registers." in markup


def test_directive_classes_empty_for_module_with_no_directives() -> None:
    """A module without directive classes yields an empty list, not an error."""
    # sphinx_fonts has no directive classes; the join produces "" and the
    # if markup else [] guard in AutoDirectives.run() returns [] not an error.
    result = _directive_classes("sphinx_fonts")
    assert result == []


def test_role_callables_empty_for_module_with_no_roles() -> None:
    """A module without role callables yields an empty list, not an error."""
    result = _role_callables("sphinx_fonts")
    assert result == []


def test_role_markup_contains_role_name_and_path() -> None:
    """Rendered role markup includes the displayed role name and summary."""
    role_fn = dict(_role_callables("sphinx_autodoc_argparse.roles"))["cli_option_role"]
    markup = _role_markup(
        "sphinx_autodoc_argparse.roles.cli_option_role", "cli-option", role_fn
    )
    assert "cli-option" in markup
    assert "Role for CLI options like --foo or -h." in markup


def test_replay_setup_records_add_directive_calls() -> None:
    """Replaying a package's setup() captures every app.add_directive call."""
    recorder = _replay_setup("sphinx_autodoc_fastmcp")
    assert recorder is not None
    directive_names = [
        args[0] for name, args, _ in recorder.calls if name == "add_directive"
    ]
    assert "fastmcp-tool" in directive_names
    assert "fastmcp-resource-template" in directive_names


def test_replay_setup_returns_none_for_module_without_setup() -> None:
    """A module with no setup() callable yields None instead of raising."""
    assert _replay_setup("sphinx_autodoc_docutils._directives") is None


def test_replay_setup_returns_none_for_unimportable_module() -> None:
    """An ImportError yields None instead of bubbling out."""
    assert _replay_setup("_does_not_exist_module_") is None


def test_replay_setup_logs_debug_when_setup_raises(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A raising setup() degrades to introspection but leaves a DEBUG breadcrumb.

    Regression guard: silent fallback would re-introduce mis-derived names
    (e.g. ``autoconfigvalueindex``) without telling the docs author.
    """
    module_name = "_replay_setup_test_module_with_raising_setup"
    fake_module = types.ModuleType(module_name)

    def _broken_setup(_app: object) -> None:
        raise RuntimeError("simulated extension setup failure")

    fake_module.setup = _broken_setup  # type: ignore[attr-defined]
    sys.modules[module_name] = fake_module
    try:
        with caplog.at_level(
            logging.DEBUG, logger="sphinx_autodoc_docutils._directives"
        ):
            assert _replay_setup(module_name) is None
    finally:
        del sys.modules[module_name]

    matching = [r for r in caplog.records if "setup replay failed" in r.getMessage()]
    assert matching, "expected a DEBUG breadcrumb when setup() raises"
    assert matching[0].levelno == logging.DEBUG


def test_registered_directives_uses_real_registration_names_for_packages() -> None:
    """Package input returns the kebab-case names passed to add_directive()."""
    pairs = dict(_registered_directives("sphinx_autodoc_fastmcp"))
    assert "fastmcp-tool-input" in pairs
    assert "fastmcp-resource-template" in pairs


def test_registered_directives_falls_back_to_module_introspection() -> None:
    """A module with no setup() is introspected for Directive subclasses."""
    pairs = dict(_registered_directives("sphinx_autodoc_docutils._directives"))
    # Class-name fallback maps via _registered_name's explicit table.
    assert "autodirective-index" in pairs


def test_registered_roles_uses_real_registration_names_for_packages() -> None:
    """Package input returns the names passed to add_role()."""
    pairs = dict(_registered_roles("sphinx_autodoc_fastmcp"))
    assert "tool" in pairs
    assert "toolicon" in pairs
    assert "badge" in pairs


def test_registered_roles_falls_back_to_module_introspection() -> None:
    """A role-defining module without setup() is introspected for *_role callables."""
    pairs = dict(_registered_roles("sphinx_autodoc_argparse.roles"))
    assert "cli-option" in pairs


def test_directive_markup_per_pair_emits_rich_block_for_each_registered_directive() -> (
    None
):
    """Iterating ``_registered_directives`` produces a rich rst:directive block per item.

    Mirrors what AutoDirectives.run() does for the package case — each
    pair flows through ``_directive_markup`` and yields the descriptor
    block (signature + role badge + facts), not just an index row.
    """
    pairs = _registered_directives("sphinx_autodoc_fastmcp")
    assert pairs, "expected fastmcp to register at least one directive"
    for registered_name, directive_cls in pairs:
        path = f"{directive_cls.__module__}.{directive_cls.__name__}"
        markup = _directive_markup(path, directive_cls, directive_name=registered_name)
        assert f"{_RICH_DIRECTIVE_BLOCK_HEADER} {registered_name}" in markup, (
            f"missing rich block for {registered_name}"
        )


def test_role_markup_per_pair_emits_rich_block_for_each_registered_role() -> None:
    """Iterating ``_registered_roles`` produces a rich rst:role block per item."""
    pairs = _registered_roles("sphinx_autodoc_fastmcp")
    assert pairs, "expected fastmcp to register at least one role"
    for registered_name, role_fn in pairs:
        role_module = getattr(role_fn, "__module__", "sphinx_autodoc_fastmcp")
        role_attr = getattr(role_fn, "__name__", registered_name)
        path = f"{role_module}.{role_attr}"
        markup = _role_markup(path, registered_name, role_fn)
        assert f"{_RICH_ROLE_BLOCK_HEADER} {registered_name}" in markup, (
            f"missing rich block for {registered_name}"
        )
