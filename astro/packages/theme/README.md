# @gp-sphinx/astro

Astro components, Zod wire-format schemas, and render utilities for the
gp-sphinx documentation platform. Consumes typed JSON emitted by the
`gp-sphinx-astro-builder` Sphinx extension and renders it through Astro
components styled with Tailwind v4.

## CSS-token strategy: dual coexistence

This package and the consuming Astro app load **two token sets**
side-by-side. The namespaces are disjoint, so they compose without
overrides:

| Token set | Variable prefix | Source | Used by |
|---|---|---|---|
| Astro OKLCH palette | `--color-bg`, `--color-fg`, `--color-accent`, `--color-admonition-{note,tip,…}`, `--color-link-*` | `astro/apps/gp-sphinx-docs/src/styles/global.css` `@theme` block | App-shell components (TopNav, Sidebar, TableOfContents, MobileSidebar, Footer) |
| Furo CSS-variable contract | `--color-background-primary`, `--color-foreground-primary`, `--color-content-foreground`, `--admonition-*`, `--api-*`, `--sidebar-*`, … (169 tokens) | `@gp-sphinx/furo-tokens` Tailwind v4 plugin loaded in `global.css` | (future) rendering components — admonitions, links, code blocks, field lists, prose |

The Furo set is a byte-for-byte port of upstream Furo's SCSS contract
maintained by `@gp-sphinx/furo-tokens`. Loading both lets components
inside this package start picking the right token namespace per
concern: anything that mirrors a Furo HTML render (Sphinx body content,
admonitions, autodoc layout) reaches for Furo tokens; anything that's
unique to the Astro UI (top nav, sidebar drawer, theme toggle) reaches
for the Astro OKLCH palette.

### Migration path (planned, not yet executed)

- **Now:** components reference Astro OKLCH tokens. Furo tokens are
  available but unused inside this package.
- **Step 1:** rendering components migrate to Furo tokens for shared
  concepts (admonitions, links, code, prose). When the first such
  migration lands, `peerDependency` on `@gp-sphinx/furo-tokens` is
  declared on this package's `package.json`.
- **Step 2:** the Astro OKLCH palette in `global.css` shrinks to the
  ~10 tokens app-shell components actually use. Everything else flows
  from `@gp-sphinx/furo-tokens`.

### Known divergence (dark mode)

The Furo plugin emits dark-mode tokens under `body[data-theme="dark"]`,
while the Astro app uses `:root[data-theme-mode="dark"]`. Light tokens
activate unconditionally; dark Furo tokens require either:

- a small selector-bridging shim in `global.css` (`:root[data-theme-mode="dark"] body { /* re-emit furo dark tokens */ }`), or
- an upstream tweak to `@gp-sphinx/furo-tokens` to also emit dark
  tokens under `:root[data-theme-mode="dark"]`.

This is a deferred task; until it's resolved, dark mode in the Astro
site renders with the Astro OKLCH palette as designed and Furo dark
tokens are dormant.

## Layout

```
astro/packages/theme/
├── src/
│   ├── index.ts                # public exports + VERSION
│   ├── schemas/                # Zod wire-format schemas (parity-tested with Pydantic)
│   │   ├── doctree.ts
│   │   ├── symbol.ts
│   │   └── xref.ts
│   ├── render/                 # render utilities (reused across pages)
│   │   ├── build-toc.ts
│   │   ├── extract-description.ts
│   │   ├── highlight-code.ts
│   │   ├── render-node.ts
│   │   ├── render-symbol.ts
│   │   └── render-with-highlighting.ts
│   └── components/             # Astro components, one per node type
└── test/                       # vitest suites (parity, smoke, render)
```

## Workflow

```console
$ pnpm --filter "@gp-sphinx/astro" test
```

```console
$ pnpm --filter "@gp-sphinx/astro" run type-check
```

The package is private (`workspace:^` only) and ships no built
artifacts — Astro's vite pipeline picks up `.ts` / `.astro` source
directly via the consuming app's `tsconfig` extension.
