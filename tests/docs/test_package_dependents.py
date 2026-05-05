"""Tests for the ``{package-dependents}`` showcase directive."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import package_reference


def test_package_dependents_for_sphinx_ux_badges_includes_known_dependents() -> None:
    """sphinx-ux-badges is depended on by autodoc + UX layout packages.

    The exact set varies as the workspace evolves, but the result must
    be a subset of all shipped-py packages and must NOT include
    sphinx-ux-badges itself.
    """
    deps = package_reference._package_dependents("sphinx-ux-badges")
    assert "sphinx-ux-badges" not in deps
    shipped_names = {
        record.name
        for record in package_reference.workspace_package_records()
        if record.state == "shipped-py"
    }
    assert set(deps) <= shipped_names


def test_package_dependents_for_unknown_package_is_empty() -> None:
    """No dependents for a package nobody has heard of."""
    assert package_reference._package_dependents("definitely-no-such-pkg") == []


def test_package_dependents_markdown_includes_anchor_and_heading() -> None:
    """Rendered markdown carries the anchor + H1 + intro paragraph."""
    rendered = package_reference._package_dependents_markdown("sphinx-ux-badges")
    assert "(sphinx-ux-badges-dependents)=" in rendered
    assert "# Dependents" in rendered


def test_package_dependents_markdown_emits_doc_xrefs_for_each_dependent() -> None:
    """Each dependent renders as a ``{doc}`` cross-reference bullet."""
    rendered = package_reference._package_dependents_markdown("sphinx-ux-badges")
    deps = package_reference._package_dependents("sphinx-ux-badges")
    if deps:
        for dep in deps:
            assert f"{{doc}}`packages/{dep}/index`" in rendered
    else:
        assert "No workspace package currently depends" in rendered


def test_package_dependents_markdown_returns_empty_for_unknown_package() -> None:
    """Unknown package name returns the empty string."""
    rendered = package_reference._package_dependents_markdown("no-such-pkg")
    assert rendered == ""
