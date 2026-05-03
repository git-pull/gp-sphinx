# AGENTS.md — `sphinx-vite-builder`

Guidance for AI agents (Claude Code, Cursor, Copilot, Codex, …) and
human contributors working on this package. Mirrors the higher-level
guidance at `gp-sphinx/CLAUDE.md`; `packages/sphinx-vite-builder/CLAUDE.md`
points here so Claude Code reads the same content as other agent runners.

## What this package is

Two orthogonal entry points sharing one subprocess core:

1. **PEP 517 build backend** at `sphinx_vite_builder.build`. Runs
   `pnpm exec vite build` before delegating wheel/sdist construction
   to `hatchling.build`. Consumer packages declare it via
   `[build-system].build-backend = "sphinx_vite_builder.build"`.
2. **Sphinx extension** at `sphinx_vite_builder:setup`. Hooks
   `builder-inited` and `build-finished` so `sphinx-build` /
   `sphinx-autobuild` automatically run vite — one-shot for prod, a
   long-lived `vite build --watch` child process for autobuild — with
   graceful teardown on signal / `atexit`.

Both heads consume the smart-subprocess core under
`sphinx_vite_builder._internal/`: `process.py` (`AsyncProcess` —
asyncio subprocess wrapper with POSIX session isolation,
SIGTERM-then-SIGKILL teardown, line-buffered stdout/stderr drainers,
captured stderr for error surfacing), `bus.py` (`AsyncioBus` — single
asyncio loop in a daemon thread for sync↔async bridging),
`vite.py` (orchestration: detect `web/`, check pnpm via `shutil.which`,
spawn install/build), and `errors.py` (`PnpmMissingError`,
`NodeModulesInstallError`, `ViteFailedError`).

## The design contract — keep this invariant

> **Sources should check for node, pnpm, etc and error if it's not
> good, then build. Wheels should have the build files baked in and
> not need node and pnpm at all.**

This is the central invariant. When you change anything in the
backend, vite orchestration, or release pipeline, ask: "does this
preserve the source-vs-wheel asymmetry?"

### Source builds — fail loud, fail informatively

A consumer building from source (cloned tree, `[tool.uv.sources]` git
URL, `pip install <repo-path>`) goes through the PEP 517 chain. The
backend's `build_wheel` / `build_editable` / `build_sdist` hooks
**MUST** run vite, and vite **MUST** be available. If pnpm or Node is
missing:

- Raise the typed exception (`PnpmMissingError`,
  `NodeModulesInstallError`, or `ViteFailedError`) — never a bare
  `subprocess.CalledProcessError` or `FileNotFoundError`. The typed
  exception lets consumers `except` cleanly via the
  `SphinxViteBuilderError` base class.
- Each error's message MUST be a multi-line, copy-pasteable hint
  formatted by `_format_*_hint()`. Include the canonical install
  paths (`corepack enable`, `https://pnpm.io/installation`), the
  resolved vite-root path, and the `SPHINX_VITE_BUILDER_SKIP=1`
  escape-hatch line.
- Detect CI via `_detect_ci_provider()`. When CI is detected, append
  the platform-specific YAML/config snippet from `_CI_SETUP_RECIPES`
  so the consumer can copy-paste the fix into their pipeline.
  Supported providers: GitHub Actions, CircleCI, Azure Pipelines,
  GitLab CI, plus a generic fallback for `CI=true`.

### Wheel installs — zero toolchain required

A consumer doing `pip install <package>==<version>` from PyPI gets a
wheel that **already contains** the vite-built `static/` tree
(populated by the backend at release time, packed via hatchling's
`artifacts` directive). The PEP 517 chain doesn't run. No backend
invocation. No `_run_vite_build()`. No `shutil.which("pnpm")`. The
end user sees Python and only Python.

### Wheel-from-sdist — the bridge case

A consumer doing `pip install <pkg>.tar.gz` (or `--no-binary :all:`)
runs the wheel-from-sdist chain:

1. pip/uv unpacks the sdist into a temp dir
2. Calls our backend's `build_wheel` against the unpacked tree
3. The backend's vite-orchestration sees no `web/` (excluded from
   sdist via `[tool.hatch.build.targets.sdist] exclude = ["web/"]`)
   and short-circuits cleanly — `_resolve_vite_root()` returns
   `None`, vite is never invoked
4. Hatchling packs the pre-baked `static/` (carried in the sdist via
   `[tool.hatch.build] artifacts`) into the wheel

Net: **sdist install also requires zero toolchain**. The
`web/`-absent short-circuit is the load-bearing primitive.

## The four QA permutations — keep them green

