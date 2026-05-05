"""Tests for the ``{workspace-package-grid} :groups: by-cluster`` extension.

The legacy default (no ``:groups:`` option) must remain identical to
the pre-extension output so existing ``docs/packages/index.md``
invocations keep rendering unchanged. The new ``by-cluster`` mode
emits one grid per cluster with framing prose, and renders Emerging
packages as GitHub-linked cards (no docname link).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import package_reference


def test_default_grid_unchanged_from_legacy_layout() -> None:
    """No ``groups=`` argument renders the original single-grid layout."""
    rendered = package_reference.workspace_package_grid_markdown()
    assert rendered.startswith("::::{grid}")
    # legacy layout has exactly one outer grid
    assert rendered.count("::::{grid}") == 1
    # no per-cluster headings appear
    assert "## " not in rendered


def test_by_cluster_grid_emits_per_cluster_heading_and_prose() -> None:
    """``groups=by-cluster`` adds a heading + framing prose for each cluster."""
    rendered = package_reference.workspace_package_grid_markdown(
        groups="by-cluster",
    )
    expected_headings = [
        "## Theme & coordinator",
        "## Tokens",
        "## Autodoc extensions",
        "## UX components",
        "## Build & SEO",
    ]
    for heading in expected_headings:
        assert heading in rendered


def test_by_cluster_grid_emits_one_grid_per_nonempty_cluster() -> None:
    """``groups=by-cluster`` opens a fresh ``{grid}`` block per cluster."""
    rendered = package_reference.workspace_package_grid_markdown(
        groups="by-cluster",
    )
    # 5 clusters all populated (tokens, autodoc, ux, theme-coordinator,
    # build-seo) -> 5 grids today.
    assert rendered.count("::::{grid}") == 5


def test_by_cluster_grid_includes_shipped_js_packages() -> None:
    """Token cluster includes ``@gp-sphinx/furo-tokens`` (shipped-js)."""
    rendered = package_reference.workspace_package_grid_markdown(
        groups="by-cluster",
    )
    assert ":::{grid-item-card} @gp-sphinx/furo-tokens" in rendered


def test_by_cluster_grid_renders_emerging_as_github_link() -> None:
    """An Emerging record renders without a docname link, pointing at GitHub."""
    record = package_reference.PackageDocsRecord(
        name="example-emerging-pkg",
        state="emerging",
        cluster="tokens",
        package_dir=pathlib.Path("/tmp/example"),
        manifest_path=None,
        src_dir=None,
        module_name="",
        description="",
        version="",
        repository_url="https://github.com/example/repo",
        pypi_url=None,
        npm_url=None,
        maturity="Unknown",
    )
    lines = package_reference._grid_card_lines_for_record(record)
    text = "\n".join(lines)
    assert ":::{grid-item-card} example-emerging-pkg" in text
    assert ":link: https://github.com/example/repo" in text
    assert ":link-type: doc" not in text
    assert "Coming soon" in text


def test_by_cluster_grid_renders_shipped_py_with_doc_link() -> None:
    """A shipped-py record uses ``:link-type: doc`` for the package's landing."""
    record = next(
        r
        for r in package_reference.workspace_package_records()
        if r.name == "sphinx-fonts"
    )
    lines = package_reference._grid_card_lines_for_record(record)
    text = "\n".join(lines)
    assert ":::{grid-item-card} sphinx-fonts" in text
    assert ":link: sphinx-fonts" in text
    assert ":link-type: doc" in text
    assert "+++" in text  # maturity badge separator


def test_workspace_package_grid_markdown_rejects_unknown_groups_argument() -> None:
    """Passing an unsupported ``groups=`` value raises ValueError."""
    with pytest.raises(ValueError, match="unsupported groups argument"):
        package_reference.workspace_package_grid_markdown(groups="alphabetical")
