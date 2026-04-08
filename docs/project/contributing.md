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
tmp-path retention for speed:

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
    -o "addopts=--tb=short --no-header --showlocals --ignore=packages/sphinx-argparse-neo --ignore=packages/sphinx-autodoc-pytest-fixtures --ignore=packages/sphinx-autodoc-docutils" \
    -o tmp_path_retention_policy=none \
    --basetemp=.cache/pytest-fast-direct \
    -q \
    --capture=tee-sys \
    tests \
    -m "not integration"
```

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

[git]: https://git-scm.com/
[uv]: https://github.com/astral-sh/uv
[entr(1)]: http://eradman.com/entrproject/
[`entr(1)`]: http://eradman.com/entrproject/
