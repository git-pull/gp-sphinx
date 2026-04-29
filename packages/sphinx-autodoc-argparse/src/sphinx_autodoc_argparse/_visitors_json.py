"""JSON visitors for the gp-sphinx-astro-builder pipeline.

Each ``argparse_*`` node serialises to a single ``cliCommand`` Pydantic
shape on the wire. The ``component`` discriminator preserves the
docutils class so the Astro renderer dispatches on it. Visitors push a
frame on the translator's internal ``_stack``; matching depart handlers
pop the frame and call ``append_node`` to attach the typed dict to the
parent's children list.

``self`` is a ``DocTreeJSONTranslator`` after Sphinx's ``MethodType``
binding — we don't import that class here to keep this extension free
of circular dependencies on ``gp-sphinx-astro-builder``.
"""

from __future__ import annotations

import typing as t

from docutils import nodes


def _open_cli_command_frame(self: t.Any, component: str, **attrs: t.Any) -> None:
    """Push a ``cliCommand`` frame onto the translator's stack."""
    payload: dict[str, t.Any] = {
        "type": "cliCommand",
        "component": component,
        "prog": attrs.get("prog"),
        "usage": attrs.get("usage"),
        "title": attrs.get("title"),
        "description": attrs.get("description"),
        "names": list(attrs.get("names", [])),
        "help": attrs.get("help"),
        "default": attrs.get("default"),
        "choices": list(attrs.get("choices", [])),
        "required": bool(attrs.get("required", False)),
        "metavar": attrs.get("metavar"),
        "name": attrs.get("name"),
        "aliases": list(attrs.get("aliases", [])),
        "classes": list(attrs.get("classes", [])),
        "children": [],
    }
    self._stack.append({"kind": "cliCommand", "data": payload})


def _close_cli_command_frame(self: t.Any) -> None:
    """Pop the current ``cliCommand`` frame and attach it to the parent."""
    frame = self._stack.pop()
    self.append_node(frame["data"])


def visit_argparse_program_json(self: t.Any, node: nodes.Element) -> None:
    """Open a cliCommand frame for an ``argparse_program``."""
    _open_cli_command_frame(self, "program", prog=node.get("prog", ""))


def depart_argparse_program_json(self: t.Any, node: nodes.Element) -> None:
    """Close the program frame."""
    _close_cli_command_frame(self)


def visit_argparse_usage_json(self: t.Any, node: nodes.Element) -> None:
    """Append a usage marker; no children, no depart."""
    self.append_node(
        {
            "type": "cliCommand",
            "component": "usage",
            "prog": None,
            "usage": node.get("usage", ""),
            "title": None,
            "description": None,
            "names": [],
            "help": None,
            "default": None,
            "choices": [],
            "required": False,
            "metavar": None,
            "name": None,
            "aliases": [],
            "classes": [],
            "children": [],
        },
    )
    raise nodes.SkipNode


def depart_argparse_usage_json(self: t.Any, node: nodes.Element) -> None:
    """No-op companion for :func:`visit_argparse_usage_json`."""


def visit_argparse_group_json(self: t.Any, node: nodes.Element) -> None:
    """Open a cliCommand frame for an ``argparse_group``."""
    _open_cli_command_frame(
        self,
        "group",
        title=node.get("title", ""),
        description=node.get("description"),
    )


def depart_argparse_group_json(self: t.Any, node: nodes.Element) -> None:
    """Close the group frame."""
    _close_cli_command_frame(self)


def visit_argparse_argument_json(self: t.Any, node: nodes.Element) -> None:
    """Append an argument marker; no children, no depart."""
    self.append_node(
        {
            "type": "cliCommand",
            "component": "argument",
            "prog": None,
            "usage": None,
            "title": None,
            "description": None,
            "names": list(node.get("names", [])),
            "help": node.get("help"),
            "default": node.get("default"),
            "choices": list(node.get("choices", []) or []),
            "required": bool(node.get("required", False)),
            "metavar": node.get("metavar"),
            "name": None,
            "aliases": [],
            "classes": [],
            "children": [],
        },
    )
    raise nodes.SkipNode


def depart_argparse_argument_json(self: t.Any, node: nodes.Element) -> None:
    """No-op companion for :func:`visit_argparse_argument_json`."""


def visit_argparse_subcommands_json(self: t.Any, node: nodes.Element) -> None:
    """Open a cliCommand frame for an ``argparse_subcommands``."""
    _open_cli_command_frame(self, "subcommands", title=node.get("title", ""))


def depart_argparse_subcommands_json(self: t.Any, node: nodes.Element) -> None:
    """Close the subcommands frame."""
    _close_cli_command_frame(self)


def visit_argparse_subcommand_json(self: t.Any, node: nodes.Element) -> None:
    """Open a cliCommand frame for an ``argparse_subcommand``."""
    _open_cli_command_frame(
        self,
        "subcommand",
        name=node.get("name", ""),
        aliases=node.get("aliases", []),
        help=node.get("help"),
    )


def depart_argparse_subcommand_json(self: t.Any, node: nodes.Element) -> None:
    """Close the subcommand frame."""
    _close_cli_command_frame(self)
