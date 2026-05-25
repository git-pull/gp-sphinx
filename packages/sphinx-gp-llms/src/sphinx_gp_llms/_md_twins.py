"""Generate per-page ``.md`` twin files alongside HTML output.

Implements the per-page Markdown endpoint convention popularized by
Mintlify, Cloudflare ("Markdown for Agents"), Stripe, and Vercel.
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
    excludes: list[str] = list(app.config.llms_excludes)
    outdir = pathlib.Path(app.outdir)
    count = 0

    for docname in sorted(app.env.found_docs):
        uri = app.builder.get_target_uri(docname)
        if _is_excluded(uri, excludes):
            continue

        source_path = pathlib.Path(app.env.doc2path(docname))
        if not source_path.exists():
            continue

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
