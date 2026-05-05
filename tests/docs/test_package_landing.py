"""Tests for the ``{package-landing}`` directive.

Exercises the pure markdown helper (``_package_landing_markdown``) and
the candidate-subpage path discovery (``_candidate_subpage_paths``) at
unit level. Integration testing of the directive itself happens via
the live docs build covered by ``tests/docs/test_objects_inv_compat.py``.
"""

from __future__ import annotations

import pathlib
import sys
import typing as t

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "docs" / "_ext"))

import package_reference


def _shipped_py_fixture() -> package_reference.PackageDocsRecord:
    """Return the live record for ``sphinx-fonts`` (smallest shipped-py package)."""
    record = next(
        (
            r
            for r in package_reference.workspace_package_records()
            if r.name == "sphinx-fonts"
        ),
        None,
    )
    assert record is not None, "sphinx-fonts must exist in the workspace"
    return record


def test_package_landing_markdown_includes_meta_directive_and_anchor() -> None:
    """Rendered markdown has the package anchor, title, and meta-badge call."""
    record = _shipped_py_fixture()
    rendered = package_reference._package_landing_markdown(record, [])
    assert f"({record.name})=" in rendered
    assert f"# {record.name}" in rendered
    assert f"```{{gp-sphinx-package-meta}} {record.name}" in rendered


def test_package_landing_markdown_includes_synopsis_block() -> None:
    """When the record has a description, it is rendered as a block-quote."""
    record = _shipped_py_fixture()
    rendered = package_reference._package_landing_markdown(record, [])
    assert "> " in rendered  # block quote marker
    assert record.description in rendered


def test_package_landing_markdown_falls_back_when_description_empty() -> None:
    """An empty description is replaced with a non-empty placeholder line."""
    record = package_reference.PackageDocsRecord(
        name="example-pkg",
        state="shipped-py",
        cluster="autodoc",
        package_dir=pathlib.Path("/tmp/example"),
        manifest_path=None,
        src_dir=None,
        module_name="example_pkg",
        description="",
        version="",
        repository_url="",
        pypi_url=None,
        npm_url=None,
        maturity="Alpha",
    )
    rendered = package_reference._package_landing_markdown(record, [])
    assert "No description provided" in rendered


def test_package_landing_markdown_with_no_subpages_emits_no_toctree() -> None:
    """When no subpages exist on disk, the hidden toctree is omitted."""
    record = _shipped_py_fixture()
    rendered = package_reference._package_landing_markdown(record, [])
    assert "```{toctree}" not in rendered


def test_package_landing_markdown_with_subpages_emits_grid_and_toctree() -> None:
    """When subpages are present, both the grid cards and toctree appear."""
    record = _shipped_py_fixture()
    rendered = package_reference._package_landing_markdown(
        record,
        ["tutorial", "reference"],
    )
    assert "::::{grid}" in rendered
    assert ":::{grid-item-card} {octicon}`rocket` Tutorial" in rendered
    assert ":::{grid-item-card} {octicon}`book` Reference" in rendered
    assert "```{toctree}" in rendered
    assert "tutorial" in rendered
    assert "reference" in rendered


def test_package_landing_markdown_extra_subpage_uses_octicon_when_known() -> None:
    """A package opting into ``errors`` gets the alert octicon and title."""
    record = _shipped_py_fixture()
    rendered = package_reference._package_landing_markdown(record, ["errors"])
    assert ":::{grid-item-card} {octicon}`alert` Errors" in rendered


def test_package_landing_markdown_unknown_subpage_uses_link_octicon() -> None:
    """A subpage with no octicon entry falls back to the generic link icon."""
    record = _shipped_py_fixture()
    rendered = package_reference._package_landing_markdown(record, ["custom-page"])
    assert ":::{grid-item-card} {octicon}`link` Custom Page" in rendered


class _CandidatePathFixture(t.NamedTuple):
    """Fixture row asserting the candidate-subpage path map."""

    test_id: str
    package_name: str
    extra: tuple[str, ...]
    expected_keys: frozenset[str]


_CANDIDATE_PATH_FIXTURES: list[_CandidatePathFixture] = [
    _CandidatePathFixture(
        test_id="defaults_only",
        package_name="sphinx-fonts",
        extra=(),
        expected_keys=frozenset(
            {"tutorial", "how-to", "reference", "explanation", "examples"},
        ),
    ),
    _CandidatePathFixture(
        test_id="defaults_plus_errors_extra",
        package_name="sphinx-fonts",
        extra=("errors",),
        expected_keys=frozenset(
            {
                "tutorial",
                "how-to",
                "reference",
                "explanation",
                "examples",
                "errors",
            },
        ),
    ),
]


@pytest.mark.parametrize(
    list(_CandidatePathFixture._fields),
    _CANDIDATE_PATH_FIXTURES,
    ids=[case.test_id for case in _CANDIDATE_PATH_FIXTURES],
)
def test_candidate_subpage_paths_covers_defaults_and_extras(
    test_id: str,
    package_name: str,
    extra: tuple[str, ...],
    expected_keys: frozenset[str],
) -> None:
    """Candidate map includes the Diátaxis defaults plus declared extras."""
    base = next(
        r
        for r in package_reference.workspace_package_records()
        if r.name == package_name
    )
    record = package_reference.PackageDocsRecord(
        name=base.name,
        state=base.state,
        cluster=base.cluster,
        package_dir=base.package_dir,
        manifest_path=base.manifest_path,
        src_dir=base.src_dir,
        module_name=base.module_name,
        description=base.description,
        version=base.version,
        repository_url=base.repository_url,
        pypi_url=base.pypi_url,
        npm_url=base.npm_url,
        maturity=base.maturity,
        docs_opts=package_reference.DocsOpts(extra=extra),
    )
    paths = package_reference._candidate_subpage_paths(record)
    assert frozenset(paths.keys()) == expected_keys
    for subpage, path in paths.items():
        assert path.name == f"{subpage}.md"
        assert path.parent.name == record.name
