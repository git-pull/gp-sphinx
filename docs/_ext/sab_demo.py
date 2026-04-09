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
from sphinx_autodoc_badges import SAB, build_badge, build_badge_group, build_toolbar


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

        # ── Structural variants ──────────────────────────────────

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

        # ── Python API type palette ──────────────────────────────

        result.append(_section("Python API types (sab-type-*)"))
        py_types = [
            ("function", SAB.TYPE_FUNCTION, "Python function"),
            ("class", SAB.TYPE_CLASS, "Python class"),
            ("method", SAB.TYPE_METHOD, "Instance method"),
            ("property", SAB.TYPE_PROPERTY, "Python property"),
            ("attribute", SAB.TYPE_ATTRIBUTE, "Class or instance attribute"),
            ("data", SAB.TYPE_DATA, "Module-level data"),
            ("exception", SAB.TYPE_EXCEPTION, "Exception class"),
            ("type alias", SAB.TYPE_TYPEALIAS, "Type alias"),
            ("module", SAB.TYPE_MODULE, "Python module"),
        ]
        type_row = nodes.paragraph()
        for label, css_class, tooltip in py_types:
            type_row += build_badge(
                label,
                tooltip=tooltip,
                classes=[SAB.BADGE, SAB.BADGE_TYPE, css_class],
            )
            type_row += nodes.Text(" ")
        result.append(type_row)

        result.append(_section("Python API types — dense variant (sab-dense)"))
        type_dense_row = nodes.paragraph()
        for label, css_class, tooltip in py_types:
            type_dense_row += build_badge(
                label,
                tooltip=tooltip,
                classes=[SAB.BADGE, SAB.DENSE, SAB.BADGE_TYPE, css_class],
            )
            type_dense_row += nodes.Text(" ")
        result.append(type_dense_row)

        result.append(_section("Python API modifiers (sab-mod-*, outlined)"))
        py_mods = [
            ("async", SAB.MOD_ASYNC, "Asynchronous"),
            ("classmethod", SAB.MOD_CLASSMETHOD, "Class method"),
            ("staticmethod", SAB.MOD_STATICMETHOD, "Static method"),
            ("abstract", SAB.MOD_ABSTRACT, "Abstract"),
            ("final", SAB.MOD_FINAL, "Final"),
        ]
        mod_row = nodes.paragraph()
        for label, css_class, tooltip in py_mods:
            mod_row += build_badge(
                label,
                tooltip=tooltip,
                classes=[SAB.BADGE, SAB.BADGE_MOD, css_class],
                fill="outline",
            )
            mod_row += nodes.Text(" ")
        result.append(mod_row)

        result.append(_section("Python API modifiers — dense variant"))
        mod_dense_row = nodes.paragraph()
        for label, css_class, tooltip in py_mods:
            mod_dense_row += build_badge(
                label,
                tooltip=tooltip,
                classes=[SAB.BADGE, SAB.DENSE, SAB.BADGE_MOD, css_class],
                fill="outline",
            )
            mod_dense_row += nodes.Text(" ")
        result.append(mod_dense_row)

        # ── pytest fixture palette ───────────────────────────────

        result.append(_section("pytest fixture types (sab-type-fixture)"))
        result.append(
            _row(
                build_badge(
                    "fixture",
                    tooltip="pytest fixture",
                    classes=[SAB.BADGE, SAB.BADGE_FIXTURE, SAB.TYPE_FIXTURE],
                ),
                label="SAB.TYPE_FIXTURE — standard",
            )
        )
        result.append(
            _row(
                build_badge(
                    "fixture",
                    tooltip="pytest fixture",
                    classes=[SAB.BADGE, SAB.DENSE, SAB.BADGE_FIXTURE, SAB.TYPE_FIXTURE],
                ),
                label="SAB.TYPE_FIXTURE — dense",
            )
        )

        result.append(_section("pytest fixture scopes (sab-scope-*)"))
        scope_row = nodes.paragraph()
        scope_dense_row = nodes.paragraph()
        for scope in ("session", "module", "class"):
            scope_row += build_badge(
                scope,
                tooltip=f"Scope: {scope}",
                classes=[SAB.BADGE, SAB.BADGE_SCOPE, SAB.scope(scope)],
            )
            scope_row += nodes.Text(" ")
            scope_dense_row += build_badge(
                scope,
                tooltip=f"Scope: {scope}",
                classes=[SAB.BADGE, SAB.DENSE, SAB.BADGE_SCOPE, SAB.scope(scope)],
            )
            scope_dense_row += nodes.Text(" ")
        result.append(scope_row)
        result.append(scope_dense_row)

        result.append(_section("pytest fixture kinds / states (outlined)"))
        state_row = nodes.paragraph()
        state_dense_row = nodes.paragraph()
        states = [
            ("factory", SAB.STATE_FACTORY, "Factory"),
            ("override", SAB.STATE_OVERRIDE, "Override hook"),
            ("auto", SAB.STATE_AUTOUSE, "Autouse"),
            ("deprecated", SAB.STATE_DEPRECATED, "Deprecated"),
        ]
        for label, css_class, tooltip in states:
            fill = "filled" if label == "deprecated" else "outline"
            state_row += build_badge(
                label,
                tooltip=tooltip,
                classes=[SAB.BADGE, SAB.BADGE_STATE, css_class],
                fill=fill,
            )
            state_row += nodes.Text(" ")
            state_dense_row += build_badge(
                label,
                tooltip=tooltip,
                classes=[SAB.BADGE, SAB.DENSE, SAB.BADGE_STATE, css_class],
                fill=fill,
            )
            state_dense_row += nodes.Text(" ")
        result.append(state_row)
        result.append(state_dense_row)

        # ── Sphinx config palette ────────────────────────────────

        result.append(_section("Sphinx config (sab-type-config / sab-mod-rebuild)"))
        result.append(
            _row(
                build_badge(
                    "config",
                    tooltip="Sphinx config value",
                    classes=[SAB.TYPE_CONFIG],
                ),
                build_badge(
                    "env",
                    tooltip="Rebuild mode: env",
                    classes=[SAB.MOD_REBUILD],
                    fill="outline",
                ),
                build_badge(
                    "html",
                    tooltip="Rebuild mode: html",
                    classes=[SAB.MOD_REBUILD],
                    fill="outline",
                ),
                label="standard",
            )
        )
        result.append(
            _row(
                build_badge(
                    "config",
                    tooltip="Sphinx config value",
                    classes=[SAB.BADGE, SAB.DENSE, SAB.TYPE_CONFIG],
                ),
                build_badge(
                    "env",
                    tooltip="Rebuild mode: env",
                    classes=[SAB.BADGE, SAB.DENSE, SAB.MOD_REBUILD],
                    fill="outline",
                ),
                build_badge(
                    "html",
                    tooltip="Rebuild mode: html",
                    classes=[SAB.BADGE, SAB.DENSE, SAB.MOD_REBUILD],
                    fill="outline",
                ),
                label="dense",
            )
        )

        # ── docutils palette ─────────────────────────────────────

        result.append(_section("docutils (sab-type-directive / role / option)"))
        result.append(
            _row(
                build_badge(
                    "directive",
                    tooltip="Docutils directive",
                    classes=[SAB.TYPE_DIRECTIVE],
                ),
                build_badge(
                    "role",
                    tooltip="Docutils role",
                    classes=[SAB.TYPE_ROLE],
                ),
                build_badge(
                    "option",
                    tooltip="Docutils option",
                    classes=[SAB.TYPE_OPTION],
                ),
                label="standard",
            )
        )
        result.append(
            _row(
                build_badge(
                    "directive",
                    tooltip="Docutils directive",
                    classes=[SAB.BADGE, SAB.DENSE, SAB.TYPE_DIRECTIVE],
                ),
                build_badge(
                    "role",
                    tooltip="Docutils role",
                    classes=[SAB.BADGE, SAB.DENSE, SAB.TYPE_ROLE],
                ),
                build_badge(
                    "option",
                    tooltip="Docutils option",
                    classes=[SAB.BADGE, SAB.DENSE, SAB.TYPE_OPTION],
                ),
                label="dense",
            )
        )

        return result


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the ``sab-badge-demo`` directive."""
    app.add_directive("sab-badge-demo", BadgeDemoDirective)
    app.add_css_file("css/sab_demo.css")
    return {"version": "0.1", "parallel_read_safe": True}
