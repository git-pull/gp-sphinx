"""LLM-friendly documentation outputs for Sphinx.

Generates ``llms.txt``, ``llms-full.txt``, ``docs.json``, and per-page
``.md`` twin files during the standard HTML build, following conventions
established by llmstxt.org (Jeremy Howard / Answer.AI), Cloudflare
("Markdown for Agents"), and Lakebed (Ping).

The extension hooks into ``build-finished`` to write output files and
``html-page-context`` to inject footer link variables into the template
context.

Examples
--------
>>> from sphinx_gp_llms import setup
>>> callable(setup)
True
"""

from __future__ import annotations

import contextlib
import logging
import typing as t

from sphinx.errors import ExtensionError
from sphinx.util.logging import getLogger

if t.TYPE_CHECKING:
    from docutils import nodes
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

_EXTENSION_VERSION = "0.0.1a29"

logger = getLogger(__name__)
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = ["setup"]


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register config values and connect build hooks.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.

    Returns
    -------
    ExtensionMetadata
        Extension metadata with version and parallel-build flags.

    Examples
    --------
    >>> from sphinx_gp_llms import setup
    >>> callable(setup)
    True
    """
    app.add_config_value(
        "llms_generate_txt",
        default=True,
        rebuild="",
        types=frozenset({bool}),
        description="Enable llms.txt generation.",
    )
    app.add_config_value(
        "llms_generate_full",
        default=True,
        rebuild="",
        types=frozenset({bool}),
        description="Enable llms-full.txt generation.",
    )
    app.add_config_value(
        "llms_generate_json",
        default=True,
        rebuild="",
        types=frozenset({bool}),
        description="Enable docs.json agent manifest generation.",
    )
    app.add_config_value(
        "llms_generate_md_twins",
        default=True,
        rebuild="",
        types=frozenset({bool}),
        description="Enable per-page .md twin file generation.",
    )
    app.add_config_value(
        "llms_txt_filename",
        default="llms.txt",
        rebuild="",
        types=frozenset({str}),
        description="Output filename for the llms.txt index.",
    )
    app.add_config_value(
        "llms_full_filename",
        default="llms-full.txt",
        rebuild="",
        types=frozenset({str}),
        description="Output filename for the concatenated full-content file.",
    )
    app.add_config_value(
        "llms_json_filename",
        default="docs.json",
        rebuild="",
        types=frozenset({str}),
        description="Output filename for the docs.json agent manifest.",
    )
    app.add_config_value(
        "llms_excludes",
        default=[],
        rebuild="",
        types=frozenset({list}),
        description=(
            "fnmatch patterns matched against each page's relative URL. "
            "Matched pages are excluded from all LLM outputs."
        ),
    )
    app.add_config_value(
        "llms_description_length",
        default=200,
        rebuild="",
        types=frozenset({int}),
        description="Maximum character length for page descriptions.",
    )

    with contextlib.suppress(ExtensionError):
        app.add_config_value(
            "site_url",
            default=None,
            rebuild="",
            types=frozenset({str, type(None)}),
            description=(
                "Site base URL — registered defensively; "
                "sphinx-gp-sitemap usually registers this first."
            ),
        )

    app.connect("build-finished", _write_llm_outputs)
    app.connect("html-page-context", _inject_llms_context)

    return {
        "version": _EXTENSION_VERSION,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }


def _resolve_site_url(app: Sphinx) -> str | None:
    """Resolve site URL from config, normalizing trailing slash."""
    url: str | None = getattr(app.config, "site_url", None) or getattr(
        app.config, "html_baseurl", None
    )
    if not url:
        return None
    return url if url.endswith("/") else url + "/"


def _write_llm_outputs(app: Sphinx, exception: BaseException | None) -> None:
    """Generate all enabled LLM output files at build-finished."""
    if exception is not None:
        return

    if not hasattr(app.builder, "get_target_uri"):
        return

    site_url = _resolve_site_url(app)
    if not site_url:
        logger.info(
            "sphinx-gp-llms: skipped — site_url and html_baseurl both unset",
            type="llms",
            subtype="configuration",
        )
        return

    if app.config.llms_generate_txt:
        from sphinx_gp_llms._llms_txt import write_llms_txt

        write_llms_txt(app, site_url)

    if app.config.llms_generate_full:
        from sphinx_gp_llms._llms_full_txt import write_llms_full_txt

        write_llms_full_txt(app, site_url)

    if app.config.llms_generate_json:
        from sphinx_gp_llms._docs_json import write_docs_json

        write_docs_json(app, site_url)

    if app.config.llms_generate_md_twins:
        from sphinx_gp_llms._md_twins import write_md_twins

        write_md_twins(app)


def _inject_llms_context(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: dict[str, t.Any],
    doctree: nodes.document | None,
) -> None:
    """Add LLM output link variables to the Jinja2 template context."""
    del templatename, doctree

    site_url = _resolve_site_url(app)
    if not site_url:
        return

    if app.config.llms_generate_md_twins:
        context["llms_md_url"] = pagename + ".md"
    if app.config.llms_generate_txt:
        context["llms_txt_url"] = app.config.llms_txt_filename
    if app.config.llms_generate_full:
        context["llms_full_url"] = app.config.llms_full_filename
    if app.config.llms_generate_json:
        context["llms_json_url"] = app.config.llms_json_filename
