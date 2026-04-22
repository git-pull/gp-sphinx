"""Functional tests for gp_sitemap's XML emission."""

from __future__ import annotations

import typing as t
from xml.etree import ElementTree

import pytest

if t.TYPE_CHECKING:
    from tests.ext.sitemap.conftest import SitemapBuildResult

_SITEMAP_NS = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
_XHTML_NS = "{http://www.w3.org/1999/xhtml}"


def _loc_values(tree: ElementTree.ElementTree[t.Any]) -> list[str]:
    root = tree.getroot()
    assert root is not None
    return [el.text or "" for el in root.iter(f"{_SITEMAP_NS}loc")]


class SitemapCase(t.NamedTuple):
    """One sitemap-emission test case."""

    test_id: str
    conf_overrides: dict[str, t.Any]
    buildername: str
    expected_loc_endings: tuple[str, ...]
    forbidden_loc_endings: tuple[str, ...]


CASES: tuple[SitemapCase, ...] = (
    SitemapCase(
        test_id="html-builder-emits-html-suffixes",
        conf_overrides={"site_url": "https://example.org/"},
        buildername="html",
        expected_loc_endings=("index.html", "about.html", "draft.html"),
        forbidden_loc_endings=(),
    ),
    SitemapCase(
        test_id="dirhtml-builder-emits-slash-suffixes",
        conf_overrides={"site_url": "https://example.org/"},
        buildername="dirhtml",
        # Sphinx sets language="en" by default when html_theme is set;
        # the default sitemap_url_scheme injects that as a path segment.
        # Index is emitted as the plain "en/", not "en/index/".
        expected_loc_endings=("en/", "about/", "draft/"),
        forbidden_loc_endings=("index.html", "about.html"),
    ),
    SitemapCase(
        test_id="excluded-pages-are-dropped",
        conf_overrides={
            "site_url": "https://example.org/",
            "sitemap_excludes": ["draft*"],
        },
        buildername="html",
        expected_loc_endings=("index.html", "about.html"),
        forbidden_loc_endings=("draft.html",),
    ),
    SitemapCase(
        test_id="non-zero-indent-pretty-prints",
        conf_overrides={
            "site_url": "https://example.org/",
            "sitemap_indent": 2,
        },
        buildername="html",
        expected_loc_endings=("index.html", "about.html", "draft.html"),
        forbidden_loc_endings=(),
    ),
)


@pytest.mark.parametrize("case", CASES, ids=[c.test_id for c in CASES])
def test_urlset(
    case: SitemapCase,
    build_sitemap_site: t.Callable[..., SitemapBuildResult],
) -> None:
    """Each case's expected <loc> values appear and forbidden ones don't."""
    built = build_sitemap_site(
        conf_overrides=case.conf_overrides,
        buildername=case.buildername,
    )
    assert built.tree is not None, (
        f"{case.test_id}: sitemap.xml was not written to {built.sitemap_path}"
    )
    locs = _loc_values(built.tree)
    for ending in case.expected_loc_endings:
        assert any(loc.endswith(ending) or loc == ending for loc in locs), (
            f"{case.test_id}: no <loc> ending in {ending!r}; got {locs!r}"
        )
    for ending in case.forbidden_loc_endings:
        assert not any(loc.endswith(ending) for loc in locs), (
            f"{case.test_id}: forbidden ending {ending!r} in {locs!r}"
        )


def test_urlset_root_has_sitemap_namespace(
    build_sitemap_site: t.Callable[..., SitemapBuildResult],
) -> None:
    """The <urlset> element carries the sitemaps.org namespace URI."""
    built = build_sitemap_site(conf_overrides={"site_url": "https://example.org/"})
    assert built.tree is not None
    root = built.tree.getroot()
    assert root is not None
    assert root.tag == f"{_SITEMAP_NS}urlset"


def test_no_site_url_skips_sitemap_silently(
    build_sitemap_site: t.Callable[..., SitemapBuildResult],
) -> None:
    """Without site_url/html_baseurl the sitemap is silently skipped.

    gp-sitemap is in gp-sphinx's DEFAULT_EXTENSIONS, so an unset deploy
    URL should not break ``sphinx-build -W``. The missing-URL notice is
    logged at INFO, not WARNING.
    """
    built = build_sitemap_site(conf_overrides={})  # site_url omitted
    assert built.tree is None
    assert "site_url" not in built.result.warnings
