"""Tests for the ``{package-kitchen-sink}`` showcase directive."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import package_reference


def test_kitchen_sink_markdown_renders_intro_for_known_package() -> None:
    """Body-only output: directive emits intro + per-directive sections.

    The stub at ``packages/<name>/kitchen-sink.md`` provides anchor +
    H1 so Sphinx finds a page title.
    """
    rendered = package_reference._kitchen_sink_markdown("sphinx-autodoc-argparse")
    assert rendered, "expected non-empty markdown for sphinx-autodoc-argparse"
    # No anchor or H1 emitted by the directive
    assert "(sphinx-autodoc-argparse-kitchen-sink)=" not in rendered
    assert "# Kitchen sink" not in rendered
    assert "Every directive and role this package registers" in rendered


def test_kitchen_sink_markdown_lists_each_directive_with_example_block() -> None:
    """Each registered directive gets a ``### `name`` heading and code fence."""
    rendered = package_reference._kitchen_sink_markdown("sphinx-autodoc-argparse")
    # sphinx-autodoc-argparse registers an ``argparse`` directive
    assert "## Directives" in rendered
    assert "### `argparse`" in rendered
    # Each directive section opens a text fence and shows .. name:: invocation
    assert "```text" in rendered
    assert ".. argparse::" in rendered


def test_kitchen_sink_markdown_lists_each_role_under_roles_heading() -> None:
    """Roles section enumerates every registered role with ``:name:`` syntax."""
    rendered = package_reference._kitchen_sink_markdown("sphinx-autodoc-fastmcp")
    if "## Roles" in rendered:
        # The heading appears only when the package registers roles
        assert "- `:" in rendered  # at least one role bullet


def test_kitchen_sink_markdown_returns_empty_for_unknown_package() -> None:
    """Unknown package name returns the empty string."""
    rendered = package_reference._kitchen_sink_markdown("definitely-no-such-pkg")
    assert rendered == ""


def test_kitchen_sink_markdown_returns_empty_for_package_with_no_surface() -> None:
    """A package whose modules register no directives or roles renders empty."""
    # gp-sphinx is a coordinator with no surface registered via add_directive
    rendered = package_reference._kitchen_sink_markdown("gp-sphinx")
    assert rendered == ""
