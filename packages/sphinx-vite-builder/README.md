# sphinx-vite-builder

PEP 517 build backend and Sphinx extension that transparently orchestrates
[Vite](https://vitejs.dev/) builds via [pnpm](https://pnpm.io/) for
Sphinx-theme packages whose static assets (CSS / JS) are produced by a
JavaScript toolchain.

## What it solves

A common pattern for modern Sphinx themes is a Python package whose
`theme/<name>/static/` directory ships built CSS and JS that were
produced by a JS build tool (Vite, webpack, …). The build artefacts are
gitignored — they're reproducibly built, not source code. But that
creates two friction points:

1. **Editable installs and source-tree builds** crash with confusing
   errors when the static dir is empty (e.g. hatchling's
   `Forced include not found`).
2. **CI workflows** must duplicate `pnpm install + vite build` setup
   steps in every job that touches the package.

`sphinx-vite-builder` owns the Vite invocation end-to-end — exactly the
way [maturin](https://github.com/PyO3/maturin) owns Cargo for
Rust+Python packages, or
[sphinx-theme-builder](https://github.com/pradyunsg/sphinx-theme-builder)
owns webpack for older Sphinx themes.

## Two heads, one subprocess core

### PEP 517 build backend

Drop-in replacement for `hatchling.build`. Runs `pnpm exec vite build`
before delegating wheel/sdist construction to hatchling.

```toml
# packages/your-theme/pyproject.toml
[build-system]
requires = ["hatchling>=1.0", "sphinx-vite-builder"]
build-backend = "sphinx_vite_builder.build"
backend-path = ["../sphinx-vite-builder/src"]    # for in-tree workspace consumption
```

The backend short-circuits when `web/` (the Vite source tree) is absent
— so `pip install <pkg>.tar.gz` from an unpacked sdist works without
pnpm or Node, because the sdist already contains pre-baked
`static/`.

### Sphinx extension

Loaded from `conf.py`. Runs Vite as part of the docs lifecycle:

- `sphinx-build` → `pnpm exec vite build` once before the docs build
- `sphinx-autobuild` → `pnpm exec vite build --watch` as a child process
  for the lifetime of the autobuild server, with idempotent re-fire on
  rebuilds and graceful teardown on signal / `atexit`

```python
# docs/conf.py
extensions = ["sphinx_vite_builder"]
sphinx_vite_root = "../packages/your-theme/web"   # path to vite project
sphinx_vite_mode = "auto"                          # auto | dev | prod | disabled
```

## Fast-fail diagnostics

When prerequisites are missing the backend / extension raises
actionable errors rather than producing broken output:

- `PnpmMissingError` — `pnpm` not on `PATH`; hint includes
  `corepack enable` and the `pnpm.io` install URL
- `NodeModulesInstallError` — `pnpm install` exited non-zero; hint
  includes the rerun command
- `ViteFailedError` — `pnpm exec vite build` exited non-zero; hint
  surfaces the captured stderr

## License

MIT — see [LICENSE](LICENSE).
