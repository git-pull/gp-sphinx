# Contributing

Thanks for looking. gp-sphinx is alpha (`0.1.0a37`) — the most useful
thing right now is a bug report with a reproduction, or a note on where
a `docs/` page misled you.

How this project writes prose — README, `CHANGES`, commit messages,
docstrings, source comments, and every `docs/` page — is set out
separately in [WRITING.md](WRITING.md). Read that before changing any of
it. The constraints every change is held to, and the map of what is
where, are in [AGENTS.md](../AGENTS.md).

## Getting set up

Install [git] and [uv]:

```console
$ git clone https://github.com/git-pull/gp-sphinx.git
```

```console
$ cd gp-sphinx
```

```console
$ uv sync --all-packages --all-extras --group dev
```

`gp-furo-theme`'s build backend (`sphinx_vite_builder.build`) runs
`pnpm exec vite build` during that install, so it needs [pnpm] and
[Node] on `PATH`. Working on Python only, without a JS toolchain, set
the documented escape hatch first — it makes the backend short-circuit
instead of failing:

```console
$ export SPHINX_VITE_BUILDER_SKIP=1
```

[git]: https://git-scm.com/
[uv]: https://github.com/astral-sh/uv
[pnpm]: https://pnpm.io/installation
[Node]: https://nodejs.org/

## The gates

CI is the order of record (`.github/workflows/tests.yml`); every gate it
runs has to pass before a change is done.

Format:

```console
$ uv run ruff format . --check
```

Lint:

```console
$ uv run ruff check .
```

Type-check:

```console
$ uv run mypy .
```

Test:

```console
$ uv run pytest
```

