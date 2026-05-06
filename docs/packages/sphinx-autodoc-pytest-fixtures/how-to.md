(sphinx-autodoc-pytest-fixtures-how-to)=

# How to

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_pytest_fixtures"]

pytest_fixture_lint_level = "warning"
pytest_fixture_external_links = {
    "db": "https://docs.example.com/testing#db",
}
```

`sphinx_autodoc_pytest_fixtures` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via `app.setup_extension()`.
You do not need to add them separately to your `extensions` list.

## Registered configuration values

```{eval-rst}
.. autoconfigvalues:: sphinx_autodoc_pytest_fixtures
```
