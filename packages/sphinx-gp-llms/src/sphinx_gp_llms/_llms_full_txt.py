"""Generate ``llms-full.txt`` — concatenated full-content Markdown.

Community convention adopted by Anthropic, Cloudflare, Mintlify, and
GitBook.  Each page's source content is included under a title header
with a source URL reference, separated by ``---`` dividers.

Examples
--------
>>> from sphinx_gp_llms._llms_full_txt import write_llms_full_txt
>>> callable(write_llms_full_txt)
True
"""

from __future__ import annotations

import fnmatch
import pathlib
import typing as t

from sphinx.util.logging import getLogger

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = getLogger(__name__)


def write_llms_full_txt(app: Sphinx, site_url: str) -> None:
    """Write ``llms-full.txt`` to the build output directory.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.
    site_url : str
        Normalized site base URL with trailing slash.

    Examples
    --------
    >>> from sphinx_gp_llms._llms_full_txt import write_llms_full_txt
    >>> callable(write_llms_full_txt)
    True
    """
    excludes: list[str] = list(app.config.llms_excludes)
    parts: list[str] = []

    for docname in sorted(app.env.found_docs):
        uri = app.builder.get_target_uri(docname)
        if _is_excluded(uri, excludes):
            continue

        title_node = app.env.titles.get(docname)
        title = title_node.astext() if title_node is not None else docname
        url = site_url + uri
        source_path = pathlib.Path(app.env.doc2path(docname))

        parts.append(f"# {title}")
        parts.append(f"Source: {url}")
        parts.append("")

        try:
            content = source_path.read_text(encoding="utf-8")
            parts.append(content.rstrip())
        except (OSError, UnicodeDecodeError):
            parts.append(f"(source not available for {docname})")

        parts.append("")
        parts.append("---")
        parts.append("")

    output = pathlib.Path(app.outdir) / app.config.llms_full_filename
    output.write_text("\n".join(parts), encoding="utf-8")
    logger.info(
        "sphinx-gp-llms: %s generated at %s",
        app.config.llms_full_filename,
        output,
        type="llms",
        subtype="information",
    )


def _is_excluded(uri: str, patterns: list[str]) -> bool:
    """Return True when *uri* matches any fnmatch pattern."""
    return any(fnmatch.fnmatch(uri, p) for p in patterns)
