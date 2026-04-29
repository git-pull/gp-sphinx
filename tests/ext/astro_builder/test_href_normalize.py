"""Tests for the refuri normaliser.

Sphinx generates relative refuris with the AstroBuilder's ``.json``
output suffix (e.g. ``packages/gp-sphinx.json#api-config``). These
strings work fine inside the JSON content layer, but the rendered
HTML pages live at trailing-slash routes (``/packages/gp-sphinx/``)
so the raw refuri doesn't match the served URL. ``normalize_doc_href``
rewrites these to canonical site URLs, leaving external URLs and
in-page anchors untouched.
"""

from __future__ import annotations

import typing as t

import pytest

from gp_sphinx_astro_builder.translator import normalize_doc_href


class HrefFixture(t.NamedTuple):
    """One refuri-normalisation case."""

    test_id: str
    raw: str
    expected: str


_FIXTURES: list[HrefFixture] = [
    HrefFixture(
        test_id="top-level-doc",
        raw="architecture.json",
        expected="/architecture/",
    ),
    HrefFixture(
        test_id="top-level-doc-with-fragment",
        raw="architecture.json#tier-1",
        expected="/architecture/#tier-1",
    ),
    HrefFixture(
        test_id="nested-doc",
        raw="packages/gp-sphinx.json",
        expected="/packages/gp-sphinx/",
    ),
    HrefFixture(
        test_id="nested-doc-with-fragment",
        raw="packages/gp-sphinx.json#api",
        expected="/packages/gp-sphinx/#api",
    ),
    HrefFixture(
        test_id="index-becomes-root",
        raw="index.json",
        expected="/",
    ),
    HrefFixture(
        test_id="section-index-keeps-trailing-slash-form",
        raw="packages/index.json",
        expected="/packages/",
    ),
    HrefFixture(
        test_id="external-url-untouched",
        raw="https://example.com/whatever",
        expected="https://example.com/whatever",
    ),
    HrefFixture(
        test_id="in-page-anchor-untouched",
        raw="#some-anchor",
        expected="#some-anchor",
    ),
    HrefFixture(
        test_id="empty-string-untouched",
        raw="",
        expected="",
    ),
    HrefFixture(
        test_id="non-json-extension-untouched",
        raw="data/payload.csv",
        expected="data/payload.csv",
    ),
]


@pytest.mark.parametrize(
    list(HrefFixture._fields),
    _FIXTURES,
    ids=[f.test_id for f in _FIXTURES],
)
def test_normalize_doc_href(test_id: str, raw: str, expected: str) -> None:
    """``normalize_doc_href`` rewrites ``.json`` refuris to canonical URLs."""
    del test_id
    assert normalize_doc_href(raw) == expected
