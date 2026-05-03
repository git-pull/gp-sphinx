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

## The contract

> **Sources should check for node, pnpm, etc and error if it's not
> good, then build. Wheels should have the build files baked in and
> not need node and pnpm at all.**

This is the central invariant of the package. The two install paths
behave asymmetrically by design:

### Wheel installs — zero toolchain required

A user running `pip install <package>` from PyPI gets a wheel that
**already contains** the vite-built `static/` tree, populated by this
backend at release time. The PEP 517 chain doesn't run on the
consumer side. No backend invocation. No `pnpm`. No Node. The end
user sees Python and only Python.

```console
$ # No pnpm, no Node, no problem
$ pip install gp-furo-theme
```

### Source builds — fail loud, fail informatively

A contributor (or downstream packager building from source) goes
through the PEP 517 chain. The backend runs `pnpm exec vite build`
to produce `static/`, and that requires pnpm + Node on PATH. If the
toolchain is missing, the backend raises a typed exception with a
multi-line, copy-pasteable hint:

```
sphinx-vite-builder: cannot bootstrap the vite toolchain.
`pnpm` is not on PATH. Install it via one of:

  corepack enable        # Node 16.10+ ships corepack
  curl -fsSL https://get.pnpm.io/install.sh | sh -

See https://pnpm.io/installation

…

Detected CI provider: GitHub Actions. Add the following to your pipeline
config (before the Python build step that triggers this backend):

          - uses: pnpm/action-setup@v6
            with:
              version: 10
          - uses: actions/setup-node@v6
            with:
              node-version: 22
              cache: pnpm
```

The error includes the resolved vite-root path, the platform-specific
CI setup recipe (GitHub Actions, CircleCI, Azure Pipelines, GitLab CI,
or generic), and the `SPHINX_VITE_BUILDER_SKIP=1` escape hatch for
environments that genuinely don't need vite to run.

### The `web/`-absent short-circuit (sdist install bridge)

A user running `pip install <pkg>.tar.gz` from an sdist runs the
PEP 517 chain too — but the sdist excludes `web/` (the Vite source
tree). The backend detects the absence, short-circuits cleanly, and
hatchling packs the pre-baked `static/` (carried in the sdist via
`[tool.hatch.build] artifacts`) into the wheel. **Sdist installs
need no toolchain either.**

The asymmetry is the whole product: the same backend is strict
(running and failing loudly) when there's a `web/` to act on, and
silent (skipping cleanly) when there's no `web/` to begin with. The
two shapes match the two consumer worlds.

## Two heads, one subprocess core

### PEP 517 build backend

Drop-in replacement for `hatchling.build`. Runs `pnpm exec vite build`
before delegating wheel/sdist construction to hatchling.

```toml
# packages/your-theme/pyproject.toml
[build-system]
requires = ["hatchling>=1.0", "sphinx-vite-builder"]
build-backend = "sphinx_vite_builder.build"

[tool.hatch.build.targets.sdist]
exclude = ["web/"]    # so the sdist→wheel chain hits the short-circuit

[tool.hatch.build]
artifacts = ["src/<your-theme>/theme/<theme-name>/static/"]
```

### Sphinx extension (Phase 1: placeholder)

The extension entry point is currently a placeholder registered in
`conf.py` to prevent import errors. Full lifecycle integration —
running Vite before the docs build and spawning a watched Vite
process during `sphinx-autobuild` — lands in a follow-up release.

For now, the [PEP 517](https://peps.python.org/pep-0517/) backend
handles all Vite orchestration during source builds and wheel
generation; that path is fully implemented and tested.

```python
# docs/conf.py
extensions = ["sphinx_vite_builder"]
```

## Fast-fail diagnostics — error type reference

| Error | When | Hint surface |
|---|---|---|
| `PnpmMissingError` | `pnpm` not on `PATH` during a source build | `corepack enable`, [pnpm.io/installation](https://pnpm.io/installation), per-CI YAML recipe, `SPHINX_VITE_BUILDER_SKIP=1` |
| `NodeModulesInstallError` | `pnpm install` exited non-zero | `cd <vite-root> && pnpm install --frozen-lockfile` rerun command, captured stderr |
| `ViteFailedError` | `pnpm exec vite build` exited non-zero | invocation context (cwd, exit code), captured stderr |

All three inherit from `SphinxViteBuilderError`, so consumers can
`except SphinxViteBuilderError` for a single catch surface.

## CI detection

The `PnpmMissingError` hint is **self-healing** when the backend
detects a CI environment. Detection precedence (most-specific wins):

| CI provider | Env var | Recipe shape |
|---|---|---|
| GitHub Actions | `GITHUB_ACTIONS=true` | `pnpm/action-setup@v6` + `actions/setup-node@v6` |
| CircleCI | `CIRCLECI=true` | `corepack enable && corepack prepare pnpm@latest-10 --activate` step |
| Azure Pipelines | `TF_BUILD=True` | `NodeTool@0` + corepack script |
| GitLab CI | `GITLAB_CI=true` | `before_script` corepack invocations |
| Generic | `CI=true` | "Use your CI's package-manager setup mechanism" |

Source: each provider's own canonical detection variable per the pnpm
[Continuous Integration docs](https://pnpm.io/continuous-integration).

## License

MIT — see [LICENSE](LICENSE).

## Agent / contributor guidance

See [`AGENTS.md`](AGENTS.md) for the design contract, architecture
map, and conventions agents and contributors should follow when
making changes. ([`CLAUDE.md`](CLAUDE.md) is a passthrough to
`AGENTS.md` for Claude Code.)
