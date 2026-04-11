# Contributing

Install [git] and [uv].

Clone:

```console
$ git clone https://github.com/git-pull/gp-sphinx.git
```

```console
$ cd gp-sphinx
```

Install packages:

```console
$ uv sync --all-packages --all-extras --group dev
```

## Tests

Preferred local commands use a fixed pytest temp root under `.cache/` and disable
tmp-path retention for speed. `just test` keeps full coverage, while
`just test-fast` is a feedback loop only and intentionally excludes
`integration` tests:

```console
$ just test
```

```console
$ uv run pytest
```

Use raw `uv run pytest` when you want the conservative direct runner without the
local temp-dir optimization.

Fast local loop without doctest-modules or integration tests:

```console
$ just test-fast
```

Canonical direct pytest command for the same fast lane:

```console
$ uv run pytest \
    -o "addopts=--tb=short --no-header --showlocals" \
    -o tmp_path_retention_policy=none \
    --basetemp="$(pwd)/.cache/pytest-fast-direct" \
    -q \
    --capture=tee-sys \
    tests \
    -m "not integration"
```

Do not use the fast lane to reason about full-suite coverage or total suite
performance; it is intentionally deselected for local iteration.

### Automatically run tests on file save

1. `just start` (via [pytest-watcher], full local lane)
2. `just start-fast` for the fast local loop
3. `just watch-test` (requires installing [entr(1)])

[pytest-watcher]: https://github.com/olzhasar/pytest-watcher

## Documentation

Default preview server: http://localhost:3124

[sphinx-autobuild] will automatically build the docs, watch for file changes and launch a server.

From home directory: `just start-docs`
From inside `docs/`: `just start`

[sphinx-autobuild]: https://github.com/executablebooks/sphinx-autobuild

### Manual documentation (the hard way)

`cd docs/` and `just html` to build. `just serve` to start http server.

Helpers:
`just build-docs`, `just serve-docs`

Rebuild docs on file change: `just watch-docs` (requires [entr(1)])

Rebuild docs and run server via one terminal: `just dev-docs` (requires above)

## Test hierarchy

Pick the **lightest** level that exercises the behavior:

| Level | When to use | Speed |
|---|---|---|
| **Pure unit** | Strings, dicts, dataclasses — no nodes, no Sphinx | microseconds |
| **Docutils tree unit** | Constructing `docutils.nodes.*` or `sphinx.addnodes.*` directly | microseconds |
| **Snapshot unit** | Large or complex output — assert via `snapshot_doctree` | microseconds |
| **Sphinx integration** (`@pytest.mark.integration`) | Must verify actual HTML output or Sphinx event wiring | 2–10 s |

The `just test-fast` lane skips integration tests for rapid feedback.
The full `just test` lane runs everything.

### Scenario caching

Integration tests use the harness in `tests/_sphinx_scenarios.py`.
`build_shared_sphinx_result()` caches builds by a SHA-256 content-hash
digest, achieving a **9.5x speedup** (~40 s to ~4.2 s for 916 tests).

Key rules:

- Always `scope="module"` or `scope="session"` on build fixtures — never
  `scope="function"`
- Use `purge_modules` to remove synthetic Python modules from `sys.modules`
  before the initial build
- Use `SCENARIO_SRCDIR_TOKEN` + `substitute_srcdir=True` for `sys.path`
  injection in scenario `conf.py` files

### Snapshot testing

The project uses [syrupy](https://github.com/toptal/syrupy) for snapshot
assertions.  Three custom fixtures (from `tests/_snapshots.py`) normalize
their inputs before asserting:

- `snapshot_doctree(doctree)` — normalizes a `nodes.Node`
- `snapshot_html_fragment(html)` — strips ANSI, normalizes whitespace
- `snapshot_warnings(warnings)` — strips noise lines and ANSI codes

Update stored snapshots after intentional output changes:

```console
$ uv run pytest --snapshot-update
```

[git]: https://git-scm.com/
[uv]: https://github.com/astral-sh/uv
[entr(1)]: http://eradman.com/entrproject/
[`entr(1)`]: http://eradman.com/entrproject/
