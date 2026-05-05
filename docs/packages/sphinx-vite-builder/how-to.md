(sphinx-vite-builder-how-to)=

# How to

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

Loaded from `conf.py`. Hooks `builder-inited` and `build-finished` so
`sphinx-build` and `sphinx-autobuild` automatically run the right vite
invocation: a one-shot `pnpm exec vite build` for plain `sphinx-build`
(or `sphinx_vite_builder_mode = "prod"`), a long-lived
`pnpm exec vite build --watch` child process for `sphinx-autobuild`
(or `sphinx_vite_builder_mode = "dev"`), with graceful SIGTERM →
SIGKILL teardown on signal / `atexit`.

```python
# docs/conf.py
extensions = ["sphinx_vite_builder"]
sphinx_vite_builder_mode = "auto"        # "auto" | "dev" | "prod"
sphinx_vite_builder_root = "/abs/path/to/web"
```

`"auto"` resolves to `"dev"` when the build is running under
`sphinx-autobuild` (detected via `SPHINX_AUTOBUILD` env var, `argv[0]`,
or parent-process inspection on Linux), otherwise `"prod"`. Setting
`sphinx_vite_builder_root` to `None` (the default) makes the extension
a complete no-op — useful when the consumer is installed from a wheel
where the static tree is already pre-baked.

## Fast-fail diagnostics

When prerequisites are missing the backend / extension raises
actionable errors rather than producing broken output:

- `PnpmMissingError` — `pnpm` not on `PATH`; hint includes
  `corepack enable`, the [pnpm.io/installation](https://pnpm.io/installation)
  URL, and a per-CI YAML/config snippet (GitHub Actions, CircleCI,
  Azure Pipelines, GitLab CI) when the build is detected to be
  running in CI.
- `NodeModulesInstallError` — `pnpm install` exited non-zero; hint
  includes the rerun command and captured stderr.
- `ViteFailedError` — `pnpm exec vite build` exited non-zero; hint
  surfaces the captured stderr.

Set `SPHINX_VITE_BUILDER_SKIP=1` in the environment to short-circuit
the backend (e.g., when an external orchestration handles vite).

```{package-reference} sphinx-vite-builder
```
