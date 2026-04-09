# Test Performance Analysis

This note tracks where time is going in the gp-sphinx test suite, which parts
of the cost are real coverage versus avoidable harnessing, and which runner
bugs are distorting local diagnostics.

The main correction from earlier drafts is unchanged:

- the default baseline is the full suite, not a deselected fast lane
- `tests -m "not integration"` and `just test-fast` are local feedback loops
  only
- optimized local commands are useful diagnostics, but they are not evidence
  that the full suite is cheap or complete

## Test categories and harnesses

This inventory is based on the current `tests/` tree plus current collection
output. The suite currently collects `801` items and passes `798` tests with
`3` skips.

| Category | Approx. files / tests | Primary harness | Current status |
| --- | --- | --- | --- |
| `ext_misc` | 18 files / 462 tests | Pure unit, parser, lexer, renderer, and transform helpers | Already light-weight |
| `layout` | 6 files / 42 tests | Mostly transform/visitor/CSS tests plus 3 real HTML contracts | Shared HTML scenarios already cached per session |
| `pytest_fixtures` | 4 files / 128 tests | Mix of pure helpers, dummy-builder doctree tests, and 4 real HTML/text E2E tests | Further narrowed this pass; only doctree and emitted-output contracts still build Sphinx |
| `workspace_root` | 7 files / 84 tests | Config, tools, docs helpers, and one synthetic-Sphinx cache smoke | Mostly light-weight; one cache semantics build smoke remains |
| `docs_doctests` | 9 files / 27 tests | `--doctest-modules` against `docs/_ext` helpers | Already light-weight |
| `package_doctests` | 7 files / 58 tests | `--doctest-modules` against selected package modules | Already light-weight |

This split matters because the suite is no longer broadly “slow because of
Sphinx”. Most files already use pure helper, parser, renderer, or doctree
assertions. The remaining expensive tests are concentrated in a very small
builder-facing surface.

## Coverage-preserving benchmark matrix

These measurements were taken from `/home/d/work/python/gp-sphinx` on
2026-04-09 after:

- the doctree-first refactor
- the shared Sphinx-scenario fixture cleanup
- the direct rewrite of the over-harnessed type-checking alias metadata smoke
- the repo-local validator compatibility follow-up:
  - `pytest` now defaults to `-s` to stay off the upstream capture-teardown
    crash path
  - `out/` now mirrors the configured `testpaths` so
    `uv run py.test --reruns 0 -vvv out` executes the real suite

| Command | Result | Meaning |
| --- | --- | --- |
| `/usr/bin/time -p uv run pytest --durations=100 --durations-min=0.02` | `798 passed, 3 skipped in 30.74s`, wall `32.23s` | Conservative full-suite baseline plus slow-test evidence |
| `uv run python -m cProfile -o /tmp/gp_sphinx_full.prof -m pytest -s` | `798 passed, 3 skipped in 36.22s` | Full-suite profile source |
| `/usr/bin/time -p uv run pytest -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-abs` | `798 passed, 3 skipped in 3.52s`, wall `3.81s` | Optimized full suite, same coverage |
| `uv run pytest --collect-only -q` | `801 tests collected in 0.91s` | Stable collection diagnostics; no longer crashes in capture teardown |
| `uv run py.test --reruns 0 -vvv out` | `798 passed, 3 skipped in 29.60s` | Required validator now runs the real suite through `out/` |

Two things stand out:

- the optimized full-coverage runner is now consistently fast at about
  `3.5s` pytest time
- the raw full-suite baseline is still much slower than the optimized run,
  which means the suite is still paying for real runner/path overhead on top of
  the remaining Sphinx work
- the raw full-suite baseline also varies more than the optimized one, which
  points to filesystem and path-resolution noise rather than a stable Python
  hot loop
- the required `py.test ... out` validator now lands in the same range as the
  raw full suite because it is finally executing the same test graph instead of
  crashing before collection

## Coverage caveat

The optimized fast lane is **not** the suite baseline.

This command:

```console
$ uv run pytest \
    -o "addopts=--tb=short --no-header --showlocals" \
    -o tmp_path_retention_policy=none \
    --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-fast-direct \
    --capture=tee-sys \
    -q \
    tests \
    -m 'not integration'
```

