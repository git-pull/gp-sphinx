# Test Performance Analysis

This note tracks where time is going in the gp-sphinx test suite, which parts
of the current cost are real coverage versus avoidable harnessing, and which
runner bugs are distorting local diagnostics.

The most important correction from earlier drafts is this:

- the default baseline is the full suite, not a deselected fast lane
- `tests -m "not integration"` is a local feedback loop only
- optimized local commands are useful diagnostics, but they are not evidence
  that the full suite is cheap or complete

## Test categories and harnesses

The suite currently falls into four broad groups. This inventory is based on a
file-level audit of `tests/` plus the current pytest collection output.

| Category | Approx. files / tests | Primary harness | Current status |
| --- | --- | --- | --- |
| `ext_misc` | 18 files / about 300 tests | Pure unit/parser/renderer tests | Already light-weight |
| `layout` | 6 files / 42 tests | Mostly transform/visitor/CSS tests, plus 3 real HTML contracts | Narrowed to one shared HTML demo per scenario family |
| `pytest_fixtures` | 4 files / about 120 tests | Mix of pure helpers, dummy-builder doctree tests, and 4 real HTML/text E2E tests | Recently split further toward helper/doctree coverage |
| `workspace_root` | 7 files / 77 tests | Config/tools/helpers plus one synthetic-Sphinx cache smoke | Mostly light-weight; one cache-semantics build smoke remains |

That split matters because the suite is no longer broadly “slow because of
Sphinx”. Most files already use pure helper, parser, renderer, or doctree
assertions. The remaining expensive tests are concentrated in a very small
builder-facing surface.

## Coverage-preserving benchmark matrix

These measurements were taken from `/home/d/work/python/gp-sphinx` on
2026-04-08 after the current doctree-first refactor, the shared Sphinx-scenario
fixture cleanup, the surgical rewrite of the remaining over-harnessed
`sphinx_autodoc_pytest_fixtures` tests, and one more runner-wide reduction:
doctests now share a session-scoped writable path instead of receiving a fresh
pytest `tmp_path` for every doctest item.

