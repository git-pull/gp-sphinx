# sphinx-autodoc-pytest-fixtures

Sphinx extension that documents pytest fixtures as first-class domain objects
with scope badges, dependency tracking, reverse-dep graphs, and auto-generated
usage snippets.

The extension auto-loads the shared stack: `sphinx_autodoc_badges` owns badge
rendering, `sphinx_autodoc_layout` owns the shared `api-*` regions and summary
wrappers, and `sphinx_autodoc_typehints_gp` owns fixture return-type rendering.

## Install

```console
$ pip install sphinx-autodoc-pytest-fixtures
```

Installing this package also installs `sphinx-autodoc-badges`,
`sphinx-autodoc-layout`, and `sphinx-autodoc-typehints-gp` as declared dependencies.

## Usage

```python
extensions = ["sphinx_autodoc_pytest_fixtures"]
```

Then document fixtures with:

```rst
.. autofixture:: myproject.conftest.my_fixture

.. autofixtures:: myproject.conftest

.. autofixture-index:: myproject.conftest

.. auto-pytest-plugin:: myproject.pytest_plugin
   :project: myproject
   :package: myproject
   :summary: Document your pytest plugin with generated install and fixture
      reference sections.
```

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-autodoc-pytest-fixtures/) for
config values, directive options, and the badge demo.
