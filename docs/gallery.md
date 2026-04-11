(gallery)=

# Gallery

Every example on this page is **rendered live** from the same extensions and
theme your project gets out of the box.  Nothing is mocked — the output below
is the real autodoc pipeline.

---

## Python API

Badges, type hints, and card layout working together on standard Python domain
directives.

```{py:module} gas_demo_api
```

### Functions

```{eval-rst}
.. autofunction:: gas_demo_api.demo_function
   :noindex:
```

```{eval-rst}
.. autofunction:: gas_demo_api.demo_async_function
   :noindex:
```

```{eval-rst}
.. autofunction:: gas_demo_api.demo_deprecated_function
   :noindex:
```

### Module data

```{eval-rst}
.. autodata:: gas_demo_api.DEMO_CONSTANT
   :noindex:
```

### Exceptions

```{eval-rst}
.. autoexception:: gas_demo_api.DemoError
   :noindex:
```

### Classes

```{eval-rst}
.. autoclass:: gas_demo_api.DemoClass
   :members:
   :undoc-members:
   :noindex:
```

### Abstract base classes

```{eval-rst}
.. autoclass:: gas_demo_api.DemoAbstractBase
   :members:
   :noindex:
```

---

## Layout regions and parameter folding

Large parameter lists fold automatically.  The class below has 13 parameters
(above the default threshold of 10), so its field list is collapsed into a
disclosure widget.

```{py:module} gal_demo_api
```

### Class with members (regions + fold)

```{eval-rst}
.. autoclass:: gal_demo_api.LayoutDemo
   :members:
   :noindex:
```

### Small function (no fold)

```{eval-rst}
.. autofunction:: gal_demo_api.compact_function
   :noindex:
```

---

## Badge palette

The full badge system — types, modifiers, sizes, and variants — rendered by
the real `build_badge` / `build_badge_group` / `build_toolbar` API:

```{sab-badge-demo}
```

---

## FastMCP tool cards

Tool documentation with safety badges and parameter tables.

```{eval-rst}
.. fastmcp-tool:: fastmcp_demo_tools.list_sessions
   :noindex:

.. fastmcp-tool:: fastmcp_demo_tools.create_session
   :noindex:

.. fastmcp-tool:: fastmcp_demo_tools.delete_session
   :noindex:
```

### Parameter table

```{eval-rst}
.. fastmcp-tool-input:: fastmcp_demo_tools.create_session
   :noindex:
```

### Tool summary

```{eval-rst}
.. fastmcp-toolsummary::
   :noindex:
```

---

## pytest fixtures

```{py:module} spf_demo_fixtures
```

### Fixture index

```{autofixture-index} spf_demo_fixtures
```

### Fixture reference

```{eval-rst}
.. autofixtures:: spf_demo_fixtures
   :no-index:
```

---

## Sphinx config values

```{eval-rst}
.. autoconfigvalue-index:: sphinx_config_demo
   :noindex:
```

```{eval-rst}
.. autoconfigvalues:: sphinx_config_demo
   :noindex:
```

---

## docutils directives and roles

### Directives

```{eval-rst}
.. autodirective-index:: docutils_demo
   :noindex:
```

```{eval-rst}
.. autodirective:: docutils_demo.DemoBadgeDirective
   :no-index:
```

### Roles

```{eval-rst}
.. autorole-index:: docutils_demo
   :noindex:
```

```{eval-rst}
.. autorole:: docutils_demo.demo_badge_role
   :no-index:
```