| Command | Result | Meaning |
| --- | --- | --- |
| `/usr/bin/time -p uv run pytest -s` | `798 passed, 3 skipped in 47.48s`, wall `50.58s` | Conservative full-suite baseline |
| `uv run pytest -s --durations=60 --durations-min=0.05` | `798 passed, 3 skipped in 42.58s` | Full-suite cost with slow-test evidence |
| `uv run python -m cProfile -o /tmp/gp_sphinx_full.prof -m pytest -s` | `798 passed, 3 skipped in 47.53s` | Full-suite profile source |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-abs` | `798 passed, 3 skipped in 4.43s`, wall `5.70s` | Optimized full suite, same coverage |
| `/usr/bin/time -p uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-integration-direct tests -m integration` | `21 passed, 695 deselected in 2.55s`, wall `3.65s` | Optimized integration diagnostics only |
| `/usr/bin/time -p just test-fast` | `689 passed, 3 skipped, 21 deselected in 1.55s`, wall `2.33s` | Preferred fast local loop only |
| `/usr/bin/time -p just test` | `798 passed, 3 skipped in 4.43s`, wall `5.73s` | Preferred full local command |

Two things stand out:

- the optimized full-coverage runner is still consistently fast at about
  `4.4–4.5s` pytest time
- the raw full-suite baseline dropped by about four seconds after removing
  per-doctest `tmp_path` churn, but it is still much slower than the optimized
  run, which means there is still meaningful runner/path overhead left on top
  of the real Sphinx work

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

intentionally deselects `integration` and skips the default `--doctest-modules`
policy. It is the right command for a local edit loop, but the wrong command
for making claims about total coverage or the real cost of the whole suite.

Use `uv run pytest -s` or `just test` when discussing the actual suite.

## What changed in the audit

The recent passes did two useful things without weakening coverage:

1. They kept most structure, transform, and store assertions at the
   doctree/snapshot layer instead of paying for a full HTML build.
2. They changed the remaining synthetic Sphinx tests to reuse
   `tmp_path_factory`-backed module roots more aggressively.
3. They stopped injecting a fresh pytest `tmp_path` into every doctest item and
   now reuse one session-scoped doctest path through `tests/conftest.py`.

Concrete examples:

- `tests/ext/layout/` now builds the shared layout demo scenarios once per
  test session through `tests/ext/layout/conftest.py`
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py` now uses a
  module-scoped cache root and a shared default dummy-builder result
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py` now
  reuses a module-scoped integration cache root
- `tests/test_sphinx_scenarios.py` now uses a shared module root and cache root
  instead of creating extra temp roots for each helper self-test

That means the remaining expensive tests are much more likely to be real
builder-facing contracts rather than accidental faux-E2E coverage.

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
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `36.64s` |
| `sphinx.application.Sphinx.build` | `28.32s` |
| `pathlib.Path.resolve` | `15.65s` |
| `posixpath.realpath` | `15.64s` |
| `posix.lstat` | `15.60s` |
| `_pytest.tmpdir.mktemp` | `0.30s` |
| `_pytest.pathlib.cleanup_dead_symlinks` | `0.33s` |
| `_pytest.pathlib.make_numbered_dir` | `0.14s` |

### What that means

The full suite is now paying for two big things:

1. runner-side path resolution and filesystem probing
2. a small set of real Sphinx builds

So the current story is more nuanced than “it was all tmp paths”:

- default `uv run pytest -s` is no longer paying huge cumulative time in
  `mktemp()` and numbered-dir cleanup after the doctest namespace switch
- but `Path.resolve()`, `realpath()`, and `lstat()` are still very expensive,
  which means path validation and filesystem probing remain a real runner cost
- the remaining Sphinx work is concentrated in a small, legitimate
  builder-facing surface
- the suite is no longer dominated by broad faux-E2E Sphinx coverage
- cProfile overhead magnifies the absolute times, but the ordering is clear:
  the current top costs are cached synthetic Sphinx builds plus path-resolution
  churn, not snapshot serialization or the doctree helper layer

This also explains why the fixed-`--basetemp` local recipes are still such a
large win: they keep the same assertions while bypassing most of pytest’s
remaining path-resolution and temp-root bookkeeping cost.

### Upstream-backed explanation of the runner cost

Local source inspection in `pytest` and CPython matches the profile:

- `_pytest.tmpdir.TempPathFactory.mktemp()` still goes through numbered
  directory creation
- `_pytest.tmpdir._ensure_relative_to_basetemp()` still calls `Path.resolve()`
  on the candidate path before creating the directory
- `_pytest.pathlib.make_numbered_dir()` scans prefixed entries and updates the
  `current` symlink
- `_pytest.pathlib.cleanup_dead_symlinks()` resolves symlink targets during
  session cleanup
- CPython `pathlib.Path.resolve()` delegates to `os.path.realpath()`, which is
  why `Path.resolve` and `posixpath.realpath` move together in the profile

So the raw suite is not “stuck” on one mystery function. It is paying for:

1. path resolution and filesystem probing
2. a smaller set of honest Sphinx builds
3. a much smaller tail of tmpdir naming and cleanup than earlier drafts showed

## Remaining slow tests in the real full suite

These timings come from the full-suite run:

```console
$ uv run pytest -s --durations=60 --durations-min=0.05
```

### Slowest remaining tests

| Test | Duration | Why it is slow |
| --- | --- | --- |
| `tests/ext/layout/test_integration.py::test_layout_demo_renders_api_component_contract` | `7.68s setup` | Real HTML build for final layout contract |
| `tests/ext/layout/test_snapshots.py::test_layout_demo_init_header_snapshot_annotation_disabled` | `6.75s setup` | Real HTML build for annotation-disabled fragment |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_used_by_link_html_smoke` | `3.76s call` | Cross-document HTML link contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_default_html_outputs_smoke` | `3.65s setup` | Real HTML output smoke |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_fixture_reference_html_resolves` | `3.57s call` | Cross-document HTML reference contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_default_fixture_store_and_domain_contract` | `0.70s setup` | Shared dummy-builder setup for real store/domain population |
| `tests/test_sphinx_scenarios.py::test_copy_scenario_tree_keeps_cached_source_pristine` | `0.67s call` | Intentional source-copy and mutation smoke |
| `tests/test_sphinx_scenarios.py::test_shared_sphinx_result_reuses_identical_builds` | `0.60s call` | Intentional shared-build cache smoke |

### Slowest remaining doctree scenarios

The heaviest doctree-layer tests are now well under a second:

| Test | Duration |
| --- | --- |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixtures_directive_myst_snapshot` | `0.72s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_myst_smoke` | `0.71s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_dependency_rendering_snapshot` | `0.68s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_short_name_fixture_reference_resolves` | `0.68s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_lint_level_error_sets_nonzero_status` | `0.66s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_rst_snapshot` | `0.66s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_warning_and_manual_option_snapshot` | `0.65s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixture_index_resolution_smoke` | `0.63s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixtures_directive_smoke` | `0.63s` |

