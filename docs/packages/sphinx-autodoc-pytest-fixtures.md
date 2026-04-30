# sphinx-autodoc-pytest-fixtures

```{gp-sphinx-package-meta} sphinx-autodoc-pytest-fixtures
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API, CSS class names, and Sphinx
config value names may change without a major version bump. Pin your
dependency to a specific version range in production.
:::

Sphinx extension for documenting pytest fixtures as first-class objects. It
registers a Python-domain fixture directive and role, autodoc helpers for bulk
fixture discovery, a higher-level pytest plugin page helper, and the
badge/index UI used throughout the page below.

Fixture pages now use the shared stack end-to-end: badge output comes from
`sphinx-ux-badges`, visible `api-*` structure comes from
`sphinx-ux-autodoc-layout`, and fixture return types use the shared
`sphinx-autodoc-typehints-gp` rendering helpers.

```console
$ pip install sphinx-autodoc-pytest-fixtures
```

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

## Working usage examples

Render a standard pytest plugin page:

````myst
:::{auto-pytest-plugin} my_project.pytest_plugin
:package: my-project
:::
````

## Live demos

```{py:module} spf_demo_fixtures
```

### Bulk autodoc

```{eval-rst}
.. autofixtures:: spf_demo_fixtures
   :no-index:
```

### Plugin page helper

:::{auto-pytest-plugin} spf_demo_fixtures
:package: sphinx-autodoc-pytest-fixtures

Add project-specific usage notes here. The helper renders the install
section, autodiscovery note, and full fixture summary/reference.
:::

#### When to use `auto-pytest-plugin`

Use this directive for a standard pytest plugin page where you want consistent
house-style: an install section, the `pytest11` autodiscovery note, and a
generated fixture summary and reference.

#### autofixtures options

| Option | Default | Description |
|--------|---------|-------------|
| `:order:` | `"source"` | `"source"` preserves module order; `"alpha"` sorts alphabetically |
| `:exclude:` | (empty) | Comma-separated fixture names to skip |
| `:no-index:` | (off) | Emit descriptions without registering fixtures in the domain index; use when the same module is documented twice on one page |

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

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-pytest-fixtures) · [PyPI](https://pypi.org/project/sphinx-autodoc-pytest-fixtures/)
