"""Tests for sphinx_autodoc_layout._nodes."""

from __future__ import annotations

from docutils import nodes
from sphinx_autodoc_layout._nodes import gal_fold, gal_region


def test_gal_region_is_general_element() -> None:
    r = gal_region(kind="narrative")
    assert isinstance(r, nodes.General)
    assert isinstance(r, nodes.Element)


def test_gal_region_stores_kind() -> None:
    r = gal_region(kind="fields")
    assert r.get("kind") == "fields"


def test_gal_fold_is_general_element() -> None:
    f = gal_fold(kind="parameters", summary="Parameters (5)")
    assert isinstance(f, nodes.General)
    assert isinstance(f, nodes.Element)


def test_gal_fold_stores_attributes() -> None:
    f = gal_fold(kind="parameters", summary="Parameters (5)", open=True)
    assert f.get("kind") == "parameters"
    assert f.get("summary") == "Parameters (5)"
    assert f.get("open") is True


def test_gal_fold_default_open_is_falsy() -> None:
    f = gal_fold(kind="parameters", summary="P (1)")
    assert not f.get("open")
