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
from sphinx_autodoc_docutils._nodes_doc import (
    AutoNode,
    AutoNodes,
    NodeInfo,
    discover_node,
    discover_nodes,
)
from sphinx_autodoc_docutils._parsers_doc import (
    AutoParser,
    AutoParsers,
    ParserInfo,
    discover_parser,
    discover_parsers,
)
from sphinx_autodoc_docutils._readers_doc import (
    AutoReader,
    AutoReaders,
    discover_reader,
    discover_readers,
)
from sphinx_autodoc_docutils._transforms_doc import (
    AutoTransform,
    AutoTransforms,
    TransformInfo,
    discover_transform,
    discover_transforms,
)
from sphinx_autodoc_docutils._translators_doc import (
    AutoTranslator,
    AutoTranslators,
    TranslatorInfo,
    discover_translator,
    discover_translators,
)
from sphinx_autodoc_docutils._writers_doc import (
    AutoWriter,
    AutoWriters,
    discover_writer,
    discover_writers,
)
from sphinx_autodoc_docutils.domain import (
    DocutilsComponentIndex,
    DocutilsDomain,
)

__all__ = [
    "AutoDirective",
    "AutoDirectives",
    "AutoNode",
    "AutoNodes",
    "AutoParser",
    "AutoParsers",
    "AutoReader",
    "AutoReaders",
    "AutoRole",
    "AutoRoles",
    "AutoTransform",
    "AutoTransforms",
    "AutoTranslator",
    "AutoTranslators",
    "AutoWriter",
    "AutoWriters",
    "DocutilsComponentIndex",
    "DocutilsDomain",
    "NodeInfo",
    "ParserInfo",
    "SetupRecorder",
    "TransformInfo",
    "TranslatorInfo",
    "discover_node",
    "discover_nodes",
    "discover_parser",
    "discover_parsers",
    "discover_reader",
    "discover_readers",
    "discover_transform",
    "discover_transforms",
    "discover_translator",
    "discover_translators",
    "discover_writer",
    "discover_writers",
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
    ...     def add_domain(self, domain: object) -> None:
    ...         self.calls.append(("add_domain", domain))
    ...     def connect(self, event: str, handler: object) -> None:
    ...         self.calls.append(("connect", event))
    ...     def add_css_file(self, filename: str) -> None:
    ...         self.calls.append(("add_css_file", filename))
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> ("add_directive", "autodirective") in fake.calls
    True
    >>> ("add_directive", "autotransform") in fake.calls
    True
    >>> ("add_domain", DocutilsDomain) in fake.calls
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
    app.add_domain(DocutilsDomain)
    app.add_directive("autodirective", AutoDirective)
    app.add_directive("autodirectives", AutoDirectives)
    app.add_directive("autorole", AutoRole)
    app.add_directive("autoroles", AutoRoles)
    app.add_directive("autotransform", AutoTransform)
    app.add_directive("autotransforms", AutoTransforms)
    app.add_directive("autoreader", AutoReader)
    app.add_directive("autoreaders", AutoReaders)
    app.add_directive("autoparser", AutoParser)
    app.add_directive("autoparsers", AutoParsers)
    app.add_directive("autowriter", AutoWriter)
    app.add_directive("autowriters", AutoWriters)
    app.add_directive("autonode", AutoNode)
    app.add_directive("autonodes", AutoNodes)
    app.add_directive("autotranslator", AutoTranslator)
    app.add_directive("autotranslators", AutoTranslators)

    _static_dir = str(pathlib.Path(__file__).parent / "_static")

    def _add_static_path(app: Sphinx) -> None:
        if _static_dir not in app.config.html_static_path:
            app.config.html_static_path.append(_static_dir)

    app.connect("builder-inited", _add_static_path)
    app.add_css_file("css/sphinx_autodoc_docutils.css")

    return {
        "version": "0.0.1a30",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
