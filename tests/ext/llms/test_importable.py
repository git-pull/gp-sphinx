"""Smoke tests for sphinx_gp_llms importability and metadata."""

from __future__ import annotations

from sphinx_gp_llms import setup


def test_setup_callable() -> None:
    """setup() is callable and returns extension metadata."""
    assert callable(setup)