intentionally deselects `integration` and skips the default
`--doctest-modules` policy. It is the right command for a local edit loop, but
the wrong command for making claims about total coverage or full-suite
performance.

Use `uv run pytest` or `just test` when discussing the actual suite.

## What changed in this audit

The recent passes did useful work without weakening coverage:

1. They kept most structure, transform, store, and warning assertions at the
   helper, doctree, or focused snapshot layer instead of paying for a full HTML
   build.
2. They changed the remaining synthetic Sphinx tests to reuse
   `tmp_path_factory`-backed roots more aggressively.
3. They stopped injecting a fresh pytest `tmp_path` into every doctest item and
   now reuse one session-scoped doctest path.
4. They changed the pytest-fixture test family to use one shared session root
   in `tests/ext/pytest_fixtures/conftest.py`.
5. They now build one shared cross-document HTML result for both fixture-link
   directions instead of paying for two separate HTML scenarios.
6. They now build one shared dummy-builder `autofixtures + usage` scenario for
   both the nested-parse smoke and the short-name reference smoke.
7. They replaced the full-page MyST `autofixtures` snapshot with a smaller
   smoke that asserts the real contract: native MyST invocation expands fixture
   descriptions in source order.
8. They changed smoke-only pytest-fixture HTML and text builds to use a
   smaller fixture module that still exercises badge, inventory, genindex, and
   text-builder output.
9. They changed the MyST `autofixtures`, MyST `doc-pytest-plugin`, and
   autofixture-index smokes to use smaller fixture modules that still exercise
   native MyST invocation, pending-xref resolution, and final table output.
10. They changed `tests/test_sphinx_scenarios.py` to use a plain-page Sphinx
    scenario for cache semantics instead of paying for `autodoc` imports that
    were not part of the contract.
11. They changed the canonical RST `doc-pytest-plugin` doctree snapshot to use
    the reduced three-fixture smoke module instead of the full demo fixture
    surface.
12. They now build one shared MyST dummy-builder scenario for both the
    `doc-pytest-plugin` and `autofixtures` smokes instead of paying for two
    separate MyST dummy builds.
13. They rewrote the type-checking alias metadata smoke as a typed helper-level
    registration test and stopped booting a dummy Sphinx build for a pure store
    assertion.
14. They removed the now-unused `spf_type_checking_root` shared fixture because
    that test family no longer needs a Sphinx scenario root.
15. They added a repo-local `out/` mirror plus default `-s` capture so the
    required validator path and `--collect-only -q` both execute instead of
    falling into the upstream zero-collection capture crash.

Concrete examples:

- `tests/ext/layout/` builds the shared layout demo scenarios once per test
  session through `tests/ext/layout/conftest.py`
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py` now uses
  a shared session root plus a shared default dummy-builder result
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py` now
  reuses the same shared session root as the doctree file and shares one
  cross-document HTML build across both directional-link checks
- `tests/ext/pytest_fixtures/test_type_checking_alias.py` now calls
  `_register_fixture_meta()` directly with a typed fake env/app and a real
  fixture module instead of building a dummy Sphinx app
- `tests/ext/pytest_fixtures/conftest.py` no longer carries a type-checking
  scenario root that no test uses
- `tests/conftest.py` injects one session-scoped doctest `tmp_path`
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py` now
  feeds a reduced fixture module into the HTML and text smoke scenarios
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py` now feeds
  reduced fixture modules into the `autofixtures`, `doc-pytest-plugin`, and
  fixture-index smokes
- `tests/test_sphinx_scenarios.py` now uses a minimal page-only scenario for
  cache identity and source-copy isolation

That means the remaining expensive tests are much more likely to be real
builder-facing contracts rather than accidental faux-E2E coverage.

## Where time goes

The current suite is paying for two big things:

1. runner-side path resolution and filesystem probing
2. a small set of real Sphinx builds

The current story is no longer “it was all tmp paths”:

- `_pytest.tmpdir.mktemp()` is now a minor cost after the doctest temp-path
  rewrite and the fixed-`--basetemp` local workflow
- `Path.resolve()`, `realpath()`, and `lstat()` are still expensive, which
  means path validation and filesystem probing remain a real raw-runner cost
- the remaining Sphinx work is concentrated in a small, legitimate
  builder-facing surface
- the suite is no longer dominated by broad faux-E2E Sphinx coverage

