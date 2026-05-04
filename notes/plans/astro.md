# Astro Documentation Platform for gp-sphinx

**Branch:** `astro-2026-04-26` **Status:** implemented (rebased onto post-PR-#29 main, 2026-05-04)

## What we're building

A documentation platform that replaces Furo with an Astro static site
while keeping Sphinx + docutils as the document pipeline. Sphinx still
parses sources and runs autodoc / intersphinx / every existing
`sphinx-*` extension; what changes is the output. Instead of HTML, we
ship a new Sphinx builder that walks each doctree and emits typed
JSON, plus structured JSON entries for autodoc symbols. An Astro
theme reads those JSON files through Astro's standard content
collections and renders them through a recursive component renderer
styled with Tailwind v4. The first site we'll build with it documents
`gp-sphinx` and the fourteen `sphinx-*` packages in this repository;
the second documents `libtmux`.

## Why

The Sphinx HTML sites at `*.git-pull.com` are functional but visually
dated, slow to iterate on, and constrained by Furo's customization
surface. Furo's layout breakpoints are SASS compile-time constants,
which means CSS custom properties can't override them — the
customization ceiling we keep hitting is structural, not cosmetic.
Astro gives modern theming (CVA + Tailwind v4), fast static builds,
content collections with typed frontmatter, MDX for component-heavy
pages, and a much better local development loop. We keep Python as
the source of truth for the document tree because Sphinx already does
that work — autodoc, intersphinx, MyST, and the fourteen `sphinx-*`
extensions in this repo all hand back enriched doctrees. We don't
reimplement any of it in TypeScript.

## The data contract

The wire format between Sphinx and Astro is JSON. The Python side
defines shapes with Pydantic v2; the TypeScript side defines the same
shapes with Zod 4. Both sides export to JSON Schema 2020-12 — Pydantic
through `model_json_schema()`, Zod through the built-in
`z.toJSONSchema()` — and a snapshot test in CI asserts the two
exports are equivalent after normalizing for one Pydantic-specific
quirk (the OpenAPI-flavored `discriminator` field, which Pydantic
adds to discriminated unions and Zod doesn't). Schema drift becomes a
test failure, not a runtime mystery.

## The map from Sphinx to Astro

| Sphinx primitive | What we build |
|---|---|
| `StandaloneHTMLBuilder` | `AstroBuilder(Builder)`. Same lifecycle (`init → read → write_doc → finish`), different output: per-doc JSON instead of per-doc HTML. Modeled on Sphinx's existing `XMLBuilder` (50 LOC at `sphinx/builders/xml.py`) which already serializes doctrees through a translator. |
| `HTML5Translator` | `DocTreeJSONTranslator(NodeVisitor)`. Stack-based; each `visit_*` pushes a child collector, each `depart_*` validates against a Pydantic model and appends to its parent. |
| `autodoc` | Same Sphinx extension, no changes. The translator detects entry into an `addnodes.desc` container, switches to a structured-symbol mode, builds a typed `Symbol` record, and leaves a `symbolRef` placeholder in the doctree. `finish()` aggregates symbols into `src/content/api/symbols.json`. |
| Python domain index (`env.domains.python_domain.data["objects"]`) | Read at `finish()` time and folded into `symbols.json`. |
| `intersphinx` + `objects.inv` | We keep emitting `objects.inv` (compatibility) and also emit a typed `xref-index.json` that other Astro sites can consume to resolve back-references. |
| Theme (Furo) | An Astro component set in `astro/packages/theme/`. IBM Plex fonts, OKLCH color tokens, CVA variants, syntax highlighting via `astro-expressive-code`. Patterns derived from `~/work/tony.sh/packages/astro/`. |
| Furo Jinja templates | Astro components, one per node type. A recursive `<Node>` component dispatches on `node.type` to the matching component. Pattern from Astro's markdoc integration `TreeNode.ts`. |
| MyST (Markdown for Sphinx) | MyST stays as the Markdown parser (it already produces standard docutils nodes, which is exactly what the translator wants). Authors keep writing `.md` and `.rst` interchangeably. |

## The packages

We ship two new packages plus one optional helper. The four-package
sketch from earlier drafts collapses because Sphinx is the engine —
there's no separate TypeScript build engine, and the Python helper
merges into the builder package.

### `gp-sphinx-astro-builder` — the Sphinx Builder

A Python package living at `packages/gp-sphinx-astro-builder/`
alongside the existing fourteen `sphinx-*` packages. It registers a
new builder with Sphinx through the standard `setup(app)` entry
point:

```python
def setup(app):
    app.add_builder(AstroBuilder)
    app.add_config_value('astro_outdir_layout', 'standard', 'env')
    return {'version': __version__, 'parallel_read_safe': True,
            'parallel_write_safe': True}
```

A consumer's `conf.py` looks like:

```python
extensions = ["gp_sphinx_astro_builder", "sphinx.ext.autodoc", ...]
```

```console
$ uv run sphinx-build -b astro docs/ astro/apps/<site>/src/
```

The package owns:

- `builder.py` — `AstroBuilder(Builder)`. Required overrides
  (`get_outdated_docs`, `get_target_uri`, `write_doc`); optional
  `init`, `prepare_writing`, `finish`. `finish()` writes the
  cross-doc artifacts (symbols.json, xref-index.json, objects.inv,
  schemas/doctree.schema.json, src/content.config.ts).
- `translator.py` — `DocTreeJSONTranslator(NodeVisitor)`. ~35
  `visit_*`/`depart_*` pairs covering the docutils + Sphinx addnode
  set the existing extensions emit.
- `models.py` — Pydantic v2 models, one per node type, plus
  `InlineNode` / `BlockNode` / `DocNode` discriminated unions and a
  top-level `Document` model. The canonical doctree schema imports
  extension-supplied node models through an entry point group
  `gp_sphinx_astro_builder.nodes`, so the union stays typed as
  extensions add nodes.
- `symbols.py` — `Symbol`, `Parameter`, `SymbolSource` plus the
  build-scoped accumulator that the translator writes into and
  `finish()` reads from.
- `intersphinx.py` — emits `objects.inv` and `xref-index.json` from
  the same source data.
- `content_config.py` — pure function rendering the
  `src/content.config.ts` template; the Astro side imports the
  parity-tested Zod schemas from the theme package.
- `schemas.py` — exports the JSON Schema for the doctree and the
  symbol model; CLI hook so the same schema can be written
  out-of-band for tooling.

The translator subclasses `nodes.SparseNodeVisitor` so unknown nodes
default to traversing children; we log a warning and emit a debug
`unknown` node rather than crashing the build.

The package follows the project's existing Python conventions: `from
__future__ import annotations`, namespace imports (`import enum`,
`import typing as t`), NumPy-style docstrings with working doctests,
plain-function tests with `t.NamedTuple` parametrization. Python ≥
3.10. Tests use the `tests._sphinx_scenarios` harness with the
appropriate level — pure tree-unit tests for the translator, full
integration builds (`@pytest.mark.integration`) for the builder.

### `@gp-sphinx/astro` — the Astro theme

A pnpm workspace package at `astro/packages/theme/`. Owns:

- `src/schemas/{doctree,symbol}.ts` — hand-written Zod schemas. Kept
  in parity with the Pydantic models through the snapshot test in
  the builder's test suite.
- `src/components/Node.astro` — the recursive renderer. Dispatches
  on `node.type`, recurses into `node.children`. Pattern from
  `~/study/typescript/astro/packages/integrations/markdoc/.../TreeNode.ts`.
- `src/components/nodes/` — one Astro component per node type
  (`Paragraph.astro`, `Section.astro`, `LiteralBlock.astro`,
  `Admonition.astro`, `List.astro`, `Reference.astro`, `Symbol.astro`,
  ~30 in total). Each is small (5–20 LOC); style lives in Tailwind
  utilities + CVA variants.
- `src/layouts/Doc.astro` — page chrome (sidebar, header, footer,
  TOC).
- `src/styles/tokens.css` — OKLCH tokens under
  `--gp-sphinx-astro-*`, wired into Tailwind v4 through a `@theme`
  block.
- `src/tailwind.preset.ts` — Tailwind preset reused by sites.

Components are independently consumable: a site can use a theme
component without using the full builder if it wants. The canonical
wiring is the recursive `<Node>` renderer reading from a content
collection populated by the builder.

### `@gp-sphinx/astro-integration` — optional Astro integration

Convenience, not load-bearing. Runs `sphinx-build -b astro` from
`astro:config:setup` and invalidates the content cache when Sphinx
re-emits, so `astro dev` triggers a Sphinx rebuild on watched-file
changes. Without it, users run `sphinx-build -b astro && astro
build` as two commands. Land this package when the dual-command
flow becomes a real friction point, not before.

## The doctree-as-JSON contract

Each source document becomes one JSON file under
`src/content/docs/<docname>.json`:

```json
{
  "id": "guide/installation",
  "title": "Installation",
  "tree": {
    "type": "section",
    "id": "installation",
    "title": [{"type": "text", "value": "Installation"}],
    "children": [
      {"type": "paragraph",
       "children": [{"type": "text", "value": "Install via pip:"}]},
      {"type": "literalBlock",
       "language": "console",
       "code": "$ pip install gp-sphinx"}
    ]
  }
}
```

Every node has a `type` discriminator. The Pydantic models are
roughly:

```python
class TextNode(BaseModel):
    type: t.Literal["text"]
    value: str

class ParagraphNode(BaseModel):
    type: t.Literal["paragraph"]
    children: list[InlineNode]

class LiteralBlockNode(BaseModel):
    type: t.Literal["literalBlock"]
    language: str | None
    code: str

class AdmonitionNode(BaseModel):
    type: t.Literal["admonition"]
    variant: t.Literal["note", "warning", "tip", "caution", ...]
    children: list[BlockNode]

class SymbolRefNode(BaseModel):
    type: t.Literal["symbolRef"]
    symbolId: str  # joins to symbols.json
```

Autodoc symbols live in a separate flat collection at
`src/content/api/symbols.json`:

```python
class Symbol(BaseModel):
    id: str                          # "gp_sphinx.config.merge_sphinx_config"
    kind: t.Literal["function", "class", "method", "attribute",
                    "property", "enum", "dataclass", "module"]
    name: str
    qualname: str
    module: str
    signature: str
    parameters: list[Parameter]
    returns: str | None
    docstring_summary: str
    docstring_body: list[BlockNode]  # full doctree of docstring body
    source: SymbolSource | None
```

`docstring_body` is itself a doctree — the `<Node>` renderer handles
it the same way as top-level docs. There's no Markdown-leaf
double-parse problem because Sphinx already parses docstrings into
the same node types as the rest of the document.

## How it works at runtime

The build proceeds top-to-bottom:

1. `sphinx-build -b astro <srcdir> <outdir>` runs. Sphinx loads
   `conf.py`, including `extensions = ["gp_sphinx_astro_builder",
   ...]`.
2. Sphinx's normal pipeline parses every source file with docutils
   + MyST, runs autodoc / intersphinx / every other registered
   extension, and produces enriched doctrees in `env`.
3. `AstroBuilder.write_doc(docname, doctree)` runs once per
   document. It instantiates a `DocTreeJSONTranslator`, calls
   `doctree.walkabout(translator)`, and writes the resulting
   Pydantic-validated JSON to
   `<outdir>/src/content/docs/<docname>.json`.
4. `AstroBuilder.finish()` writes the cross-doc artifacts:
   `src/content/api/symbols.json` (autodoc aggregation),
   `xref-index.json` (intersphinx targets), `objects.inv` (legacy
   compat), `schemas/doctree.schema.json` (the Pydantic JSON
   Schema), and `src/content.config.ts` (Astro collection
   definitions importing the parity-tested Zod schemas).
5. The user runs `pnpm -C astro/apps/<site> build`. Astro reads
   `src/content.config.ts`, picks up the JSON files through the
   `glob()` and `file()` loaders, and validates every entry against
   the Zod schemas at build time.
6. The site's single dynamic page (`src/pages/[...slug].astro`)
   iterates the `docs` collection through `getStaticPaths()`,
   passes each entry's `data.tree` to the `<Node>` recursive
   renderer, and Astro emits a static HTML file per entry.

In dev (`astro dev`), the `glob()` and `file()` loaders watch their
respective inputs. The optional integration package re-runs
`sphinx-build` when watched Python files or sources change.

## Where everything lives

```
gp-sphinx/
├── packages/                                          # 14 existing sphinx-* packages
│   ├── ...
│   ├── sphinx-gp-theme/                               # Furo wrapper, runs unchanged through Step 9
│   └── gp-sphinx-astro-builder/                       # NEW
│       ├── pyproject.toml                             # uv workspace member (auto, packages/* glob)
│       └── src/gp_sphinx_astro_builder/
│           ├── __init__.py                            # setup() registers builder + nodes
│           ├── builder.py                             # AstroBuilder(Builder)
│           ├── translator.py                          # DocTreeJSONTranslator(NodeVisitor)
│           ├── models.py                              # Pydantic models per node type
│           ├── symbols.py                             # Symbol model + autodoc aggregator
│           ├── intersphinx.py                         # objects.inv + xref-index.json
│           ├── content_config.py                      # generates src/content.config.ts
│           └── schemas.py                             # exports doctree.schema.json
├── astro/
│   ├── pnpm-workspace.yaml
│   ├── package.json                                   # root scripts: build, dev, test, lint, type-check
│   ├── biome.json
│   ├── vitest.workspace.ts
│   ├── tsconfig.base.json                             # extends "astro/tsconfigs/strictest"
│   ├── packages/
│   │   ├── theme/                                     # @gp-sphinx/astro
│   │   │   ├── src/schemas/{doctree,symbol}.ts
│   │   │   ├── src/components/Node.astro
│   │   │   ├── src/components/nodes/                  # one per node type, ~30 files
│   │   │   ├── src/layouts/Doc.astro
│   │   │   ├── src/styles/tokens.css
│   │   │   └── src/tailwind.preset.ts
│   │   └── integration/                               # @gp-sphinx/astro-integration (optional, deferred)
│   ├── apps/
│   │   └── gp-sphinx-docs/                            # first dogfood site
│   │       ├── astro.config.ts
│   │       ├── conf.py                                # extensions = [..., 'gp_sphinx_astro_builder']
│   │       ├── docs/                                  # .rst / .md sources
│   │       └── src/                                   # populated by sphinx-build -b astro
│   │           ├── content/                           # gitignored, regenerated each build
│   │           ├── content.config.ts                  # generated, gitignored
│   │           └── pages/[...slug].astro              # consumes both collections
│   ├── fixtures/                                      # test fixtures shared across packages
│   └── AGENTS.md                                      # Astro-side conventions for AI agents
└── notes/plans/astro.md                               # this document
```

The pnpm workspace is rooted at `astro/`. `gp-sphinx-astro-builder`
joins the existing uv workspace automatically — the root
`pyproject.toml`'s `[tool.uv.workspace] members = ["packages/*"]`
already covers it. CI runs both `uv sync --all-packages` and `pnpm
-C astro install` and gates on both stacks staying green.

## First consumer: gp-sphinx itself

The first site we ship documents `gp-sphinx` and its fourteen child
packages. This is intentional dogfood: the platform documents the
package whose docs platform it's replacing. It also forces the
renderer to handle every node kind that matters, because the
`sphinx-*` packages between them cover all the interesting cases:

- Plain functions and classes (every package)
- Sphinx config values (`sphinx-autodoc-sphinx`, `sphinx-gp-opengraph`)
- Custom `docutils` directives (`sphinx-ux-badges` registers a node +
  directive)
- Custom roles (across the autodoc packages)
- pytest fixtures documented as first-class symbols
  (`sphinx-autodoc-pytest-fixtures` self-documents)
- argparse-based CLI documentation (`sphinx-autodoc-argparse`)
- FastMCP tools (`sphinx-autodoc-fastmcp`)
- Type annotations with cross-references (`sphinx-autodoc-typehints-gp`)
- Layout primitives (`sphinx-ux-autodoc-layout`)

The site lives at `astro/apps/gp-sphinx-docs/`. It deploys to the
same AWS infrastructure the existing docs use (S3 + CloudFront +
Cloudflare DNS). Per-PR previews go to a new bucket served through
the existing CloudFront distribution with a path-based behavior.

## Second consumer: libtmux

Once the renderer handles gp-sphinx's surface, the next site is
`libtmux`. libtmux exercises a different shape of Python API:

- Concrete classes with `__init__` signatures (`Server`, `Session`,
  `Window`, `Pane`)
- `enum.Enum` types with multiple variants (`OptionScope`,
  `WindowDirection`, `PaneDirection`, `ResizeAdjustmentDirection`)
- `@dataclasses.dataclass` classes with field annotations
- A method-chain fluent API style
- An embedded pytest plugin (`libtmux.pytest_plugin`) with fixtures
  documented through doctests and hidden setup blocks

The libtmux site replaces `libtmux.git-pull.com`. We build the
renderer's component set with libtmux's surface in mind from the
start so the second consumer is mostly a config change, not new
code.

## Build sequence

In order. Each step is small enough to land as a single PR; each
"done when" is an objective check. Quality gates per
`CLAUDE.md` run before each commit (`uv run ruff format .`,
`uv run pytest`, `uv run ruff check . --fix --show-fixes`, `uv run
mypy`; once `astro/` exists, also `pnpm -C astro lint type-check
test`).

1. **Spike the builder end-to-end with one paragraph.** Smallest
   possible vertical slice. Source `index.rst` containing `Hello
   world.` becomes `src/content/docs/index.json` with a `Document`
   wrapping a single `section → paragraph → text` node tree, validated
   by Pydantic. Files: `packages/gp-sphinx-astro-builder/pyproject.toml`,
   `models.py` with `TextNode` / `ParagraphNode` / `SectionNode` /
   `Document`, `translator.py` with the seven required visit/depart
   pairs, `builder.py` with the `XMLBuilder`-shaped class,
   `__init__.py` registering the builder, and a smoke integration
   test using `tests._sphinx_scenarios.build_isolated_sphinx_result`.
   Done when the integration test asserts the JSON file exists,
   parses, and validates against `Document.model_validate_json(...)`.
   This is the load-bearing step; if `add_builder` + `walkabout` +
   Pydantic validation + JSON emission works end-to-end here, every
   later step is "add more node types."

2. **Cover the prose node set.** Add Pydantic models, translator
   visitors, and unit tests for the high-frequency docutils nodes:
   `emphasis`, `strong`, `literal`, `literal_block`, `bullet_list`,
   `enumerated_list`, `list_item`, `definition_list`,
   `definition_list_item`, `term`, `definition`, `block_quote`,
   `note`, `warning`, `attention`, `caution`, `important`, `tip`,
   `hint`, `reference` (internal + external), `target`, `image`,
   `transition`, `comment`. Tests are pure tree-unit (no Sphinx
   build), NamedTuple-parametrized per `CLAUDE.md`. Done when each
   node type has a passing round-trip test.

3. **Schema export and Zod parity.** Builder's `finish()` writes
   `<outdir>/schemas/doctree.schema.json` via
   `TypeAdapter(DocNode).json_schema()`. Theme package gains
   hand-written Zod schemas in
   `astro/packages/theme/src/schemas/doctree.ts`. A snapshot test
   in the builder's test suite asserts `z.toJSONSchema(zodDocNode)`
   matches the Pydantic output after stripping the OpenAPI
   `discriminator` annotation Pydantic adds (helper:
   `tests/_schema_compare.py`). Done when the parity test passes
   and a Vitest test in the theme imports the Zod schema and
   validates a fixture JSON.

4. **autodoc → typed Symbol collection.** `addnodes.desc` containers
   emit a `Symbol` rather than a generic doctree node. The
   translator switches modes on `desc` entry, populates a
   build-scoped accumulator, and leaves a `symbolRef` placeholder
   in the doctree. `finish()` writes
   `src/content/api/symbols.json`. Done when an integration test
   using `sphinx.ext.autodoc` against a fixture module covering
   function / class / method / enum / dataclass produces a JSON
   that validates against the `Symbol` model and the doctree
   correctly references the symbol IDs.

5. **Cross-references → xref-index.json + objects.inv.**
   `pending_xref` nodes resolve through Sphinx's existing transform
   phase; the new work is emitting the cross-doc artifacts.
   `intersphinx.py` writes both formats from one source of truth.
   Done when `objects.inv` round-trips through Sphinx's standard
   inventory parser bit-equivalent to the existing HTML build's
   output for the same project, and `xref-index.json` validates
   against a Zod schema.

6. **Generated `src/content.config.ts`.** `content_config.py` is a
   pure function returning TypeScript source; `finish()` writes the
   file. The output imports the parity-tested Zod schemas from
   `@gp-sphinx/astro` and wires them into `defineCollection`
   for both the `docs` (glob loader) and `api` (file loader)
   collections. Done when `astro check` against the emitted file
   in a fixture site passes.

7. **Scaffold the Astro theme and workspace.** `astro/` finally
   appears: pnpm workspace, Biome, Vitest workspace, TypeScript
   base config (`extends "astro/tsconfigs/strictest"`), `astro/AGENTS.md`,
   and `astro/packages/theme/` with the recursive `<Node>` renderer
   plus stubs for ~30 per-type components. Tailwind v4 + CVA + IBM
   Plex via Fontsource. Done when `pnpm -C astro install / lint /
   type-check / test` are all green.

8. **Wire the dogfood app.** A real Astro app at
   `astro/apps/gp-sphinx-docs/` consumes the emitted collections
   and the theme components. The single dynamic route
   `src/pages/[...slug].astro` loads from both `docs` and `api`
   collections and dispatches to `<Doc>`. Build flow:
   `sphinx-build -b astro` then `pnpm build`. Done when the
   `merge_sphinx_config` symbol page renders with a real signature,
   NumPy docstring, resolved cross-references, and the Tailwind v4
   dark mode toggles correctly.

9. **Cover the remaining sphinx-* directives.** Each existing
   extension under `packages/sphinx-*/` registers a JSON visitor
   for its custom node, ships a Pydantic model (registered through
   the `gp_sphinx_astro_builder.nodes` entry point group), and the
   theme adds a matching component. One commit per package, ~14
   total; priority by what `gp-sphinx-docs` actually renders first
   (`sphinx-ux-badges`, `sphinx-ux-autodoc-layout`,
   `sphinx-autodoc-typehints-gp`, then the rest).

10. **Switch gp-sphinx-docs from Furo to Astro.** The cutover for
    the first site. Replace the GitHub Actions docs workflow's
    `sphinx-build -b html` step with the dual `sphinx-build -b astro
    && pnpm -C astro/apps/gp-sphinx-docs build` flow; deploy `dist/`
    to the existing S3 bucket. Done when `gp-sphinx.git-pull.com`
    serves the Astro site and a manual smoke test confirms PageSpeed
    score ≥ existing Furo baseline. Until this step, both paths
    exist; nothing breaks during the transition.

Steps 11+ (deferred to separate sessions): libtmux migration; per-PR
previews via the existing CloudFront distribution; Furo deprecation
in `merge_sphinx_config` (one release of warning); removal of
`sphinx-gp-theme` once every consumer is on Astro; the optional
`@gp-sphinx/astro-integration` Astro integration that runs
`sphinx-build` automatically during `astro dev`.

## Standards

The new code follows the conventions in this repo's `CLAUDE.md`.
Highlights that apply directly to this work:

- **CSS namespace.** All classes the new components emit use
  `gp-sphinx-astro-*` (Tier A) or `gp-sphinx-astro-<pkg>__<thing>`
  (Tier B BEM). Custom properties use `--gp-sphinx-astro-<token>`.
  The new theme never touches Furo's CSS variables — Furo-themed
  sites continue to work through Step 9.
- **Python imports.** The Python builder uses namespace imports
  (`import enum`, `import typing as t`); `from __future__ import
  annotations`; NumPy-style docstrings with working doctests on
  every public function.
- **Tests.** Plain functions, no `class TestFoo:` groupings.
  `t.NamedTuple` for parametrization where it improves readability.
  The lightest test level that exercises the behavior — pure
  tree-unit tests for the translator (build a doctree directly,
  walk it, assert the JSON), full Sphinx integration tests for
  the builder, snapshot tests for anything multi-line.
- **Schema parity.** The Pydantic ↔ Zod snapshot test is the
  load-bearing safeguard against schema drift; it runs in CI on
  every PR.
- **Commits.** `Scope(type[detail]): description` with `why:` and
  `what:` blocks, as elsewhere in this repo.

The TypeScript packages follow the same patterns `~/work/tony.sh`
uses: Biome for lint and format, Vitest for tests (workspace
projects per package), CVA for variant-driven components, Zod 4 for
schemas, pnpm via Corepack (pinned in `package.json`'s
`packageManager` field), `extends "astro/tsconfigs/strictest"` for
the base TypeScript config.

## Decisions to make later

These don't block any of the steps above. Each gets resolved at the
point it actually matters.

- **Whether to commit the generated `src/content/`, `objects.inv`,
  and `xref-index.json`, or treat them strictly as build artifacts.**
  Default plan is gitignore + regenerate each build; reconsider if
  per-PR previews need stable hashes.
- **How to handle `:py:func:`-style xrefs inside MDX prose pages.**
  If we ever author hand-written prose that's not a docutils source,
  a remark plugin reading `xref-index.json` is the path; the
  plugin lives in the theme package. Land when there's a real
  hand-written MDX page that needs it.
- **Which OKLCH palette and the Furo color-token mapping.**
  `~/work/tony.sh` ships four palettes (amber, emerald, purple,
  sky); pick one when there's a renderer to look at and decide how
  Furo's `--color-api-*` tokens map to the new ones. Calibrating
  against an empty page is unrewarding.
- **How the libtmux fixture stays current.** The libtmux site needs
  a test fixture — vendor a snapshot, use a git submodule, or
  regenerate from the live `~/work/python/libtmux` checkout when
  something changes upstream. Decide when libtmux is the active
  consumer; until then a vendored snapshot is fine.

## Pointers

Read-only references for anyone implementing this. None of these get
modified.

- `~/study/python/sphinx/sphinx/builders/__init__.py` — the
  `Builder` base class and lifecycle methods.
- `~/study/python/sphinx/sphinx/builders/xml.py` — `XMLBuilder`,
  the closest existing model for a doctree-serializing builder
  (~50 LOC).
- `~/study/python/sphinx/sphinx/writers/html5.py` — `HTML5Translator`
  for the visit/depart pattern.
- `~/study/python/sphinx/sphinx/addnodes.py` — the ~51 Sphinx-specific
  node classes the translator must handle.
- `~/study/python/docutils/docutils/nodes.py` — `NodeVisitor`,
  `SparseNodeVisitor`, and the docutils node taxonomy.
- `~/study/python/myst-parser/myst_parser/mdit_to_docutils/base.py`
  — confirmation that MyST emits standard docutils nodes (no MyST-
  specific output node types to handle).
- `~/study/python/pydantic/pydantic/json_schema.py` — Pydantic v2's
  JSON Schema export, especially the OpenAPI-style discriminator
  handling.
- `~/study/typescript/zod/packages/zod/src/v4/core/to-json-schema.ts`
  — Zod 4's built-in JSON Schema export.
- `~/study/typescript/zod/packages/zod/src/v4/classic/from-json-schema.ts`
  — Zod 4's built-in JSON Schema import.
- `~/study/typescript/astro/packages/astro/src/content/loaders/glob.ts`
  — the `glob()` content loader.
- `~/study/typescript/astro/packages/astro/src/content/loaders/file.ts`
  — the `file()` content loader.
- `~/study/typescript/astro/packages/integrations/markdoc/` — for
  `TreeNode.ts`, the recursive renderer pattern the `<Node>`
  component follows.
- `~/work/tony.sh/packages/astro/` — the theme template the new
  theme is derived from; component patterns, OKLCH palette, Tailwind
  v4 setup, Biome / Vitest / CVA conventions.
- `~/work/cv/packages/react/src/styles/style.css` — OKLCH 11-stop
  scale reference.
- `packages/sphinx-ux-badges/src/sphinx_ux_badges/__init__.py` —
  the existing pattern for custom-directive node + builder-specific
  visitor registration; the model for how each `sphinx-*` extension
  adds its JSON visitor in Step 9.
- `/home/d/work/python/gp-sphinx/CLAUDE.md` — repo conventions the
  new code has to follow.