Documentation is a gate, not a courtesy. Examples in docstrings and in
the `docs/_ext/` demo modules are executed by `pytest`; the doctest
flags live in `pyproject.toml`, so there is no separate doctest step and
a green `pytest` is the proof for those. Markdown pages under `docs/`
are not executed — see
[WRITING.md](WRITING.md#documented-examples-that-run) for exactly which
blocks run and the one mistake that silently removes a test.

Before claiming a test or a gate works, show it failing. A gate that has
never been red is an assumption.

## Code style

`ruff` and `mypy` catch most of this automatically; the rest is
convention the linters do not enforce.

- **Standard library imports are namespaced**: `import enum`, not
  `from enum import Enum`. Third-party packages may use `from X import
  Y`. `dataclasses` is the one standard-library exception, for the
  cleaner `from dataclasses import dataclass, field` decorator syntax.
- **Typing uses `import typing as t`**, accessed via the namespace:
  `t.NamedTuple`, `t.Callable`, and so on.
- **`from __future__ import annotations`** is required at the top of
  every Python file; `ruff`'s `required-imports` enforces it.
- **Prefer the typed `env.domains.<name>_domain` accessors** over
  `env.get_domain("<literal>")` — `env.domains.python_domain`, not
  `env.get_domain("py")`. The typed accessors return the concrete
  domain subclass, so mypy sees subclass-specific attributes
  (`progoptions`, `data["objects"]`, …) without a cast. They require
  Sphinx 8.1's `_DomainsContainer`, which is this workspace's floor.

### Logging

- Use `logging.getLogger(__name__)` in every module; add a
  `NullHandler` in library `__init__.py` files. Never configure
  handlers, levels, or formatters in library code — that is the
  application's job.
- Use lazy formatting — `logger.debug("msg %s", val)`, not an f-string —
  so interpolation is skipped when the level is filtered and log
  aggregators group messages by template instead of by literal string.
  Guard an expensive `val` with `if logger.isEnabledFor(logging.DEBUG)`.
- Messages are lowercase, past tense, and end without punctuation:
  `"config merged"`, not `"Config merged."`. Keep the message short; put
  details in `extra`.
- Use `logger.exception()` only inside an `except` block you are not
  re-raising from. Use `logger.error(..., exc_info=True)` for a
  traceback outside an `except` block. `logger.exception()` followed by
  `raise` duplicates the traceback.
- Assert on `caplog.records`, not `caplog.text` — `caplog.record_tuples`
  cannot see `extra` fields. Scope capture with
  `caplog.at_level(logging.DEBUG, logger="gp_sphinx.config")`.

## Tests

Preferred local commands use a fixed pytest temp root under `.cache/`
and disable tmp-path retention for speed:

```console
$ just test
```

Use raw `uv run pytest` for the conservative direct runner without that
local optimization — this is also CI's own command.

Fast local loop, without `--doctest-modules` or integration tests:

```console
$ just test-fast
```

Do not use the fast lane to reason about full-suite coverage or total
suite performance; it is intentionally deselected for local iteration.
`just test` (or plain `pytest`) is the coverage-complete lane.

Run continuously while developing:

```console
$ just start
```

Requires [pytest-watcher]; `just start-fast` runs the fast lane
continuously instead, and `just watch-test` (requires [entr(1)]) is a
third option.

[pytest-watcher]: https://github.com/olzhasar/pytest-watcher
[entr(1)]: http://eradman.com/entrproject/

### Test level hierarchy

Pick the **lightest** level that exercises the behaviour. Never reach
for a full Sphinx build when a docutils node test suffices — an
integration build takes 2-10 s, a node test runs in microseconds.

| Level | When to use |
| --- | --- |
| Pure unit | Transforming strings, dicts, dataclasses — no nodes, no Sphinx |
| Docutils tree unit | Testing transforms/visitors/renderers by constructing `nodes.*` directly |
| Snapshot unit | Same as docutils tree, but output is large or complex — assert via `snapshot_doctree` |
| Sphinx integration (`@pytest.mark.integration`) | Any test that constructs a `Sphinx` app, including `buildername="dummy"`, walks a built doctree, or asserts on `result.warnings` |

All tests are plain `def test_*` functions — no `class TestFoo:`
groupings. Every test function and every `NamedTuple` fixture class is
fully type-annotated; mypy runs over `tests/` in CI.

### Parametrizing with NamedTuple

Use `t.NamedTuple` for any parametrized test with three or more inputs.
Two wiring styles are in use; pick whichever reads more clearly for the
case at hand — unpack all fields as separate parameters (dominant,
self-documenting signature), or pass the whole struct as `case` when it
is reused in assertion messages or has many fields. `test_id: str` is
always the first field; the fixture list is `_FOO_FIXTURES`
(module-private, all-caps); the fixture class is `FooFixture` or
`FooCase`, never `TestFoo`.

### Docutils tree unit tests

Construct `docutils.nodes` and `sphinx.addnodes` objects directly to
test transforms, visitors, and renderers without a Sphinx build — follow
the pattern in `tests/ext/layout/test_transforms.py`. Put `_make_*()`
builder helpers at the top of the test file. Never import
`sphinx.application.Sphinx` in a pure tree test.

### Snapshot tests

[syrupy] backs three fixtures (`tests/_snapshots.py`, loaded via
`pytest_plugins`) that normalize their inputs before asserting, so
build-path churn and docutils version noise do not cause spurious
failures: `snapshot_doctree`, `snapshot_html_fragment`, and
`snapshot_warnings`. Update stored snapshots after an intentional output
change:

```console
$ uv run pytest --snapshot-update
```

[syrupy]: https://github.com/toptal/syrupy

### Integration tests (full Sphinx build)

Use the harness in `tests/_sphinx_scenarios.py`:
`SphinxScenario`/`ScenarioFile` describe a synthetic project;
`build_shared_sphinx_result()` builds once per content-hash digest and
`build_isolated_sphinx_result()` builds fresh per test for mutating
assertions; `get_doctree()` and `read_output()` read back the result.
Always use a **module-** or **session-scoped** fixture for the build,
never function-scoped, so the expensive build is shared across the
module's tests — follow `tests/ext/typehints_gp/test_integration.py`.
Mark every such test `@pytest.mark.integration`.

`build_shared_sphinx_result()`'s content-hash caching is why the full
suite runs in seconds rather than tens of seconds; see
`notes/test-analysis.md` for the profiling data and the per-package
migration history behind that harness.

### Available fixtures

| Fixture | Source | When to use |
| --- | --- | --- |
| `tmp_path`, `tmp_path_factory` | pytest | Per-test / per-session temp directories |
| `monkeypatch` | pytest | Env vars, module attributes, `sys.modules` patching |
| `caplog` | pytest | Log assertions — use `.records`, not `.text` |
| `snapshot_doctree`, `snapshot_html_fragment`, `snapshot_warnings` | `tests/_snapshots.py` | Normalized snapshot assertions |
| `spf_suite_root`, `spf_doctree_root`, `spf_html_root` | `tests/ext/pytest_fixtures/conftest.py` | Session roots for the pytest-fixtures extension tests |
| `simple_parser`, `parser_with_groups`, … | `tests/ext/argparse/conftest.py` | `ArgumentParser` permutations for argparse tests |

### Anti-patterns

No `class TestFoo:` groupings. No `unittest.mock.patch` — use
`monkeypatch`. No `tempfile.mkdtemp()` — use `tmp_path`. No `Sphinx()`
instantiation in a unit test — build docutils nodes directly. No
unannotated test functions. No inline tuples in `parametrize` with three
or more fields — use `NamedTuple`. No function-scoped Sphinx build
fixtures.

## Documentation

Default preview server: <http://localhost:3124>.

[sphinx-autobuild] builds the docs, watches for file changes, and serves
them:

```console
$ just start-docs
```

Build once:

```console
$ just build-docs
```

Both are repository-root wrappers around `docs/justfile`; run
`just html`, `just serve`, `just watch-docs` (requires [entr(1)]), or
`just dev-docs` directly from inside `docs/` for the individual steps.

CI builds with warnings as errors:

```console
$ uv run sphinx-build -W -b dirhtml docs docs/_build/html
```

`docs/packages/<name>/` pages, the API reference, and the changelog page
are generated from live workspace metadata and `CHANGES` respectively —
see [WRITING.md](WRITING.md#generated-pages) before hand-editing one.

[sphinx-autobuild]: https://github.com/executablebooks/sphinx-autobuild

## Releasing

Never create tags. Never push tags. The owner handles tagging and tag
pushes, because a tag triggers the publish workflow. See
[Release commits](WRITING.md#release-commits).

All publishable workspace packages share one lockstep version. Bump it
everywhere with:

```console
$ just bump-version <new-version>
```

That updates every `pyproject.toml` and exposed `__version__`, relocks,
and validates the result via `scripts/ci/package_tools.py
check-versions`. Update `CHANGES` before or alongside the bump. The
release commit itself is plain and short (`Tag v<version>`), per
[Release commits](WRITING.md#release-commits) — the release manager
creates and pushes the tag after review; that push is what triggers
`release.yml` to build every package and publish to PyPI. See
[the releasing reference](https://github.com/git-pull/gp-sphinx/blob/main/docs/project/releasing.md)
for the full checklist.

## Pull requests

One subject per pull request. Unrelated cleanup found along the way
belongs in its own commit, and usually in its own pull request.

Discuss a substantial change via an issue before making it.

You may merge once you have the sign-off of one other developer. If you
do not have permission to merge, ask a reviewer to merge it for you.

Commit format is in [WRITING.md](WRITING.md#commits).

## Decorum

- Participants will be tolerant of opposing views.
- Participants must ensure that their language and actions are free of
  personal attacks and disparaging personal remarks.
- When interpreting the words and actions of others, participants
  should always assume good intentions.
- Behaviour which can be reasonably considered harassment will not be
  tolerated.

Based on [Ruby's Community Conduct Guideline](https://www.ruby-lang.org/en/conduct/).

## Security

Please do not open a public issue for a vulnerability. Use GitHub's
private reporting instead: open a
[new security advisory](https://github.com/git-pull/gp-sphinx/security/advisories/new)
on this repository.
