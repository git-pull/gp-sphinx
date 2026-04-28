# AGENTS.md (Astro side)

This is the Astro static-site renderer for the gp-sphinx documentation
platform. It consumes typed JSON emitted by the
`gp-sphinx-astro-builder` Sphinx extension and renders it through Astro
components styled with Tailwind v4.

The full design lives in `notes/plans/astro.md` (workspace root).

## Layout

```
astro/
├── pnpm-workspace.yaml          # pnpm workspace config
├── package.json                 # root scripts: test, lint, format, type-check
├── biome.json                   # lint + format
├── tsconfig.base.json           # strict TypeScript baseline
└── packages/
    └── theme/                   # @gp-sphinx-astro/theme
        ├── src/                 # source: components, schemas, index.ts
        └── test/                # vitest tests
```

## Workflow

```console
$ pnpm -C astro install
```

```console
$ pnpm -C astro test
```

```console
$ pnpm -C astro lint
```

```console
$ pnpm -C astro type-check
```

All four must be green before any commit.

## Conventions

- Match `/home/d/work/python/gp-sphinx/CLAUDE.md` where applicable: CSS
  namespace `gp-sphinx-astro-*`, commit format
  `Scope(type[detail]): description` with `why:` + `what:` blocks.
- TypeScript: strict mode, no implicit `any`, no unchecked indexed
  access, `verbatimModuleSyntax` on, `import type` for type-only imports.
- Zod: `zod/v4` import path. Hand-written schemas in
  `packages/theme/src/schemas/` mirror the Pydantic models in the
  builder; a Vitest parity test asserts they produce equivalent JSON
  Schemas after normalising Pydantic's OpenAPI discriminator quirk.
- Vitest: tests live in each package's `test/` directory; default
  `*.test.ts` pattern.
- Biome: replaces ESLint + Prettier; one tool, lint and format together.
