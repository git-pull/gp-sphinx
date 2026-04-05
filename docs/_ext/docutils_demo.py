"""Synthetic directives and roles for live autodoc-docutils demos.

Examples
--------
>>> DemoBadgeDirective.required_arguments
1
>>> demo_badge_role.content
True
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from docutils.parsers.rst import Directive, directives

if t.TYPE_CHECKING:
    from docutils.parsers.rst.states import Inliner


class DemoBadgeDirective(Directive):
    """Render a short badge-like paragraph for directive demos."""

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    has_content = False
    option_spec: t.ClassVar[dict[str, t.Any]] = {"class": directives.class_option}

    def run(self) -> list[nodes.Node]:
        """Return a paragraph node for the requested badge label."""
        paragraph = nodes.paragraph(text=f"demo badge: {self.arguments[0]}")
        paragraph["classes"].extend(self.options.get("class", []))
        return [paragraph]


class DemoCalloutDirective(Directive):
    """Render a simple titled container for directive demos."""

    required_arguments = 0
    optional_arguments = 0
    has_content = True
    option_spec: t.ClassVar[dict[str, t.Any]] = {
        "title": directives.unchanged_required,
    }

    def run(self) -> list[nodes.Node]:
        """Return a container with an optional title and paragraph content."""
        container = nodes.container()
        if "title" in self.options:
            container += nodes.strong(text=self.options["title"])
        if self.content:
            container += nodes.paragraph(text=" ".join(self.content))
        return [container]


def demo_badge_role(
    name: str,
    rawtext: str,
    text: str,
    lineno: int,
    inliner: Inliner | None,
    options: dict[str, t.Any] | None = None,
    content: list[str] | None = None,
) -> tuple[list[nodes.Node], list[nodes.system_message]]:
    """Return a literal node with badge-style classes.

    Examples
    --------
    >>> nodes_, messages = demo_badge_role(
    ...     "demo-badge",
    ...     ":demo-badge:`Alpha`",
    ...     "Alpha",
    ...     1,
    ...     None,
    ... )
    >>> nodes_[0].astext()
    'Alpha'
    >>> messages
    []
    """
    merged_options = options or {}
    classes = ["demo-badge"]
    classes.extend(merged_options.get("class", []))
    return [nodes.literal(rawtext, text, classes=classes)], []


demo_badge_role.options = {"class": directives.class_option}
demo_badge_role.content = True
