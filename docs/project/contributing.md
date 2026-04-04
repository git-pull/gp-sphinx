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

```console
$ uv run py.test
```

### Automatically run tests on file save

1. `just start` (via [pytest-watcher])
2. `just watch-test` (requires installing [entr(1)])

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
