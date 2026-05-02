# gp-sphinx-vite

Transparent Vite + pnpm orchestration for Sphinx theme asset pipelines.

A Sphinx extension that spawns `pnpm exec vite build --watch` from
`builder-inited` so theme authors iterating templates and SCSS get fresh
`furo.css` / `furo.js` on disk without remembering a separate
`vite build` command. The extension is a no-op in production (when
`sphinx-build` runs without the autobuild driver), so wheels published to
PyPI never carry a Node runtime requirement.

## Status

Skeleton — only `setup()` and config-value registration are wired up.
Subprocess management (`ViteProcess`), the asyncio↔threading bridge, and
the actual spawn/teardown lifecycle (with signal handling and idempotent
re-spawn for `sphinx-autobuild`) land in subsequent commits.

## Usage (eventual)

```python
# conf.py
extensions = ["gp_sphinx_vite"]

# Optional. Defaults to "auto": dev iff SPHINX_AUTOBUILD env var is set
# or sys.argv[0] ends with "sphinx-autobuild"; prod (no-op) otherwise.
gp_sphinx_vite_mode = "auto"

# Optional. Path to the directory containing package.json + vite.config.ts.
# Defaults to <theme directory>/web (resolved relative to the active theme).
gp_sphinx_vite_root = None
```

## Config

| Name | Type | Default |
|------|------|---------|
| `gp_sphinx_vite_mode` | `Literal["auto", "dev", "prod"]` | `"auto"` |
| `gp_sphinx_vite_root` | `str \| None` | `None` (auto-detect) |
