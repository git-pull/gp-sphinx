"""Sitemap generator for Sphinx.

Drop-in replacement for ``sphinx-sitemap`` with Sphinx 8.1+ idioms.
Behavior is identical to upstream ``sphinx_sitemap`` v2.9.0 with three
modernizations:

1. Page enumeration runs once at ``build-finished`` over
   ``app.env.found_docs`` (the env-merged set of all documented files),
   using ``app.builder.get_target_uri(pagename)`` for each URL. This
   keeps sitemaps complete on incremental builds — where Sphinx fires
   ``html-page-context`` only for re-written pages — and across
   ``sphinx-build -j N`` workers, since ``found_docs`` is part of the
   merged env. Upstream ``sphinx-sitemap`` collected per-page via
   ``html-page-context`` and reconstructed URLs from ``html_file_suffix``,
   missing ``html_link_suffix`` divergence and the URL-quoting that
   ``get_target_uri`` performs.
2. Builder-kind detection uses the public ``app.builder.name == "dirhtml"``
   rather than monkey-patching ``env.is_directory_builder``. (Now folded
   into ``get_target_uri``, which already routes per builder.)
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

    from sphinx.util.typing import ExtensionMetadata

_EXTENSION_VERSION = "0.0.1a18"
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
        description=(
            "Site base URL prepended to every sitemap entry. Auto-derived "
            "from ``docs_url`` (trailing-slash normalized) under "
            "gp-sphinx; falls back to ``html_baseurl`` when unset. If "
            "both are unset the build is skipped silently at INFO level."
        ),
    )
    app.add_config_value(
        "sitemap_url_scheme",
        default="{lang}{version}{link}",
        rebuild="",
        types=frozenset({str}),
        description=(
            "Per-URL composition template formatted with ``lang`` "
            "(``language/`` or empty), ``version`` (``version/`` or "
            "empty), and ``link`` (the page's relative URL). Auto-set "
            "to flat ``{link}`` under gp-sphinx; multilingual or "
            "version-pinned hosts can pass ``{lang}{version}{link}`` "
            "via ``**overrides``."
        ),
    )
    app.add_config_value(
        "sitemap_locales",
        default=[],
        rebuild="",
        types=frozenset({list, type(None)}),
        description=(
            'Locales emitted as ``<xhtml:link rel="alternate" '
            "hreflang=...>`` siblings on every URL. Empty list "
            "auto-detects sub-directories of every ``locale_dirs`` entry; "
            "``[None]`` explicitly suppresses hreflang alternates. "
            "Underscores in locale codes become hyphens for IANA "
            "compatibility."
        ),
    )
    app.add_config_value(
        "sitemap_filename",
        default="sitemap.xml",
        rebuild="",
        types=frozenset({str}),
        description=("Output filename written under the build's ``outdir``."),
    )
    app.add_config_value(
        "sitemap_excludes",
        default=[],
        rebuild="",
        types=frozenset({list}),
        description=(
            "fnmatch patterns matched against each page's relative URL "
            "(after the builder applies its suffix). Matched pages are "
            "dropped from the sitemap; everything else is included."
        ),
    )
    app.add_config_value(
        "sitemap_show_lastmod",
        default=False,
        rebuild="",
        types=frozenset({bool}),
        description=(
            "When ``True``, lazy-loads ``sphinx-last-updated-by-git`` and "
            "emits a ``<lastmod>`` element per page from the source "
            "file's latest commit timestamp. If the supporting "
            "extension is not installed, gp-sitemap warns once and "
            "silently disables the flag."
        ),
    )
    app.add_config_value(
        "sitemap_indent",
        default=0,
        rebuild="",
        types=frozenset({int}),
        description=(
            "XML indent width in spaces. ``0`` minifies the output; "
            "any positive value pretty-prints via ``ElementTree.indent``."
        ),
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
            description=(
                "Sphinx core's canonical HTML base URL — re-registered "
                "defensively here to serve as the ``site_url`` fallback "
                "on Sphinx versions that ship without it."
            ),
        )

    app.connect("config-inited", _maybe_enable_git_lastmod)
    app.connect("build-finished", _write_sitemap)

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        # Safe at True because page enumeration runs once at build-finished
        # in the main process, iterating app.env.found_docs (which Sphinx
        # merges across parallel-read workers). No per-handler state.
        "parallel_write_safe": True,
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


def _write_sitemap(app: Sphinx, exception: BaseException | None) -> None:
    """Enumerate ``app.env.found_docs`` and serialize the sitemap.

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

    if not hasattr(app.builder, "get_target_uri"):
        # Non-HTML-family builders (text, json, manpage, …) have no
        # canonical URL surface; nothing to emit.
        return

    site_url = app.builder.config.site_url or app.builder.config.html_baseurl
    if not site_url:
        # INFO rather than WARNING because sphinx-gp-sitemap is in gp-sphinx's
        # DEFAULT_EXTENSIONS: users who haven't configured a deploy URL
        # should silently skip sitemap emission rather than break builds
        # that run with ``-W``.
        logger.info(
            "sphinx-gp-sitemap: sitemap skipped — site_url and html_baseurl both unset",
            type="sitemap",
            subtype="configuration",
        )
        return
    # Normalize the resolved base URL so the scheme.format() concatenation
    # below never produces malformed joins (e.g. "https://example.comindex.html"
    # when html_baseurl is the source and lacks a trailing slash). gp-sphinx
    # already normalizes site_url upstream of us, but a user setting
    # html_baseurl directly bypasses that path.
    if not site_url.endswith("/"):
        site_url = site_url + "/"

    config = app.builder.config
    excludes = list(config.sitemap_excludes)

    git_last_updated: dict[str, t.Any] = {}
    if config.sitemap_show_lastmod:
        git_last_updated = getattr(app.env, "git_last_updated", None) or {}

    links: list[SitemapLink] = []
    # Iterate in sorted order so the emitted sitemap is byte-stable across
    # builds — env.found_docs is a set with no defined iteration order.
    for pagename in sorted(app.env.found_docs):
        # get_target_uri applies html_link_suffix and URL-quotes the
        # pagename, matching what the HTML builder emits in <a href>
        # links. Doing it ourselves with html_file_suffix would diverge
        # for sites that set html_link_suffix (e.g. "/" for clean URLs)
        # and for pages whose names contain spaces or other reserved
        # characters.
        sitemap_link = app.builder.get_target_uri(pagename)
        if _is_excluded(sitemap_link, excludes):
            continue

        last_updated: str | None = None
        entry = git_last_updated.get(pagename)
        if entry:
            timestamp, _show_sourcelink = entry
            if timestamp:
                last_updated = dt.datetime.fromtimestamp(
                    int(timestamp), dt.timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ")

        links.append((sitemap_link, last_updated))

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

    If ``sitemap_locales`` is explicitly set, its values win — except
    that any sequence whose elements are all ``None`` is treated as
    the documented suppress-hreflang sentinel (``[None]`` in the
    README, ``(None,)`` if the user wrote a tuple). Otherwise,
    auto-detect by listing sub-directories of each ``locale_dirs``
    entry.
    """
    configured: list[str] | None = app.builder.config.sitemap_locales
    if configured:
        # Sentinel: any sequence of only-None elements suppresses
        # alternates. The list-vs-tuple distinction is invisible to
        # the user (Sphinx accepts both with only an advisory warning),
        # so accept either spelling rather than crashing in
        # _hreflang_formatter on a stray None.
        if all(item is None for item in configured):
            return []
        return [item for item in configured if item is not None]

    locales: list[str] = []
    confdir = pathlib.Path(app.confdir)
    for locale_dir_setting in app.builder.config.locale_dirs:
        locale_dir = confdir / locale_dir_setting
        if not locale_dir.is_dir():
            continue
        locales.extend(entry.name for entry in locale_dir.iterdir() if entry.is_dir())
    return locales
