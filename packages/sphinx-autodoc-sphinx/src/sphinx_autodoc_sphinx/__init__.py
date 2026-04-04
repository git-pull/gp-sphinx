"""Sphinx extension for documenting config values registered by extensions."""

from __future__ import annotations

import typing as t

from sphinx.application import Sphinx

from sphinx_autodoc_sphinx._directives import (
    AutoconfigvalueDirective,
    AutoconfigvalueIndexDirective,
    AutoconfigvaluesDirective,
    AutosphinxconfigIndexDirective,
)

if t.TYPE_CHECKING:
    from sphinx.util.typing import ExtensionMetadata


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register config-value documentation directives.

    Examples
    --------
    >>> class FakeApp:
    ...     def __init__(self) -> None:
    ...         self.calls: list[tuple[str, str]] = []
    ...     def add_directive(self, name: str, directive: object) -> None:
    ...         self.calls.append(("add_directive", name))
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> ("add_directive", "autoconfigvalue") in fake.calls
    True
    >>> metadata["parallel_read_safe"]
    True
    """
    app.add_directive("autoconfigvalue", AutoconfigvalueDirective)
    app.add_directive("autoconfigvalues", AutoconfigvaluesDirective)
    app.add_directive("autoconfigvalue-index", AutoconfigvalueIndexDirective)
    app.add_directive("autosphinxconfig-index", AutosphinxconfigIndexDirective)
    return {
        "version": "0.0.1a0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
