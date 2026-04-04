# sphinx-autodoc-pytest-fixtures

Sphinx extension that documents pytest fixtures as first-class domain objects
with scope badges, dependency tracking, reverse-dep graphs, and auto-generated
usage snippets.

## Install

```console
$ pip install sphinx-autodoc-pytest-fixtures
```

## Usage

```python
extensions = ["sphinx_autodoc_pytest_fixtures"]
```

Then document fixtures with:

```rst
.. autofixture:: myproject.conftest.my_fixture

.. autofixtures:: myproject.conftest

.. autofixture-index:: myproject.conftest
```

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-autodoc-pytest-fixtures/) for
config values, directive options, and the badge demo.
