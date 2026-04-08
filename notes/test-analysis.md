# Test Performance Analysis

This note captures where the test suite was spending time during local runs in
`/home/d/work/python/gp-sphinx`, what changed after the doctree-first refactor,
and why the remaining cost is mostly pytest temp-directory management rather
than Sphinx itself.

## Command timings

| Command | Result |
| --- | --- |
| `uv run pytest -s` | `790 passed, 3 skipped in 78.56s` |
| `uv run pytest -o "addopts=..." --capture=tee-sys -q tests -m 'not integration' --durations=25 --durations-min=0.05` | `681 passed, 3 skipped, 21 deselected in 31.77s` |
| `uv run pytest -o "addopts=..." -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-fast-direct --capture=tee-sys -q tests -m 'not integration'` | `681 passed, 3 skipped, 21 deselected in 2.53s`, wall time `3.39s` |
| `uv run pytest -s tests -m integration --durations=25 --durations-min=0.05` | `21 passed, 687 deselected in 18.20s` |
| `uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-integration-direct tests -m integration` | `21 passed, 687 deselected in 3.11s`, wall time `4.45s` |
| `uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-abs` | `790 passed, 3 skipped in 5.00s`, wall time `6.21s` |
| `just test-fast` via `/usr/bin/just 1.21.0` | `681 passed, 3 skipped, 21 deselected in 2.39s`, wall time `3.17s` |
| `just test` via `/usr/bin/just 1.21.0` | `790 passed, 3 skipped in 4.99s`, wall time `6.20s` |

## Profile findings

### Fast lane without fixed basetemp

The fast-lane cProfile was taken with:

```console
$ uv run python -m cProfile \
    -o /tmp/gp_sphinx_fast.prof \
    -m pytest \
    -o "addopts=--tb=short --no-header --showlocals --ignore=packages/sphinx-argparse-neo --ignore=packages/sphinx-autodoc-pytest-fixtures --ignore=packages/sphinx-autodoc-docutils" \
    --capture=tee-sys \
    -q \
    tests \
    -m 'not integration'
```

Top cumulative costs:

| Function | Cumulative time |
| --- | --- |
| `posix.lstat` | `31.29s` |
| `pathlib.Path.resolve` / `posixpath.realpath` | `28.92s` |
| `_pytest.pathlib.cleanup_dead_symlinks` | `26.66s` |
| `_pytest.tmpdir.tmp_path` / `_mk_tmp` / `mktemp` | `24.17s` |
| `_pytest.pathlib.make_numbered_dir` | `14.51s` |

Conclusion: the dominant cost in the raw fast lane is pytest temp-directory
retention, numbering, cleanup, and path resolution. The tests are paying for
`tmp_path` machinery more than for their own logic.

### Integration lane before fixed basetemp

The integration cProfile was taken with:

```console
$ uv run python -m cProfile \
    -o /tmp/gp_sphinx_integration.prof \
    -m pytest \
    -s \
    tests \
    -m integration
```

Top cumulative costs:

| Function | Cumulative time |
| --- | --- |
| `tests._sphinx_scenarios.build_shared_sphinx_result` | `33.85s` |
| `sphinx.application.Sphinx.build` | `23.50s` |
| `tests.ext.pytest_fixtures._scenario_support.build_fixture_result` | `14.83s` |
| `posix.lstat` / `Path.resolve` / `realpath` | `13.99s` |
| `sphinx.builders.html.handle_page` / Jinja render path | `12.12s` to `10.54s` |

Conclusion: the integration lane is doing real Sphinx work, but even there a
meaningful chunk of time was going into temp-path resolution overhead before
the fixed-basetemp recipes. With the runner fix in place, the remaining slow
tests are the intentional builder-facing contracts.

## Remaining slow tests under the default integration runner

Current `--durations` output shows the remaining heavy tests are mostly the
intended E2E surface:

| Test | Approx. duration |
| --- | --- |
| `tests/ext/layout/test_integration.py::test_layout_demo_renders_api_component_contract` | `2.56s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_used_by_link_html_smoke` | `2.35s` |
| `tests/ext/layout/test_snapshots.py::test_layout_demo_init_header_snapshot_annotation_disabled` | `2.18s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_cross_document_fixture_reference_html_resolves` | `2.17s` |
| `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_integration.py::test_default_html_outputs_smoke` | `1.66s` |
| `tests/test_sphinx_scenarios.py::test_shared_sphinx_result_reuses_identical_builds` | `1.47s` |

