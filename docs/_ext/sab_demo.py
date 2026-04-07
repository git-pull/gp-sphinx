"""Live badge demo directive for the sphinx-autodoc-badges docs page.

Renders every badge variant using the real ``build_badge`` /
``build_badge_group`` / ``build_toolbar`` API so the page exercises
the actual Python + CSS pipeline.
"""

from __future__ import annotations

import typing as t

from docutils import nodes
from sphinx.application import Sphinx
from sphinx.util.docutils import SphinxDirective
from sphinx_autodoc_badges import build_badge, build_badge_group, build_toolbar


class BadgeDemoDirective(SphinxDirective):
    """Insert a gallery of badge variants into the doctree."""

    has_content = False
    required_arguments = 0

    def run(self) -> list[nodes.Node]:
        """Build a gallery of every badge variant."""
        result: list[nodes.Node] = []

        def _section(title: str) -> nodes.paragraph:
            p = nodes.paragraph()
            p += nodes.strong(text=title)
            return p

        def _row(*badge_nodes: nodes.Node, label: str = "") -> nodes.paragraph:
            p = nodes.paragraph()
            for n in badge_nodes:
                p += n
                p += nodes.Text(" ")
            if label:
                p += nodes.literal(text=label)
            return p

        result.append(_section("Size variants (xs / sm / default / lg / xl)"))
        result.append(
            _row(
                build_badge("xs", size="xs", tooltip="Extra small"),
                build_badge("sm", size="sm", tooltip="Small"),
                build_badge("md", tooltip="Default (no size class)"),
                build_badge("lg", size="lg", tooltip="Large"),
                build_badge("xl", size="xl", tooltip="Extra large"),
                label='build_badge("lg", size="lg")',
            )
        )

        result.append(_section("Filled (default)"))
        result.append(
            _row(
                build_badge("label", tooltip="Default filled badge"),
                label='build_badge("label")',
            )
        )
        result.append(
            _row(
                build_badge(
                    "with icon",
                    icon="\U0001f50d",
                    tooltip="Badge with emoji icon",
                ),
                label='build_badge("with icon", icon="\\U0001f50d")',
            )
        )

        result.append(_section("Outline"))
        result.append(
            _row(
                build_badge("outline", fill="outline", tooltip="Outline variant"),
                label='build_badge("outline", fill="outline")',
            )
        )

        result.append(_section("Icon-only"))
        result.append(
            _row(
                build_badge(
                    "",
                    style="icon-only",
                    icon="\U0001f50d",
                    tooltip="Icon-only badge",
                ),
                label='build_badge("", style="icon-only", icon="\\U0001f50d")',
            )
        )

        result.append(_section("Inline-icon (inside code chips)"))
        code = nodes.literal(text="some_function()")
        inline_icon = build_badge(
            "",
            style="inline-icon",
            icon="\u270f\ufe0f",
            tooltip="Inline icon",
            tabindex="",
        )
        wrapper = nodes.paragraph()
        wrapper += inline_icon
        wrapper += code
        wrapper += nodes.Text(" ")
        wrapper += nodes.literal(
            text='build_badge("", style="inline-icon", icon="\\u270f\\ufe0f")'
        )
        result.append(wrapper)

        result.append(_section("Badge group"))
        group = build_badge_group(
            [
                build_badge("alpha", tooltip="First"),
                build_badge("beta", tooltip="Second"),
                build_badge("gamma", tooltip="Third"),
            ]
        )
        result.append(_row(group, label="build_badge_group([...badges...])"))

        result.append(_section("Toolbar (push-right in flex heading)"))
        tb = build_toolbar(
            build_badge_group(
                [
                    build_badge(
                        "readonly",
                        icon="\U0001f50d",
                        tooltip="Read-only",
                    ),
                    build_badge("tool", tooltip="MCP tool"),
                ]
            )
        )
        heading_container = nodes.container(classes=["sab-demo-toolbar-heading"])
        heading_p = nodes.paragraph()
        heading_p += nodes.strong(text="Example heading ")
        heading_p += tb
        heading_container += heading_p
        result.append(heading_container)
        result.append(_row(label="build_toolbar(build_badge_group([...]))"))

        return result


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the ``sab-badge-demo`` directive."""
    app.add_directive("sab-badge-demo", BadgeDemoDirective)
    app.add_css_file("css/sab_demo.css")
    return {"version": "0.1", "parallel_read_safe": True}
