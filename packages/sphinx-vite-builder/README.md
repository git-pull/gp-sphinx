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

No pnpm, no Node — just Python:

```console
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

## Quick start — two activation variants

`sphinx-vite-builder` ships two orthogonal ways to wire vite into a
hatchling-built Python package. Pick whichever fits the consumer's
existing build setup; they are mutually exclusive at the
`[build-system].build-backend` level.

### Variant 1 — PEP 517 backend (drop-in replacement)

The simplest activation. Replace `hatchling.build` with
`sphinx_vite_builder.build` and you're done.

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

### Variant 2 — Hatchling build hook (composable)

For projects that want to keep `build-backend = "hatchling.build"` and
layer vite on top of an existing hatchling hook stack
(`version`, custom build scripts, etc.):

```toml
# packages/your-theme/pyproject.toml
[build-system]
requires = ["hatchling>=1.0", "sphinx-vite-builder"]
build-backend = "hatchling.build"

[tool.hatch.build.hooks.vite]

[tool.hatch.build.targets.sdist]
exclude = ["web/"]

[tool.hatch.build]
artifacts = ["src/<your-theme>/theme/<theme-name>/static/"]
```

Both variants share the same orchestration core — same SKIP env var,
same `web/`-absent short-circuit, same fast-fail diagnostics. Pick
variant 1 for simplicity, variant 2 for composability.

### Sphinx extension (orthogonal to either build variant)

The Sphinx-extension head is independent of the backend / hook
choice. Wire it into a docs build to get vite running automatically
during `sphinx-build` (one-shot) and `sphinx-autobuild` (watched).

```python
# docs/conf.py
extensions = ["sphinx_vite_builder"]
sphinx_vite_builder_mode = "auto"        # "auto" | "dev" | "prod"
sphinx_vite_builder_root = "/abs/path/to/web"
```

`"auto"` resolves to `"dev"` when the build is running under
`sphinx-autobuild` (detected via `SPHINX_AUTOBUILD` env var, `argv[0]`,
or parent-process inspection on Linux), `"prod"` otherwise. Setting
`sphinx_vite_builder_root` to `None` (the default) makes the extension
a complete no-op — useful when the consumer is installed from a wheel
where the static tree is already pre-baked.

## Comparison with similar tools

| Tool | Toolchain owned | Activation strategy | Bootstrap |
|---|---|---|---|
| [`maturin`](https://github.com/PyO3/maturin) | Rust (Cargo) | self-hosting via `bootstrap` shim | `puccinialin` auto-installs Rust |
| [`sphinx-theme-builder`](https://github.com/pradyunsg/sphinx-theme-builder) | Node (webpack) | rolls own ZIP packing | `nodeenv` (isolated Node env) |
| [`hatch-jupyter-builder`](https://github.com/jupyterlab/hatch-jupyter-builder) | Node (npm/yarn) | hatchling build hook | user-managed Node |
| `sphinx-vite-builder` | Node (vite) | PEP 517 backend **or** hatchling hook | user-managed pnpm (corepack) |

`sphinx-vite-builder` deliberately diverges from `sphinx-theme-builder`'s
`nodeenv` approach: pnpm via corepack is the modern Node convention, and
auto-installing Node into the project tree pulls in significant friction
for editable workflows. Compared to `maturin`, the Rust analog,
sphinx-vite-builder doesn't auto-install pnpm — pnpm isn't pip-installable,
so the failure mode is "user runs `corepack enable`" rather than "backend
bootstraps a Node env."

## Migrating from manual orchestration

If your project currently runs `pnpm exec vite build` from a CI step,
a justfile recipe, or a Makefile target, you can drop those:

| Was | Now |
|---|---|
| `tests.yml` step: `pnpm install && pnpm exec vite build` | The backend / hook handles it; only keep pnpm/Node setup |
| `release.yml` step: `pnpm install && pnpm exec vite build` | Same — keep pnpm/Node setup, drop the manual build call |
| `justfile` recipe `_assets-build` as prerequisite of `html` | Drop the recipe; the Sphinx extension's PROD-mode hook runs vite |
| Hatchling `[tool.hatch.build] force-include` for `static/` | Drop; the backend produces the static tree before hatchling packs |

Keep your CI's pnpm + Node setup steps — the backend needs them at
build time even though the wheel installation doesn't.

## Fast-fail diagnostics — error reference

| Error | When | Hint includes |
|---|---|---|
| `PnpmMissingError` | `pnpm` not on `PATH` during a source build | `corepack enable`, [pnpm.io/installation](https://pnpm.io/installation), per-CI YAML recipe, `SPHINX_VITE_BUILDER_SKIP=1` |
| `NodeModulesInstallError` | `pnpm install` exited non-zero | `cd <vite-root> && pnpm install --frozen-lockfile` rerun command, captured stderr |
| `ViteFailedError` | `pnpm exec vite build` exited non-zero | invocation context (cwd, exit code), captured stderr |

All three inherit from `SphinxViteBuilderError`, so consumers can
`except SphinxViteBuilderError` for a single catch surface.

## CI recipe gallery

The `PnpmMissingError` hint is **self-healing** when the backend
detects a CI environment — it embeds the platform-specific setup
recipe in the error message. They are also reproduced here for
search-discoverability.

### GitHub Actions (`GITHUB_ACTIONS=true`)

```yaml
- uses: pnpm/action-setup@v6
  with:
    version: 10