The raw full-suite `/usr/bin/time` output is also telling:

- wall `32.23s`
- user `4.80s`
- sys `1.47s`

That wide wall-vs-CPU gap is consistent with filesystem and process overhead,
not a Python-level hot loop.

### Where execution appears to stall

There is no evidence of an infinite loop in the current suite. The apparent
“stalls” are concentrated in two places:

- front-loaded fixture setup for the remaining shared HTML Sphinx scenarios,
  especially `layout` and cross-document fixture HTML tests
- zero-collection teardown paths in pytest capture, where the process exits the
  test run and then crashes in capture shutdown

In other words, the suite does not appear to hang in one test body. It spends
time in setup-heavy builder fixtures and in runner teardown for the known
capture bug.

## Full-suite profile findings

The current full-suite cProfile was taken with:

```console
$ uv run python -m cProfile \
    -o /tmp/gp_sphinx_full.prof \
    -m pytest \
    -s
```

### Biggest cumulative costs

| Function | Cumulative time |
| --- | --- |
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `25.75s` |
| `sphinx.application.Sphinx.build` | `18.60s` |
| `pathlib.Path.resolve` | `11.12s` |
| `posixpath.realpath` | `11.11s` |
| `posix.lstat` | `11.08s` |
| `_pytest.tmpdir.mktemp` | `0.20s` |
| `_pytest.pathlib.cleanup_dead_symlinks` | `0.24s` |

### What that means

- the dominant raw-suite cost is now cached synthetic Sphinx builds plus
  path-resolution churn
- numbered temp-dir creation is no longer a primary offender
- `cleanup_dead_symlinks()` is still present, but it is not a top-level cost
  anymore
- snapshot serialization is not close to the top of the profile, which is one
  reason a custom Syrupy extension is not the right performance lever

### Upstream-backed explanation of runner cost

Local source inspection in pytest and CPython matches the profile:

- `_pytest.tmpdir.TempPathFactory.mktemp()` still goes through numbered
  directory creation
- `_pytest.tmpdir._ensure_relative_to_basetemp()` calls `Path.resolve()`
- `_pytest.pathlib.make_numbered_dir()` scans prefixed entries and updates the
  `current` symlink
- `_pytest.pathlib.cleanup_dead_symlinks()` resolves symlink targets during
  cleanup
- CPython `pathlib.Path.resolve()` delegates to `os.path.realpath()`
- `_pytest.capture.FDCapture.snap()` calls `tmpfile.truncate()`, which matches
  the zero-collection crash traceback

So the raw suite is not “stuck” on one mystery function. It is paying for:

1. path resolution and filesystem probing
2. a smaller set of honest Sphinx builds
3. a much smaller tail of tmpdir naming and cleanup than earlier drafts showed

## Remaining slow tests in the real full suite

These timings come from:

```console
$ uv run pytest --durations=100 --durations-min=0.02
```

| Test | Duration | Cause classification |
| --- | --- | --- |
| `tests/ext/layout/test_integration.py::test_layout_demo_renders_api_component_contract` | `4.68s setup` | Real builder contract |
| `tests/ext/layout/test_snapshots.py::test_layout_demo_init_header_snapshot_annotation_disabled` | `4.44s setup` | Real builder contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_fixture_reference_html_resolves` | `4.32s setup` | Real builder contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_default_html_outputs_smoke` | `3.76s setup` | Real builder contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixture_index_resolution_smoke` | `0.80s call` | Necessary dummy-builder xref/table contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_dependency_rendering_snapshot` | `0.79s call` | Necessary dummy-builder doctree contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_myst_smoke` | `0.79s setup` | Necessary dummy-builder MyST contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_default_fixture_store_and_domain_contract` | `0.76s setup` | Necessary shared dummy-builder setup |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_lint_level_error_sets_nonzero_status` | `0.71s call` | Necessary dummy-builder doctree/error contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_text_builder_does_not_crash` | `0.70s call` | Real builder contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixtures_directive_smoke` | `0.69s setup` | Necessary dummy-builder nested-parse contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_warning_and_manual_option_snapshot` | `0.69s call` | Necessary dummy-builder doctree contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_rst_snapshot` | `0.64s call` | Necessary dummy-builder doctree contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_manual_directive_without_module_registers_unqualified_name` | `0.60s call` | Necessary dummy-builder domain-registration contract |
| `tests/test_sphinx_scenarios.py::test_shared_sphinx_result_reuses_identical_builds` | `0.45s call` | Intentional cache semantics smoke |
| `tests/test_sphinx_scenarios.py::test_copy_scenario_tree_keeps_cached_source_pristine` | `0.40s call` | Intentional cache-copy smoke |

