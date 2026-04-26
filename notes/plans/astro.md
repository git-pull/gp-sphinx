# Astro Documentation Platform for gp-sphinx

**Branch:** `astro-2026-04-26` **Status:** plan, not yet implemented

## What we're building

A documentation platform that gives Python projects a fast, modern,
beautifully themed Astro site with the same API-rendering capabilities
Sphinx's `autodoc` and `intersphinx` extensions provide today. Three
published NPM packages plus one workspace Python package. The Astro site
reads structured API data from a small Python helper, validates it on
the TypeScript side, and renders it through a visual theme derived from
`~/work/tony.sh`. The first site we'll build with it documents
`gp-sphinx` and the fourteen `sphinx-*` packages currently in this
repository; the second documents `libtmux`.

## Why

The Sphinx-based docs sites at `*.git-pull.com` are functional but
visually dated, slow to iterate on, and constrained by Furo's
customization surface. Astro gives modern theming (CVA + Tailwind v4),
fast static builds, content collections with typed frontmatter, MDX for
component-heavy pages, and a much better local development loop. We keep
Python as the source of truth for API data because that's where the
introspection has to happen — Python's runtime knows what's an
`enum.Enum`, what's `@dataclasses.dataclass`, what `inspect.signature`
returns, and what the new `annotationlib.Format` enum on Python 3.14+
produces. We don't try to reimplement that in TypeScript.

## The map from Sphinx to Astro

| Sphinx primitive | What we build |
|---|---|
| `Builder` (HTML, JSON, dirhtml) | An Astro integration that registers a content loader and a few virtual modules. The Astro build is the build. |
| `autodoc` extension | A TypeScript engine that calls a small Python helper. The helper introspects the configured packages with `inspect.signature` + `annotationlib`; the engine validates the JSON it gets back with Zod and exposes a typed graph. |
| Python domain index (`env.domains.python_domain.data["objects"]`) | The same idea, served as a typed JSON graph through a virtual module the theme imports. |
| `intersphinx` extension + `objects.inv` files | A TypeScript parser for `objects.inv`, plus an Astro plugin that resolves cross-project references at build time. |
| Theme (Furo, alabaster, etc.) | An Astro component set derived from `~/work/tony.sh` — IBM Plex fonts, OKLCH color tokens, CVA variants, syntax highlighting via `astro-expressive-code`. |
| MyST (Markdown for Sphinx) | Astro's built-in Markdown plus optional MDX for pages that need components. The Markdown parser stays MyST-flavoured because that's what `gp-sphinx`'s existing extensions already configure. |

## The packages

### `gp-sphinx-astro-builder` — the Astro integration

This is what an Astro site installs. A consumer's `astro.config.mjs`
looks like:

```ts
import { defineConfig } from 'astro/config'
import gpSphinxAstro from 'gp-sphinx-astro-builder'

export default defineConfig({
  site: 'https://gp-sphinx.git-pull.com',
  integrations: [gpSphinxAstro({ packages: ['gp_sphinx', 'sphinx_gp_theme'] })],
})
```

It hooks into Astro's standard integration points (`astro:config:setup`,
`astro:server:setup`) and does three things:

- Registers a content collection backed by a custom content loader. The
  loader runs `gp-sphinx-tsx-builder` against the configured Python
  packages, validates the result, and exposes it through a virtual
  module (`virtual:gp-sphinx-astro/api`) that the theme imports.
- Provides an MDX integration alongside the default Markdown so authors
  can pick `.md` for prose and `.mdx` for component-heavy pages without
  changing config.
- Wires the dev server's HMR loop: when a watched Python file changes,
  the builder re-runs, the cached graph is invalidated through
  `server.moduleGraph.invalidateModule`, and the page hot-reloads.

The integration is the only thing site authors install directly.
Everything else (`gp-sphinx-tsx-builder`, `gp-sphinx-astro-theme`,
`gp-sphinx-astro-py`) gets pulled in transitively.

### `gp-sphinx-tsx-builder` — the TypeScript engine

Public surface is TypeScript. Internally it spawns the Python helper
through `uv run` (or `uvx` for ephemeral runs), parses the helper's
stdout as JSON, validates it against Zod schemas, and returns a typed
`ApiGraph` object. Independently testable with Vitest — the test suite
uses small fixture packages to exercise each symbol kind.

A few practical points the engine has to handle:

- One Python process per build invocation, not a long-lived daemon. The
  Astro build calls the engine once; the engine calls Python once.
- The helper's stdout is the only data channel; stderr is captured for
  error reporting.
- Each call writes its output to a content-hashed file under
  `.astro/cache/` so a partial Python failure doesn't poison the next
  clean build.
