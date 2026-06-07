"""Synthetic Sphinx extension components for live autodoc demos.

Grows one demo class per component type so the
``docs/packages/sphinx-autodoc-sphinx`` examples page can exercise the
``autobuilder`` and ``autodomain`` directives against realistic
metadata.

Examples
--------
>>> DemoArchiveBuilder.name
'demo-archive'
"""

from __future__ import annotations

import typing as t

from sphinx.builders import Builder
from sphinx.domains import Domain, ObjType
from sphinx.locale import _
from sphinx.roles import XRefRole

if t.TYPE_CHECKING:
    from collections.abc import Iterator, Set

    from docutils import nodes
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata


class DemoArchiveBuilder(Builder):
    """Bundle every rendered page into one archive artifact.

    A deliberately small builder: it reports all documents as outdated,
    writes nothing per page, and exists so the autodoc output has a
    realistic name/format/image-type surface to display.
    """

    name = "demo-archive"
    format = "archive"
    epilog = "The demo archive is in %(outdir)s."
    supported_image_types: list[str] = ["image/svg+xml", "image/png"]  # noqa: RUF012 — matches upstream sphinx.builders.Builder shape

    def get_outdated_docs(self) -> Iterator[str]:
        """Report every document as outdated."""
        yield from self.env.found_docs

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        """Return the in-archive URI for a document."""
        return f"{docname}.txt"

    def prepare_writing(self, docnames: Set[str]) -> None:
        """No writer state is needed for the demo."""

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        """Skip per-document output; the demo archives nothing."""


class DemoTopicDomain(Domain):
    """Describe demo topics with one object type and matching role."""

    name = "demotopic"
    label = "Demo topics"

    object_types = {  # noqa: RUF012 — matches upstream sphinx.domains.Domain shape
        "topic": ObjType(_("topic"), "topic"),
    }

    roles = {  # noqa: RUF012 — XRefRole instances are safe to share across domains
        "topic": XRefRole(),
    }


def setup(app: Sphinx) -> ExtensionMetadata:
    """Register the demo extension components with Sphinx.

    Examples
    --------
    >>> class FakeApp:
    ...     def __init__(self) -> None:
    ...         self.calls: list[tuple[str, object]] = []
    ...     def add_builder(self, cls: object) -> None:
    ...         self.calls.append(("add_builder", cls))
    ...     def add_domain(self, cls: object) -> None:
    ...         self.calls.append(("add_domain", cls))
    >>> fake = FakeApp()
    >>> metadata = setup(fake)  # type: ignore[arg-type]
    >>> ("add_builder", DemoArchiveBuilder) in fake.calls
    True
    >>> ("add_domain", DemoTopicDomain) in fake.calls
    True
    >>> metadata["parallel_read_safe"]
    True
    """
    app.add_builder(DemoArchiveBuilder)
    app.add_domain(DemoTopicDomain)
    return {
        "version": "0.0.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
