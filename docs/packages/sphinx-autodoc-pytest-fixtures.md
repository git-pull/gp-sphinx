# sphinx-autodoc-pytest-fixtures

{bdg-warning-line}`Alpha` {bdg-primary}`extension`

Sphinx extension that documents pytest fixtures as first-class domain objects
with scope badges, dependency tracking, and auto-generated usage snippets.

```console
$ pip install sphinx-autodoc-pytest-fixtures
```

## Usage

Add to your Sphinx extensions:

```python
extensions = ["sphinx_autodoc_pytest_fixtures"]
```

## Directives

| Directive | Description |
|-----------|-------------|
| `.. py:fixture:: name` | Document a single fixture with full metadata |
| `.. autofixture:: module.name` | Autodoc-style single fixture (use `eval-rst` in MyST) |
| `.. autofixtures:: module` | Discover and document all fixtures in a module |
| `.. autofixture-index:: module` | Summary table with badge columns |

## Role

`:fixture:\`name\`` — cross-reference to a documented fixture.

## Configuration

| Config | Default | Description |
|--------|---------|-------------|
| `pytest_fixture_hidden_dependencies` | `PYTEST_HIDDEN` (frozenset) | Fixture names to hide from "Depends on" |
| `pytest_fixture_builtin_links` | `PYTEST_BUILTIN_LINKS` (dict) | Fallback URLs for pytest builtins |
| `pytest_external_fixture_links` | `{}` | Custom external fixture links |
| `pytest_fixture_lint_level` | `"warning"` | Validation severity: `"none"`, `"warning"`, or `"error"` |

## py:fixture options

| Option | Type | Description |
|--------|------|-------------|
| `:scope:` | string | `function`, `module`, `class`, or `session` |
| `:autouse:` | flag | Mark as autouse |
| `:depends:` | string | Comma-separated dependency fixtures |
| `:kind:` | string | `resource`, `factory`, or `override_hook` |
| `:return-type:` | string | Return type annotation |
| `:usage:` | string | `auto` or `none` |
| `:params:` | string | Parametrized values |
| `:teardown:` | flag | Mark as yield fixture |
| `:async:` | flag | Mark as async |
| `:deprecated:` | string | Version string |
| `:replacement:` | string | Replacement fixture name |

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-autodoc-pytest-fixtures)

---

## Badge demo

Visual reference for all badge permutations. Use this page to verify badge
rendering across themes, zoom levels, and light/dark modes.

```{py:module} spf_demo_fixtures
```

### Fixture index

```{autofixture-index} spf_demo_fixtures
```

---

### Plain (FIXTURE badge only)

Function scope, resource kind, not autouse. Shows only the green FIXTURE badge.

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_plain
```

---

### Scope badges

#### Session scope

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_session
```

#### Module scope

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_module
```

#### Class scope

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_class
```

---

### Kind badges

#### Factory kind

Return type `type[str]` is auto-detected as factory — no explicit `:kind:` needed.

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_factory
```

#### Override hook

Requires explicit `:kind: override_hook` since it cannot be inferred from type.

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_override_hook
   :kind: override_hook
```

---

### State badges

#### Autouse

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_autouse
```

#### Deprecated

The `deprecated` badge is set via the `:deprecated:` RST option on `py:fixture`.

```{eval-rst}
.. py:fixture:: demo_deprecated
   :deprecated: 1.0
   :replacement: demo_plain
   :return-type: str

   Return a deprecated value. Use :fixture:`demo_plain` instead.
```

---

### Combinations

#### Session + Factory

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_session_factory
```

#### Session + Autouse

```{eval-rst}
.. autofixture:: spf_demo_fixtures.demo_session_autouse
```