- Schema-version mismatch between the JS schema and the Python helper is
  a hard build failure, not a warning.

### `gp-sphinx-astro-theme` — the visual layer

A package of Astro components plus the Tailwind preset that styles them.
Component shapes follow tony.sh: CVA for variant-driven components
(`SymbolCard`, `Badge`, `Sidebar`), `astro-expressive-code` for syntax
highlighting, IBM Plex Sans + Mono via Fontsource. Color tokens are
OKLCH-defined CSS custom properties under the
`--gp-sphinx-astro-theme-*` namespace, mirroring `gp-sphinx`'s existing
CSS-namespace convention.

Components are independently consumable: the theme exposes the
primitives, but the integration's content collection is the canonical
wiring. A site can use a theme component without using the integration
if it wants.

### `gp-sphinx-astro-py` — the Python introspection helper

A small Python workspace package living at
`astro/python/gp-sphinx-astro-py/`. Member of the existing root
`pyproject.toml`'s `[tool.uv.workspace.members]` so it's installable
through the same `uv sync` that installs every other Python package in
the repo.

One CLI entry point (declared in `pyproject.toml` as
`gp-sphinx-astro-py` mapping to `gp_sphinx_astro_py.cli:main`):

```console
$ uv run gp-sphinx-astro-py introspect <package> [--format json]
```

The command imports the named package, walks its public surface using
`inspect`, `annotationlib.get_annotations(..., format=Format.STRING)`,
and `__all__` where present, and emits JSON shaped to match the Zod
schema in `gp-sphinx-tsx-builder`. NumPy-style docstrings are passed
through unchanged; the TypeScript side renders them. Existing autodoc
extensions in this repo (`sphinx-autodoc-typehints-gp`,
`sphinx-autodoc-pytest-fixtures`, `sphinx-autodoc-fastmcp`, etc.) can
register entry points under the `gp_sphinx_astro_py.contributors` group
to add symbol-kind-specific data without modifying the helper itself.

