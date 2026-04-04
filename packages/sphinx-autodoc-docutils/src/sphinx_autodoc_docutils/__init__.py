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


def setup(app: Sphinx) -> dict[str, t.Any]:
    """Register the extension."""
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
