"""Sitemap generator for Sphinx.

Drop-in replacement for ``sphinx-sitemap`` with Sphinx 8.1+ idioms.
Behavior is identical to upstream ``sphinx_sitemap`` v2.9.0 with three
modernizations:

1. ``env.temp_data["sphinx_gp_sitemap_links"]`` is a plain ``list[tuple[...]]``
   rather than a ``multiprocessing.Queue``. Because ``temp_data`` is
   per-process and not merged across parallel workers, sphinx-gp-sitemap only
   advertises ``parallel_read_safe`` and intentionally omits
   ``parallel_write_safe``: under ``sphinx-build -j N`` link collection
   would be incomplete, so the extension is single-write-process only.
2. Builder-kind detection uses the public ``app.builder.name == "dirhtml"``
   rather than monkey-patching ``env.is_directory_builder``.
3. The ``html_baseurl`` config value is only registered when not already
   registered — via a small ``try/except sphinx.errors.ExtensionError``
   rather than a bare ``except BaseException``.

Examples
--------
>>> from sphinx_gp_sitemap import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import contextlib
import datetime as dt
import fnmatch
import logging
import pathlib
import typing as t
from xml.etree import ElementTree

from sphinx.application import Sphinx
from sphinx.errors import ExtensionError
from sphinx.util.logging import getLogger

if t.TYPE_CHECKING:
    from collections.abc import Iterable

    from docutils import nodes
    from sphinx.util.typing import ExtensionMetadata

_EXTENSION_VERSION = "0.0.1a9"
_LINKS_KEY = "sphinx_gp_sitemap_links"
_SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
_XHTML_NS = "http://www.w3.org/1999/xhtml"

# sphinx-gp-sitemap uses Sphinx's logger adapter so ``type=``/``subtype=`` kwargs
# work for warning classification, but still attaches NullHandler to the
# underlying stdlib logger so the library doesn't emit "no handlers" warnings
# when imported outside a Sphinx build (per CLAUDE.md #Logger setup).
logger = getLogger(__name__)
logging.getLogger(__name__).addHandler(logging.NullHandler())

SitemapLink = tuple[str, str | None]  # (relative link, last_updated ISO8601 or None)

__all__ = ["setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register config values and connect sitemap-emission hooks.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.

    Returns
    -------
    ExtensionMetadata
        Extension metadata — version plus parallel-build flags.

    Examples
    --------
    >>> from sphinx_gp_sitemap import setup
    >>> callable(setup)
    True
    """
    app.add_config_value(
        "site_url",
        default=None,
        rebuild="",
        types=frozenset({str, type(None)}),
    )
    app.add_config_value(
        "sitemap_url_scheme",
        default="{lang}{version}{link}",
        rebuild="",
        types=frozenset({str}),
    )
    app.add_config_value(
        "sitemap_locales",
        default=[],
        rebuild="",
        types=frozenset({list, type(None)}),
    )
    app.add_config_value(
        "sitemap_filename",
        default="sitemap.xml",
        rebuild="",
        types=frozenset({str}),
    )
    app.add_config_value(
        "sitemap_excludes",
        default=[],
        rebuild="",
        types=frozenset({list}),
    )
    app.add_config_value(
        "sitemap_show_lastmod",
        default=False,
        rebuild="",
        types=frozenset({bool}),
    )
    app.add_config_value(
        "sitemap_indent",
        default=0,
        rebuild="",
        types=frozenset({int}),
    )
    # html_baseurl is usually registered by Sphinx core already — suppress the
    # duplicate-registration error without losing the legitimate single-
    # registration path.
    with contextlib.suppress(ExtensionError):
        app.add_config_value(
            "html_baseurl",
            default=None,
            rebuild="",
            types=frozenset({str, type(None)}),
        )

    app.connect("config-inited", _maybe_enable_git_lastmod)
    app.connect("builder-inited", _init_link_store)
    app.connect("html-page-context", _collect_page_link)
    app.connect("build-finished", _write_sitemap)

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
    }


def _maybe_enable_git_lastmod(
    app: Sphinx,
    config: t.Any,
) -> None:
    """Load ``sphinx_last_updated_by_git`` lazily when lastmod is enabled.

    Deferred to ``config-inited`` so ``config.sitemap_show_lastmod`` has
    had its default populated by Sphinx before we read it. Disables the
    feature on import failure rather than aborting the build.
    """
    if not config.sitemap_show_lastmod:
        return
    try:
        app.setup_extension("sphinx_last_updated_by_git")
    except ExtensionError as exc:
        logger.warning(
            "%s",
            exc,
            type="sitemap",
            subtype="configuration",
        )
        config.sitemap_show_lastmod = False


def _init_link_store(app: Sphinx) -> None:
    """Initialize the shared ``env.temp_data`` list on each build start."""
    app.env.temp_data[_LINKS_KEY] = []