### What is still over-harnessed?

The clearest over-harnessed test from the previous pass is now gone.

The remaining “lighter harness” candidates are no longer the multi-second
tests. They are sub-second doctree tests that still build a dummy Sphinx app
because they exercise:

- nested directive parsing
- post-transform injection
- `pending_xref` resolution
- domain/store population
- status/warning behavior

Those are real Sphinx behaviors, so there is less easy speed left to harvest
without giving up signal.

## Caching status

### What is working

- layout HTML scenarios are cached once per session
- pytest-fixture doctree and HTML scenarios now share one session root across
  doctree and integration tests
- the type-checking alias metadata smoke no longer needs any Sphinx scenario or
  cache at all
- doctest examples now reuse one session-scoped writable path
- identical Sphinx scenarios still reuse the same in-memory and on-disk cached
  result via `tests._sphinx_scenarios.build_shared_sphinx_result`

### What is still not shareable

The remaining expensive Sphinx scenarios mostly differ for good reasons:

- builder name (`html`, `text`, `dummy`)
- document graph (`api.rst` vs `usage.rst` cross-document cases)
- MyST versus RST source shape
- lint-level behavior
- specific transform/xref scenarios

That means the current remaining costs are mostly **not** a case of broken or
missing cache reuse. They are different scenarios with intentionally different
inputs.

## What should stay as true E2E

These tests still deserve the harness they use:

- final layout `dt.api-header` HTML contract
- final layout header HTML fragment snapshots
- fixture cross-document HTML links
- `objects.inv` generation
- `genindex.html` generation
- text-builder smoke

These are emitted-output contracts, not just structure or store-state checks.
Trying to demote them further would mostly trade away confidence rather than
buy meaningful speed.

## Where further surgical refactors still make sense

The rule for future work should be:

- if the contract is ordering, filtering, static node scaffolding, generated
  directive text, or warning normalization, keep it as a pure helper or doctree
  test
- if the contract is emitted HTML/text/inventory or cross-document reference
  behavior, keep it as a builder-backed test

Concretely:

- continue auditing any new `tmp_path` use and prefer deterministic paths or
  shared `tmp_path_factory` roots when the test does not need isolation
- keep moving page-level snapshots down to fragment or smoke-level contracts
  when helper tests already pin the scaffolding behavior
- prefer doctree or fragment snapshots over full-page snapshots when the
  contract stops at post-transform structure rather than emitted builder output
- do not build a dummy or HTML Sphinx app for pure metadata/store assertions
- do not introduce a second Sphinx test harness next to
  `tests/_sphinx_scenarios.py`

### Syrupy custom-extension audit

This pass also re-checked the local `syrupy` study tree to see whether a custom
snapshot extension would be worth the complexity.

It is not the right lever here:

- the profile still puts Sphinx builds and path resolution far above snapshot
  serialization
- Syrupy already amortizes discovery well enough for this suite shape
- the expensive remaining snapshot tests are expensive because of the Sphinx
  harness beneath them, not because of snapshot encoding itself

## Runner bugs and anomalies

### `uv run py.test --reruns 0 -vvv out`

This now works in the repo:

```console
$ uv run py.test --reruns 0 -vvv out
```

- collects and runs the full suite through `out/`
- passes with `798 passed, 3 skipped in 29.60s`
- no longer trips the zero-collection capture teardown crash

### `uv run pytest --collect-only -q`

This now works in the repo:

```console
$ uv run pytest --collect-only -q
```

- collects `801` items
- no longer exits through the broken capture teardown path
- completes in about `0.91s`

### Why the repo now behaves differently

The underlying pytest bug still appears to be upstream:

