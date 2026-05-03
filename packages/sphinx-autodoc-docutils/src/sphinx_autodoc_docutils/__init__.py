"""Sphinx extension for documenting docutils directives and roles."""

from __future__ import annotations

import logging
import pathlib
import typing as t

from sphinx_autodoc_docutils._directives import (
    AutoDirective,
    AutoDirectives,
    AutoRole,
    AutoRoles,
    SetupRecorder,
    replay_setup,
)

__all__ = [
    "AutoDirective",
    "AutoDirectives",
    "AutoRole",
    "AutoRoles",
    "SetupRecorder",
    "replay_setup",
    "setup",
]

if t.TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

logging.getLogger(__name__).addHandler(logging.NullHandler())


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register docutils directive and role autodoc directives.

    Examples
    --------
    >>> class FakeApp:
    ...     def __init__(self) -> None:
    ...         self.calls: list[tuple[str, object]] = []
    ...     def setup_extension(self, name: str) -> None:
    ...         self.calls.append(("setup_extension", name))
    ...     def add_directive(self, name: str, directive: object) -> None:
    ...         self.calls.append(("add_directive", name))
    ...     def connect(self, event: str, handler: object) -> None:
    ...         self.calls.append(("connect", event))
    ...     def add_css_file(self, filename: str) -> None:
    ...         self.calls.append(("add_css_file", filename))
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> ("add_directive", "autodirective") in fake.calls
    True
    >>> ("setup_extension", "sphinx_ux_autodoc_layout") in fake.calls
    True
    >>> ("add_css_file", "css/sphinx_autodoc_docutils.css") in fake.calls
    True
    >>> metadata["parallel_read_safe"]
    True
    """
    app.setup_extension("sphinx_ux_badges")
    app.setup_extension("sphinx_ux_autodoc_layout")
    app.setup_extension("sphinx_autodoc_typehints_gp")
    app.add_directive("autodirective", AutoDirective)
    app.add_directive("autodirectives", AutoDirectives)
    app.add_directive("autorole", AutoRole)
    app.add_directive("autoroles", AutoRoles)

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_autodoc_docutils.css")

    return {
        "version": "0.0.1a16",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
