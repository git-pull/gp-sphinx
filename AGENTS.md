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
uv pip install --editable .
uv pip sync

# Install with development dependencies
uv pip install --editable . -G dev
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

gp-sphinx uses pytest for testing. Tests verify that configuration merging, default values, and override behavior work correctly.

### Testing Guidelines

1. **Use functional tests only**: Write tests as standalone functions, not classes. Avoid `class TestFoo:` groupings - use descriptive function names and file organization instead.

2. **Preferred pytest patterns**
   - Use `tmp_path` (pathlib.Path) fixture over Python's `tempfile`
   - Use `monkeypatch` fixture over `unittest.mock`

3. **Running tests continuously**
   - Use pytest-watcher during development: `uv run ptw .`
   - For doctests: `uv run ptw . --now --doctest-modules`

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
