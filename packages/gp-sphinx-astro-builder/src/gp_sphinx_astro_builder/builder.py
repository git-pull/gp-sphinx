"""Sphinx ``astro`` builder.

Walks each doctree through :class:`DocTreeJSONTranslator`, validates the
result through the Pydantic :class:`Document` model, and writes one JSON file
per source document into ``<outdir>/src/content/docs/<docname>.json``. The
layout matches Astro's standard ``glob()`` content loader so an Astro site
configured with ``glob({ pattern: '**/*.json', base: './src/content/docs' })``
picks up every emitted file as one collection entry.
"""

from __future__ import annotations

import json
import typing as t

from sphinx.builders import Builder
from sphinx.util import logging
from sphinx.util.inventory import InventoryFile
from sphinx.util.osutil import _last_modified_time

from gp_sphinx_astro_builder.content_config import render_content_config
from gp_sphinx_astro_builder.intersphinx import build_xref_index_entries
from gp_sphinx_astro_builder.schemas import (
    export_doctree_schema,
    export_symbol_schema,
)
from gp_sphinx_astro_builder.symbols import SymbolAccumulator
from gp_sphinx_astro_builder.translator import DocTreeJSONTranslator

if t.TYPE_CHECKING:
    from collections.abc import Iterator, Set as AbstractSet

    from docutils import nodes


logger = logging.getLogger(__name__)


class AstroBuilder(Builder):
    """Emit one Pydantic-validated JSON file per source document.

    Output layout
    -------------
    ``<outdir>/src/content/docs/<docname>.json``

    The relative ``src/content/docs/`` prefix mirrors Astro's content
    collection conventions, so a downstream Astro site whose
    ``content.config.ts`` uses ``glob({ pattern: '**/*.json', base:
    './src/content/docs' })`` consumes the build output without further
    wiring.
    """

    name = "astro"
    format = "json"
    epilog = "The Astro JSON files are in %(outdir)s."
    out_suffix = ".json"
    allow_parallel = True
    default_translator_class = DocTreeJSONTranslator

    def init(self) -> None:
        """Initialize the build-scoped symbol accumulator."""
        self._symbol_accumulator = SymbolAccumulator()

    def get_target_uri(self, docname: str, typ: str | None = None) -> str:
        """Return the JSON path (relative URI) for ``docname``."""
        return docname + self.out_suffix

    def get_outdated_docs(self) -> Iterator[str]:
        """Yield every source document whose JSON output is missing or stale."""
        for docname in self.env.found_docs:
            if docname not in self.env.all_docs:
                yield docname
                continue
            target_path = self._target_path(docname)
            try:
                target_mtime = _last_modified_time(target_path)
            except OSError:
                target_mtime = 0
            try:
                source_mtime = _last_modified_time(self.env.doc2path(docname))
            except OSError:
                continue
            if source_mtime > target_mtime:
                yield docname

    def prepare_writing(self, docnames: AbstractSet[str]) -> None:
        """No per-build preparation required for the spike."""

    def write_doc(self, docname: str, doctree: nodes.document) -> None:
        """Walk ``doctree`` through the JSON translator and write the result."""
        self.current_docname = docname
        translator = DocTreeJSONTranslator(
            doctree,
            self,
            docname=docname,
            symbol_accumulator=self._symbol_accumulator,
        )
        doctree.walkabout(translator)
        document = translator.result()

        target_path = self._target_path(docname)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(
            document.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

    def finish(self) -> None:
        """Emit cross-document artifacts.

        Writes the canonical JSON Schema for the doctree wire format to
        ``<outdir>/schemas/doctree.schema.json`` and the accumulated symbol
        records to ``<outdir>/src/content/api/symbols.json``. The TypeScript
        side validates Zod schemas against the schema file and consumes the
        symbol entries through Astro's ``file()`` content loader.
        """
        schemas_dir = self.outdir / "schemas"
        schemas_dir.mkdir(parents=True, exist_ok=True)
        (schemas_dir / "doctree.schema.json").write_text(
            json.dumps(export_doctree_schema(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (schemas_dir / "symbol.schema.json").write_text(
            json.dumps(export_symbol_schema(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        symbols_path = self.outdir / "src" / "content" / "api" / "symbols.json"
        symbols_path.parent.mkdir(parents=True, exist_ok=True)
        symbols_path.write_text(
            self._symbol_accumulator.to_json(),
            encoding="utf-8",
        )

        # Cross-reference inventory: Sphinx-format objects.inv plus a typed
        # JSON shape that the Astro side can ingest without parsing zlib.
        InventoryFile.dump(str(self.outdir / "objects.inv"), self.env, self)
        xref_entries = build_xref_index_entries(self.env, self)
        (self.outdir / "xref-index.json").write_text(
            json.dumps(
                [entry.model_dump() for entry in xref_entries],
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        # Astro content collection wiring: the TypeScript file that imports
        # the parity-tested theme schemas and registers them with
        # defineCollection() against the canonical artefact paths.
        content_config_path = self.outdir / "src" / "content.config.ts"
        content_config_path.parent.mkdir(parents=True, exist_ok=True)
        content_config_path.write_text(
            render_content_config(),
            encoding="utf-8",
        )

    def _target_path(self, docname: str):  # type: ignore[no-untyped-def]
        """Return the absolute path for the JSON file emitted for ``docname``."""
        return self.outdir / "src" / "content" / "docs" / (docname + self.out_suffix)
