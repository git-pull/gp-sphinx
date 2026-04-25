"""Functional tests for sphinx_gp_opengraph's html-page-context meta emission.

Each case builds a tiny real Sphinx site with the extension active and
asserts the emitted ``<meta ...>`` tags under the expected keys.
"""

from __future__ import annotations

import typing as t

import pytest

if t.TYPE_CHECKING:
    from tests.ext.opengraph.conftest import OgBuildResult

pytestmark = pytest.mark.integration


class MetaCase(t.NamedTuple):
    """One emission test case."""

    test_id: str
    conf_overrides: dict[str, t.Any]
    index_markdown: str | None  # None keeps the default body
    expected_present: dict[str, str]
    expected_absent: tuple[str, ...]


_DEFAULT_INDEX = None  # sentinel — use conftest default


CASES: tuple[MetaCase, ...] = (
    MetaCase(
        test_id="bare-defaults-emits-type-and-title",
        conf_overrides={"ogp_site_url": "https://example.org/"},
        index_markdown=_DEFAULT_INDEX,
        expected_present={
            "og:type": "website",
            "og:title": "Welcome to sphinx-gp-opengraph-test",
            "og:site_name": "sphinx-gp-opengraph-test",
            "og:url": "https://example.org/index.html",
        },
        expected_absent=("og:image", "og:image:alt"),
    ),
    MetaCase(
        test_id="with-image-and-alt",
        conf_overrides={
            "ogp_site_url": "https://example.org/",
            "ogp_image": "_static/og.png",
            "ogp_image_alt": "hero banner",
        },
        index_markdown=_DEFAULT_INDEX,
        expected_present={
            "og:image": "https://example.org/_static/og.png",
            "og:image:alt": "hero banner",
        },
        expected_absent=(),
    ),
    MetaCase(
        test_id="custom-meta-tags-emit-verbatim",
        conf_overrides={
            "ogp_site_url": "https://example.org/",
            "ogp_custom_meta_tags": (
                '<meta name="twitter:card" content="summary_large_image" />',
            ),
        },
        index_markdown=_DEFAULT_INDEX,
        expected_present={"twitter:card": "summary_large_image"},
        expected_absent=(),
    ),
    MetaCase(
        test_id="site-name-disabled-emits-no-site-name",
        conf_overrides={
            "ogp_site_url": "https://example.org/",
            "ogp_site_name": False,
        },
        index_markdown=_DEFAULT_INDEX,
        expected_present={"og:type": "website"},
        expected_absent=("og:site_name",),
    ),
    MetaCase(
        test_id="description-absent-is-not-an-error",
        conf_overrides={
            "ogp_site_url": "https://example.org/",
            "ogp_enable_meta_description": False,
        },
        # Single heading only — no body text -> no description extracted.
        index_markdown="# Heading only\n",
        expected_present={"og:type": "website"},
        expected_absent=("og:description", "description"),
    ),
)


@pytest.mark.parametrize("case", CASES, ids=[c.test_id for c in CASES])
def test_meta_emission(
    case: MetaCase,
    build_og_site: t.Callable[..., OgBuildResult],
) -> None:
    """Each case's expected tags appear and absent tags do not."""
    built = build_og_site(
        conf_overrides=case.conf_overrides,
        index_markdown=case.index_markdown,
    )
    for key, want in case.expected_present.items():
        assert key in built.meta, f"{case.test_id}: missing {key!r} in {built.meta!r}"
        assert built.meta[key] == want, (
            f"{case.test_id}: {key}={built.meta[key]!r} != {want!r}"
        )
    for key in case.expected_absent:
        assert key not in built.meta, (
            f"{case.test_id}: unexpected {key!r} in {built.meta!r}"
        )


def test_og_description_extracted_from_body(
    build_og_site: t.Callable[..., OgBuildResult],
) -> None:
    """Body paragraphs flow into og:description without the title leaking."""
    built = build_og_site(
        conf_overrides={"ogp_site_url": "https://example.org/"},
    )
    assert "og:description" in built.meta
    description = built.meta["og:description"]
    # Title should be elided; body should be present.
    assert "Welcome to sphinx-gp-opengraph-test" not in description
    assert "body paragraph" in description
