# gp-sphinx-vite

```{gp-sphinx-package-meta} gp-sphinx-vite
```

Transparent [Vite] + [pnpm] orchestration for Sphinx theme asset
pipelines. A Sphinx extension that spawns `pnpm exec vite build --watch`
from `builder-inited` so theme authors iterating templates and styles
get fresh `furo.css` / `furo.js` on disk without remembering a separate
`vite build` command. The extension is a no-op in production, so wheels
published to PyPI never carry a Node runtime requirement.

```console
$ pip install gp-sphinx-vite
```

## Status

Skeleton — only {py:func}`~gp_sphinx_vite.setup` and config-value
registration are wired up. Subprocess management (`ViteProcess`), the
asyncio↔threading bridge, and the actual spawn/teardown lifecycle
(with signal handling and idempotent re-spawn for [sphinx-autobuild])
land in subsequent commits.

## Downstream `conf.py` (eventual)

```python
extensions = ["gp_sphinx_vite"]

# Optional. Defaults to "auto": dev iff SPHINX_AUTOBUILD env var is set
# or sys.argv[0] ends with "sphinx-autobuild"; prod (no-op) otherwise.
gp_sphinx_vite_mode = "auto"

# Optional. Path to the directory containing package.json + vite.config.ts.
# Defaults to <theme directory>/web (resolved relative to the active theme).
gp_sphinx_vite_root = None
```

```{package-reference} gp-sphinx-vite
```

## Wiring `just build` / `make build` for downstream users

[sphinx-autobuild] runs `gp_sphinx_vite`'s `builder-inited` hook,
which detects the autobuild process by argv0 / the `SPHINX_AUTOBUILD`
env var and spawns `pnpm exec vite build --watch` itself — so
`sphinx-autobuild docs/ _build/html` "just works" with no extra
plumbing. Plain `sphinx-build` runs in `prod` mode where the
extension is intentionally a no-op (so wheels published to PyPI
never require a Node runtime), so the `vite build` step has to
happen *before* `sphinx-build` in the orchestration layer that
calls it.

A small `assets-build` recipe that depends on every HTML-output
target covers the gap. The recipe is idempotent — it skips the
build when no `web/` source tree is present (wheel install with
pre-built assets) or when `pnpm` isn't on PATH (graceful
degradation; any pre-existing output remains in place).

### justfile

```text
# Build vite-managed theme assets before any HTML-output build.
[private]
_assets-build:
    #!/usr/bin/env bash
    set -euo pipefail
    web_root=$(uv run python -c 'import gp_furo_theme; r = gp_furo_theme.get_vite_root(); print(r or "")' 2>/dev/null || true)
    if [ -z "$web_root" ]; then
        echo "[assets] no web/ source tree (wheel install) — skipping vite build"
        exit 0
    fi
    if ! command -v pnpm >/dev/null 2>&1; then
        echo "[assets] pnpm not on PATH; skipping vite build"
        exit 0
    fi
    if [ ! -d "$web_root/node_modules" ]; then
        (cd "$web_root" && pnpm install --frozen-lockfile)
    fi
    (cd "$web_root" && pnpm exec vite build)

html: _assets-build
    sphinx-build -b dirhtml . _build/html

dirhtml: _assets-build
    sphinx-build -b dirhtml . _build/dirhtml
```

The `[private]` attribute hides `_assets-build` from
`just --list`; it's a pure dependency target. Add the same
prerequisite to every other HTML-output builder you ship
(`singlehtml`, `htmlhelp`, `qthelp`, `devhelp`, `epub`).
Non-HTML builders (`text`, `man`, `latex`, `gettext`,
`linkcheck`, `doctest`) don't need the theme assets and should
*not* depend on `_assets-build`.

### Makefile

```makefile
.PHONY: _assets-build html dirhtml clean

_assets-build:
	@web_root=$$(uv run python -c 'import gp_furo_theme; r = gp_furo_theme.get_vite_root(); print(r or "")' 2>/dev/null || true); \
	if [ -z "$$web_root" ]; then \
		echo "[assets] no web/ source tree (wheel install) — skipping vite build"; \
		exit 0; \
	fi; \
	if ! command -v pnpm >/dev/null 2>&1; then \
		echo "[assets] pnpm not on PATH; skipping vite build"; \
		exit 0; \
	fi; \
	if [ ! -d "$$web_root/node_modules" ]; then \
		(cd "$$web_root" && pnpm install --frozen-lockfile); \
	fi; \
	(cd "$$web_root" && pnpm exec vite build)

html: _assets-build
	sphinx-build -b dirhtml . _build/html

dirhtml: _assets-build
	sphinx-build -b dirhtml . _build/dirhtml
```

### Locating the vite root from your own theme

The recipe shells into `gp_furo_theme.get_vite_root()` because that
is the canonical helper for the gp-sphinx-shipped theme. If you
maintain a *different* Sphinx theme parent that ships its own
Vite-managed assets, expose an equivalent helper from your
package's `__init__.py`:

```python
import pathlib

def get_vite_root() -> pathlib.Path | None:
    """Return the absolute web/ path under a workspace checkout, or None for wheel installs."""
    candidate = pathlib.Path(__file__).resolve().parents[2] / "web"
    return candidate if candidate.is_dir() else None
```

Then swap the `gp_furo_theme` import in the recipe for your own
package name. This keeps the orchestration layer agnostic about
where the source tree actually lives — wheel installs stay
zero-Node, workspace checkouts get a fresh build automatically.

## Reference

```{eval-rst}
.. autofunction:: gp_sphinx_vite.setup
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/gp-sphinx-vite)

[Vite]: https://vitejs.dev
[pnpm]: https://pnpm.io
[sphinx-autobuild]: https://github.com/sphinx-doc/sphinx-autobuild
