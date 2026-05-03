"""OpenGraph and Twitter meta-tag emission for Sphinx.

Drop-in replacement for ``sphinxext-opengraph`` with the same ``ogp_*``
configuration surface, minus the matplotlib-based social-card generator.
The ``ogp_social_cards`` config value is still accepted (so existing
``conf.py`` files do not error), but setting it emits a one-line warning
directing users to the static-image alternative.

The ``setup()`` registers every ``ogp_*`` config value and connects the
``html-page-context`` hook that emits OpenGraph and Twitter ``<meta>``
tags alongside an optional ``<meta name="description">``.

Examples
--------
>>> from sphinx_gp_opengraph import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import html
import logging
import os
import pathlib
import types
import typing as t
import urllib.parse

from docutils import nodes
from sphinx.application import Sphinx

from sphinx_gp_opengraph._description import get_description
from sphinx_gp_opengraph._meta import get_meta_description
from sphinx_gp_opengraph._title import get_title

if t.TYPE_CHECKING:
    from sphinx.builders import Builder
    from sphinx.config import Config
    from sphinx.util.typing import ExtensionMetadata

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

_EXTENSION_VERSION = "0.0.1a16.dev2"

DEFAULT_DESCRIPTION_LENGTH = 200

# A selection from
# https://www.iana.org/assignments/media-types/media-types.xhtml#image
IMAGE_MIME_TYPES: frozenset[str] = frozenset(
    {"gif", "apng", "webp", "jpeg", "jpg", "png", "bmp", "heic", "heif", "tiff"},
)

__all__ = [
    "DEFAULT_DESCRIPTION_LENGTH",
    "IMAGE_MIME_TYPES",
    "setup",
]


def html_page_context(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, t.Any],
    doctree: nodes.document,
) -> None:
    """Inject OpenGraph / Twitter meta tags into ``context['metatags']``.

    Skipped for the ``epub`` builder and for pages without a resolved
    doctree (e.g. rendered search indexes).
    """
    del pagename, templatename  # sourced from ``context`` when needed
    if app.builder.name == "epub":
        return
    if not doctree:
        return
    context["metatags"] += get_tags(
        context,
        doctree,
        config=app.config,
        builder=app.builder,
    )


def get_tags(
    context: dict[str, t.Any],
    doctree: nodes.document,
    *,
    config: Config,
    builder: Builder,
) -> str:
    """Compose the block of ``<meta>`` tags for one page.

    Parameters
    ----------
    context : dict[str, Any]
        Sphinx HTML page context (provides ``title``, ``pagename``,
        ``meta`` field-list, and existing ``metatags`` string).
    doctree : docutils.nodes.document
        Resolved doctree for the page, walked to extract the description.
    config : sphinx.config.Config
        Project configuration (sources all ``ogp_*`` values).
    builder : sphinx.builders.Builder
        Active HTML-family builder (used for per-page URL resolution).

    Returns
    -------
    str
        Newline-terminated block of ``<meta>`` tags ready to append to
        ``context['metatags']``. Empty when the page sets
        ``ogp_disable`` in its field list.
    """
    fields: dict[str, t.Any] = context.get("meta") or {}
    if "ogp_disable" in fields:
        return ""

    tags: dict[str, str] = {}
    meta_tags: dict[str, str] = {}  # Non-og <meta name="..."> tags

    try:
        desc_len = int(
            fields.get("ogp_description_length", config.ogp_description_length),
        )
    except ValueError:
        desc_len = DEFAULT_DESCRIPTION_LENGTH

    title, title_excluding_html = get_title(context["title"])
    description = get_description(doctree, desc_len, {title, title_excluding_html})

    tags["og:title"] = title
    tags["og:type"] = config.ogp_type

    if not config.ogp_site_url and os.getenv("READTHEDOCS"):
        ogp_site_url = _ambient_site_url()
    else:
        ogp_site_url = config.ogp_site_url

    ogp_canonical_url = config.ogp_canonical_url or ogp_site_url

    page_url = urllib.parse.urljoin(
        ogp_canonical_url,
        builder.get_target_uri(context["pagename"]),
    )
    tags["og:url"] = page_url

    site_name = _resolve_site_name(config)
    if site_name:
        tags["og:site_name"] = site_name

    if description:
        tags["og:description"] = description
        if config.ogp_enable_meta_description and not get_meta_description(
            context["metatags"],
        ):
            meta_tags["description"] = description

    image_url, ogp_image_alt, ogp_use_first_image = _resolve_image(fields, config)

    first_image = None
    if ogp_use_first_image:
        found = doctree.next_node(nodes.image)
        if (
            found
            and pathlib.Path(found.get("uri", "")).suffix[1:].lower()
            in IMAGE_MIME_TYPES
        ):
            first_image = found
            image_url = found["uri"]
            ogp_image_alt = found.get("alt")

    if image_url:
        if "og:image" not in fields:
            image_url_parsed = urllib.parse.urlparse(image_url)
            if not image_url_parsed.scheme:
                root = page_url if first_image else ogp_site_url
                image_url = urllib.parse.urljoin(root, image_url_parsed.path)
            tags["og:image"] = image_url

        if isinstance(ogp_image_alt, str):
            tags["og:image:alt"] = ogp_image_alt
        elif ogp_image_alt is None and site_name:
            tags["og:image:alt"] = site_name
        elif ogp_image_alt is None and title:
            tags["og:image:alt"] = title

    fields.pop("og:image:alt", None)

    # Arbitrary og:* overrides supplied through MyST / field-list frontmatter
    tags.update({k: v for k, v in fields.items() if k.startswith("og:")})

    return (
        "\n".join(
            [_make_tag(p, c) for p, c in tags.items()]
            + [_make_tag(p, c, "name") for p, c in meta_tags.items()]
            + list(config.ogp_custom_meta_tags),
        )
        + "\n"
    )


def _ambient_site_url() -> str:
    """Derive a site URL from ReadTheDocs env when ``ogp_site_url`` is unset."""
    rtd_canonical_url = os.getenv("READTHEDOCS_CANONICAL_URL")
    if not rtd_canonical_url:
        msg = "ReadTheDocs did not provide a valid canonical URL"
        raise RuntimeError(msg)
    parsed = urllib.parse.urlsplit(rtd_canonical_url)
    return urllib.parse.urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, "", ""),
    )


def _resolve_site_name(config: Config) -> str | None:
    """Return the resolved site name or ``None`` when explicitly disabled."""
    if config.ogp_site_name is False:
        return None
    if config.ogp_site_name is None:
        return t.cast("str", config.project)
    return t.cast("str", config.ogp_site_name)


def _resolve_image(
    fields: dict[str, t.Any],
    config: Config,
) -> tuple[str | None, str | bool | None, bool]:
    """Return (image_url, alt_text, use_first_image) for this page.

    Per-page field-list ``og:image`` wins; otherwise fall back to
    ``config.ogp_image`` / ``config.ogp_use_first_image``.
    """
    if "og:image" in fields:
        image_url: str | None = fields["og:image"]
        ogp_use_first_image = False
        ogp_image_alt: str | bool | None = fields.get("og:image:alt")
        fields.pop("og:image", None)
    else:
        image_url = config.ogp_image
        ogp_use_first_image = bool(config.ogp_use_first_image)
        ogp_image_alt = fields.get("og:image:alt", config.ogp_image_alt)
    return image_url, ogp_image_alt, ogp_use_first_image


def _make_tag(
    property_: str,
    content: str,
    attr: t.Literal["property", "name"] = "property",
) -> str:
    """Render one ``<meta>`` tag, HTML-escaping ``&``, ``<``, ``>``, and quotes.

    Centralising the escape here is the boundary that keeps every meta tag
    safe — titles, site names, descriptions, image alts, and custom
    field-list values all flow through this function. Per-source escaping
    (e.g. pre-escaping the description) would either leave other paths
    unsafe or double-escape (``&`` → ``&amp;`` → ``&amp;amp;``).
    """
    safe_content = html.escape(content, quote=True)
    return f'<meta {attr}="{property_}" content="{safe_content}" />'


def _warn_if_social_cards_used(app: Sphinx, config: Config) -> None:
    """Emit a one-line deprecation warning when ``ogp_social_cards`` is set.

    sphinx-gp-opengraph deliberately omits the matplotlib-based card generator
    upstream ships. The ``ogp_social_cards`` config value remains
    registered so existing ``conf.py`` files do not error — but its value
    is ignored. Users who want per-page social preview images should
    provide static PNGs and point ``ogp_image`` (plus per-page
    ``og:image`` frontmatter) at them.
    """
    del app  # unused; required by Sphinx's config-inited signature
    if config.ogp_social_cards:
        logger.warning(
            "sphinx-gp-opengraph: ogp_social_cards ignored — "
            "sphinx-gp-opengraph ships no card generator",
        )


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register config values and connect the html-page-context hook.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.

    Returns
    -------
    ExtensionMetadata
        Extension metadata — version and parallel-build flags.

    Examples
    --------
    >>> from sphinx_gp_opengraph import setup
    >>> callable(setup)
    True
    """
    # ogp_site_url="" allows relative URLs by default. Not officially
    # supported by OGP but matches upstream sphinxext-opengraph.
    app.add_config_value(
        "ogp_site_url",
        "",
        "html",
        types=frozenset({str}),
        description=(
            "Site base URL joined with each page's relative path to form "
            "``og:url``. Required for absolute URLs; auto-derived from "
            "``docs_url`` under gp-sphinx."
        ),
    )
    app.add_config_value(
        "ogp_canonical_url",
        "",
        "html",
        types=frozenset({str}),
        description=(
            "Separate canonical URL used to build ``og:url``; falls back "
            "to ``ogp_site_url`` when empty."
        ),
    )
    app.add_config_value(
        "ogp_description_length",
        DEFAULT_DESCRIPTION_LENGTH,
        "html",
        types=frozenset({int}),
        description=(
            "Truncation cap (characters) applied to ``og:description`` "
            "after extracting the first body paragraph."
        ),
    )
    app.add_config_value(
        "ogp_image",
        None,
        "html",
        types=frozenset({str, types.NoneType}),
        description=(
            "Site-default OpenGraph image path or absolute URL. "
            "Auto-derived from ``docs_url`` under gp-sphinx; per-page "
            "``og:image`` front-matter overrides."
        ),
    )
    app.add_config_value(
        "ogp_image_alt",
        None,
        "html",
        types=frozenset({str, bool, types.NoneType}),
        description=(
            "Alt text for ``ogp_image``. Falls back to ``og:site_name`` "
            "then ``og:title``; ``False`` suppresses the alt tag entirely."
        ),
    )
    app.add_config_value(
        "ogp_use_first_image",
        False,
        "html",
        types=frozenset({bool}),
        description=(
            "When ``True`` and no per-page override is set, use the "
            "first in-page image as ``og:image``."
        ),
    )
    app.add_config_value(
        "ogp_type",
        "website",
        "html",
        types=frozenset({str}),
        description="Value emitted as the ``og:type`` tag.",
    )
    app.add_config_value(
        "ogp_site_name",
        None,
        "html",
        types=frozenset({str, bool, types.NoneType}),
        description=(
            "Value emitted as ``og:site_name``. Defaults to the Sphinx "
            "``project`` name; ``False`` suppresses the tag."
        ),
    )
    # Accepted-but-ignored: warned about in _warn_if_social_cards_used.
    app.add_config_value(
        "ogp_social_cards",
        None,
        "html",
        types=frozenset({dict, types.NoneType}),
        description=(
            "Accepted-but-ignored compatibility shim for upstream "
            "``sphinxext-opengraph``. Setting any value emits a one-line "
            "WARNING at ``config-inited``; provide a static PNG via "
            "``ogp_image`` or per-page ``og:image`` instead."
        ),
    )
    app.add_config_value(
        "ogp_custom_meta_tags",
        (),
        "html",
        types=frozenset({list, tuple}),
        description=(
            "Raw ``<meta>`` tag strings appended verbatim after the "
            "structured ``og:*`` block — the supported escape hatch for "
            "Twitter card declarations and image-dimension hints."
        ),
    )
    app.add_config_value(
        "ogp_enable_meta_description",
        True,
        "html",
        types=frozenset({bool}),
        description=(
            'When ``True``, emit a ``<meta name="description">`` '
            "mirroring ``og:description`` unless the page already "
            "defines one."
        ),
    )

    app.connect("html-page-context", html_page_context)
    app.connect("config-inited", _warn_if_social_cards_used)

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
