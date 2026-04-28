(gp-sphinx-astro-builder)=

# gp-sphinx-astro-builder

```{gp-sphinx-package-meta} gp-sphinx-astro-builder
```

:::{admonition} Pre-alpha
:class: warning

This package is the in-progress Sphinx builder for the planned Astro
documentation platform (see `notes/plans/astro.md` in the workspace
root). Public API is not yet stable; nothing here is wired into a
shipped site.
:::

A Sphinx builder that walks each doctree and emits typed JSON
validated by Pydantic v2 models. The output is consumed by an Astro
static site through standard content collections, with Zod schemas
on the TypeScript side kept in parity with the Pydantic models
through a JSON Schema 2020-12 snapshot test.

For install and source links, see the package
[README](https://github.com/git-pull/gp-sphinx/tree/main/packages/gp-sphinx-astro-builder#readme).
The architecture overview lives in
[`notes/plans/astro.md`](https://github.com/git-pull/gp-sphinx/blob/main/notes/plans/astro.md).

```{package-reference} gp-sphinx-astro-builder
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/gp-sphinx-astro-builder)
