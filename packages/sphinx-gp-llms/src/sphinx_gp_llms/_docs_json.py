"""Generate ``docs.json`` — an agent-oriented documentation manifest.

Follows the agent-manifest convention established by Lakebed (Ping,
``github.com/pingdotgg/span``).  The manifest provides structured
metadata including ``agentEntrypoints``, a flat ``pages[]`` array with
per-page ``markdownUrl`` and ``headings[]`` outlines.

Examples
--------
>>> from sphinx_gp_llms._docs_json import write_docs_json
>>> callable(write_docs_json)
True
"""

from __future__ import annotations

import fnmatch
import json
import pathlib
import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx.util.logging import getLogger

from sphinx_gp_llms._description import get_first_paragraph
from sphinx_gp_llms._toctree import extract_toctree_sections

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx

logger = getLogger(__name__)


class _Heading(t.TypedDict):
    id: str
    level: int
    text: str


class _Page(t.TypedDict):
    title: str
    description: str
    section: str
    url: str
    markdownUrl: str
    headings: list[_Heading]


class _AgentEntrypoints(t.TypedDict):
    manifest: str
    llms: str
    llmsFull: str


class _DocsManifest(t.TypedDict):
    name: str
    url: str
    description: str
    sourceRepository: str
    agentEntrypoints: _AgentEntrypoints
    pages: list[_Page]


def write_docs_json(app: Sphinx, site_url: str) -> None:
    """Write ``docs.json`` to the build output directory.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.
    site_url : str
        Normalized site base URL with trailing slash.

    Examples
    --------
    >>> from sphinx_gp_llms._docs_json import write_docs_json
    >>> callable(write_docs_json)
    True
    """
    excludes: list[str] = list(app.config.llms_excludes)
    sections = extract_toctree_sections(app)

    section_map: dict[str, str] = {}
    for section in sections:
        caption = section.caption or "Documentation"
        for docname in section.docnames:
            section_map[docname] = caption

    pages: list[_Page] = []
    for docname in sorted(app.env.found_docs):
        uri = app.builder.get_target_uri(docname)
        if _is_excluded(uri, excludes):
            continue

        title = app.env.titles[docname].astext()
        desc = get_first_paragraph(app, docname, app.config.llms_description_length)
        headings = _extract_headings(app, docname)

        pages.append(
            _Page(
                title=title,
                description=desc,
                section=section_map.get(docname, ""),
                url="/" + uri,
                markdownUrl="/" + docname + ".md",
                headings=headings,
            )
        )

    source_repo = _get_source_repository(app)
    root_desc = get_first_paragraph(
        app, app.config.root_doc, app.config.llms_description_length
    )

    manifest = _DocsManifest(
        name=app.config.project,
        url=site_url.rstrip("/"),
        description=root_desc,
        sourceRepository=source_repo,
        agentEntrypoints=_AgentEntrypoints(
            manifest="/" + app.config.llms_json_filename,
            llms="/" + app.config.llms_txt_filename,
            llmsFull="/" + app.config.llms_full_filename,
        ),
        pages=pages,
    )

    output = pathlib.Path(app.outdir) / app.config.llms_json_filename
    output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info(
        "sphinx-gp-llms: %s generated at %s",
        app.config.llms_json_filename,
        output,
        type="llms",
        subtype="information",
    )


def _extract_headings(app: Sphinx, docname: str) -> list[_Heading]:
    """Extract heading id/level/text from the table-of-contents tree."""
    toc = app.env.tocs.get(docname)
    if toc is None:
        return []
    headings: list[_Heading] = []
    _walk_toc(toc, level=1, headings=headings)
    return headings


def _walk_toc(
    node: nodes.Node,
    level: int,
    headings: list[_Heading],
) -> None:
    """Recursively walk a toc bullet_list, collecting headings."""
    if isinstance(node, nodes.bullet_list):
        for item in node.children:
            _walk_toc(item, level, headings)
    elif isinstance(node, nodes.list_item):
        for child in node.children:
            if isinstance(child, addnodes.compact_paragraph):
                for ref in child.findall(nodes.reference):
                    anchor = ref.get("anchorname", "")
                    text = ref.astext()
                    heading_id = anchor.lstrip("#") if anchor else ""
                    if text:
                        headings.append(_Heading(id=heading_id, level=level, text=text))
            elif isinstance(child, nodes.bullet_list):
                _walk_toc(child, level + 1, headings)


def _get_source_repository(app: Sphinx) -> str:
    """Read source_repository from theme options."""
    theme_opts = getattr(app.config, "html_theme_options", None)
    if isinstance(theme_opts, dict):
        return str(theme_opts.get("source_repository", ""))
    return ""


def _is_excluded(uri: str, patterns: list[str]) -> bool:
    """Return True when *uri* matches any fnmatch pattern."""
    return any(fnmatch.fnmatch(uri, p) for p in patterns)
