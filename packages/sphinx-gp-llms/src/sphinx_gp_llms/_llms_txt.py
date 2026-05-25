"""Generate ``llms.txt`` — a structured Markdown index for LLM agents.

Follows the specification at https://llmstxt.org/ (Jeremy Howard,
Answer.AI, September 2024).  The file uses H1 for the project name,
a blockquote summary, and H2 sections of bulleted ``[title](url)``
links grouped by toctree caption.

Examples
--------
>>> from sphinx_gp_llms._llms_txt import write_llms_txt
>>> callable(write_llms_txt)
True
"""

from __future__ import annotations

import fnmatch
import pathlib
import typing as t

from sphinx.util.logging import getLogger

from sphinx_gp_llms._description import get_first_paragraph
from sphinx_gp_llms._toctree import extract_toctree_sections

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = getLogger(__name__)


def write_llms_txt(app: Sphinx, site_url: str) -> None:
    """Write ``llms.txt`` to the build output directory.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.
    site_url : str
        Normalized site base URL with trailing slash.

    Examples
    --------
    >>> from sphinx_gp_llms._llms_txt import write_llms_txt
    >>> callable(write_llms_txt)
    True
    """
    excludes: list[str] = list(app.config.llms_excludes)
    sections = extract_toctree_sections(app)
    lines: list[str] = []

    lines.append(f"# {app.config.project}")
    lines.append("")

    max_len: int = app.config.llms_description_length
    desc = get_first_paragraph(app, app.config.root_doc, max_len)
    if desc:
        lines.append(f"> {desc}")
        lines.append("")

    for section in sections:
        section_name = section.caption or "Documentation"
        lines.append(f"## {section_name}")
        lines.append("")
        for docname in section.docnames:
            uri = app.builder.get_target_uri(docname)
            if _is_excluded(uri, excludes):
                continue
            title = app.env.titles[docname].astext()
            url = site_url + uri
            page_desc = get_first_paragraph(
                app, docname, app.config.llms_description_length
            )
            entry = f"- [{title}]({url})"
            if page_desc:
                entry += f": {page_desc}"
            lines.append(entry)
        lines.append("")

    output = pathlib.Path(app.outdir) / app.config.llms_txt_filename
    output.write_text("\n".join(lines), encoding="utf-8")
    logger.info(
        "sphinx-gp-llms: %s generated at %s",
        app.config.llms_txt_filename,
        output,
        type="llms",
        subtype="information",
    )


def _is_excluded(uri: str, patterns: list[str]) -> bool:
    """Return True when *uri* matches any fnmatch pattern."""
    return any(fnmatch.fnmatch(uri, p) for p in patterns)
