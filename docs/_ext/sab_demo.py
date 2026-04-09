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

        # ── All structural variants ──────────────────────────────

        result.append(_section("No icon"))
        result.append(
            _row(
                build_badge("label", tooltip="Plain filled badge"),
                label='build_badge("label")',
            )
        )

        result.append(_section("With icon — left (default, sab-badge[data-icon])"))
        result.append(
            _row(
                build_badge("readonly", icon="\U0001f50d", tooltip="Icon on left"),
                build_badge(
                    "mutating",
                    icon="\u270f\ufe0f",
                    tooltip="Icon on left",
                    classes=[SAB.TYPE_CLASS],
                ),
                label='build_badge("readonly", icon="🔍")',
            )
        )

        result.append(_section("With icon — right (sab-icon-right)"))
        result.append(
            _row(
                build_badge(
                    "readonly",
                    icon="\U0001f50d",
                    tooltip="Icon on right",
                    classes=[SAB.ICON_RIGHT],
                ),
                build_badge(
                    "mutating",
                    icon="\u270f\ufe0f",
                    tooltip="Icon on right",
                    classes=[SAB.ICON_RIGHT, SAB.TYPE_CLASS],
                ),
                label='build_badge("readonly", icon="🔍", classes=[SAB.ICON_RIGHT])',
            )
        )

        result.append(_section("Icon-only — 16x16 coloured box (sab-icon-only)"))
        result.append(
            _row(
                build_badge(
                    "",
                    style="icon-only",
                    icon="\U0001f50d",
                    tooltip="Icon-only (no text)",
                ),
                build_badge(
                    "",
                    style="icon-only",
                    icon="\u270f\ufe0f",
                    tooltip="Icon-only mutating",
                    classes=[SAB.TYPE_CLASS],
                ),
                build_badge(
                    "",
                    style="icon-only",
                    icon="\U0001f4a3",
                    tooltip="Icon-only destructive",
                    classes=[SAB.TYPE_EXCEPTION],
                ),
                label='build_badge("", style="icon-only", icon="🔍")',
            )
        )

        result.append(
            _section("Inline-icon — bare emoji inside code chip (sab-inline-icon)")
        )
        wrapper = nodes.paragraph()
        wrapper += build_badge(
            "",
            style="inline-icon",
            icon="\u270f\ufe0f",
            tooltip="Inline icon",
            tabindex="",
        )
        wrapper += nodes.literal(text="some_function()")
        wrapper += nodes.Text("  ")
        wrapper += build_badge(
            "",
            style="inline-icon",
            icon="\U0001f50d",
            tooltip="Inline icon search",
            tabindex="",
        )
        wrapper += nodes.literal(text="other_func()")
        wrapper += nodes.Text("  ")
        wrapper += nodes.literal(text='build_badge("", style="inline-icon", icon="✏️")')
        result.append(wrapper)

        result.append(_section("Outline (sab-outline)"))
        result.append(
            _row(
                build_badge("outline", fill="outline", tooltip="Outline, no bg"),
                build_badge(
                    "outline + icon",
                    icon="\U0001f50d",
                    fill="outline",
                    tooltip="Outline with icon left",
                ),
                build_badge(
                    "outline + icon right",
                    icon="\U0001f50d",
                    fill="outline",
                    classes=[SAB.ICON_RIGHT],
                    tooltip="Outline with icon right",
                ),
                label='build_badge("outline", fill="outline")',
            )
        )

        result.append(
            _section("Dense (sab-dense) — compact bordered, dotted underline")
        )
        result.append(
            _row(
                build_badge(
                    "dense",
                    tooltip="Dense, no icon",
                    classes=[SAB.DENSE, SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "dense + icon left",
                    icon="\U0001f50d",
                    tooltip="Dense with icon left",
                    classes=[SAB.DENSE, SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "dense + icon right",
                    icon="\U0001f50d",
                    tooltip="Dense with icon right",
                    classes=[SAB.DENSE, SAB.ICON_RIGHT, SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "",
                    style="icon-only",
                    icon="\U0001f50d",
                    tooltip="Dense icon-only (icon-only overrides display)",
                    classes=[SAB.TYPE_FUNCTION],
                ),
                label="SAB.DENSE + icon variants",
            )
        )

        result.append(_section("Dense + outline"))
        result.append(
            _row(
                build_badge(
                    "dense outline",
                    fill="outline",
                    classes=[SAB.DENSE],
                    tooltip="Dense outline",
                ),
                build_badge(
                    "dense outline + icon left",
                    icon="\U0001f50d",
                    fill="outline",
                    classes=[SAB.DENSE],
                    tooltip="Dense outline with icon left",
                ),
                build_badge(
                    "dense outline + icon right",
                    icon="\U0001f50d",
                    fill="outline",
                    classes=[SAB.DENSE, SAB.ICON_RIGHT],
                    tooltip="Dense outline with icon right",
                ),
                label="SAB.DENSE + outline",
            )
        )

        # ── All sizes ────────────────────────────────────────────

        result.append(_section("All sizes — standard pill"))
        result.append(
            _row(
                build_badge(
                    "xxs",
                    size="xxs",
                    tooltip="Extra-extra small",
                    classes=[SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "xxs+icon",
                    size="xxs",
                    icon="\U0001f50d",
                    tooltip="Extra-extra small with icon",
                    classes=[SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "xs",
                    size="xs",
                    tooltip="Extra small",
                    classes=[SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "xs+icon",
                    size="xs",
                    icon="\U0001f50d",
                    tooltip="Extra small with icon",
                    classes=[SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "sm",
                    size="sm",
                    tooltip="Small",
                    classes=[SAB.TYPE_CLASS],
                ),
                build_badge(
                    "sm+icon",
                    size="sm",
                    icon="\U0001f50d",
                    tooltip="Small with icon",
                    classes=[SAB.TYPE_CLASS],
                ),
                build_badge(
                    "md",
                    size="md",
                    tooltip="Medium (alias: default)",
                    classes=[SAB.TYPE_METHOD],
                ),
                build_badge(
                    "md+icon",
                    size="md",
                    icon="\U0001f50d",
                    tooltip="Medium with icon",
                    classes=[SAB.TYPE_METHOD],
                ),
                build_badge(
                    "default", tooltip="Default size (= md)", classes=[SAB.TYPE_METHOD]
                ),
                build_badge(
                    "default+icon",
                    icon="\U0001f50d",
                    tooltip="Default with icon (= md)",
                    classes=[SAB.TYPE_METHOD],
                ),
                build_badge(
                    "lg",
                    size="lg",
                    tooltip="Large",
                    classes=[SAB.TYPE_FIXTURE],
                ),
                build_badge(
                    "lg+icon",
                    size="lg",
                    icon="\U0001f50d",
                    tooltip="Large with icon",
                    classes=[SAB.TYPE_FIXTURE],
                ),
                build_badge(
                    "xl",
                    size="xl",
                    tooltip="Extra large",
                    classes=[SAB.TYPE_CONFIG],
                ),
                build_badge(
                    "xl+icon",
                    size="xl",
                    icon="\U0001f50d",
                    tooltip="Extra large with icon",
                    classes=[SAB.TYPE_CONFIG],
                ),
                label="xxs / xs / sm / md / default / lg / xl",
            )
        )

        result.append(_section("All sizes — dense"))
        result.append(
            _row(
                build_badge(
                    "xxs",
                    size="xxs",
                    tooltip="Extra-extra small dense",
                    classes=[SAB.DENSE, SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "xxs+icon",
                    size="xxs",
                    icon="\U0001f50d",
                    tooltip="Extra-extra small dense + icon",
                    classes=[SAB.DENSE, SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "xs",
                    size="xs",
                    tooltip="Extra small dense",
                    classes=[SAB.DENSE, SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "xs+icon",
                    size="xs",
                    icon="\U0001f50d",
                    tooltip="Extra small dense + icon",
                    classes=[SAB.DENSE, SAB.TYPE_FUNCTION],
                ),
                build_badge(
                    "sm",
                    size="sm",
                    tooltip="Small dense",
                    classes=[SAB.DENSE, SAB.TYPE_CLASS],
                ),
                build_badge(
                    "sm+icon",
                    size="sm",
                    icon="\U0001f50d",
                    tooltip="Small dense + icon",
                    classes=[SAB.DENSE, SAB.TYPE_CLASS],
                ),
                build_badge(
                    "md",
                    size="md",
                    tooltip="Medium dense (alias: default)",
                    classes=[SAB.DENSE, SAB.TYPE_METHOD],
                ),
                build_badge(
                    "md+icon",
                    size="md",
                    icon="\U0001f50d",
                    tooltip="Medium dense + icon",
                    classes=[SAB.DENSE, SAB.TYPE_METHOD],
                ),
                build_badge(
                    "default",
                    tooltip="Default dense (= md)",
                    classes=[SAB.DENSE, SAB.TYPE_METHOD],
                ),
                build_badge(
                    "default+icon",
                    icon="\U0001f50d",
                    tooltip="Default dense + icon (= md)",
                    classes=[SAB.DENSE, SAB.TYPE_METHOD],
                ),
                build_badge(
                    "lg",
                    size="lg",
                    tooltip="Large dense",
                    classes=[SAB.DENSE, SAB.TYPE_FIXTURE],
                ),
                build_badge(
                    "lg+icon",
                    size="lg",
                    icon="\U0001f50d",
                    tooltip="Large dense + icon",
                    classes=[SAB.DENSE, SAB.TYPE_FIXTURE],
                ),
                build_badge(
                    "xl",
                    size="xl",
                    tooltip="Extra large dense",
                    classes=[SAB.DENSE, SAB.TYPE_CONFIG],
                ),
                build_badge(
                    "xl+icon",
                    size="xl",
                    icon="\U0001f50d",
                    tooltip="Extra large dense + icon",
                    classes=[SAB.DENSE, SAB.TYPE_CONFIG],
                ),
                label="xxs / xs / sm / md / default / lg / xl (sab-dense)",
            )
        )

        # ── Icon positions with colour — representative rows ──────

        result.append(
            _section("Icon positions — standard (no icon / left / right / icon-only)")
        )
        for colour_label, colour_class, icon, colour_tooltip in [
            ("function", SAB.TYPE_FUNCTION, "\U0001f4e6", "Python function"),
            ("fixture", SAB.TYPE_FIXTURE, "\U0001f9ea", "pytest fixture"),
            ("config", SAB.TYPE_CONFIG, "\u2699\ufe0f", "Sphinx config"),
            ("directive", SAB.TYPE_DIRECTIVE, "\U0001f4d1", "Docutils directive"),
        ]:
            row = nodes.paragraph()
            row += build_badge(
                colour_label,
                tooltip=f"{colour_tooltip} — no icon",
                classes=[SAB.BADGE_TYPE, colour_class],
            )
            row += nodes.Text("  ")
            row += build_badge(
                colour_label,
                icon=icon,
                tooltip=f"{colour_tooltip} — icon left",
                classes=[SAB.BADGE_TYPE, colour_class],
            )
            row += nodes.Text("  ")
            row += build_badge(
                colour_label,
                icon=icon,
                tooltip=f"{colour_tooltip} — icon right",
                classes=[SAB.BADGE_TYPE, colour_class, SAB.ICON_RIGHT],
            )
            row += nodes.Text("  ")
            row += build_badge(
                "",
                style="icon-only",
                icon=icon,
                tooltip=f"{colour_tooltip} — icon-only",
                classes=[colour_class],
            )
            row += nodes.Text("    ")
            row += nodes.literal(
                text=f"{colour_label}: none / left / right / icon-only"
            )
            result.append(row)

        result.append(_section("Icon positions — dense"))
        for colour_label, colour_class, icon, colour_tooltip in [
            ("function", SAB.TYPE_FUNCTION, "\U0001f4e6", "Python function"),
            ("fixture", SAB.TYPE_FIXTURE, "\U0001f9ea", "pytest fixture"),
            ("config", SAB.TYPE_CONFIG, "\u2699\ufe0f", "Sphinx config"),
            ("directive", SAB.TYPE_DIRECTIVE, "\U0001f4d1", "Docutils directive"),
        ]:
            row = nodes.paragraph()
            row += build_badge(
                colour_label,
                tooltip=f"{colour_tooltip} dense — no icon",
                classes=[SAB.DENSE, SAB.BADGE_TYPE, colour_class],
            )
            row += nodes.Text("  ")
            row += build_badge(
                colour_label,
                icon=icon,
                tooltip=f"{colour_tooltip} dense — icon left",
                classes=[SAB.DENSE, SAB.BADGE_TYPE, colour_class],
            )
            row += nodes.Text("  ")
            row += build_badge(
                colour_label,
                icon=icon,
                tooltip=f"{colour_tooltip} dense — icon right",
                classes=[
                    SAB.DENSE,
                    SAB.BADGE_TYPE,
                    colour_class,
                    SAB.ICON_RIGHT,
                ],
            )
            row += nodes.Text("    ")
            row += nodes.literal(text=f"{colour_label} (dense): none / left / right")
            result.append(row)

        # ── Badge group ──────────────────────────────────────────

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

        # ── Python API type palette (standard + dense) ───────────

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
                classes=[SAB.BADGE_TYPE, css_class],
            )
            type_row += nodes.Text(" ")
        result.append(type_row)

        result.append(_section("Python API types — dense variant (sab-dense)"))
        type_dense_row = nodes.paragraph()
        for label, css_class, tooltip in py_types:
            type_dense_row += build_badge(
                label,
                tooltip=tooltip,
                classes=[SAB.DENSE, SAB.BADGE_TYPE, css_class],
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
                classes=[SAB.BADGE_MOD, css_class],
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
                classes=[SAB.DENSE, SAB.BADGE_MOD, css_class],
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
                    classes=[SAB.BADGE_FIXTURE, SAB.TYPE_FIXTURE],
                ),
                label="SAB.TYPE_FIXTURE — standard",
            )
        )
        result.append(
            _row(
                build_badge(
                    "fixture",
                    tooltip="pytest fixture",
                    classes=[SAB.DENSE, SAB.BADGE_FIXTURE, SAB.TYPE_FIXTURE],
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
                classes=[SAB.BADGE_SCOPE, SAB.scope(scope)],
            )
            scope_row += nodes.Text(" ")
            scope_dense_row += build_badge(
                scope,
                tooltip=f"Scope: {scope}",
                classes=[SAB.DENSE, SAB.BADGE_SCOPE, SAB.scope(scope)],
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
                classes=[SAB.BADGE_STATE, css_class],
                fill=fill,
            )
            state_row += nodes.Text(" ")
            state_dense_row += build_badge(
                label,
                tooltip=tooltip,
                classes=[SAB.DENSE, SAB.BADGE_STATE, css_class],
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
                    classes=[SAB.DENSE, SAB.TYPE_CONFIG],
                ),
                build_badge(
                    "env",
                    tooltip="Rebuild mode: env",
                    classes=[SAB.DENSE, SAB.MOD_REBUILD],
                    fill="outline",
                ),
                build_badge(
                    "html",
                    tooltip="Rebuild mode: html",
                    classes=[SAB.DENSE, SAB.MOD_REBUILD],
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
                    classes=[SAB.DENSE, SAB.TYPE_DIRECTIVE],
                ),
                build_badge(
                    "role",
                    tooltip="Docutils role",
                    classes=[SAB.DENSE, SAB.TYPE_ROLE],
                ),
                build_badge(
                    "option",
                    tooltip="Docutils option",
                    classes=[SAB.DENSE, SAB.TYPE_OPTION],
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
