# justfile for gp-sphinx
# https://just.systems/

set shell := ["bash", "-uc"]

# File patterns
py_files := "find . -type f -not -path '*/\\.*' | grep -i '.*[.]py$' 2> /dev/null"
doc_files := "find . -type f -not -path '*/\\.*' | grep -i '.*[.]rst$\\|.*[.]md$\\|.*[.]css$\\|.*[.]py$\\|mkdocs\\.yml\\|CHANGES\\|TODO\\|.*conf\\.py' 2> /dev/null"
all_files := "find . -type f -not -path '*/\\.*' | grep -i '.*[.]py$\\|.*[.]rst$\\|.*[.]md$\\|.*[.]css$\\|.*[.]py$\\|mkdocs\\.yml\\|CHANGES\\|TODO\\|.*conf\\.py' 2> /dev/null"
fast_test_addopts := "--tb=short --no-header --showlocals"
pytest_local_opts := "-o tmp_path_retention_policy=none"
pytest_full_basetemp := ".cache/pytest-full"
pytest_fast_basetemp := ".cache/pytest-fast"
pytest_watch_basetemp := ".cache/pytest-watch"
pytest_fast_watch_basetemp := ".cache/pytest-fast-watch"

# List all available commands
default:
    @just --list

# Run tests with pytest
test *args:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .cache
    cache_root="$(pwd)/{{ pytest_full_basetemp }}"
    recipe_args="{{ args }}"
    if [[ -n "${recipe_args// }" ]]; then
        uv run pytest \
            -s \
            {{ pytest_local_opts }} \
            --basetemp="${cache_root}" \
            {{ args }}
    else
        uv run pytest \
            -s \
            {{ pytest_local_opts }} \
            --basetemp="${cache_root}"
    fi

# Run the fast local test lane without doctest-modules or integration tests
test-fast:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .cache
    cache_root="$(pwd)/{{ pytest_fast_basetemp }}"
    uv run pytest \
        {{ pytest_local_opts }} \
        -o "addopts={{ fast_test_addopts }}" \
        --basetemp="${cache_root}" \
        -q \
        --capture=tee-sys \
        tests \
        -m "not integration"

# Run tests then start continuous testing with pytest-watcher
start:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .cache
    cache_root="$(pwd)/{{ pytest_watch_basetemp }}"
    just test
    uv run ptw . \
        --runner "uv run pytest -s {{ pytest_local_opts }} --basetemp=${cache_root}"

# Run the fast local test lane continuously with pytest-watcher
start-fast:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .cache
    cache_root="$(pwd)/{{ pytest_fast_watch_basetemp }}"
    just test-fast
    uv run ptw . \
        --runner "uv run pytest {{ pytest_local_opts }} -o \"addopts={{ fast_test_addopts }}\" --basetemp=${cache_root} -q --capture=tee-sys tests -m \"not integration\""

# Watch files and run tests on change (requires entr)
watch-test:
    #!/usr/bin/env bash
    set -euo pipefail
    mkdir -p .cache
    if command -v entr > /dev/null; then
        {{ all_files }} | entr -c just test
    else
        just test
        just _entr-warn
    fi

# Build documentation
build-docs:
    just -f docs/justfile html

# Watch files and rebuild docs on change
watch-docs:
    #!/usr/bin/env bash
    set -euo pipefail
    if command -v entr > /dev/null; then
        {{ doc_files }} | entr -c just build-docs
    else
        just build-docs
        just _entr-warn
    fi

# Serve documentation
serve-docs:
    just -f docs/justfile serve

# Watch and serve docs simultaneously
dev-docs:
    #!/usr/bin/env bash
    set -euo pipefail
    just watch-docs &
    just serve-docs

# Start documentation server with auto-reload
start-docs:
    just -f docs/justfile start

# Start documentation design mode (watches static files)
design-docs:
    just -f docs/justfile design

# Format code with ruff
ruff-format:
    uv run ruff format .

# Run ruff linter
ruff:
    uv run ruff check .

# Watch files and run ruff on change
watch-ruff:
    #!/usr/bin/env bash
    set -euo pipefail
    if command -v entr > /dev/null; then
        {{ py_files }} | entr -c just ruff
    else
        just ruff
        just _entr-warn
    fi

# Run mypy type checker
mypy:
    uv run mypy $({{ py_files }})

# Watch files and run mypy on change
watch-mypy:
    #!/usr/bin/env bash
    set -euo pipefail
    if command -v entr > /dev/null; then
        {{ py_files }} | entr -c just mypy
    else
        just mypy
        just _entr-warn
    fi

[private]
_entr-warn:
    @echo "----------------------------------------------------------"
    @echo "     ! File watching functionality non-operational !      "
    @echo "                                                          "
    @echo "Install entr(1) to automatically run tasks on file change."
    @echo "See https://eradman.com/entrproject/                      "
    @echo "----------------------------------------------------------"