- the external repro still fails under pytest `9.0.2`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` does not avoid it
- the traceback is still `FileNotFoundError` in `_pytest.capture.FDCapture.snap()`

The repo now stays off that path deliberately:

- `pytest` defaults to `-s`, which avoids the broken global capture teardown
- `out/` mirrors the configured `testpaths`, so validators that insist on
  `... out` now point at a real collection root instead of a missing path

### `uv run pytest --collect-only`

This works:

```console
$ uv run pytest --collect-only
```

- collects `801` items
- does not hit the broken capture path

### Tiny external repro

The capture failure also reproduces outside the repo in a tiny throwaway
project:

```console
$ uv run --with pytest pytest --collect-only -q
```

```console
$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    uv run --with pytest pytest --collect-only -q
```

```console
$ uv run --with pytest py.test -vvv
```

```console
$ PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    uv run --with pytest py.test -vvv
```

Observed behavior:

- the external repro uses plain pytest `9.0.2`
- the failure still reproduces with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`
- the traceback is the same `FileNotFoundError` in `_pytest/capture.py`

This still looks much more like an upstream pytest runner/capture bug than a
repo-specific plugin interaction.

A quick GitHub/web search on 2026-04-09 did not surface an obvious existing
pytest issue matching this exact `tmpfile.truncate()` / zero-collection
failure, so the repo now keeps the local mitigation and treats the current
repro steps as filing-ready evidence if an upstream report becomes worthwhile.

### Relative repo-local `--basetemp`

Relative repo-local `--basetemp` remains unstable for some pathless pytest
invocations. Absolute repo-local basetemps under `.cache/` remain the stable
workaround and are what `just test` and `just test-fast` use.

### `just` version mismatch

The shell-visible `just` is still:

```console
$ just --version
```

```text
just 1.21.0
```

while:

```console
$ mise which just
```

points to:

```text
/home/d/.config/mise/installs/just/1.49.0/just
```

So recipes should continue avoiding any behavior that depends on the newer
binary being the one actually resolved in this shell.

## Doctree and snapshot audit

The current doctree/snapshot split is in good shape:

- helper tests now cover directive-text ordering, `:no-index:` emission, MyST
  `eval-rst` wrapping, doc-pytest-plugin intro scaffolding, and fixture-index
  row filtering without paying for Sphinx
- dummy-builder doctree tests now cover only the behaviors that actually need
  Sphinx: nested parsing, xref resolution, post-transforms, warnings, and
  status codes
- layout HTML snapshots are already focused on the `dt.api-header` fragment
  instead of whole pages

One more specific improvement landed in this pass:

- the MyST `autofixtures` test no longer snapshots the full page doctree
- it now asserts the real contract directly: native MyST invocation expands
  generated fixture descriptions in the expected source order and does not leak
  directive wrapper text into the final doctree
- one shared cross-document HTML build now covers both fixture-link directions
- one shared dummy-builder `autofixtures + usage` scenario now covers both the
  nested-parse smoke and the short-name fixture-reference smoke
- one shared MyST dummy-builder scenario now covers both the
  `doc-pytest-plugin` and `autofixtures` smokes
- smoke-only HTML, text, MyST, and cache-scenario tests now use smaller source
  modules or page trees when the contract does not depend on the larger demo
  fixture surface

That is a good example of a rewrite that reduces harness cost and snapshot
surface without reducing signal.

## Why no custom Syrupy extension

A custom Syrupy extension is still not the right next step.

Current bottlenecks are:

- pytest runner overhead in raw runs
- a small set of real Sphinx builds

Current needs are already covered by `tests/_snapshots.py` and
`snapshot.with_defaults(...)`:

- doctree `pformat()` normalization
- focused HTML fragment normalization
- warning text normalization

There is no current evidence that snapshot storage layout, custom comparators,
or one-snapshot-per-file storage would buy a meaningful runtime improvement or
more accurate signal.

## Recommendations

1. Keep `uv run pytest` and `just test` as the honest suite baselines.
2. Keep `just test-fast` as a productivity loop only; do not cite it as proof
   that the full suite is fast.
3. Keep the current doctree-first / snapshot-first strategy.
4. Continue replacing page-level or full-build tests only when the contract is
   helper-level behavior, ordering, filtering, static scaffolding, or warning
   normalization.
5. Keep builder-backed tests for emitted HTML/text/inventory and cross-document
   reference behavior.
6. Keep the repo-local mitigation for the upstream-style capture bug:
   default `-s`, the `out/` mirror for validator compatibility, and absolute
   repo-local `--basetemp` paths for optimized diagnostics.