def _collect_page_link(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, t.Any],
    doctree: nodes.document | None,
) -> None:
    """Append one ``(relative_link, last_updated)`` entry per built page.

    Called once per page during HTML emission via ``html-page-context``.
    """
    del templatename, context, doctree  # unused
    config = app.builder.config
    file_suffix = config.html_file_suffix or ".html"

    last_updated: str | None = None
    if config.sitemap_show_lastmod:
        git_last_updated = getattr(app.env, "git_last_updated", None) or {}
        entry = git_last_updated.get(pagename)
        if entry:
            timestamp, _show_sourcelink = entry
            if timestamp:
                last_updated = dt.datetime.fromtimestamp(
                    int(timestamp), dt.timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")

    if app.builder.name == "dirhtml":
        if pagename == "index":
            sitemap_link = ""
        elif pagename.endswith("/index"):
            sitemap_link = pagename[: -len("/index")] + "/"
        else:
            sitemap_link = pagename + "/"
    else:
        sitemap_link = pagename + file_suffix

    if _is_excluded(sitemap_link, list(config.sitemap_excludes)):
        return

    links = t.cast("list[SitemapLink]", app.env.temp_data.setdefault(_LINKS_KEY, []))
    links.append((sitemap_link, last_updated))


def _write_sitemap(app: Sphinx, exception: BaseException | None) -> None:
    """Serialize the collected links to ``<outdir>/<sitemap_filename>``.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.
    exception : BaseException | None
        Exception raised during build, if any. The sitemap is still
        written on clean builds; on failures it's suppressed.
    """
    if exception is not None:
        return

    site_url = app.builder.config.site_url or app.builder.config.html_baseurl
    if not site_url:
        # INFO rather than WARNING because sphinx-gp-sitemap is in gp-sphinx's
        # DEFAULT_EXTENSIONS: users who haven't configured a deploy URL
        # should silently skip sitemap emission rather than break builds
        # that run with ``-W``.
        logger.info(
            "sphinx-gp-sitemap: skipping sitemap — set site_url or html_baseurl "
            "in conf.py to enable",
            type="sitemap",
            subtype="configuration",
        )
        return

    links = t.cast(
        "list[SitemapLink]",
        app.env.temp_data.get(_LINKS_KEY, []),
    )
    if not links:
        logger.info(
            "sphinx-gp-sitemap: no pages collected for %s",
            app.config.sitemap_filename,
            type="sitemap",
            subtype="information",
        )
        return

    ElementTree.register_namespace("xhtml", _XHTML_NS)
    root = ElementTree.Element("urlset", xmlns=_SITEMAP_NS)

    locales = _resolve_locales(app)
    scheme = app.config.sitemap_url_scheme
    language = app.builder.config.language
    lang_segment = f"{language}/" if language else ""
    version_segment = (
        f"{app.builder.config.version}/" if app.builder.config.version else ""
    )

    for sitemap_link, last_updated in links:
        url_el = ElementTree.SubElement(root, "url")
        ElementTree.SubElement(url_el, "loc").text = site_url + scheme.format(
            lang=lang_segment,
            version=version_segment,
            link=sitemap_link,
        )
        if last_updated:
            ElementTree.SubElement(url_el, "lastmod").text = last_updated
        for locale in locales:
            locale_segment = f"{locale}/"
            ElementTree.SubElement(
                url_el,
                f"{{{_XHTML_NS}}}link",
                rel="alternate",
                hreflang=_hreflang_formatter(locale),
                href=site_url
                + scheme.format(
                    lang=locale_segment,
                    version=version_segment,
                    link=sitemap_link,
                ),
            )

    sitemap_path = pathlib.Path(app.outdir) / app.config.sitemap_filename
    if isinstance(app.config.sitemap_indent, int) and app.config.sitemap_indent > 0:
        ElementTree.indent(root, space=" " * app.config.sitemap_indent)
    ElementTree.ElementTree(root).write(
        sitemap_path,
        xml_declaration=True,
        encoding="utf-8",
        method="xml",
    )

    logger.info(
        "sphinx-gp-sitemap: %s generated for URL %s at %s",
        app.config.sitemap_filename,
        site_url,
        sitemap_path,
        type="sitemap",
        subtype="information",
    )


def _is_excluded(sitemap_link: str, patterns: Iterable[str]) -> bool:
    """Return True when ``sitemap_link`` matches any fnmatch pattern."""
    return any(fnmatch.fnmatch(sitemap_link, pattern) for pattern in patterns)


def _hreflang_formatter(lang: str) -> str:
    """Format a locale code into an ``hreflang``-compatible string.

    References
    ----------
    - https://en.wikipedia.org/wiki/Hreflang#Common_Mistakes
    - https://github.com/readthedocs/readthedocs.org/pull/5638
    """
    return lang.replace("_", "-") if "_" in lang else lang


def _resolve_locales(app: Sphinx) -> list[str]:
    """Return the list of locale codes to emit as hreflang alternates.

    If ``sitemap_locales`` is explicitly set (and not ``[None]``), its
    values win. Otherwise, auto-detect by listing sub-directories of
    each ``locale_dirs`` entry.
    """
    configured: list[str] | None = app.builder.config.sitemap_locales
    if configured:
        if configured == [None]:
            return []
        return list(configured)

    locales: list[str] = []
    confdir = pathlib.Path(app.confdir)
    for locale_dir_setting in app.builder.config.locale_dirs:
        locale_dir = confdir / locale_dir_setting
        if not locale_dir.is_dir():
            continue
        locales.extend(entry.name for entry in locale_dir.iterdir() if entry.is_dir())
    return locales