The package follows the project's existing Python conventions: `from
__future__ import annotations`, namespace imports (`import enum`,
`import typing as t`), NumPy-style docstrings with working doctests,
plain-function tests with `t.NamedTuple` parametrization where useful.
Python ≥3.10; Python 3.14+ gives the cleanest annotation output.

## Intersphinx

Sphinx projects publish an `objects.inv` file at the root of their built
docs. Other projects download those inventories, parse them, and use
them to resolve cross-project references like `:py:func:`os.path.join``.
We need the same capability.

Two pieces:

- A TypeScript parser for `objects.inv` (zlib-deflated record format,
  well-documented in Sphinx). Pure function: bytes in, typed inventory
  out. Vitest tests against fixture inventories. Whether this lives
  inside `gp-sphinx-tsx-builder` or as its own small package is a
  packaging detail — start it as a module inside the TS builder, split
  out if a second consumer appears.
- An Astro plugin (registered by `gp-sphinx-astro-builder`) that
  downloads the configured external inventories at build time, parses
  them, and exposes a `resolveXref(domain, role, target)` helper plus a
  remark plugin that rewrites `:py:func:` links in Markdown content to
  resolved URLs.

External inventories the first sites will need: Python stdlib
(`docs.python.org/3/objects.inv`), Sphinx, docutils, pytest. Internal
inventories: cross-references between the fourteen `sphinx-*` packages
so links between them resolve.

## How it works at runtime

The build proceeds top-to-bottom:

1. Astro starts (`astro build` or `astro dev`) and loads its config. The
   config calls `gpSphinxAstro({ packages: ["gp_sphinx",
   "sphinx_gp_theme", ...] })` from `gp-sphinx-astro-builder`.
2. The integration registers its content loader and virtual modules with
   Astro.
3. The content loader runs. It calls `gp-sphinx-tsx-builder.build({
   packages, root, cache })`.
4. The TS builder spawns the Python helper through `uv run
   gp-sphinx-astro-py introspect <packages>`.
5. The Python helper imports each package, walks its public surface, and
   writes JSON to stdout.
6. The TS builder validates the JSON against its Zod schemas and returns
   a typed `ApiGraph`.
7. The content loader exposes the graph through
   `virtual:gp-sphinx-astro/api`.
8. The theme components import from the virtual module and render pages.
9. In `astro dev`, file watchers re-trigger steps 3–8 when a watched
   Python file or content file changes; the rest of the page tree is
   preserved.

## Where everything lives

The four new packages and the Astro example site live under a new
top-level `astro/` directory inside the existing monorepo:

```
gp-sphinx/
├── packages/                          # existing 14 sphinx-* packages, unchanged
├── pyproject.toml                     # existing root; gains one new uv workspace member
├── astro/
│   ├── pnpm-workspace.yaml
│   ├── package.json                   # root scripts: build, dev, test, lint, type-check
│   ├── biome.json
│   ├── vitest.workspace.ts
│   ├── tsconfig.base.json             # extends astro/tsconfigs/strictest
│   ├── packages/
│   │   ├── builder/                   # @gp-sphinx-astro/builder (gp-sphinx-astro-builder)
│   │   ├── tsx-builder/               # @gp-sphinx-astro/tsx-builder (gp-sphinx-tsx-builder)
│   │   └── theme/                     # @gp-sphinx-astro/theme (gp-sphinx-astro-theme)
│   ├── python/
│   │   └── gp-sphinx-astro-py/        # uv workspace member
│   │       ├── pyproject.toml
│   │       ├── src/gp_sphinx_astro_py/
│   │       └── tests/
│   ├── apps/
│   │   └── gp-sphinx-docs/            # the first site, documents gp-sphinx itself
│   ├── fixtures/                      # test fixtures shared across packages
│   └── AGENTS.md                      # Astro-side conventions for AI agents
```

The pnpm workspace is rooted at `astro/`. The Python helper joins the
existing uv workspace through one addition to the root `pyproject.toml`:

```toml
[tool.uv.workspace]
members = [
    "packages/*",
    "astro/python/gp-sphinx-astro-py",  # new
]
```

CI runs both `uv sync --all-packages` and `pnpm -C astro install` and
gates on both stacks staying green.

## First consumer: gp-sphinx itself

The first site we ship with the new platform documents `gp-sphinx` and
its fourteen child packages. This is intentional dogfood: the platform
documents the package whose docs platform it's replacing. It also forces
the renderer to handle every symbol kind that matters, because the
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

The site lives at `astro/apps/gp-sphinx-docs/`. It deploys to the same
AWS infrastructure the existing docs use (S3 + CloudFront + Cloudflare
DNS) so we don't introduce a second cloud provider. Per-PR previews go
to a new bucket served through the existing CloudFront distribution with
a path-based behavior.

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

The libtmux site replaces `libtmux.git-pull.com`. Build the renderer's
component set with libtmux's surface in mind from the start so the
second consumer is mostly a config change, not new code.

## Build sequence

In order. Each step is small enough to land as a single PR; each "done
when" is an objective check.

1. **Scaffold the workspace.** Create `astro/`, the pnpm workspace, the
   Biome config, the Vitest workspace config, the TypeScript base config
   (`extends "astro/tsconfigs/strictest"`), the `astro/AGENTS.md`. Empty
   placeholder packages for `builder`, `tsx-builder`, `theme`. Add
   `astro/python/gp-sphinx-astro-py` as a uv workspace member with one
   no-op CLI command. Done when `pnpm -C astro install`, `pnpm -C astro
   test`, `pnpm -C astro lint`, `pnpm -C astro type-check`, and `uv sync
   --all-packages` all pass with empty packages, and CI runs both
   stacks.
2. **Introspect one symbol.** Make `gp-sphinx-astro-py introspect
   gp_sphinx` emit JSON for `gp_sphinx.config.merge_sphinx_config` —
   name, signature, parameters, return annotation, docstring. Done when
   the JSON validates against a hand-written Zod schema in
   `gp-sphinx-tsx-builder` and a Vitest snapshot test passes.
3. **Wire the TS builder.** `gp-sphinx-tsx-builder.build()` spawns the
   Python helper, parses stdout, returns a typed `ApiGraph`. Done when a
   Vitest test calls `build({ packages: ["gp_sphinx"] })` and gets back
   a validated graph containing the symbol from step 2.
4. **Wire the Astro integration.** `gp-sphinx-astro-builder` registers a
   content loader that calls the TS builder and exposes the graph
   through `virtual:gp-sphinx-astro/api`. Done when an empty
   `astro/apps/gp-sphinx-docs/` site can `import { graph } from
   'virtual:gp-sphinx-astro/api'` at build time and access the symbol
   from step 2.
5. **First theme component.** `gp-sphinx-astro-theme` exports a
   `<SymbolCard symbol={...} />` Astro component that renders one symbol
   with its signature and docstring. Done when the dogfood site's index
   page renders the `merge_sphinx_config` card and the OKLCH theme
   tokens are visibly applied.
6. **Loop through the symbol kinds.** Add introspection support and
   theme components for each kind in turn (classes, enums, dataclasses,
   directives, roles, config values, pytest fixtures, MCP tools,
   argparse CLIs). Done when each kind has a test fixture, a passing
   Vitest snapshot, and renders correctly in the dogfood site.
7. **Intersphinx.** Add the `objects.inv` parser, the Astro plugin, and
   the remark integration. Configure the dogfood site to consume Python
   stdlib + Sphinx + docutils + pytest inventories. Done when a Markdown
   link `[merge](:py:func:\`gp_sphinx.config.merge_sphinx_config\`)`
   resolves to the right page during build.
8. **Deploy the dogfood site.** Wire the existing GitHub Actions docs
   workflow to also build and deploy the Astro site to a parallel S3
   bucket served through the existing CloudFront distribution. Done when
   the dogfood site is publicly accessible.
9. **Switch on libtmux.** Configure a second Astro app (or extend the
   dogfood site, depending on whether we want one URL or two) to
   introspect libtmux. Done when libtmux's docs site is rebuilt with the
   new platform.

## Standards

The new code follows the conventions in this repo's `CLAUDE.md`.
Highlights that apply directly to this work:

- **CSS namespace.** All classes the new components emit use
  `gp-sphinx-astro-*` (Tier A) or `gp-sphinx-astro-<pkg>__<thing>` (Tier
  B BEM). Custom properties use `--gp-sphinx-astro-<token>`. The new
  theme never touches Furo's CSS variables — Furo-themed sites continue
  to work.
- **Python imports.** The Python helper uses namespace imports (`import
  enum`, `import typing as t`); `from __future__ import annotations`;
  NumPy-style docstrings with working doctests on every public function.
- **Tests.** Plain functions, no `class TestFoo:` groupings.
  `t.NamedTuple` for parametrization where it improves readability. The
  lightest test level that exercises the behavior — Vitest unit tests by
  default; integration tests against full Astro builds only when wiring
  is what's being tested.
- **Commits.** `Scope(type[detail]): description` with `why:` and
  `what:` blocks, as elsewhere in this repo.

The TypeScript packages follow the same patterns `~/work/tony.sh` uses:
Biome for lint and format, Vitest for tests (workspace projects per
package), CVA for variant-driven components, Zod 4 for schemas, pnpm via
Corepack (pinned in `package.json`'s `packageManager` field), `extends
"astro/tsconfigs/strictest"` for the base TypeScript config.

## Decisions to make later

These don't block any of the steps above. Each gets resolved at the
point it actually matters.

- **Whether to enforce `.md` only or allow `.md` plus `.mdx`.** Astro's
  MDX integration with `extendMarkdownConfig: true` lets both formats
  coexist with the same remark plugins, so this is a policy choice, not
  a technical one. Default to allowing both; add a lint rule to enforce
  `.md`-only later if we want.
- **Which OKLCH palette and the Furo color-token mapping.** tony.sh
  ships four palettes (amber, emerald, purple, sky); pick one when
  there's a renderer to look at and decide how Furo's `--color-api-*`
  tokens map to the new ones. Calibrating against an empty page is
  unrewarding.
- **How the libtmux fixture stays current.** The libtmux site needs a
  test fixture — vendor a snapshot, use a git submodule, or regenerate
  from the live `~/work/python/libtmux` checkout when something changes
  upstream. Decide when libtmux is the active consumer; until then a
  vendored snapshot is fine.

## Pointers

Read-only references for anyone implementing this. None of these get
modified.

- `~/study/python/sphinx/sphinx/builders/` — for the `Builder` class
  shape and lifecycle methods (`init`, `prepare_writing`, `write_doc`,
  `finish`). The Astro integration plays the same role on the Astro
  side.
- `~/study/python/sphinx/sphinx/domains/python/__init__.py` — for the
  typed `ObjectEntry` records the Python domain stores. Useful when
  deciding what fields the JSON helper should emit.
- `~/study/python/docutils/docutils/nodes.py` — for the docutils node
  tree the Python helper sees when it walks documents.
- `~/study/python/myst-parser/myst_parser/` — for the
  Markdown-to-doctree parser. `gp-sphinx`'s existing extensions
  configure this; the Python helper uses it when it parses MyST-flavored
  docstrings.
- `~/study/typescript/astro/packages/astro/src/integrations/` — for the
  integration API the Astro builder package plugs into.
- `~/study/typescript/astro/packages/integrations/mdx/src/index.ts` —
  for the `extendMarkdownConfig` mechanism that lets `.md` and `.mdx`
  share remark plugins.
- `~/work/tony.sh/packages/astro/` — the theme template the new theme is
  derived from; component patterns, OKLCH palette, Tailwind v4 setup.
- `/home/d/work/python/gp-sphinx/CLAUDE.md` — repo conventions the new
  code has to follow.
