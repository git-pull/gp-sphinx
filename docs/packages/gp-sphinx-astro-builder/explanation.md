(gp-sphinx-astro-builder-explanation)=

# Explanation

## The data contract

The wire format between Sphinx and Astro is JSON. The Python side
defines shapes with [Pydantic v2](https://docs.pydantic.dev/); the
TypeScript side defines the same shapes with [Zod 4](https://zod.dev/).
Both sides export to JSON Schema 2020-12 — Pydantic through
`model_json_schema()`, Zod through the built-in `z.toJSONSchema()` —
and a snapshot test in CI asserts the two exports are equivalent
after normalizing for one Pydantic-specific quirk (the OpenAPI-flavored
`discriminator` field, which Pydantic adds to discriminated unions
and Zod doesn't). Schema drift becomes a test failure, not a runtime
mystery.

## The map from Sphinx to Astro

| Sphinx primitive | What we build |
|---|---|
| `StandaloneHTMLBuilder` | `AstroBuilder(Builder)`. Same lifecycle (`init → read → write_doc → finish`), different output: per-doc JSON instead of per-doc HTML. Modeled on Sphinx's existing `XMLBuilder` (50 LOC at `sphinx/builders/xml.py`) which already serializes doctrees through a translator. |
| `HTML5Translator` | `DocTreeJSONTranslator(NodeVisitor)`. Stack-based; each `visit_*` pushes a child collector, each `depart_*` validates against a Pydantic model and appends to its parent. |
| `autodoc` | Same Sphinx extension, no changes. The translator detects entry into an `addnodes.desc` container, switches to a structured-symbol mode, builds a typed `Symbol` record, and leaves a `symbolRef` placeholder in the doctree. `finish()` aggregates symbols into `src/content/api/symbols.json`. |
| Python domain index (`env.domains.python_domain.data["objects"]`) | Read at `finish()` time and folded into `symbols.json`. |
| `intersphinx` + `objects.inv` | We keep emitting `objects.inv` (compatibility) and also emit a typed `xref-index.json` that other Astro sites can consume to resolve back-references. |
| Theme (Furo) | An Astro component set under `astro/packages/theme/` (`@gp-sphinx/astro`). IBM Plex fonts, OKLCH color tokens, CVA variants, Shiki syntax highlighting. |
| Furo Jinja templates | Astro components, one per node type. A recursive `<Node>` component dispatches on `node.type` to the matching component. |
| MyST (Markdown for Sphinx) | MyST stays as the Markdown parser (it already produces standard docutils nodes, which is exactly what the translator wants). Authors keep writing `.md` and `.rst` interchangeably. |

## Why a JSON builder

Sphinx's built-in builders all target a final rendering surface
(HTML, ePub, LaTeX, manpage). The Astro pipeline needs the *doctree
itself* — a structured, typed intermediate — so the renderer lives
in TypeScript next to the rest of the site. Emitting JSON also makes
every node a first-class artifact: tests can snapshot it, other
tools can index it, and the wire format is the contract instead of
the rendered HTML being the contract.

The doctree-as-JSON contract decouples authoring (Sphinx + MyST,
unchanged) from delivery (Astro + Tailwind + Shiki). Sphinx
extensions that emit nodes — autodoc, sphinx-design, the workspace's
own `sphinx-ux-badges` and friends — all flow through the same
translator without per-extension HTML templates.

For deeper architectural background, see `notes/plans/astro.md` in
the workspace root.
