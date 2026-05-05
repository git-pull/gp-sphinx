"""Tests for the ``{cluster-toctree}`` directive.

Verifies the rendered hidden toctree only includes Shipped packages
(shipped-py + shipped-js), skipping Emerging packages so the build
never references a missing docname (Risk 2 mitigation).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import package_reference


def _toctree_lines(rendered: str) -> list[str]:
    """Return the leaf entries inside the rendered ``{toctree}`` block."""
    inside = False
    leaves: list[str] = []
    for line in rendered.splitlines():
        if line.startswith("```{toctree}"):
            inside = True
            continue
        if line.startswith("```") and inside:
            inside = False
            continue
        if not inside:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(":"):
            continue
        leaves.append(stripped)
    return leaves


def test_cluster_toctree_autodoc_includes_seven_autodoc_packages() -> None:
    """The autodoc cluster has exactly the seven sphinx-autodoc-* packages."""
    rendered = package_reference._cluster_toctree_markdown(
        "autodoc",
        caption=None,
        titlesonly=False,
    )
    leaves = _toctree_lines(rendered)
    assert len(leaves) == 7
    assert all(leaf.startswith("packages/sphinx-autodoc-") for leaf in leaves)
    assert all(leaf.endswith("/index") for leaf in leaves)


def test_cluster_toctree_renders_caption_and_titlesonly_when_requested() -> None:
    """Optional :caption: and :titlesonly: lines appear when set."""
    rendered = package_reference._cluster_toctree_markdown(
        "autodoc",
        caption="Autodoc",
        titlesonly=True,
    )
    assert ":caption: Autodoc" in rendered
    assert ":titlesonly:" in rendered
    assert ":hidden:" in rendered


def test_cluster_toctree_omits_caption_when_unset() -> None:
    """No :caption: line is emitted when the option is None."""
    rendered = package_reference._cluster_toctree_markdown(
        "autodoc",
        caption=None,
        titlesonly=False,
    )
    assert ":caption:" not in rendered


def test_cluster_toctree_returns_empty_for_unknown_cluster() -> None:
    """Empty cluster name renders as empty string (caller logs warning)."""
    rendered = package_reference._cluster_toctree_markdown(
        "definitely-no-such-cluster",
        caption=None,
        titlesonly=False,
    )
    assert rendered == ""


def test_cluster_toctree_includes_shipped_js_packages() -> None:
    """The tokens cluster includes JS-only Shipped packages alongside Python ones."""
    rendered = package_reference._cluster_toctree_markdown(
        "tokens",
        caption=None,
        titlesonly=False,
    )
    leaves = _toctree_lines(rendered)
    assert "packages/sphinx-fonts/index" in leaves
    assert "packages/@gp-sphinx/furo-tokens/index" in leaves


def test_cluster_toctree_skips_emerging_packages() -> None:
    """No Emerging package appears in any cluster's toctree."""
    emerging_names = {
        record.name
        for record in package_reference.workspace_package_records()
        if record.state == "emerging"
    }
    if not emerging_names:
        pytest.skip("no Emerging packages in workspace; nothing to assert")

    for cluster in ("theme-coordinator", "tokens", "autodoc", "ux", "build-seo"):
        rendered = package_reference._cluster_toctree_markdown(
            cluster,
            caption=None,
            titlesonly=False,
        )
        leaves = _toctree_lines(rendered)
        for emerging in emerging_names:
            assert f"packages/{emerging}/index" not in leaves


def test_cluster_toctree_leaves_are_alphabetical() -> None:
    """Within a cluster, package landings sort alphabetically by name."""
    rendered = package_reference._cluster_toctree_markdown(
        "autodoc",
        caption=None,
        titlesonly=False,
    )
    leaves = _toctree_lines(rendered)
    assert leaves == sorted(leaves)


def test_cluster_toctree_every_shipped_package_classified() -> None:
    """Every Shipped package falls into one of the recognized clusters."""
    expected_clusters = {"theme-coordinator", "tokens", "autodoc", "ux", "build-seo"}
    seen: set[str] = set()
    for cluster in expected_clusters:
        rendered = package_reference._cluster_toctree_markdown(
            cluster,
            caption=None,
            titlesonly=False,
        )
        for leaf in _toctree_lines(rendered):
            # leaf format: packages/<name>/index
            seen.add(leaf[len("packages/") : -len("/index")])
    shipped_names = {
        record.name
        for record in package_reference.workspace_package_records()
        if record.state in {"shipped-py", "shipped-js"}
    }
    missing = shipped_names - seen
    assert not missing, f"Shipped packages without a cluster: {sorted(missing)}"
