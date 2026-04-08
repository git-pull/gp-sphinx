# Test Performance Analysis

This note tracks where time is going in the gp-sphinx test suite, which parts
of the current cost are real coverage versus avoidable harnessing, and which
runner bugs are distorting local diagnostics.

The most important correction from earlier drafts is this:

- the default baseline is the full suite, not a deselected fast lane
- `tests -m "not integration"` is a local feedback loop only
- optimized local commands are useful diagnostics, but they are not evidence
  that the full suite is cheap or complete

## Coverage-preserving benchmark matrix

These measurements were taken from `/home/d/work/python/gp-sphinx` on
2026-04-08 after the current doctree-first refactor and the latest shared
Sphinx-scenario fixture cleanup.

| Command | Result | Meaning |
| --- | --- | --- |
| `uv run pytest -s` | `790 passed, 3 skipped in 77.44s` | Conservative full-suite baseline |
| `uv run pytest -s --durations=60 --durations-min=0.05` | `790 passed, 3 skipped in 86.49s` | Full-suite cost with slow-test evidence |
| `uv run python -m cProfile -o /tmp/gp_sphinx_full_current.prof -m pytest -s` | `790 passed, 3 skipped in 79.67s` | Full-suite profile source |
| `uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-abs` | `790 passed, 3 skipped in 4.26s`, wall `5.25s` | Optimized full suite, same coverage |
| `uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-integration-direct tests -m integration` | `21 passed, 687 deselected in 2.37s`, wall `3.37s` | Optimized integration lane only |
| `uv run pytest -o "addopts=--tb=short --no-header --showlocals" -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-fast-direct --capture=tee-sys -q tests -m 'not integration'` | `681 passed, 3 skipped, 21 deselected in 1.83s`, wall `2.37s` | Optimized fast local loop only |
| `just test` | `790 passed, 3 skipped in 4.42s`, wall `5.37s` | Preferred full local command |
| `just test-fast` | `681 passed, 3 skipped, 21 deselected in 1.92s`, wall `2.52s` | Preferred fast local loop |

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

Concrete examples:

- `tests/ext/layout/` now builds the shared layout demo scenarios once per
  module through `tests/ext/layout/conftest.py`
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py` now uses a
  module-scoped cache root and a shared default dummy-builder result
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py` now
  reuses a module-scoped integration cache root

That means the remaining expensive tests are much more likely to be real
builder-facing contracts rather than accidental faux-E2E coverage.

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
| `posix.lstat` | `37.14s` |
| `pathlib.Path.resolve` | `35.41s` |
| `posixpath.realpath` | `35.37s` |
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `29.25s` |
| `sphinx.application.Sphinx.build` | `22.20s` |
| `_pytest.tmpdir.pytest_sessionfinish` / temp cleanup | `20.37s` |
| `_pytest.tmpdir._mk_tmp` / `tmp_path` / `mktemp` | `20.61s` to `20.79s` |
| `_pytest.pathlib.cleanup_dead_symlinks` | `20.37s` |
| `_pytest.pathlib.make_numbered_dir` | `12.64s` |

### What that means

The full suite is now paying for two big things:

1. pytest temp-path bookkeeping and cleanup
2. a small set of real Sphinx builds

So the current story is more nuanced than “it was all tmp paths”:

- default `uv run pytest -s` is still heavily inflated by `_pytest.tmpdir` and
  `_pytest.pathlib`
- but the remaining Sphinx work is now concentrated in a small, legitimate
  builder-facing surface
- the suite is no longer dominated by broad faux-E2E Sphinx coverage

This also explains why the fixed-`--basetemp` local recipes are such a large
win: they keep the same assertions while bypassing most of pytest’s numbered
temp-dir churn.

## Remaining slow tests in the real full suite

These timings come from the full-suite run:

```console
$ uv run pytest -s --durations=60 --durations-min=0.05
```

### Slowest remaining tests

| Test | Duration | Why it is slow |
| --- | --- | --- |
| `tests/ext/layout/test_integration.py::test_layout_demo_renders_api_component_contract` | `4.73s setup` | Real HTML build for final layout contract |
| `tests/ext/layout/test_snapshots.py::test_layout_demo_init_header_snapshot_annotated` | `4.68s setup` | Real HTML build for final header fragment |
| `tests/ext/layout/test_snapshots.py::test_layout_demo_init_header_snapshot_annotation_disabled` | `4.67s setup` | Real HTML build for annotation-disabled fragment |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_used_by_link_html_smoke` | `3.22s call` | Cross-document HTML link contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_fixture_reference_html_resolves` | `3.11s call` | Cross-document HTML reference contract |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_default_html_outputs_smoke` | `2.88s setup` | Real HTML output smoke |
| `tests/test_sphinx_scenarios.py::test_shared_sphinx_result_reuses_identical_builds` | `2.00s call` | Intentional shared-build cache smoke |

### Slowest remaining doctree scenarios

The heaviest doctree-layer tests are now well under a second:

| Test | Duration |
| --- | --- |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_dependency_rendering_snapshot` | `0.72s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_short_name_fixture_reference_resolves` | `0.65s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_doc_pytest_plugin_rst_snapshot` | `0.65s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixtures_directive_myst_snapshot` | `0.64s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py::test_autofixture_index_table_snapshot` | `0.61s` |

That is a strong sign that the current doctree/snapshot split is doing its job:
the remaining costs above one second are mostly the tests that genuinely need a
builder.

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

It does **not** mean chasing the remaining layout and cross-document HTML tests
out of integration just because they are visible in `--durations`.

## Collection policy cleanup

The redundant global `--ignore=` filters were removed from pytest config and the
mirrored fast-lane command.

Reason:

- `testpaths` already excludes those package source trees
- the ignored directories do not contain `>>>` doctest examples
- `uv run pytest -s --collect-only` still reports `793 tests collected`
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

and reports the expected `793 tests collected`.

### Relative repo-local `--basetemp`

Relative repo-local `--basetemp` is still unstable for some pathless pytest
invocations. Absolute repo-local basetemps under `.cache/` remain the stable
choice for local recipes.

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

## References

- [pytest temporary directories and retention](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- [Sphinx testing API](https://www.sphinx-doc.org/en/master/extdev/testing.html)
- [Syrupy README](https://github.com/syrupy-project/syrupy)
- [just 1.48.0 release notes](https://github.com/casey/just/releases/tag/1.48.0)
- [just 1.49.0 release notes](https://github.com/casey/just/releases/tag/1.49.0)
