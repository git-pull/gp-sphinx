# sphinx-vite-builder

```{gp-sphinx-package-meta} sphinx-vite-builder
```

A [PEP 517](https://peps.python.org/pep-0517/) build backend and Sphinx extension that orchestrates
[Vite](https://vitejs.dev/) builds via [pnpm](https://pnpm.io/) for any
Sphinx-theme package whose static assets (CSS / JS) are produced by a
JavaScript toolchain. The same pattern that
[maturin](https://github.com/PyO3/maturin) uses for Rust+Python and
that [sphinx-theme-builder](https://github.com/pradyunsg/sphinx-theme-builder)
uses for webpack, applied to vite + pnpm.

```console
$ pip install sphinx-vite-builder
```

## Two heads, one core

### [PEP 517](https://peps.python.org/pep-0517/) build backend

Drop-in replacement for `hatchling.build`. Runs `pnpm exec vite build`
before delegating wheel/sdist construction to hatchling. End users who
`pip install` from PyPI don't need pnpm or Node — the wheel ships with
the static assets already populated.

```toml
# packages/your-theme/pyproject.toml
[build-system]
requires = ["hatchling>=1.0", "sphinx-vite-builder"]
build-backend = "sphinx_vite_builder.build"
backend-path = ["../sphinx-vite-builder/src"]    # for in-tree workspace consumption
```

### Sphinx extension

Loaded from `conf.py`. Hooks the Sphinx event lifecycle so
`sphinx-build` / `sphinx-autobuild` automatically run the right vite
invocation — one-shot for production builds, watch mode for autobuild —
without contributors needing a justfile or Makefile.

```python
# docs/conf.py
extensions = ["sphinx_vite_builder"]
```

## Fast-fail diagnostics

When prerequisites are missing the backend / extension raises
actionable errors rather than producing broken output:

- `PnpmMissingError` — `pnpm` not on `PATH`; hint includes
  `corepack enable` and the [pnpm.io/installation](https://pnpm.io/installation) URL
- `NodeModulesInstallError` — `pnpm install` exited non-zero; hint
  includes the rerun command
- `ViteFailedError` — `pnpm exec vite build` exited non-zero; hint
  surfaces the captured stderr

Set `SPHINX_VITE_BUILDER_SKIP=1` in the environment to short-circuit
the backend (e.g., when an external orchestration handles vite).

```{package-reference} sphinx-vite-builder
```
