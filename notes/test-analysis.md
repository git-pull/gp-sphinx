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
| `ext_misc` | 18 files / 300 tests | Pure unit, parser, lexer, renderer, and transform helpers | Already light-weight |
| `layout` | 6 files / 42 tests | Mostly transform/visitor/CSS tests plus 3 real HTML contracts | Shared HTML scenarios already cached per session |
| `pytest_fixtures` | 4 files / 128 tests | Mix of pure helpers, dummy-builder doctree tests, and 4 real HTML/text E2E tests | Further narrowed this pass; shared roots now live in `tests/ext/pytest_fixtures/conftest.py` |
| `workspace_root` | 7 files / 77 tests | Config, tools, docs helpers, and one synthetic-Sphinx cache smoke | Mostly light-weight; one cache semantics build smoke remains |

This split matters because the suite is no longer broadly “slow because of
Sphinx”. Most files already use pure helper, parser, renderer, or doctree
assertions. The remaining expensive tests are concentrated in a very small
builder-facing surface.

## Coverage-preserving benchmark matrix

These measurements were taken from `/home/d/work/python/gp-sphinx` on
2026-04-08 after:

- the doctree-first refactor
- the shared Sphinx-scenario fixture cleanup
- the surgical rewrite of over-harnessed
  `sphinx_autodoc_pytest_fixtures` tests
- one more rewrite in this pass:
  - shared session roots for pytest-fixture doctree, integration, and
    type-checking scenarios
  - the MyST `autofixtures` page-level snapshot replaced with a smaller
    contract-focused smoke
  - doctests still share one session-scoped writable path instead of paying
    for a fresh pytest temp directory per doctest item

| Command | Result | Meaning |
| --- | --- | --- |
| `/usr/bin/time -p uv run pytest -s` | `798 passed, 3 skipped in 28.53s`, wall `31.31s` | Conservative full-suite baseline |
| `uv run pytest -s --durations=60 --durations-min=0.05` | `798 passed, 3 skipped in 34.36s` | Full-suite cost with slow-test evidence |
| `uv run python -m cProfile -o /tmp/gp_sphinx_full_current.prof -m pytest -s` | `798 passed, 3 skipped in 33.00s` | Full-suite profile source |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-abs` | `798 passed, 3 skipped in 5.35s`, wall `6.96s` | Optimized full suite, same coverage |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-integration-direct tests -m integration` | `21 passed, 695 deselected in 2.38s`, wall `3.43s` | Optimized integration diagnostics only |
| `/usr/bin/time -p uv run pytest -o "addopts=--tb=short --no-header --showlocals" -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-fast-direct --capture=tee-sys -q tests -m 'not integration'` | `689 passed, 3 skipped, 21 deselected in 1.32s`, wall `2.01s` | Optimized fast local loop only |
| `/usr/bin/time -p just test` | `798 passed, 3 skipped in 5.29s`, wall `6.90s` | Preferred full local command |
| `/usr/bin/time -p just test-fast` | `689 passed, 3 skipped, 21 deselected in 1.55s`, wall `2.40s` | Preferred fast local loop only |

Two things stand out:

- the optimized full-coverage runner is still consistently fast at about
  `5.3s` pytest time
- the raw full-suite baseline is still much slower than the optimized run,
  which means the suite is still paying for real runner/path overhead on top of
  the remaining Sphinx work

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

Use `uv run pytest -s` or `just test` when discussing the actual suite.

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
5. They replaced the full-page MyST `autofixtures` snapshot with a smaller
   smoke that asserts the real contract: native MyST invocation expands fixture
   descriptions in source order.

Concrete examples:

- `tests/ext/layout/` builds the shared layout demo scenarios once per test
  session through `tests/ext/layout/conftest.py`
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py` now uses
  a shared session root plus a shared default dummy-builder result
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py` now
  reuses the same shared session root as the doctree file
- `tests/ext/pytest_fixtures/test_type_checking_alias.py` now reuses that same
  session root instead of a per-test temp root
- `tests/conftest.py` injects one session-scoped doctest `tmp_path`

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

- wall `31.31s`
- user `5.79s`
- sys `1.61s`

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
    -o /tmp/gp_sphinx_full_current.prof \
    -m pytest \
    -s
```

### Biggest cumulative costs

| Function | Cumulative time |
| --- | --- |
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `22.83s` |
| `sphinx.application.Sphinx.build` | `16.75s` |
| `pathlib.Path.resolve` | `8.20s` |
| `posixpath.realpath` | `8.18s` |
| `posix.lstat` | `8.16s` |
| `_pytest.tmpdir.mktemp` | `0.09s` |
| `_pytest.pathlib.cleanup_dead_symlinks` | `0.22s` |

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
$ uv run pytest -s --durations=60 --durations-min=0.05
```

