(gp-sphinx-astro-builder-reference)=

# Reference

## Module layout

The package owns these modules under
`packages/gp-sphinx-astro-builder/src/gp_sphinx_astro_builder/`:

`builder.py`
: `AstroBuilder(Builder)`. Required overrides
  (`get_outdated_docs`, `get_target_uri`, `write_doc`); optional
  `init`, `prepare_writing`, `finish`. `finish()` writes the
  cross-doc artifacts.

`translator.py`
: `DocTreeJSONTranslator(NodeVisitor)`. Stack-based; each `visit_*`
  pushes a child collector, each `depart_*` validates against a
  Pydantic model and appends to its parent. Subclasses
  `nodes.SparseNodeVisitor` so unknown nodes traverse children with
  a warning instead of crashing the build.

`models.py`
: Pydantic v2 models, one per node type, plus `InlineNode` /
  `BlockNode` / `DocNode` discriminated unions and a top-level
  `Document` model. The canonical doctree schema imports
  extension-supplied node models through an entry point group
  (`gp_sphinx_astro_builder.nodes`), so the union stays typed as
  extensions add nodes.

`symbols.py`
: `Symbol`, `Parameter`, `SymbolSource` plus the build-scoped
  accumulator the translator writes into and `finish()` reads from.

`intersphinx.py`
: Emits `objects.inv` and `xref-index.json` from the same source
  data.

`content_config.py`
: Pure function rendering the `src/content.config.ts` template; the
  Astro side imports the parity-tested Zod schemas from the theme
  package.

`schemas.py`
: Exports the JSON Schema for the doctree and the symbol model; CLI
  hook so the same schema can be written out-of-band for tooling.

## Builder name

| Field | Value |
|---|---|
| `Builder.name` | `astro` |
| Output suffix | `.json` |
| Format | JSON |
| Parallel-safe (read) | yes |
| Parallel-safe (write) | yes |

## Configuration values

| Key | Default | Description |
|---|---|---|
| `astro_outdir_layout` | `"standard"` | Output directory layout. `"standard"` matches Astro content collection conventions (`src/content/<collection>/<doc>.json`). |

## Output artifacts

Per build, `finish()` emits:

- One `<docname>.json` per source document — the validated doctree.
- `src/content/api/symbols.json` — aggregated `Symbol` records from
  every `addnodes.desc` container the translator encountered.
- `xref-index.json` — typed cross-reference table consumable by
  other Astro sites.
- `objects.inv` — standard Sphinx intersphinx inventory (preserved
  for compatibility with non-Astro consumers).
- `schemas/doctree.schema.json` — JSON Schema 2020-12 export of the
  Pydantic doctree models.
- `src/content.config.ts` — Astro content-collection config wiring
  Zod schemas to the emitted JSON files.
