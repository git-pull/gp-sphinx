"""Unit tests for shared-stack extension setup across autodoc packages."""

from __future__ import annotations

import collections.abc as cabc
import types
import typing as t

import pytest
from sphinx.application import Sphinx

import sphinx_autodoc_api_style
import sphinx_autodoc_docutils
import sphinx_autodoc_fastmcp
import sphinx_autodoc_pytest_fixtures
import sphinx_autodoc_sphinx


class _SetupCase(t.NamedTuple):
    """Typed setup-case metadata for shared-stack consumers."""

    test_id: str
    setup: t.Callable[[Sphinx], cabc.Mapping[str, t.Any]]
    expected_extensions: tuple[str, ...]


_SETUP_CASES = (
    _SetupCase(
        "api_style",
        sphinx_autodoc_api_style.setup,
        (
            "sphinx.ext.autodoc",
            "sphinx_autodoc_badges",
            "sphinx_autodoc_layout",
        ),
    ),
    _SetupCase(
        "pytest_fixtures",
        sphinx_autodoc_pytest_fixtures.setup,
        (
            "sphinx.ext.autodoc",
            "sphinx_autodoc_badges",
            "sphinx_autodoc_layout",
            "sphinx_typehints_gp",
        ),
    ),
    _SetupCase(
        "autodoc_sphinx",
        sphinx_autodoc_sphinx.setup,
        (
            "sphinx_autodoc_badges",
            "sphinx_autodoc_layout",
            "sphinx_typehints_gp",
        ),
    ),
    _SetupCase(
        "autodoc_docutils",
        sphinx_autodoc_docutils.setup,
        (
            "sphinx_autodoc_badges",
            "sphinx_autodoc_layout",
            "sphinx_typehints_gp",
        ),
    ),
    _SetupCase(
        "fastmcp",
        sphinx_autodoc_fastmcp.setup,
        (
            "sphinx_autodoc_badges",
            "sphinx_autodoc_layout",
            "sphinx_typehints_gp",
        ),
    ),
)


@pytest.mark.parametrize("case", _SETUP_CASES, ids=[case.test_id for case in _SETUP_CASES])
def test_shared_stack_setup_autoloads_expected_extensions(case: _SetupCase) -> None:
    """Each shipped autodoc extension loads the shared stack explicitly."""
    setup_calls: list[str] = []
    css_files: list[str] = []

    app = types.SimpleNamespace(
        config=types.SimpleNamespace(html_static_path=[]),
        setup_extension=setup_calls.append,
        connect=lambda *args, **kwargs: None,
        add_css_file=css_files.append,
        add_js_file=lambda *args, **kwargs: None,
        add_config_value=lambda *args, **kwargs: None,
        add_directive=lambda *args, **kwargs: None,
        add_directive_to_domain=lambda *args, **kwargs: None,
        add_role=lambda *args, **kwargs: None,
        add_role_to_domain=lambda *args, **kwargs: None,
        add_autodocumenter=lambda *args, **kwargs: None,
        add_crossref_type=lambda *args, **kwargs: None,
        add_node=lambda *args, **kwargs: None,
    )

    metadata = case.setup(t.cast(Sphinx, app))

    for extension_name in case.expected_extensions:
        assert extension_name in setup_calls
    assert metadata["parallel_read_safe"] is True
    assert metadata["parallel_write_safe"] is True
    assert css_files
