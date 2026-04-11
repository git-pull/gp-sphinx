"""Snapshot coverage for transformed layout doctrees."""

from __future__ import annotations

import types
import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx_autodoc_layout._nodes import build_api_slot
from sphinx_autodoc_layout._transforms import on_doctree_resolved

from sphinx_autodoc_fastmcp._models import ParamInfo, ToolInfo
from sphinx_autodoc_fastmcp._prototype import build_tool_desc_prototype


def _make_parameter(
    name: str,
    *,
    default: str | None = None,
) -> addnodes.desc_parameter:
    parameter = addnodes.desc_parameter()
    parameter += addnodes.desc_sig_name("", name)
    if default is not None:
        parameter += addnodes.desc_sig_space("", " ")
        parameter += addnodes.desc_sig_operator("", "=")
        parameter += addnodes.desc_sig_space("", " ")
        parameter += nodes.inline("", default, classes=["default_value"])
    return parameter


def _make_parameter_field_list(types: dict[str, str]) -> nodes.field_list:
    field_list = nodes.field_list()
    field = nodes.field()
    field += nodes.field_name("", "Parameters")
    body = nodes.field_body()
    bullets = nodes.bullet_list()
    for name, type_name in types.items():
        paragraph = nodes.paragraph()
        paragraph += addnodes.literal_strong("", name)
        paragraph += nodes.Text(" (")
        paragraph += nodes.emphasis("", type_name)
        paragraph += nodes.Text(")")
        bullets += nodes.list_item("", paragraph)
    body += bullets
    field += body
    field_list += field
    return field_list


def _make_large_signature_desc() -> addnodes.desc:
    desc = addnodes.desc(domain="py", objtype="method")
    signature = addnodes.desc_signature(ids=["demo.Session.__init__"])
    signature += addnodes.desc_name("", "__init__")
    parameter_list = addnodes.desc_parameterlist()
    parameter_list += _make_parameter("session_name")
    parameter_list += _make_parameter("window_name", default='"main"')
    parameter_list += _make_parameter("start_directory", default='"/tmp"')
    parameter_list += _make_parameter("attach", default="True")
    parameter_list += _make_parameter("kill_session", default="False")
    parameter_list += _make_parameter("environment", default="None")
    parameter_list += _make_parameter("x", default="80")
    parameter_list += _make_parameter("y", default="24")
    parameter_list += _make_parameter("command", default='"bash"')
    parameter_list += _make_parameter("shell", default='"zsh"')
    parameter_list += _make_parameter("socket_name", default='"default"')
    parameter_list += _make_parameter("socket_path", default="None")
    parameter_list += _make_parameter("config_file", default="None")
    signature += parameter_list
    badge_group = nodes.inline(classes=["sab-badge-group"])
    badge_group += nodes.inline("", "method", classes=["sab-badge"])
    signature += build_api_slot("badges", badge_group)
    source_span = nodes.inline(classes=["viewcode-link"])
    source_span += nodes.Text("[source]")
    signature += build_api_slot(
        "source-link",
        nodes.reference("", "", source_span, internal=False),
    )
    desc += signature
    content = addnodes.desc_content()
    content += nodes.paragraph("", "Create a richly configurable session.")
    content += _make_parameter_field_list(
        {
            "session_name": "str",
            "window_name": "str",
            "start_directory": "str",
            "attach": "bool",
            "kill_session": "bool",
            "environment": "dict[str, str] | None",
            "x": "int",
            "y": "int",
            "command": "str",
            "shell": "str",
            "socket_name": "str",
            "socket_path": "str | None",
            "config_file": "str | None",
        }
    )
    desc += content
    return desc


def _rendered_desc(
    *,
    show_annotations: bool,
) -> addnodes.desc:
    desc = _make_large_signature_desc()
    return _rendered_managed_desc(
        desc,
        show_annotations=show_annotations,
    )


def _rendered_managed_desc(
    desc: addnodes.desc,
    *,
    show_annotations: bool,
) -> addnodes.desc:
    app = t.cast(
        t.Any,
        types.SimpleNamespace(
            config=types.SimpleNamespace(
                gal_enabled=True,
                gal_collapsed_threshold=10,
                gal_fold_parameters=True,
                gal_signature_show_annotations=show_annotations,
                html_permalinks=True,
            ),
            builder=types.SimpleNamespace(format="html", add_permalinks=True),
        ),
    )
    doctree = t.cast(nodes.document, nodes.section("", desc))
    on_doctree_resolved(app, doctree, "index")
    return desc


