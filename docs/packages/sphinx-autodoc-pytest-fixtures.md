# sphinx-autodoc-pytest-fixtures

{bdg-warning-line}`Alpha` {bdg-primary}`extension`

Sphinx extension for documenting pytest fixtures as first-class objects. It
registers a Python-domain fixture directive and role, autodoc helpers for bulk
fixture discovery, and the badge/index UI used throughout the page below.

```console
$ pip install sphinx-autodoc-pytest-fixtures
```

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_pytest_fixtures"]

pytest_fixture_lint_level = "warning"
pytest_external_fixture_links = {
    "db": "https://docs.example.com/testing#db",
}
```

## Registered configuration values

```{eval-rst}
.. autoconfigvalue-index:: sphinx_autodoc_pytest_fixtures
.. autoconfigvalues:: sphinx_autodoc_pytest_fixtures
```

## Registered directives and roles

```{eval-rst}
.. autodirective-index:: sphinx_autodoc_pytest_fixtures
.. autorole-index:: sphinx_autodoc_pytest_fixtures
```

## Live demos

```{py:module} spf_demo_fixtures
```

### Fixture index

```{autofixture-index} spf_demo_fixtures
```

### Bulk autodoc

```{eval-rst}
.. autofixtures:: spf_demo_fixtures
```

### Single autodoc entries

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_plain
   :no-index:
```

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_session_factory
   :no-index:
```

### Manual domain directive

```{eval-rst}
.. py:fixture:: demo_deprecated
   :no-index:
   :deprecated: 1.0
   :replacement: demo_plain
   :return-type: str

   Return a deprecated value. Use :fixture:`demo_plain` instead.
```

```{package-reference} sphinx-autodoc-pytest-fixtures
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-autodoc-pytest-fixtures)
