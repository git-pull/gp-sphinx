"""Snapshot coverage for transformed layout doctrees."""

from __future__ import annotations

import types
import typing as t

from docutils import nodes
from sphinx import addnodes
from sphinx_autodoc_layout._nodes import build_api_slot
from sphinx_autodoc_layout._transforms import on_doctree_resolved


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
    badge_group = nodes.inline(classes=["gas-badge-group"])
    badge_group += nodes.inline("", "method", classes=["gas-badge"])
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