The two doctree-heavy pytest-fixture scenarios that previously sat around
`1.0–1.5s` each are now below `0.6s`, because their row/filtering and
doc-pytest-plugin assembly logic moved into direct helper tests instead of
always paying for a synthetic Sphinx app.

## What is still legitimately E2E

These tests are still doing the right amount of harnessing, because their
contract is emitted output rather than doctree structure:

- Layout final `dt.api-header` HTML contract
- Fixture cross-document HTML links
- `objects.inv` generation
- `genindex.html` generation
- Text-builder smoke

The doctree-first split already moved most previous faux-E2E checks into
doctree, store, or focused snapshot coverage. The latest surgical refactor also
demoted more `sphinx_autodoc_pytest_fixtures` behavior into pure helper tests:

- generated nested `autofixture` directive text
- fixture-index row selection and static table structure
- doc-pytest-plugin intro and section assembly

That leaves the builder-backed fixture tests focused on cross-document links,
resolved references, and emitted file output.

## Temp-path heavy areas

The repo still has a lot of `tmp_path` usage:

- `tests/ext/test_sphinx_fonts.py`
- `tests/ext/pytest_fixtures/test_sphinx_pytest_fixtures_doctree.py`
- `tests/test_snapshots.py`
- `tests/test_sphinx_scenarios.py`
- `tests/ext/layout/test_snapshots.py`
- `tests/ext/layout/test_integration.py`

Not all of those are a problem. The main takeaway is that once the runner uses
a fixed `--basetemp` and `tmp_path_retention_policy=none`, the remaining tmp
usage becomes cheap enough that only truly unnecessary filesystem fixtures are
worth rewriting.

## Known bugs and anomalies

### `py.test` capture teardown failure

This command is currently broken in the local environment:

```console
$ uv run py.test --reruns 0 -vvv
```

Observed behavior:

- pytest collects `0` items
- teardown crashes in `_pytest/capture.py`
- final exception is `FileNotFoundError: [Errno 2] No such file or directory`

The same failure pattern also appears with some `pytest -q <explicit paths>`
invocations when collection returns zero items. This looks like an external
runner/capture bug in the current Python 3.14 / pytest environment, not a
gp-sphinx test-design bug.

### Relative repo-local `--basetemp` plus pathless pytest is unstable

This command shape also proved unstable locally:

```console
$ uv run pytest \
    -o tmp_path_retention_policy=none \
    --basetemp=.cache/pytest-full
```

Observed behavior:

- pytest collects `0` items
- teardown crashes in `_pytest/capture.py`
- the same command succeeds when either:
  - `-s` is enabled, or
  - `--basetemp` is an absolute repo-local path such as
    `/home/d/work/python/gp-sphinx/.cache/pytest-full-abs`

The local `just` recipes now use absolute `.cache` paths and `-s` for the full
suite to avoid this edge case while still keeping the cache inside the repo.

### `just` version mismatch

The active shell resolves:

```console
$ which just
/usr/bin/just
```

```console
$ just --version
just 1.21.0
```

But `mise` points to:

```console
$ mise which just
/home/d/.config/mise/installs/just/1.49.0/just
```

Repo recipes should stay compatible with the shell-visible binary until PATH is
made consistent in the actual developer shell.

## Why we are not adding a custom Syrupy extension

After reviewing upstream Syrupy examples and the current local helpers:

- `tests/_snapshots.py` already centralizes normalization with
  `snapshot.with_defaults(...)`
- current needs are normalized doctree text, focused HTML fragments, and
  warning-text cleanup
- a custom extension would mainly buy snapshot directory/layout customization,
  not better correctness

So the current fixture-based helper approach is sufficient for now. Revisit a
custom extension only if snapshot storage layout or one-fragment-per-file
snapshots becomes a concrete maintenance problem.

## Latest raw-suite note

The raw `uv run pytest -s` benchmark is intentionally kept as the conservative
baseline: `790 passed, 3 skipped in 78.56s`.

It still pays for pytest's default temp-path behavior and the current
capture-path oddities. The optimized local recipes are the preferred developer
path; they preserve the same coverage while avoiding the temp-dir cost center
that dominates the default runner.

## References

- [pytest temporary directories and retention](https://docs.pytest.org/en/stable/how-to/tmp_path.html)
- [Sphinx testing API](https://www.sphinx-doc.org/en/master/extdev/testing.html)
- [just 1.48.0 release notes](https://github.com/casey/just/releases/tag/1.48.0)
- [just 1.49.0 release notes](https://github.com/casey/just/releases/tag/1.49.0)
