# AGENTS.md

This file provides guidance to AI agents (including Claude Code, Cursor, and other LLM-powered tools) when working with code in this repository.

## CRITICAL REQUIREMENTS

### Test Success
- ALL tests MUST pass for code to be considered complete and working
- Never describe code as "working as expected" if there are ANY failing tests
- Even if specific feature tests pass, failing tests elsewhere indicate broken functionality
- Changes that break existing tests must be fixed before considering implementation complete
- A successful implementation must pass linting, type checking, AND all existing tests

## Project Overview

gp-sphinx (`gp_sphinx`) is a shared Sphinx documentation platform for Python projects. It consolidates duplicated docs configuration, extensions, theme settings, and workarounds from 14+ repositories into a single reusable package.

Key features:
- `merge_sphinx_config()` API for shared defaults with per-project overrides
- Shared extension list (autodoc, intersphinx, myst_parser, sphinx_design, etc.)
- Shared Furo theme configuration (CSS variables, fonts, sidebar, footer)
- Bundled workarounds (tabs.js removal, spa-nav.js injection)
- Shared font configuration (IBM Plex via Fontsource)

## Development Environment

This project uses:
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) for dependency management
- [ruff](https://github.com/astral-sh/ruff) for linting and formatting
- [mypy](https://github.com/python/mypy) for type checking
- [pytest](https://docs.pytest.org/) for testing
  - [pytest-watcher](https://github.com/olzhasar/pytest-watcher) for continuous testing

## Common Commands

### Setting Up Environment

```bash
# Install dependencies
uv sync --all-packages

# Install with development dependencies
uv sync --all-packages --all-extras --group dev
```

### Running Tests

```bash
# Run all tests
just test
# or directly with pytest
uv run pytest

# Run a single test file
uv run pytest tests/test_config.py

# Run a specific test
uv run pytest tests/test_config.py::test_merge_sphinx_config

# Run tests with test watcher
just start
# or
uv run ptw .

# Run tests with doctests
uv run ptw . --now --doctest-modules
```

### Linting and Type Checking

```bash
# Run ruff for linting
just ruff
# or directly
uv run ruff check .

# Format code with ruff
just ruff-format
# or directly
uv run ruff format .

# Run ruff linting with auto-fixes
uv run ruff check . --fix --show-fixes

# Run mypy for type checking
just mypy
# or directly
uv run mypy src tests

# Watch mode for linting (using entr)
just watch-ruff
just watch-mypy
```

### Development Workflow

Follow this workflow for code changes:

1. **Format First**: `uv run ruff format .`
2. **Run Tests**: `uv run pytest`
3. **Run Linting**: `uv run ruff check . --fix --show-fixes`
4. **Check Types**: `uv run mypy`
5. **Verify Tests Again**: `uv run pytest`

### Documentation

```bash
# Build documentation
just build-docs

# Start documentation server with auto-reload
just start-docs
```

## Code Architecture

gp-sphinx provides a shared configuration layer for Sphinx documentation:

```
gp_sphinx/
  __init__.py          # Package entry point
  config.py            # merge_sphinx_config() and config building logic
  defaults.py          # Default extensions, theme options, MyST config, fonts
  assets/              # Shared JS/CSS (spa-nav.js, workarounds)
  _compat.py           # Sphinx/docutils version compatibility
```

### Core Modules

1. **Config** (`src/gp_sphinx/config.py`)
   - `merge_sphinx_config()` API for building complete Sphinx config
   - Deep-merge support for theme options
   - Per-project override mechanism

2. **Defaults** (`src/gp_sphinx/defaults.py`)
   - `DEFAULT_EXTENSIONS` list
   - `DEFAULT_THEME_OPTIONS` dict
   - `DEFAULT_MYST_EXTENSIONS` list
   - `DEFAULT_FONT_FAMILIES` dict
   - Shared sidebar configuration

## Testing Strategy

All tests are plain functions (`def test_*`). No `class TestFoo:` groupings. Every test
function and every `NamedTuple` fixture class must be fully type-annotated; mypy runs as
part of CI.

Run continuously while developing:

```console
$ uv run ptw .
```

Include doctests:

```console
$ uv run ptw . --now --doctest-modules
```

### Test Level Hierarchy

Pick the **lightest** level that exercises the behavior. Never reach for a full Sphinx
build when a docutils node test suffices — an integration build takes 2–10 s, a node
test runs in microseconds.

| Level | When to use |
|---|---|
| **Pure unit** | Transforming strings, dicts, dataclasses — no nodes, no Sphinx |
| **Docutils tree unit** | Testing transforms/visitors/renderers by constructing `nodes.*` directly |
| **Snapshot unit** | Same as docutils tree, but output is large or complex — assert via `snapshot_doctree` |
| **Sphinx integration** (`@pytest.mark.integration`) | Must verify actual HTML output or Sphinx event wiring |

### Type Annotations (required everywhere)

Every test function must annotate all parameters and the return type:

```python
def test_something(value: str, expected: int) -> None:
    assert compute(value) == expected
```

Every `NamedTuple` fixture class must annotate all fields.

### NamedTuple Parametrization

Use `t.NamedTuple` for any parametrized test with three or more inputs. Two wiring
styles are in use — pick whichever reads more clearly for the case at hand.

**Style A — unpack all fields** (dominant; used in `test_unit.py`, lexer tests, etc.)

Each field becomes a typed parameter in the test function, which makes the signature
self-documenting:

```python
import typing as t

import pytest


class FooFixture(t.NamedTuple):
    """Test case for foo()."""

    test_id: str  # always the first field
    input: str
    expected: str


_FOO_FIXTURES: list[FooFixture] = [
    FooFixture(test_id="basic", input="a", expected="A"),
    FooFixture(test_id="empty", input="", expected=""),
]


@pytest.mark.parametrize(
    list(FooFixture._fields),
    _FOO_FIXTURES,
    ids=[f.test_id for f in _FOO_FIXTURES],
)
def test_foo(test_id: str, input: str, expected: str) -> None:
    """foo() uppercases its input."""
    assert foo(input) == expected
```

**Style B — pass whole struct as `case`** (used in `test_directives.py`,
`test_nodes.py`, when the struct is reused in assertion messages or has many fields):

```python
@pytest.mark.parametrize(
    "case",
    _FOO_FIXTURES,
    ids=lambda c: c.test_id,
)
def test_foo(case: FooFixture) -> None:
    """foo() uppercases its input."""
    assert foo(case.input) == case.expected
```

Naming conventions:

- `test_id: str` is **always the first field**
- Fixture list: `_FOO_FIXTURES` (module-private, all-caps)
- Fixture class: `FooFixture` or `FooCase` — never `TestFoo`

### Docutils Tree Unit Tests (no Sphinx build)

Test transforms, visitors, and renderers by constructing `docutils.nodes` and
`sphinx.addnodes` objects directly. Follow the pattern in
`tests/ext/layout/test_transforms.py`:

```python
from docutils import nodes
from sphinx import addnodes


def _make_desc(
    *content_children: nodes.Node,
    domain: str = "py",
    objtype: str = "function",
) -> addnodes.desc:
    desc = addnodes.desc(domain=domain, objtype=objtype)
    desc += addnodes.desc_signature()
    content = addnodes.desc_content()
    for child in content_children:
        content += child
    desc += content
    return desc


def test_transform_wraps_content_runs() -> None:
    """_wrap_content_runs groups consecutive content nodes."""
    desc = _make_desc(nodes.paragraph("", "summary"), nodes.field_list())
    _wrap_content_runs(desc)
    assert any(isinstance(n, ContentGroup) for n in desc[1])
```

- Put `_make_*()` builder helpers at the top of the test file, near the tests that use
  them.
- Never import `sphinx.application.Sphinx` in a pure tree test.
- Use `nodes.document()` (with a minimal `settings` object from
  `docutils.frontend.OptionParser`) only when the transform requires a real document
  root.

### Snapshot Tests (syrupy)

Use when the expected output is too large or fragile to inline. The three fixtures
(from `tests/_snapshots.py`, loaded automatically via `pytest_plugins`) normalize their
inputs before asserting so that build-path churn and docutils version noise do not cause
spurious failures:

- `snapshot_doctree(doctree, *, name=None, roots=())` — normalizes a `nodes.Node`
- `snapshot_html_fragment(fragment, *, name=None, roots=())` — strips ANSI, normalizes whitespace
- `snapshot_warnings(warnings, *, name=None, roots=())` — strips noise lines and ANSI codes

```python
import typing as t


def test_layout_render(
    snapshot_doctree: t.Callable[..., None],
) -> None:
    """Transform produces a stable doctree."""
    desc = _make_large_signature_desc()
    on_doctree_resolved(desc)
    snapshot_doctree(desc)
```

Update stored snapshots after intentional output changes:

```console
$ uv run pytest --snapshot-update
```

### Integration Tests (full Sphinx build)

Use the harness in `tests/_sphinx_scenarios.py`. The key types and helpers:

- `SphinxScenario(files=(...), confoverrides={}, buildername="html")` — describes the
  synthetic project; `buildername` defaults to `"html"`, override for text builds
- `ScenarioFile(relative_path, contents, substitute_srcdir=False)` — one source file
- `build_shared_sphinx_result(cache_root, scenario, *, purge_modules=())` — builds
  once per content-hash digest; `purge_modules` removes named modules from `sys.modules`
  before the initial build to prevent stale import cache — required when scenario files
  inject a Python module into `sys.path`
- `build_isolated_sphinx_result(cache_root, tmp_path, scenario, *, purge_modules=())`
  — fresh build per test, for mutating assertions
- `derive_sphinx_scenario_cache_root(tmp_path)` — derives a stable per-session cache
  root from any `tmp_path` by using its parent directory
- `copy_scenario_tree(cache_root, scenario, destination_root)` — materialize source
  files into a directory without running a Sphinx build
- `get_doctree(result, docname, post_transforms=False)` — deep-copied doctree from
  the built environment
- `read_output(result, filename)` — reads a built output file as a string

Always use a **module-scoped** (or session-scoped) fixture for the build — never
function-scoped — so the expensive Sphinx build is shared across all tests in the
module. Follow the pattern in `tests/ext/typehints_gp/test_integration.py`:

```python
import textwrap

import pytest

from tests._sphinx_scenarios import (
    SCENARIO_SRCDIR_TOKEN,
    ScenarioFile,
    SharedSphinxResult,
    SphinxScenario,
    build_shared_sphinx_result,
    read_output,
)

_CONF_PY = textwrap.dedent(
    """\
    import sys
    sys.path.insert(0, r"__SCENARIO_SRCDIR__")
    extensions = ["sphinx.ext.autodoc", "my_extension"]
    """
)

_INDEX_RST = textwrap.dedent(
    """\
    Demo
    ====

    .. autofunction:: my_module.my_function
    """
)


@pytest.fixture(scope="module")
def my_html_result(
    tmp_path_factory: pytest.TempPathFactory,
) -> SharedSphinxResult:
    """Build a minimal Sphinx project using my_extension."""
    cache_root = tmp_path_factory.mktemp("my-ext-html")
    scenario = SphinxScenario(
        files=(
            ScenarioFile("index.rst", _INDEX_RST),
            ScenarioFile(
                "conf.py",
                _CONF_PY.replace("__SCENARIO_SRCDIR__", SCENARIO_SRCDIR_TOKEN),
                substitute_srcdir=True,
            ),
        ),
    )
    return build_shared_sphinx_result(
        cache_root,
        scenario,
        purge_modules=("my_module", "my_extension"),
    )


@pytest.mark.integration
def test_my_feature_appears_in_html(my_html_result: SharedSphinxResult) -> None:
    """Extension renders the expected markup."""
    html = read_output(my_html_result, "index.html")
    assert "my-feature" in html
```

Rules:
- Always mark with `@pytest.mark.integration`
- Always `scope="module"` or `scope="session"` on the build fixture — never
  `scope="function"`
- Use `textwrap.dedent("""...""")` for inline source strings
- Use `SCENARIO_SRCDIR_TOKEN` + `substitute_srcdir=True` for `sys.path` injection in
  `conf.py`

> **See also:** `notes/test-analysis.md` — profiling data, 9.5x speedup rationale,
> and the per-package migration history for the shared autodoc stack.

### Available Fixtures Reference

| Fixture | Source | When to use |
|---|---|---|
| `tmp_path` | pytest built-in | Per-test temp directory |
| `tmp_path_factory` | pytest built-in | Session/module fixtures that create temp dirs |
| `monkeypatch` | pytest built-in | Env vars, module attributes, `sys.modules` patching |
| `caplog` | pytest built-in | Log assertions; use `caplog.records`, not `caplog.text` |
| `snapshot_doctree` | `tests/_snapshots.py` | Normalized doctree snapshot assertion |
| `snapshot_html_fragment` | `tests/_snapshots.py` | Normalized HTML string snapshot assertion |
| `snapshot_warnings` | `tests/_snapshots.py` | Normalized Sphinx warning snapshot assertion |
| `spf_suite_root`, `spf_doctree_root`, `spf_html_root` | `tests/ext/pytest_fixtures/conftest.py` | Session roots for sphinx-pytest-fixture ext tests |
| `simple_parser`, `parser_with_groups`, … | `tests/ext/argparse_neo/conftest.py` | `ArgumentParser` permutations for argparse_neo tests |

### Anti-Patterns

- **No `class TestFoo:` groupings** — use descriptive function names and file
  organization instead
- **No `unittest.mock.patch`** — use `monkeypatch`
- **No `tempfile.mkdtemp()`** — use `tmp_path`
- **No `Sphinx()` instantiation in a unit test** — build docutils nodes directly
- **No unannotated test functions** — every parameter and `-> None` must be typed
- **No `# doctest: +SKIP`** in module doctests (see Doctests section)
- **No inline tuples in `parametrize`** when there are three or more fields — use
  `NamedTuple`
- **No function-scoped Sphinx build fixtures** — always module- or session-scoped

## Coding Standards

Key highlights:

### Imports

- **Use namespace imports for standard library modules**: `import enum` instead of `from enum import Enum`
  - **Exception**: `dataclasses` module may use `from dataclasses import dataclass, field` for cleaner decorator syntax
  - This rule applies to Python standard library only; third-party packages may use `from X import Y`
- **For typing**, use `import typing as t` and access via namespace: `t.NamedTuple`, etc.
- **Use `from __future__ import annotations`** at the top of all Python files

### Docstrings

Follow NumPy docstring style for all functions and methods:

```python
"""Short description of the function or class.

Detailed description using reStructuredText format.

Parameters
----------
param1 : type
    Description of param1
param2 : type
    Description of param2

Returns
-------
type
    Description of return value
"""
```

### Doctests

**All functions and methods MUST have working doctests.** Doctests serve as both documentation and tests.

**CRITICAL RULES:**
- Doctests MUST actually execute - never comment out function calls or similar
- Doctests MUST NOT be converted to `.. code-block::` as a workaround (code-blocks don't run)
- If you cannot create a working doctest, **STOP and ask for help**

**Available tools for doctests:**
- `doctest_namespace` fixtures (from conftest.py): `tmp_path`
- Ellipsis for variable output: `# doctest: +ELLIPSIS`
- Update `conftest.py` to add new fixtures to `doctest_namespace`

**`# doctest: +SKIP` is NOT permitted** - it's just another workaround that doesn't test anything.

**When output varies, use ellipsis:**
```python
>>> result = merge_sphinx_config(project="test", version="1.0", copyright="2026")
>>> result["project"]
'test'
>>> len(result["extensions"]) > 10  # doctest: +ELLIPSIS
True
```

### Logging Standards

These rules guide future logging changes; existing code may not yet conform.

#### Logger setup

- Use `logging.getLogger(__name__)` in every module
- Add `NullHandler` in library `__init__.py` files
- Never configure handlers, levels, or formatters in library code -- that's the application's job

#### Lazy formatting

`logger.debug("msg %s", val)` not f-strings. Two rationales:
- Deferred string interpolation: skipped entirely when level is filtered
- Aggregator message template grouping: `"Running %s"` is one signature grouped x10,000; f-strings make each line unique

When computing `val` itself is expensive, guard with `if logger.isEnabledFor(logging.DEBUG)`.

#### Log levels

| Level | Use for | Examples |
|-------|---------|----------|
| `DEBUG` | Internal mechanics | Config merge steps, extension resolution |
| `INFO` | User-visible operations | Config loaded, extensions resolved |
| `WARNING` | Recoverable issues, deprecation | Unknown extension, deprecated option |
| `ERROR` | Failures that stop an operation | Invalid config, missing dependency |

#### Message style

- Lowercase, past tense for events: `"config merged"`, `"extension resolved"`
- No trailing punctuation
- Keep messages short; put details in `extra`, not the message string

#### Exception logging

- Use `logger.exception()` only inside `except` blocks when you are **not** re-raising
- Use `logger.error(..., exc_info=True)` when you need the traceback outside an `except` block
- Avoid `logger.exception()` followed by `raise` -- this duplicates the traceback

#### Testing logs

Assert on `caplog.records` attributes, not string matching on `caplog.text`:
- Scope capture: `caplog.at_level(logging.DEBUG, logger="gp_sphinx.config")`
- Filter records rather than index by position
- `caplog.record_tuples` cannot access extra fields -- always use `caplog.records`

#### Avoid

- f-strings/`.format()` in log calls
- Catch-log-reraise without adding new context
- `print()` for diagnostics
- Logging secret env var values (log key names only)

### Git Commit Standards

Format commit messages as:
```
Scope(type[detail]): concise description

why: Explanation of necessity or impact.
what:
- Specific technical changes made
- Focused on a single topic
```

Common commit types:
- **feat**: New features or enhancements
- **fix**: Bug fixes
- **refactor**: Code restructuring without functional change
- **docs**: Documentation updates
- **chore**: Maintenance (dependencies, tooling, config)
- **test**: Test-related updates
- **style**: Code style and formatting
- **py(deps)**: Dependencies
- **py(deps[dev])**: Dev Dependencies
- **ai(rules[AGENTS])**: AI rule updates
- **ai(claude[rules])**: Claude Code rules (CLAUDE.md)
- **ai(claude[command])**: Claude Code command changes

Example:
```
config(feat[merge]): Add deep-merge support for theme options

why: Enable per-project theme overrides without replacing entire dict
what:
- Add deep_merge() helper for nested dict merging
- Update merge_sphinx_config() to deep-merge theme_options
- Add tests for nested override behavior
```
For multi-line commits, use heredoc to preserve formatting:
```bash
git commit -m "$(cat <<'EOF'
feat(Component[method]) add feature description

why: Explanation of the change.
what:
- First change
- Second change
EOF
)"
```

## Documentation Standards

### Code Blocks in Documentation

When writing documentation (README, CHANGES, docs/), follow these rules for code blocks:

**One command per code block.** This makes commands individually copyable. For sequential commands, either use separate code blocks or chain them with `&&` or `;` and `\` continuations (keeping it one logical command).

**Put explanations outside the code block**, not as comments inside.

Good:

Run the tests:

```console
$ uv run pytest
```

Run with coverage:

```console
$ uv run pytest --cov
```

Bad:

```console
# Run the tests
$ uv run pytest

# Run with coverage
$ uv run pytest --cov
```

### Shell Command Formatting

These rules apply to shell commands in documentation (README, CHANGES, docs/), **not** to Python doctests.

**Use `console` language tag with `$ ` prefix.** This distinguishes interactive commands from scripts and enables prompt-aware copy in many terminals.

Good:

```console
$ uv run pytest
```

Bad:

```bash
uv run pytest
```

**Split long commands with `\` for readability.** Each flag or flag+value pair gets its own continuation line, indented. Positional parameters go on the final line.

Good:

```console
$ pipx install \
    --suffix=@next \
    --pip-args '\--pre' \
    --force \
    'gp-sphinx'
```

Bad:

```console
$ pipx install --suffix=@next --pip-args '\--pre' --force 'gp-sphinx'
```

## Debugging Tips

When stuck in debugging loops:

1. **Pause and acknowledge the loop**
2. **Minimize to MVP**: Remove all debugging cruft and experimental code
3. **Document the issue** comprehensively for a fresh approach
4. **Format for portability** (using quadruple backticks)
