# Test Performance Analysis

This note captures where the test suite was spending time during local runs in
`/home/d/work/python/gp-sphinx`, what changed after the doctree-first refactor,
and why the remaining cost is mostly pytest temp-directory management rather
than Sphinx itself.

## Command timings

| Command | Result |
| --- | --- |
| `uv run pytest -s` | `781 passed, 3 skipped in 91.73s` |
| `uv run pytest -o "addopts=..." --capture=tee-sys -q tests -m 'not integration'` | `670 passed, 3 skipped, 23 deselected in 25.35s` |
| `uv run pytest -o "addopts=..." -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-fast-direct --capture=tee-sys -q tests -m 'not integration'` | `670 passed, 3 skipped, 23 deselected in 2.45s`, wall time `3.07s` |
| `uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-integration-direct tests -m integration` | `23 passed, 676 deselected in 3.18s`, wall time `4.54s` |
| `uv run pytest -s -o tmp_path_retention_policy=none --basetemp=/home/d/work/python/gp-sphinx/.cache/pytest-full-abs` | `781 passed, 3 skipped in 5.22s`, wall time `6.47s` |
| `just test-fast` via `/usr/bin/just 1.21.0` | `670 passed, 3 skipped, 23 deselected in 1.91s`, wall time `2.60s` |
| `just test` via `/usr/bin/just 1.21.0` | `781 passed, 3 skipped in 5.01s`, wall time `6.27s` |

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
meaningful chunk of time is still going into temp-path resolution overhead.

## What is still legitimately E2E

These tests are still doing the right amount of harnessing, because their
contract is emitted output rather than doctree structure:

- Layout final `dt.api-header` HTML contract
- Fixture cross-document HTML links
- `objects.inv` generation
- `genindex.html` generation
- Text-builder smoke

The doctree-first split already moved most previous faux-E2E checks into
doctree, store, or focused snapshot coverage.

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

## References

- [pytest builtin fixtures and `tmp_path_factory`](https://docs.pytest.org/en/4.6.x/builtin.html)
- [just 1.48.0 release notes](https://github.com/casey/just/releases/tag/1.48.0)
- [just 1.49.0 release notes](https://github.com/casey/just/releases/tag/1.49.0)
