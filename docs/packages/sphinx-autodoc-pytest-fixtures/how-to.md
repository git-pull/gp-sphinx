(sphinx-autodoc-pytest-fixtures-how-to)=

# How to

Use this extension when a pytest plugin needs fixture reference pages with
scope badges, linting for missing docs, and optional links back to external
fixture documentation.

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_pytest_fixtures"]

pytest_fixture_lint_level = "warning"
pytest_fixture_external_links = {
    "db": "https://docs.example.com/testing#db",
}
```

`sphinx_autodoc_pytest_fixtures` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via
{py:meth}`~sphinx.application.Sphinx.setup_extension`. You do not need to add
them separately to your `extensions` list.

## Find configuration values

The {doc}`reference` page lists the configuration values registered by the
extension.
