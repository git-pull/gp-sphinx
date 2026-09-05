"""Generate per-page ``.md`` twin files alongside HTML output.

Implements the per-page Markdown endpoint convention popularized by
Cloudflare ("Markdown for Agents"), Stripe, Anthropic, and Vercel.
Each HTML page at ``/path/page.html`` gets a Markdown sibling at
``/path/page.md`` containing the original source content.

Examples
--------
>>> from sphinx_gp_llms._md_twins import write_md_twins
>>> callable(write_md_twins)
True
"""

from __future__ import annotations

import fnmatch
import pathlib
import shutil
import typing as t

from sphinx.util.logging import getLogger

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = getLogger(__name__)


def has_md_twin(app: Sphinx, docname: str) -> bool:
    """Return whether :func:`write_md_twins` writes a twin for *docname*.

    The footer link and the twin writer must agree: a page linked to a
    ``.md`` sibling that was never written is a 404 the build cannot see,
    because the link is rendered from the template rather than resolved as
    a reference.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.
    docname : str
        Document name, as passed to ``html-page-context``.

    Returns
    -------
    bool
        ``True`` when a twin exists for *docname*.

    Examples
    --------
    >>> from sphinx_gp_llms._md_twins import has_md_twin
    >>> callable(has_md_twin)
    True
    """
    if docname not in app.env.found_docs:
        return False
    if _is_excluded(
        app.builder.get_target_uri(docname), list(app.config.llms_excludes)
    ):
        return False
    return pathlib.Path(app.env.doc2path(docname)).exists()


def write_md_twins(app: Sphinx) -> None:
    """Copy source files as ``.md`` siblings in the build output directory.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.

    Examples
    --------
    >>> from sphinx_gp_llms._md_twins import write_md_twins
    >>> callable(write_md_twins)
    True
    """
    outdir = pathlib.Path(app.outdir)
    count = 0

    for docname in sorted(app.env.found_docs):
        if not has_md_twin(app, docname):
            continue

        source_path = pathlib.Path(app.env.doc2path(docname))
        target = outdir / (docname + ".md")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target)
        count += 1

    logger.info(
        "sphinx-gp-llms: %d .md twin files written",
        count,
        type="llms",
        subtype="information",
    )


def _is_excluded(uri: str, patterns: list[str]) -> bool:
    """Return True when *uri* matches any fnmatch pattern."""
    return any(fnmatch.fnmatch(uri, p) for p in patterns)