Verified end-to-end as of v0.0.1a16.dev0:

| # | Path | Toolchain | Expected |
|---|---|---|---|
| 1 | wheel install from PyPI | none | succeeds; static present |
| 2 | sdist install from PyPI (`--no-binary :all:`) | none | succeeds; static present (backend short-circuits) |
| 3 | source build (`uv build` from cloned tree) | with pnpm + Node | succeeds; wheel contains static |
| 4 | source build (`uv build` from cloned tree) | none | fails with `PnpmMissingError` + CI-platform recipe |

When you add a new failure mode or a new short-circuit branch, add a
new row here AND a corresponding test in
`tests/test_sphinx_vite_builder_vite.py`.

## Architecture map

```
sphinx_vite_builder/
├── __init__.py              Sphinx extension entry: setup(app)
├── build.py                 PEP 517/660 hooks (delegate to hatchling)
├── py.typed
└── _internal/
    ├── errors.py            SphinxViteBuilderError + 3 subclasses
    ├── process.py           AsyncProcess (asyncio subprocess wrapper)
    ├── bus.py               AsyncioBus (sync↔async bridge)
    └── vite.py              run_vite_build() + CI detection + hint formatters
```

Neither head calls the other; both consume `_internal/`. The PEP 517
hooks in `build.py` MUST stay 1:1 mirrors of `flit_core.buildapi` and
`hatchling.build` — every hook runs `run_vite_build()` then delegates.
Optional hooks (`get_requires_for_build_*`, `prepare_metadata_for_build_*`)
alias to hatchling by identity — vite has no influence on dependency
resolution or distribution metadata, so wrapping them would be wrong.

## When you add a new public function

- Add doctests. Every public function MUST have working doctests
  per the workspace convention. Use ELLIPSIS for variable output.
- Add NumPy-style docstrings: short summary, Parameters, Returns,
  Raises, Examples.
- Add type annotations everywhere, including return types
  (`-> None` on test functions). mypy runs strict mode.

## When you add a new error path

- Add a new `*Error` subclass in `errors.py` if the failure has a
  distinct semantic meaning. Inherit from `SphinxViteBuilderError`.
- Add a `_format_*_hint(...)` function in `vite.py` for the
  copy-pasteable diagnostic. Wrap the raise:
  `raise NewError(_format_new_error_hint(...))`.
- If the new path is reachable in CI, ensure the message includes
  enough context to fix-from-the-message-itself. Add a CI-recipe
  block via `_format_ci_recipe_block()` if relevant.
- Add tests for: positive case (path triggers correctly), each error
  branch (specific exception, with key strings present in message),
  inheritance from `SphinxViteBuilderError`.

## When you change `release.yml` or the workspace

The workspace's `release.yml` MUST keep the pnpm + Node setup steps
that run before `uv build`, otherwise the wheels published to PyPI
would be empty of static (the v0.0.1a15 broken-release pattern that
motivated this whole package). The required steps are:

```yaml
- uses: pnpm/action-setup@v6
  with:
    version: 10
- uses: actions/setup-node@v6
  with:
    node-version: 22
    cache: pnpm
```

If you find yourself removing those, ask: "is the source-build path
still going to produce a populated `static/` in the wheel?" The
answer must be yes.

## When in doubt

- Read the full plan at gp-sphinx issue #28.
- Look at how PR #29 wired everything together initially.
- Look at how libtmux-mcp PR #33 exercises both consumer paths in
  CI — the WITH-wheels and WITHOUT-wheels permutations both have
  green runs that are good reference points.
- Run the local QA matrix: clean venv install of the published
  wheel, clean venv install of the published sdist (`--no-binary`),
  clean clone + `uv build` with toolchain stripped (must fail
  loudly), clean clone + `uv build` with toolchain present (must
  succeed).

## What NOT to do

- **Do not** add `web/` to the sdist. Excluding it is what makes the
  wheel-from-sdist short-circuit work.
- **Do not** commit anything from `static/` to git. Build artefacts
  are produced reproducibly; check-in is forbidden by workspace
  policy.
- **Do not** silently swallow vite/pnpm subprocess failures. Every
  non-zero exit goes through a typed exception with a
  copy-pasteable hint.
- **Do not** auto-install pnpm via the backend (the maturin
  `puccinialin`-style trick doesn't apply here — pnpm isn't
  pip-installable). The contract is "pnpm is your responsibility,
  here's how to install it on your platform".
- **Do not** change `SPHINX_VITE_BUILDER_SKIP=1` semantics without
  thinking through the wheel-vs-source asymmetry. The escape hatch
  is correct for wheel-only environments; using it during a real
  source build silently produces broken artefacts.
