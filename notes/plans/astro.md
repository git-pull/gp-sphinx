# Astro Documentation Stack for gp-sphinx

**Status:** Plan / exploratory
**Date:** 2026-04-26
**Scope:** Parallel Astro-based documentation toolchain for the gp-sphinx
constellation, with libtmux as the first consumer (recreating
<https://libtmux.git-pull.com>).

This is a workspace planning artifact. It is not a contract — final structure
will be decided when scaffolding lands.

---

## Why a parallel stack?

gp-sphinx today is a Sphinx-native platform: 14 packages built around Furo,
autodoc, and intersphinx. That investment is not going away. This plan
describes a **second** documentation pipeline — Astro + TypeScript — that:

- Owns the rendering layer end-to-end (no Sphinx HTML output to skin).
- Reuses the gp-sphinx visual language and tony.sh's Tailwind/typography work.
- Reads Python source directly, with Python doing the semantics (signatures,
  annotations, docstrings) so we hit Sphinx-autodoc parity where it matters.
- Resolves cross-references against existing Sphinx `objects.inv` inventories
  so links into Python stdlib, tmuxp, and other git-pull projects keep working.

The Sphinx pipeline stays. The Astro pipeline is for projects that want a
modern, Vite-fast docs site with the same data. libtmux is the proving ground.

---

## Architectural shape

A **hybrid sidecar pipeline with a schema firewall**:

| Owner | Responsibilities |
|---|---|
| **Node / TypeScript** | Filesystem scanning, deterministic ordering, caching, stable IDs, intersphinx parsing, Astro integration, rendering. |
| **Python (sidecar)** | Import semantics, runtime introspection, annotation evaluation (PEP 649 / `annotationlib`), RST→Markdown conversion. |
| **Zod** | The wire contract between them. The UI never sees unvalidated Python output. |

This split is non-negotiable for the same reason mypy and pyright have to
import or re-implement Python: only Python can answer "what does this name
actually resolve to?" — so we let it.

### Fast path vs truth path

- **Fast path (Node, best-effort):** scan files, parse with `tree-sitter-python`,
  extract imports/defs/docstrings/raw annotation text. Works even when imports
  fail. Used for navigation, the file index, and the API table of contents.
- **Truth path (Python sidecar, imports allowed):** `uv run python -m
  gp_sphinx_sidecar` imports modules off the discovered list and uses
  `inspect.signature`, `inspect.getdoc`, and `annotationlib.get_annotations`
  to extract evaluated types. Used to fill in everything the static pass
  couldn't.

The contract layer marshals both views into the same Zod schema. Renderers
read the schema, never raw Python or raw tree-sitter nodes.

---

## Public package layout

The user-facing surface is three packages, matching the names you proposed:

| Package | Role |
|---|---|
| **`gp-sphinx-tsx-builder`** | The "engine" — high-level TypeScript API. Discover → parse → introspect → graph. Pure data in, pure data out. Vitest-snapshotted. Has zero Astro coupling. |
| **`gp-sphinx-astro-builder`** | The Astro integration. Wraps the engine, exposes a virtual module + Content Loader, watches Python sources, generates static paths. |
| **`gp-sphinx-astro-theme`** | The visuals — Tailwind v4 plugin (OKLCH theme variables ported from tony.sh), IBM Plex font config, layout components, autodoc components (`<ApiModule />`, `<ApiClass />`, `<ApiFunction />`). |

Internally, each public package is composed of focused private packages so we
can test in isolation. They live under the `@gp-sphinx-astro/*` scope and are
not published.

```text
gp-sphinx/                                        # existing Python monorepo
├── packages/                                     # existing Python packages (sphinx-*)
│   ├── gp-sphinx/
│   ├── sphinx-gp-theme/
│   ├── sphinx-fonts/
│   ├── sphinx-ux-badges/
│   ├── sphinx-autodoc-typehints-gp/
│   └── ...                                       # 14 total today
├── astro/                                        # NEW — parallel JS workspace
│   ├── pnpm-workspace.yaml
│   ├── package.json                              # update:all, ncu, type-check, biome
│   ├── tsconfig.base.json                        # TS 5.9 strict
│   ├── vitest.workspace.ts
│   ├── biome.json
│   ├── AGENTS.md                                 # JS-side conventions
│   ├── packages/
│   │   ├── schema/                               # @gp-sphinx-astro/schema   (private)
│   │   ├── discover/                             # @gp-sphinx-astro/discover (private)
│   │   ├── parse/                                # @gp-sphinx-astro/parse    (private, tree-sitter)
│   │   ├── bridge/                               # @gp-sphinx-astro/bridge   (private, uv/uvx)
│   │   ├── intersphinx/                          # @gp-sphinx-astro/intersphinx (private)
│   │   ├── tsx-builder/                          # gp-sphinx-tsx-builder     (PUBLIC — facade)
│   │   ├── astro-builder/                        # gp-sphinx-astro-builder   (PUBLIC — integration)
│   │   └── astro-theme/                          # gp-sphinx-astro-theme     (PUBLIC — UI/Tailwind)
│   ├── python/
│   │   └── gp_sphinx_sidecar/                    # uv-managed Python sidecar
│   │       ├── pyproject.toml
│   │       └── src/gp_sphinx_sidecar/
│   ├── fixtures/
│   │   └── libtmux/                              # subset of libtmux for tests
│   └── apps/
│       └── libtmux-docs/                         # the actual site
```

### Why nest under `astro/`?

Keeps the Node tooling out of the way of the Python uv workspace. Python work
continues to use `uv sync`, `just test`, `pytest`. JS work uses `pnpm
install`, `pnpm test`, `pnpm typecheck`. CI runs both side-by-side. No
crosstalk in the package manager.

The Python sidecar lives inside `astro/python/` rather than as a top-level
gp-sphinx package because it has a single consumer (the bridge) and a tight
coupling to the Zod schema versioning. Promoting it to a normal gp-sphinx
package would invite drift.

---

## The contract — `@gp-sphinx-astro/schema`

Zero logic, only Zod schemas. **Every cross-boundary payload starts here.**
If Python returns garbage, Zod fails fast at the validation step rather than
crashing the renderer.

### Hard requirements

- **`protocolVersion: 1`** at the top of every payload. Bump on breaking changes.
- **Stable IDs** — `id = "<module>:<qualname>:<kind>"`, fully deterministic so
  the same input produces the same anchor across builds.
- **Source spans** — file + line range on every symbol, for "view source"
  links and deep links from search results.
- **Two annotation channels per symbol:**
  - `annotationText: string` — the doc-friendly representation, always
    populated when the source has any annotation. Comes from
    `annotationlib.Format.STRING` on Python 3.14+, falling back to raw
    tree-sitter text on older versions.
  - `annotationValue: TypeRef | null` — the evaluated type (recursive
    discriminated union: `name | subscript | union | callable | tuple |
    literal | unknown`). Optional — only populated when "truth mode" is
    enabled and `Format.FORWARDREF` succeeds.

  Why two channels: Python 3.14's `annotationlib` explicitly supports
  multiple retrieval formats, and `STRING` is the documentation-friendly one.
  `VALUE` raises on unevaluable annotations; `FORWARDREF` lets us inspect
  without resolving. We carry both so the UI never has to make this decision.

### Object model — what we need for autodoc parity

```typescript
// packages/schema/src/index.ts (sketch)
export const Module = z.object({ /* … */ })
export const Package = z.object({ /* … */ })
export const Class = z.object({
  bases: z.array(z.string()),
  mro: z.array(z.string()).optional(),
  methods: z.array(Function),
  attributes: z.array(Attribute),
  /* … */
})
export const Function = z.object({
  signature: Signature,
  decorators: z.array(z.string()),
  isAsync: z.boolean(),
  isGenerator: z.boolean(),
  /* … */
})
export const Variable = z.object({
  annotationText: z.string().nullable(),
  annotationValue: TypeRef.nullable(),
  reprTruncated: z.string().nullable(),
})
export const ApiIndex = z.object({
  protocolVersion: z.literal(1),
  packages: z.array(Package),
  modules: z.record(z.string(), Module),
  errors: z.array(AnalysisError),
})
```

Errors are first-class (import failure, runtime failure, parse failure) —
structured data, not thrown strings. The renderer can degrade gracefully and
show "(failed to import this module — see build log)" instead of producing a
broken page.

### Versioning

Schema breakage cascades. The plan: pin every internal package to the schema
version, bump in lockstep. Consumers of the public packages get a stable API
because the public packages re-export only what's stable, never the raw
internal types.

---

## Discovery, parsing, and the static layer

### `@gp-sphinx-astro/discover`

The cartographer. Maps the filesystem with `fast-glob`, distinguishes regular
packages (`__init__.py`) from PEP 420 namespace packages (no `__init__.py`),
honors `.gitignore`, and produces a deterministic list of files and modules.

Tested against an in-memory FS (`memfs`) so we can assert "excludes
`__pycache__`", "detects namespace packages", "computes qualified names
correctly" without touching disk.

### `@gp-sphinx-astro/parse`

The structure layer. `tree-sitter-python` extracts imports, classes,
functions, decorators, type aliases, raw annotation expressions as text.
Lazy-loads the WASM grammar via TS 5.9 `import defer` so cold-start cost is
paid only when analysis actually starts.

Output: `ModuleSymbols` per file. This is enough for navigation, search, and
"show me the public surface without importing anything" — important because
many real packages can't be imported in arbitrary environments.

Tested with snapshots: feed Python source strings → assert the extracted
JSON matches a stored snapshot. Covers PEP 695 type aliases (`type A[T] =
…`), PEP 649 deferred annotations, `__all__`, and decorator chains.

---

## The Python sidecar — `@gp-sphinx-astro/bridge`

The truth layer. Spawns Python via `uv` (from the consumer project's env),
captures stdout, validates against the schema, returns typed data.

### Execution policy

| Strategy | When |
|---|---|
| `uv run python -m gp_sphinx_sidecar …` | **Default.** Project-aware execution against the consumer's `pyproject.toml`. uv syncs first; we get the exact installed versions. |
| `uvx gp-sphinx-sidecar …` | When the sidecar is published as a tool and the consumer is just running it ephemerally. |

For libtmux docs builds, the default is `uv run` against the libtmux repo so
imports resolve exactly like the package does in real life. This also means
docs builds inherit the libtmux `pyproject.toml` Python version constraint —
no surprise mismatches.

### Sidecar CLI surface

The sidecar package exposes a small command set:

| Command | Purpose |
|---|---|
| `resolve-imports <name>...` | Classify top-level import targets (stdlib / builtin / external / local). **Top-level only** — see footgun below. |
| `introspect-module <dotted.path>` | Import a module and return schema'd API data. |
| `introspect-package <dotted.path>` | Walk a package and introspect every module, with allow/deny lists. |
| `rst-to-md <docstring>` | Convert a reStructuredText docstring to Markdown via docutils, so Astro can render it. |

#### Footgun: dotted `find_spec`

`importlib.util.find_spec("a.b.c")` **imports** the parent package `a.b`
automatically. We never call dotted `find_spec` from the "no-import"
classifier — `resolve-imports` only takes top-level names. The filesystem
index is the source of truth for local modules; Python's import machinery is
only consulted to classify externals. This is documented prominently in the
sidecar source.

#### Annotation format policy

| Mode | `annotationlib.Format` | When |
|---|---|---|
| **Default (safe)** | `STRING` | Always works, doesn't evaluate, perfect for docs. |
| **Truth mode (semantic)** | `FORWARDREF` | When the consumer enables it. Lets us link types without resolving. |
| **Strict (rare)** | `VALUE` | Only when the consumer accepts that unevaluable annotations will surface as errors. |

Default is `STRING` because docs that fail to build are worse than docs with
unlinked types. Consumers opt into richer modes.

### Subprocess hygiene

The bridge is the I/O boundary and **only** the I/O boundary:

- spawns uv/uvx, streams stdout/stderr
- enforces timeouts (default 30s, configurable per command)
- caps output size (default 16MB) to prevent runaway processes
- exit-code handling: non-zero → structured error in the schema, never throw
- does **not** parse JSON beyond capturing the bytes
- does **not** know any Python semantics

Tests: mocked subprocess (timeouts, stderr propagation, exit codes), plus
one micro-integration that runs a tiny Python snippet printing a known JSON
blob. No real Python execution in unit tests.

---

## Intersphinx — `@gp-sphinx-astro/intersphinx`

Critical for libtmux because its docs link heavily into Python stdlib, the
existing tmuxp Sphinx site, and other git-pull projects. Without intersphinx
the new Astro site loses cross-project references.

Pure TypeScript: `node:zlib` to inflate, line parser for the v2 format,
optional URL fetcher for remote inventories.

```typescript
// packages/intersphinx/src/parse.ts (sketch)
import { inflateSync } from 'node:zlib'

export function parseInventory(buffer: Buffer, baseUrl: string): Inventory {
  // header lines: "# Sphinx inventory version 2", "# Project: …", "# Version: …"
  // body: zlib-deflated lines of "name domain:role priority uri displayName"
  // returns: { project, version, baseUrl, entries: Map<"domain:role:name", Entry> }
}
```

Resolver API:

```typescript
const resolver = createResolver({ inventories: [pythonStdlib, tmuxp, libtmux] })
resolver.resolve('libtmux.Server', { role: 'class', domain: 'py' })
// → { url, displayText, source: 'libtmux' }
```

Tested with **real `objects.inv` files** committed as fixtures (Python
stdlib, tmuxp, libtmux's current Sphinx build). When the fixture format
changes upstream we catch it immediately.

---

## The TypeScript builder — `gp-sphinx-tsx-builder`

The public engine. Composes the internal layers and presents a stable,
documented API. **Has no Astro dependency** — it should be usable from a
plain Node CLI, a CI script, or any other consumer.

### Public surface

```typescript
// gp-sphinx-tsx-builder
export type { ApiIndex, Module, Class, Function, Variable, TypeRef } from '…'

export async function analyzePackage(
  rootDir: string,
  options?: AnalyzeOptions,
): Promise<ApiIndex>

export async function analyzeModule(
  modulePath: string,
  options?: AnalyzeOptions,
): Promise<Module>

export function buildApiGraph(index: ApiIndex): ApiGraph
//   - SCC / topo-sorted modules
//   - cross-references between Class.bases and Module.classes
//   - public-surface computation (__all__ where present, underscore rules elsewhere)
//   - stable anchor slugs

export function loadInventory(path: string | URL): Promise<Inventory>
export function createResolver(opts: ResolverOptions): Resolver
```

### Output is the snapshot

The "high-level API output" the user asked for is `ApiIndex`. It is:

- fully sorted (alphabetical within each category)
- stable IDs and anchor slugs
- cross-links resolved (a method's return type points at the class)
- public surface computed
- snapshotted in tests against the libtmux fixture

That snapshot is the regression harness. Any time someone changes the parser
or the bridge, the libtmux snapshot diff reveals the behavior change.

---

## Astro integration — `gp-sphinx-astro-builder`

Bridges the engine to Astro using the official integration lifecycle.

### What it does

1. **`astro:config:setup` hook:**
   - Run `analyzePackage()` on the consumer-configured Python source root.
   - Inject a Vite plugin that exposes a virtual module
     (`virtual:gp-sphinx-astro/api`) returning the cached `ApiIndex`.
   - Register an Astro Content Loader (`pythonLoader`) so consumers can
     `defineCollection({ loader: pythonLoader({ root: '…' }) })` and use
     content collections like Markdown.
   - Optional: register a remark/rehype plugin for `:py:class:`Server``-style
     intersphinx references in MDX.
2. **Dev-server file watch:** when `**/*.py` changes under the configured
   root, invalidate the cached `ApiIndex` and trigger a reload. This is what
   makes the "edit Python, see docs update" loop actually work.
3. **`astro:build:done` hook:** report stats (modules analyzed, parse time,
   intersphinx hit rate, errors).

### Page generation

The user explicitly wants consumers to write their own Astro pages, not have
the integration force a routing convention. The integration provides the
data; the page is one route file:

```astro
---
// src/pages/api/[...slug].astro
import { Module } from 'gp-sphinx-astro-theme'
import api from 'virtual:gp-sphinx-astro/api'

export function getStaticPaths() {
  return Object.keys(api.modules).map((name) => ({
    params: { slug: name.replace(/\./g, '/') },
    props: { module: api.modules[name] },
  }))
}

const { module } = Astro.props
---
<Module data={module} />
```

That's the entire wiring. Consumers can route however they want, mix in
hand-written MDX, group differently, etc.

---

## Theme & components — `gp-sphinx-astro-theme`

Ports the tony.sh visual language and gp-sphinx's existing typography
choices into reusable Astro components. Three layers:

### 1. Tailwind v4 plugin

Following tony.sh's `@tony/sh-tailwind-plugin` pattern. Exports:

- **OKLCH theme variables** — perceptually uniform palettes for `amber`,
  `emerald`, `purple`, `sky`. CSS variables `--color-{theme}-{role}` plus
  semantic aliases `--theme-{role}` (primary, secondary, accent, surface,
  text, muted).
- **Opacity utilities** — `text-theme-primary/40`, `bg-theme-secondary/60`
  via `color-mix(in srgb, var(--theme-color) {opacity}%, transparent)`.
- **Typography presets** — IBM Plex Sans (body) + IBM Plex Mono (code), the
  same Fontsource families `sphinx-fonts` already standardizes on.
- **Component utilities** — focus rings (`focus-visible:ring-2
  ring-theme-primary/40`), card hover states, smooth transitions.

### 2. Layout components (Astro)

Direct ports / adaptations from tony.sh:

- `<DocsLayout>` — sidebar + content + ToC, matching tony.sh's three-column
  structure, with mobile-responsive ToC and sidebar collapse
- `<TopNav>` — project switcher, search, theme toggle
- `<Sidebar>` — module/class navigation, intersphinx-aware
- `<MobileToC>` — collapsible on small screens
- `<Footer>` — version, build info, link to source

### 3. Autodoc components

The "render an API symbol" surface that mirrors what Sphinx autodoc gives
you, but as Astro components:

| Component | Renders |
|---|---|
| `<ApiPackage data={…} />` | Top-level package overview, module list |
| `<ApiModule data={…} />` | Module page: docstring, classes, functions, variables |
| `<ApiClass data={…} />` | Class signature, bases, MRO summary, methods, attributes |
| `<ApiFunction data={…} />` | Function/method signature with parameter kinds, return type, docstring |
| `<ApiVariable data={…} />` | Module-level constant: annotation + truncated repr |
| `<ApiSignature data={…} />` | Just the signature line, useful for inline cross-refs |
| `<ApiDocstring content={…} />` | Markdown-rendered docstring with intersphinx link rewriting |
| `<TypeAnnotation ref={…} />` | A linked, syntax-highlighted type expression |
| `<Reference target="…" />` | An intersphinx cross-reference |

Each accepts a Zod-typed prop, so consumers get autocomplete and TypeScript
errors when the schema changes.

The `<TypeAnnotation>` component is where intersphinx really pays off: a
type like `tmuxp.WorkspaceLoader | None` becomes two linked spans (one to
the local libtmux build context, one to tmuxp's Sphinx site) plus
unannotated text, with no manual work in the docstring.

### CSS scoping

All component classes use a `gp-sphinx-astro-` prefix following the existing
gp-sphinx CSS standards (Tier A: `gp-sphinx-astro-<concept>`, Tier B:
`gp-sphinx-astro-<pkg>__<thing>`). Custom properties mirror:
`--gp-sphinx-astro-<token>`. Furo-owned variables remain reserved for the
Sphinx side; they don't collide because the Astro stack has its own
stylesheet.

---

## The example site — `apps/libtmux-docs`

A working Astro site that exercises the whole stack, both as the proving
ground and as the future deployment target for <https://libtmux.git-pull.com>.

### Configuration

```typescript
// astro.config.mjs
import { defineConfig } from 'astro/config'
import gpSphinxAstro from 'gp-sphinx-astro-builder'
import { theme } from 'gp-sphinx-astro-theme'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  site: 'https://libtmux.git-pull.com',
  integrations: [
    gpSphinxAstro({
      package: '../../../libtmux/src/libtmux',  // absolute or repo-relative
      annotationFormat: 'STRING',                 // safe default
      intersphinx: [
        { name: 'python', url: 'https://docs.python.org/3/' },
        { name: 'tmuxp', url: 'https://tmuxp.git-pull.com/' },
      ],
    }),
  ],
  vite: { plugins: [tailwindcss(), theme()] },
})
```

### Content structure

- `src/content/docs/**` — hand-authored prose (quickstart, guides, recipes),
  exactly as the current Sphinx site has them. Migrated MDX.
- `src/pages/api/[...slug].astro` — auto-generated API pages. One route
  file, hundreds of pages.
- `src/pages/index.astro` — homepage with the existing copy, restyled to the
  new theme.

### Renewed layout

Per the brief: "renewed layout." Concrete changes from the current Furo site:

- Three-column desktop (sidebar / content / ToC), collapsing to two then one
  on smaller screens, matching tony.sh.
- Type badges next to symbols (class / function / async / classmethod /
  property) using the same `sphinx-ux-badges` visual conventions.
- Live type cross-references in signatures, hovering shows a small popover
  with the linked type's docstring summary.
- Search with full-text index over docstrings (Pagefind, configured by
  `gp-sphinx-astro-builder`).

---

## Testing strategy

Vitest v4 "projects" model at the `astro/` root. Each package isolated.

| Package | Test type | Strategy |
|---|---|---|
| `schema` | **Unit** | Fixture matrix: feed valid/invalid JSON to Zod, assert strict rejection of malformed payloads. Roundtrip tests for every shape. |
| `discover` | **Unit (memfs)** | Build directory trees in memory, assert package detection, namespace packages, exclusions. No real disk. |
| `parse` | **Snapshot** | Feed Python 3.14 source strings, assert `ModuleSymbols` matches stored snapshot. Covers PEP 695, PEP 649, decorators, `__all__`. |
| `bridge` | **Unit (mocked subprocess)** | `vi.mock('node:child_process')`. Exit codes, timeouts, stderr propagation, output truncation. **No real Python.** |
| `bridge` | **Integration (real uv, marked)** | One micro-integration that runs `uv run python -c '…'` with a known output. Marked `@integration`, run in CI but skipped in unit. |
| `intersphinx` | **Fixture** | Real committed `objects.inv` files (Python stdlib, tmuxp, libtmux). Assert URL resolution, name-shadowing rules. |
| `tsx-builder` | **Snapshot (libtmux)** | Run `analyzePackage('fixtures/libtmux')`, assert the entire `ApiIndex` matches a snapshot. **The regression harness.** |
| `astro-builder` | **Astro test utils** | Verify the integration registers correctly, the virtual module loads, the Content Loader returns the expected entries. One full `astro build` against the libtmux app in CI. |
| `astro-theme` | **Component (Astro Container API)** | Render each component with example props, assert key markup and class names are present. |

### libtmux as the reference fixture

The libtmux source is checked out into `astro/fixtures/libtmux/` at a pinned
ref (or imported via a workspace symlink for local dev). The
`tsx-builder` snapshot test runs against that exact tree. Everything
upstream feeds into it: parser changes, bridge changes, schema changes —
all surface as a libtmux-shaped diff that's easy to read.

When libtmux's actual API changes, we update the pinned ref and regenerate
the snapshot. That's also a moment to spot-check the rendered docs site —
they must still build cleanly.

---

## Build, lint, and CI

Following the AGENTS.md / CLAUDE.md conventions already in place:

### Root scripts (`astro/package.json`)

```json
{
  "scripts": {
    "build": "pnpm -r build",
    "dev": "pnpm -r --parallel dev",
    "test": "vitest",
    "test:unit": "vitest run --project=unit",
    "test:integration": "vitest run --project=integration",
    "type-check": "pnpm -r typecheck",
    "lint": "biome check .",
    "lint:fix": "biome check --fix .",
    "update:all": "pnpm -r up",
    "ncu": "npx npm-check-updates -u -r && pnpm install"
  }
}
```

### TypeScript baseline (`tsconfig.base.json`)

TS 5.9, strict mode, `verbatimModuleSyntax`, `isolatedDeclarations`,
`exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`,
`erasableSyntaxOnly`. Each package extends with declaration emit and
sourcemaps.

### Biome

Single config at `astro/biome.json`. Tab indentation, single quotes,
semicolons-as-needed (matching tony.sh). Rules: `noUnusedImports`,
`noUnusedVariables`, `useConst`, warn on `noNonNullAssertion`.

### CI

Two parallel pipelines:

| Pipeline | Runs |
|---|---|
| **Python** | `uv sync`, `uv run pytest`, `uv run mypy`, `uv run ruff check`, doctests. Unchanged from today. |
| **JS** | `pnpm install`, `pnpm test`, `pnpm typecheck`, `pnpm lint`, `pnpm build`. Runs in `astro/`. |

The JS pipeline has one more job: `pnpm --filter libtmux-docs build` against
the pinned libtmux fixture. Cached. Fails the build if the snapshot fixture
diverges without an explicit update.

---

## Migration path

This is a parallel stack, so there's no "switch over" date. Suggested
phases:

1. **Scaffold** the JS workspace, pin Astro 6.x, port the Tailwind plugin
   and font config. Get an empty libtmux-docs site building. **Goal: green
   CI on JS pipeline doing nothing useful yet.**
2. **Schema + discover + parse.** Pure Node. No Python. Snapshot test
   against the libtmux fixture for module discovery and structural
   extraction. **Goal: a JSON dump of "what's in libtmux" that matches
   reality.**
3. **Skeleton site.** Wire the Astro integration to consume the Node-only
   data, render `<ApiModule>` and `<ApiClass>` with annotation text only.
   **Goal: a libtmux docs site that renders every public symbol but with
   minimal type information.**
4. **Bridge + sidecar.** Add the Python sidecar. Now `<ApiFunction>`
   signatures show evaluated types, link cross-references, surface
   `__init__` docstrings inherited from parents. **Goal: parity with the
   current Sphinx autodoc output.**
5. **Intersphinx.** Hook up tmuxp + Python stdlib. Live cross-references in
   signatures and prose. **Goal: every linked type works.**
6. **Polish.** Search, theme switching, version dropdown, redirects from
   the existing Sphinx URL shape so old links keep working. **Goal:
   shippable replacement for libtmux.git-pull.com.**

At any point during phases 1–5 the existing Sphinx site continues to ship.
Phase 6 is the cutover.

---

## Open questions

- **Sphinx 8.1+ floor.** The existing gp-sphinx workspace requires Sphinx
  8.1+ for the typed `env.domains.<name>_domain` accessors. The Astro stack
  has no Sphinx dependency at runtime, but it does parse `objects.inv`
  files generated by Sphinx. Do we declare which Sphinx versions we'll
  guarantee parsing for? Today: v2 format only. Future: v3 if/when it
  ships.
- **Reusing existing Python infrastructure.** Several gp-sphinx packages
  (`sphinx-autodoc-typehints-gp`, `sphinx-autodoc-pytest-fixtures`,
  `sphinx-autodoc-fastmcp`) embed knowledge about how to introspect Python
  symbols. The sidecar could in principle import these as libraries to
  reuse their logic. Should it? Pros: less duplication, immediate parity.
  Cons: tight coupling to Sphinx-specific contracts, harder to publish the
  sidecar as a standalone tool. **Tentative answer: don't import them
  initially. Re-evaluate if we duplicate >200 lines of introspection
  logic.**
- **Schema export to JSON Schema.** Zod can emit JSON Schema. Should we
  publish that alongside the npm package so non-TypeScript consumers (a
  future Rust CLI? A VS Code extension?) can validate the same payloads?
  Cheap to add; defer the decision until we have a non-TS consumer.
- **Python version floor.** `annotationlib` is 3.14+. The bridge has
  fallback logic for older Pythons via `typing.get_type_hints`. Do we
  declare 3.14 as the recommended floor and 3.10 as the minimum (matching
  gp-sphinx's existing 3.10+ floor)? Probably yes.
- **Two annotation channels in the schema.** Worth the complexity? In
  practice the renderer almost always uses `annotationText`. The
  `annotationValue` is only consulted when we want to *link* a type. If
  this ends up underused after phase 4, consider collapsing.
- **MDX vs Markdown.** Astro supports both. Existing Sphinx prose is RST.
  Migration: docutils-converted RST→MD via the sidecar handles the bulk;
  pages with rich directives need hand-conversion to MDX. Plan to convert
  ~80% mechanically and hand-fix the rest.
- **Search.** Pagefind is the default plan (static, fast, no infra). If
  search quality is poor we revisit (Algolia? local Lunr?). Pagefind
  doesn't index API symbols by default — the `astro-builder` integration
  emits a `_pagefind` data attribute on each `<ApiClass>` so symbols are
  indexed.

---

## What this plan deliberately does not do

- **Replace the Sphinx pipeline.** gp-sphinx's Sphinx side is mature and
  has 14 packages worth of investment. This is parallel work for projects
  that want a different rendering layer.
- **Auto-author Astro pages.** The user explicitly wants consumers to
  write their own Astro pages. The integration provides data and
  components; routing and composition are the consumer's call.
- **Handle non-Python languages.** Tree-sitter is generic but the bridge,
  schema, and components are Python-specific. A future `gp-sphinx-astro-c`
  or `-rust` would be a separate effort with shared schema scaffolding.
- **Provide a CLI.** The `tsx-builder` package is a library. If a CLI is
  useful later (`gp-sphinx-astro analyze ./libtmux > api.json`), it ships
  as a separate `gp-sphinx-astro-cli` package.

---

## Pointers

- Existing CSS / class conventions: `CLAUDE.md` "CSS Standards" — `gp-sphinx-*`
  tier A/B namespacing, axis-value modifiers, custom property mirroring.
  The Astro stack extends with `gp-sphinx-astro-*`.
- Test patterns: `CLAUDE.md` "Testing Strategy" — type-annotated functions,
  `NamedTuple` parametrization, snapshot fixtures via `tests/_snapshots.py`.
  The JS side mirrors the spirit but uses Vitest snapshots.
- Logging: `CLAUDE.md` "Logging Standards" — lowercase, past-tense, lazy
  formatting, structured `extra`. Apply to Python sidecar; the Node side
  uses Astro's logger.
- Commit format: `Scope(type[detail]): description` from `CLAUDE.md`
  "Git Commit Standards." Suggested scope for this work: `astro` (e.g.
  `astro(feat[bridge])`).
