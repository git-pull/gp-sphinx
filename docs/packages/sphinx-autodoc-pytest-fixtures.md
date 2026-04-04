# sphinx-autodoc-pytest-fixtures

Sphinx extension that documents pytest fixtures as first-class domain objects
with scope badges, dependency tracking, and auto-generated usage snippets.

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