def _make_confval_desc() -> addnodes.desc:
    desc = addnodes.desc(domain="std", objtype="confval")
    signature = addnodes.desc_signature(ids=["confval.demo_option"])
    signature += addnodes.desc_name("", "demo_option")
    badge_group = nodes.inline(classes=["sas-badge-group"])
    badge_group += nodes.inline("", "config", classes=["sas-badge--type"])
    badge_group += nodes.inline("", " ")
    badge_group += nodes.inline("", "env", classes=["sas-badge--rebuild"])
    badge_group += nodes.inline("", " ")
    badge_group += nodes.inline("", "stable", classes=["sas-badge--status"])
    signature += build_api_slot("badges", badge_group)
    desc += signature
    content = addnodes.desc_content()
    content += nodes.field_list(
        "",
        nodes.field(
            "",
            nodes.field_name("", "Type"),
            nodes.field_body("", nodes.paragraph("", "bool")),
        ),
        nodes.field(
            "",
            nodes.field_name("", "Default"),
            nodes.field_body(
                "",
                nodes.literal_block(
                    "",
                    "{'accent': 'teal', 'surface': 'paper', 'ink': 'charcoal'}",
                ),
            ),
        ),
    )
    content += nodes.paragraph("", "A demo option.")
    desc += content
    return desc


def _make_rst_directive_desc() -> addnodes.desc:
    desc = addnodes.desc(domain="rst", objtype="directive")
    signature = addnodes.desc_signature(ids=["directive-demo-directive"])
    signature += addnodes.desc_name("", "demo-directive")
    badge_group = nodes.inline(classes=["sadoc-badge-group"])
    badge_group += nodes.inline("", "directive", classes=["sadoc-badge--type"])
    signature += build_api_slot("badges", badge_group)
    desc += signature
    content = addnodes.desc_content()
    content += nodes.paragraph("", "A demo directive.")
    option_desc = addnodes.desc(domain="rst", objtype="directive:option")
    option_sig = addnodes.desc_signature(ids=["directive-option-demo-opt"])
    option_sig += addnodes.desc_name("", "demo-opt")
    option_badges = nodes.inline(classes=["sadoc-badge-group"])
    option_badges += nodes.inline("", "option", classes=["sadoc-badge--type"])
    option_sig += build_api_slot("badges", option_badges)
    option_desc += option_sig
    option_content = addnodes.desc_content()
    option_content += nodes.paragraph("", "A demo option.")
    option_content += nodes.literal_block("", "option = directives.class_option")
    option_desc += option_content
    content += option_desc
    desc += content
    return desc


def _make_fastmcp_tool_desc() -> addnodes.desc:
    return build_tool_desc_prototype(
        ToolInfo(
            name="list_sessions",
            title="List Sessions",
            module_name="demo_tools",
            area="api",
            safety="readonly",
            annotations={},
            func=lambda server: "[]",
            docstring=(
                "List sessions for one server.\n\n"
                "Use the filters to narrow the returned sessions."
            ),
            params=[
                ParamInfo("server", "str", True, "", "Server name."),
                ParamInfo("limit", "int", False, "20", "Maximum number to return."),
                ParamInfo("cursor", "str | None", False, "None", "Pagination cursor."),
                ParamInfo("project", "str | None", False, "None", "Project filter."),
                ParamInfo(
                    "status", "'open' | 'closed'", False, "'open'", "Status filter."
                ),
                ParamInfo("owner", "str | None", False, "None", "Owner filter."),
                ParamInfo("region", "str | None", False, "None", "Region filter."),
                ParamInfo(
                    "updated_after",
                    "str | None",
                    False,
                    "None",
                    "Updated filter.",
                ),
                ParamInfo(
                    "updated_before",
                    "str | None",
                    False,
                    "None",
                    "Updated filter.",
                ),
                ParamInfo(
                    "include_archived",
                    "bool",
                    False,
                    "False",
                    "Archive filter.",
                ),
                ParamInfo(
                    "expand",
                    "str | None",
                    False,
                    "None",
                    "Expansion options.",
                ),
                ParamInfo(
                    "request_id",
                    "str | None",
                    False,
                    "None",
                    "Request id.",
                ),
            ],
            return_annotation="str",
        )
    )


def test_large_signature_snapshot_annotated(
    snapshot_doctree: t.Callable[..., None],
) -> None:
    """Large signatures snapshot their structured header and folded content."""
    snapshot_doctree(
        _rendered_desc(show_annotations=True),
        name="large_signature_annotated",
    )


def test_large_signature_snapshot_annotation_disabled(
    snapshot_doctree: t.Callable[..., None],
) -> None:
    """Annotation-disabled signatures snapshot the stripped expanded panel."""
    snapshot_doctree(
        _rendered_desc(show_annotations=False),
        name="large_signature_annotation_disabled",
    )


def test_confval_snapshot(snapshot_doctree: t.Callable[..., None]) -> None:
    """Confval entries snapshot their shared header/body decomposition."""
    snapshot_doctree(
        _rendered_managed_desc(_make_confval_desc(), show_annotations=True),
        name="confval_entry",
    )


def test_rst_directive_snapshot(snapshot_doctree: t.Callable[..., None]) -> None:
    """RST directive entries snapshot their shared header/body decomposition."""
    snapshot_doctree(
        _rendered_managed_desc(_make_rst_directive_desc(), show_annotations=True),
        name="rst_directive_entry",
    )


def test_fastmcp_tool_prototype_snapshot(
    snapshot_doctree: t.Callable[..., None],
) -> None:
    """FastMCP prototype entries snapshot the shared desc layout contract."""
    snapshot_doctree(
        _rendered_managed_desc(_make_fastmcp_tool_desc(), show_annotations=True),
        name="fastmcp_tool_prototype",
    )