That is a strong sign that the current doctree/snapshot split is doing its job:
the remaining costs above one second are mostly the tests that genuinely need a
builder.

## What the latest rewrite changed

The most recent refactor removed a few remaining cases where the suite was
still paying for more harness than the contract required:

- `tests/ext/layout/conftest.py` now builds the default and
  annotation-disabled layout HTML once per test session instead of once per
  module
- `tests/test_sphinx_scenarios.py::test_shared_sphinx_result_reuses_identical_builds`
  now uses a `dummy` builder and asserts cache semantics instead of paying for
  `index.html`
- `tests/conftest.py` now injects one session-scoped doctest `tmp_path`
  instead of paying for a fresh pytest temp directory for every doctest item
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures.py` now covers
  directive-text ordering, MyST `eval-rst` wrapping, doc-pytest-plugin intro
  scaffolding, and fixture-index row selection as pure helper tests
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py` keeps one
  real dummy-builder smoke for nested parsing and xref resolution, but replaces
  heavier full-page doctree snapshots with smaller smokes where the contract is
  “generated content is inserted in the right place”

Those rewrites added tests instead of removing them. The suite now collects
`801` items and passes `798` tests with `3` skips.

## What should stay as true E2E

These tests still deserve the harness they use:

- final layout `dt.api-header` HTML contract
- final layout header HTML fragment snapshots
- fixture cross-document HTML links
- `objects.inv` generation
- `genindex.html` generation
- text-builder smoke

Those are emitted-output contracts, not just structure or store-state checks.
Trying to demote them further would mostly trade away confidence rather than
buy meaningful speed.

## Where further surgical refactors still make sense

The current rule for future work should be:

- if the contract is ordering, filtering, static node scaffolding, generated
  directive text, or warning normalization, prefer a pure helper or doctree test
- if the contract is emitted HTML/text/inventory output or cross-document
  reference behavior, keep a real Sphinx builder

That means future refactors should focus on:

- helper extraction in `sphinx_autodoc_pytest_fixtures` before nested parsing or
  xref resolution
- repeated scenario-family reuse with `tmp_path_factory` cache roots
- avoiding per-test `tmp_path` when a module-scoped cache root is enough
- avoiding fresh doctest temp roots unless a doctest truly needs isolation

It does **not** mean chasing the remaining layout and cross-document HTML tests
out of integration just because they are visible in `--durations`.

## Collection policy cleanup

The redundant global `--ignore=` filters were removed from pytest config and the
mirrored fast-lane command.

Reason:

- `testpaths` already excludes those package source trees
- the ignored directories do not contain `>>>` doctest examples
- `uv run pytest -s --collect-only` still reports `801 tests collected`
  after removal

That makes the analysis less misleading: the fast lane is now clearly a local
workflow choice, not an apparently broader collection policy hidden behind
global ignores.

## Runner bugs and anomalies

