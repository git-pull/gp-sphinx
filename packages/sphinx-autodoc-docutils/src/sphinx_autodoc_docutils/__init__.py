"""Sphinx extension for documenting docutils directives and roles."""

from __future__ import annotations

import typing as t

from sphinx.application import Sphinx

from sphinx_autodoc_docutils._directives import (
    AutoDirective,
    AutoDirectiveIndex,
    AutoDirectives,
    AutoRole,
    AutoRoleIndex,
    AutoRoles,
)

if t.TYPE_CHECKING:
    from sphinx.util.typing import ExtensionMetadata


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register docutils directive and role autodoc directives.

    Examples
    --------
    >>> class FakeApp:
    ...     def __init__(self) -> None:
    ...         self.calls: list[tuple[str, str]] = []
    ...     def add_directive(self, name: str, directive: object) -> None:
    ...         self.calls.append(("add_directive", name))
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> ("add_directive", "autodirective") in fake.calls
    True
    >>> metadata["parallel_read_safe"]
    True
    """
    app.add_directive("autodirective", AutoDirective)
    app.add_directive("autodirectives", AutoDirectives)
    app.add_directive("autodirective-index", AutoDirectiveIndex)
    app.add_directive("autorole", AutoRole)
    app.add_directive("autoroles", AutoRoles)
    app.add_directive("autorole-index", AutoRoleIndex)

    return {
        "version": "0.0.1a0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
