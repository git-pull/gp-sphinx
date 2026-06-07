(sphinx-autodoc-pytest-fixtures-examples)=

# Examples

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

