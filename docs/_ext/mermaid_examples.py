"""Embed the committed sphinx-gp-mermaid example diagrams into the docs.

Reads the gallery under ``packages/sphinx-gp-mermaid/examples/`` and, per
diagram, emits its ``.mmd`` source alongside the light and dark SVG the
extension renders it to, wrapped in the extension's ``gp-sphinx-mermaid``
figure markup so furo's ``body[data-theme]`` toggle applies.

The committed SVGs are inlined verbatim (they are already id/size normalized),
so the docs build needs no mermaid-cli toolchain and never shells out to
``mmdc``. Regenerate the SVGs with
``packages/sphinx-gp-mermaid/examples/generate.py``.
"""

from __future__ import annotations

import html
import pathlib
import typing as t

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

_EXAMPLES_DIR = (
    pathlib.Path(__file__).resolve().parents[2]
    / "packages"
    / "sphinx-gp-mermaid"
    / "examples"
)

#: Display titles for stems whose title-cased form reads poorly.
_TITLES: dict[str, str] = {
    "er": "Entity relationship",
    "gitgraph": "Git graph",
}


def _title_for(stem: str) -> str:
    """Return a display title for an example stem.

    >>> _title_for("er")
    'Entity relationship'
    >>> _title_for("flowchart")
    'Flowchart'
    """
    return _TITLES.get(stem, stem.replace("_", " ").capitalize())


def _figure_markup(light: str, dark: str, *, alt: str) -> str:
    """Wrap a light/dark SVG pair in the extension's figure markup.

    Mirrors ``sphinx_gp_mermaid``'s HTML visitor so furo's
    ``body[data-theme]`` rules toggle the committed variants with no script.

    >>> markup = _figure_markup("<svg/>", "<svg/>", alt="A flow")
    >>> 'class="gp-sphinx-mermaid"' in markup
    True
    >>> markup.count("gp-sphinx-mermaid__variant--theme-")
    2
    """
    aria = f' aria-label="{html.escape(alt, quote=True)}"'
    return "".join(
        [
            '<figure class="gp-sphinx-mermaid">',
            (
                '<div class="gp-sphinx-mermaid__variant '
                f'gp-sphinx-mermaid__variant--theme-light" role="img"{aria}>'
                f"{light}</div>"
            ),
            (
                '<div class="gp-sphinx-mermaid__variant '
                'gp-sphinx-mermaid__variant--theme-dark" role="img" '
                f'aria-hidden="true">{dark}</div>'
            ),
            "</figure>",
        ],
    )


class MermaidExamplesDirective(SphinxDirective):
    """Insert the committed mermaid example gallery into the doctree."""

    has_content = False
    required_arguments = 0

    def run(self) -> list[nodes.Node]:
        """Emit each example's source and its dual-theme rendered figure."""
        src_dir = _EXAMPLES_DIR / "src"
        rendered_dir = _EXAMPLES_DIR / "rendered"
        result: list[nodes.Node] = []
        for source_path in sorted(src_dir.glob("*.mmd")):
            stem = source_path.stem
            light_path = rendered_dir / f"{stem}.light.svg"
            dark_path = rendered_dir / f"{stem}.dark.svg"
            for path in (source_path, light_path, dark_path):
                self.env.note_dependency(str(path))
            source = source_path.read_text(encoding="utf-8").rstrip("\n")
            light = light_path.read_text(encoding="utf-8")
            dark = dark_path.read_text(encoding="utf-8")
            title = _title_for(stem)

            heading = nodes.rubric()
            heading += nodes.Text(title)
            result.append(heading)
            result.append(nodes.literal_block(source, source))
            result.append(
                nodes.raw("", _figure_markup(light, dark, alt=title), format="html"),
            )
        return result


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the ``mermaid-examples`` directive.

    Parameters
    ----------
    app : Sphinx
        Sphinx application instance.

    Returns
    -------
    ExtensionMetadata
        Extension metadata marking the directive parallel-read safe.

    Examples
    --------
    >>> from mermaid_examples import setup
    >>> callable(setup)
    True
    """
    app.add_directive("mermaid-examples", MermaidExamplesDirective)
    return {"parallel_read_safe": True}