- uses: actions/setup-node@v6
  with:
    node-version: 22
```

`cache: pnpm` is intentionally omitted: setup-node's pnpm cache
lookup expects a `pnpm-lock.yaml` at the consumer repo root, which
fails when sphinx-vite-builder runs from a transitive git source
(the lockfile lives inside the source-built package's checkout, not
the consumer repo). Workspaces that own their own `pnpm-lock.yaml`
at the repo root may add `cache: pnpm` for a small speed-up.

### CircleCI (`CIRCLECI=true`)

```yaml
- run:
    name: Install pnpm via corepack
    command: |
      corepack enable
      corepack prepare pnpm@latest-10 --activate
```

### Azure Pipelines (`TF_BUILD=True`)

```yaml
- task: NodeTool@0
  inputs:
    versionSpec: '22.x'
- script: |
    corepack enable
    corepack prepare pnpm@latest-10 --activate
```

### GitLab CI (`GITLAB_CI=true`)

```yaml
before_script:
  - corepack enable
  - corepack prepare pnpm@latest-10 --activate
```

### Generic CI (any other `CI=true`)

Use your CI's package-manager setup mechanism to put `pnpm` (>=10)
and `node` (>=22) on PATH before the Python build step runs.

Detection precedence (most-specific wins): each provider's canonical
env var per the pnpm
[Continuous Integration docs](https://pnpm.io/continuous-integration)
is checked first; the generic `CI=true` is the fallback for "we know
we're in CI but don't recognise the provider."

## Troubleshooting

**`PnpmMissingError: pnpm is not on PATH`** — install pnpm via
`corepack enable` (Node 16.10+) or follow the per-CI recipe in the
error message. If you're in an environment that genuinely doesn't
need vite to run (e.g. building from a pre-baked sdist), set
`SPHINX_VITE_BUILDER_SKIP=1` in the environment.

**`NodeModulesInstallError`** — `pnpm install --frozen-lockfile`
exited non-zero. The error surfaces the captured stderr. Common
causes: stale `pnpm-lock.yaml` (run `pnpm install` interactively to
refresh), network/registry timeout (retry), or `engines` mismatch
(check the project's `package.json` `engines` field against the
installed Node/pnpm versions).

**`ViteFailedError`** — `pnpm exec vite build` exited non-zero.
Captured stderr is included in the hint. This is usually a
project-side compile error (TypeScript type check, SCSS syntax,
missing import) rather than a tooling problem. Reproduce with
`(cd <vite-root> && pnpm exec vite build)` to see vite's full output.

**Wheel ships without `static/` content** — the backend ran but the
artefacts didn't make it into the wheel. Verify your `pyproject.toml`
has the `[tool.hatch.build] artifacts = ["src/.../static/"]`
declaration. Hatchling's documented "VCS-ignored include" mechanism
requires this even when the path is on disk; `force-include` does
not work for editable builds.

**`just html` (or any plain `sphinx-build`) doesn't rebuild assets** —
make sure `sphinx_vite_builder` is loaded in `extensions` and that
`sphinx_vite_builder_root` points at your `web/` directory. The
extension's PROD-mode hook runs `pnpm exec vite build` once before
the build proceeds; without it, you'd need a manual orchestration
step.

## License

MIT — see [LICENSE](LICENSE).

## Agent / contributor guidance

See [`AGENTS.md`](AGENTS.md) for the design contract, architecture
map, and conventions agents and contributors should follow when
making changes. ([`CLAUDE.md`](CLAUDE.md) is a passthrough to
`AGENTS.md` for Claude Code.)
