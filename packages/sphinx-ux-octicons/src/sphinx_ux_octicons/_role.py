"""Sphinx role implementation for ``{octicon}``."""

from __future__ import annotations

from docutils import nodes
from sphinx.util.docutils import SphinxRole

from sphinx_ux_octicons._nodes import OcticonNode
from sphinx_ux_octicons._render import render_octicon


class OcticonRole(SphinxRole):
    """Inline role that emits a GitHub Octicon SVG.

    The role text accepts up to three ``;``-separated arguments:
    ``name``, ``name;height``, or ``name;height;classes``. ``height`` is a
    CSS length (``1em``, ``24px``, ``1.5rem``); ``classes`` is a
    whitespace-separated list of extra CSS classes.

    Emits an :class:`OcticonNode` whose HTML visitor writes the inline
    SVG and skips descent, while non-HTML builders (text, man, LaTeX)
    fall back via MRO to ``visit_inline`` and render the icon name as
    visible text.

    Examples
    --------
    >>> from sphinx_ux_octicons._role import OcticonRole
    >>> callable(OcticonRole)
    True
    >>> issubclass(OcticonRole, SphinxRole)
    True
    """

    def run(self) -> tuple[list[nodes.Node], list[nodes.system_message]]:
        """Parse the role text and emit the icon node.

        Returns
        -------
        tuple[list[nodes.Node], list[nodes.system_message]]
            ``([node], [])`` on success, ``([problematic], [message])`` on
            parse failure.

        Examples
        --------
        >>> from sphinx_ux_octicons._role import OcticonRole
        >>> OcticonRole.run.__qualname__
        'OcticonRole.run'
        """
        values = self.text.split(";")
        name = values[0].strip()
        height = values[1].strip() if len(values) >= 2 and values[1].strip() else "1em"
        classes = tuple(values[2].split()) if len(values) >= 3 else ()
        try:
            svg = render_octicon(name, height=height, classes=classes)
        except (KeyError, ValueError) as exc:
            message = self.inliner.reporter.error(
                f"invalid octicon {self.text!r}: {exc}",
                line=self.lineno,
            )
            problematic = self.inliner.problematic(
                self.rawtext,
                self.rawtext,
                message,
            )
            return [problematic], [message]

        node = OcticonNode(name, svg_markup=svg)
        self.set_source_info(node)
        return [node], []