| Test | Duration | Cause classification |
| --- | --- | --- |
| `tests/ext/layout/test_integration.py::test_layout_demo_renders_api_component_contract` | `4.18s setup` | Real builder contract |
| `tests/ext/layout/test_snapshots.py::test_layout_demo_init_header_snapshot_annotation_disabled` | `3.97s setup` | Real builder contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_used_by_link_html_smoke` | `3.78s call` | Real builder contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_fixture_reference_html_resolves` | `3.77s call` | Real builder contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_default_html_outputs_smoke` | `3.26s setup` | Real builder contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_dependency_rendering_snapshot` | `0.73s call` | Necessary dummy-builder doctree contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_warning_and_manual_option_snapshot` | `0.67s call` | Necessary dummy-builder doctree contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_lint_level_error_sets_nonzero_status` | `0.67s call` | Necessary dummy-builder doctree/error contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_text_builder_does_not_crash` | `0.67s call` | Real builder contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_myst_smoke` | `0.66s call` | Necessary dummy-builder MyST contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_default_fixture_store_and_domain_contract` | `0.65s setup` | Necessary shared dummy-builder setup |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixtures_directive_myst_smoke` | `0.63s call` | Necessary dummy-builder MyST contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_short_name_fixture_reference_resolves` | `0.60s call` | Necessary dummy-builder xref contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixtures_directive_smoke` | `0.60s call` | Necessary dummy-builder nested-parse contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_rst_snapshot` | `0.60s call` | Necessary dummy-builder doctree contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixture_index_resolution_smoke` | `0.58s call` | Necessary dummy-builder xref/table contract |
| `tests/test_sphinx_scenarios.py::test_shared_sphinx_result_reuses_identical_builds` | `0.58s call` | Intentional cache semantics smoke |
| `tests/ext/pytest_fixtures/test_type_checking_alias.py::test_type_checking_alias_qualified_in_fixture_meta` | `0.54s call` | Necessary dummy-builder metadata contract |
| `tests/test_sphinx_scenarios.py::test_copy_scenario_tree_keeps_cached_source_pristine` | `0.52s call` | Intentional cache-copy smoke |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_manual_directive_without_module_registers_unqualified_name` | `0.52s call` | Necessary dummy-builder domain-registration contract |

### What is still over-harnessed?

At this point, very little.

The best remaining “lighter harness” candidates are no longer the multi-second
tests. They are the sub-second doctree tests that still build a dummy Sphinx
app because they exercise:

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
  doctree, integration, and type-checking tests
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
- do not introduce a second Sphinx test harness next to
  `tests/_sphinx_scenarios.py`

## Runner bugs and anomalies

### `uv run py.test --reruns 0 -vvv out`

This still reproduces the zero-collection capture failure in the repo:

```console
$ uv run py.test --reruns 0 -vvv out
```

- collects `0` items
- prints `no tests ran`
- crashes during teardown in `_pytest.capture.FDCapture.snap()`
- raises `FileNotFoundError` from `tmpfile.truncate()`

### `uv run pytest --collect-only -q`

This also still fails in the repo:

```console
$ uv run pytest --collect-only -q
```

- collects `0` items
- exits through the same capture teardown path
- fails with the same `FileNotFoundError`

### `uv run pytest -s --collect-only`

This works:

```console
$ uv run pytest -s --collect-only
```

- collects `801` items
- does not hit the broken quiet capture path

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

- the external repro uses plain pytest `9.0.3`
- the failure still reproduces with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`
- the traceback is the same `FileNotFoundError` in `_pytest/capture.py`

This now looks much more like an upstream pytest runner/capture bug than a
repo-specific plugin interaction.

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

1. Keep `uv run pytest -s` and `just test` as the honest suite baselines.
2. Keep `just test-fast` as a productivity loop only; do not cite it as proof
   that the full suite is fast.
3. Keep the current doctree-first / snapshot-first strategy.
4. Continue replacing page-level or full-build tests only when the contract is
   helper-level behavior, ordering, filtering, static scaffolding, or warning
   normalization.
5. Keep builder-backed tests for emitted HTML/text/inventory and cross-document
   reference behavior.
6. Treat the zero-collection capture failure as an upstream-style runner bug
   until proven otherwise; keep the current local workflow workaround instead of
   redesigning the suite around it.