### `uv run py.test --reruns 0 -vvv`

This command is still broken:

```console
$ uv run py.test --reruns 0 -vvv
```

Observed behavior:

- collects `0` items
- then crashes during `_pytest/capture.py`
- final exception:
  `FileNotFoundError: [Errno 2] No such file or directory`

### `uv run pytest --collect-only -q`

This command shows the same failure pattern:

```console
$ uv run pytest --collect-only -q
```

Observed behavior:

- reports `no tests collected in 0.02s`
- then crashes in `_pytest/capture.py` on `self.tmpfile.truncate()`

The pathless quiet form is broken, but the explicit non-quiet form works:

```console
$ uv run pytest -s --collect-only
```

and reports the expected `801 tests collected`.

### Relative repo-local `--basetemp`

Relative repo-local `--basetemp` is still unstable for some pathless pytest
invocations. Absolute repo-local basetemps under `.cache/` remain the stable
choice for local recipes.

### Quiet collect-only / `py.test` likely expose an upstream capture bug

The likely failure path is now much clearer from local source inspection:

- `_pytest.capture.FDCapture.snap()` calls `self.tmpfile.truncate()`
- both `uv run py.test --reruns 0 -vvv` and `uv run pytest --collect-only -q`
  tear down after collecting zero items
- in this environment the temporary capture file is already gone by the time
  `truncate()` runs, producing `FileNotFoundError`

The external repro is now much stronger than earlier drafts:

- in a tiny empty temp directory,
  `uv run --with pytest pytest --collect-only -q` crashes the same way
- the same tiny repro still crashes with `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`
- in the same tiny empty temp directory,
  `uv run --with pytest py.test -vvv` also crashes the same way
- that `py.test` repro also still crashes with
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`

That moves this from “suspected repo/plugin interaction” to “very likely
upstream pytest runner bug”, at least for the Python 3.13/3.14 and pytest 9.x
combination exercised here.

### `just` version mismatch

Current shell-visible tools:

```console
$ which just
/usr/bin/just
```

```console
$ just --version
just 1.21.0
```

```console
$ mise which just
/home/d/.config/mise/installs/just/1.49.0/just
```

So repo recipes should continue to avoid depending on 1.49.0-only behavior
until PATH is aligned in the actual developer shell.

## Why we are not adding a custom Syrupy extension

After another pass through upstream Syrupy and the current local snapshot
helpers, the answer is still “not yet”.

Current needs are already covered by:

- `tests/_snapshots.py`
- `snapshot.with_defaults(...)`
- narrow normalization of doctree strings, warning text, and focused HTML
  fragments

A custom Syrupy extension would only become worth it if we had a concrete need
for:

- one-fragment-per-file snapshot storage
- custom comparator behavior
- custom snapshot directory semantics

None of those is the current bottleneck. The real remaining costs are pytest
tmpdir behavior and a small set of legitimate Sphinx builds.

## Practical conclusion

The current state is much healthier than before:

- the full suite is slow mainly because of pytest temp-dir machinery plus a
  narrow builder-facing E2E surface
- the doctree/snapshot refactor already removed most unnecessary Sphinx
  harnessing
- fixed absolute `--basetemp` plus `tmp_path_retention_policy=none` gives a
  very fast local loop without weakening assertions

So the next performance work should stay surgical:

1. keep using `just test` and `just test-fast` for local work
2. keep the full suite as the only honest baseline for coverage discussions
3. only demote more tests when the contract is clearly helper/doctree/store
   state rather than emitted output
4. if we want another meaningful speed pass, investigate the pytest runner
   behavior upstream before shrinking more legitimate builder tests

## References

- [pytest temporary directories and retention](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- [Sphinx testing API](https://www.sphinx-doc.org/en/master/extdev/testing.html)
- [Syrupy README](https://github.com/syrupy-project/syrupy)
- [just 1.48.0 release notes](https://github.com/casey/just/releases/tag/1.48.0)
- [just 1.49.0 release notes](https://github.com/casey/just/releases/tag/1.49.0)
