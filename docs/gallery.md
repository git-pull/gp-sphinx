(gallery)=

# Gallery

Every example on this page is **rendered live** from the same extensions and
theme your project gets out of the box.  Nothing is mocked — the output below
is the real autodoc pipeline.

---

## Python API

Badges, type hints, and card layout working together on standard Python domain
directives.

```{py:module} gp_demo_api
:no-index:
```

### Functions

```{eval-rst}
.. autofunction:: gp_demo_api.demo_function
   :noindex:
```

```{eval-rst}
.. autofunction:: gp_demo_api.demo_async_function
   :noindex:
```

```{eval-rst}
.. autofunction:: gp_demo_api.demo_deprecated_function
   :noindex:
```

### Module data

```{eval-rst}
.. autodata:: gp_demo_api.DEMO_CONSTANT
   :noindex:
```

### Exceptions

```{eval-rst}
.. autoexception:: gp_demo_api.DemoError
   :noindex:
```

### Classes

```{eval-rst}
.. autoclass:: gp_demo_api.DemoClass
   :members:
   :undoc-members:
   :noindex:
```

### Abstract base classes

```{eval-rst}
.. autoclass:: gp_demo_api.DemoAbstractBase
   :members:
   :noindex:
```

---

## Layout regions and parameter folding

Large parameter lists fold automatically.  The class below has 13 parameters
(above the default threshold of 10), so its field list is collapsed into a
disclosure widget.

```{py:module} api_demo_layout
:no-index:
```

### Class with members (regions + fold)

```{eval-rst}
.. autoclass:: api_demo_layout.LayoutDemo
   :members:
   :noindex:
```

### Small function (no fold)

```{eval-rst}
.. autofunction:: api_demo_layout.compact_function
   :noindex:
```

---

## Badge palette

The full badge system — types, modifiers, sizes, and variants — rendered by
the real `build_badge` / `build_badge_group` / `build_toolbar` API:

```{gp-sphinx-badge-demo}
```

---

## FastMCP tool cards

Tool documentation with safety badges and parameter tables.

```{eval-rst}
.. fastmcp-tool:: fastmcp_demo_tools.list_sessions
   :no-index:

.. fastmcp-tool:: fastmcp_demo_tools.create_session
   :no-index:

.. fastmcp-tool:: fastmcp_demo_tools.delete_session
   :no-index:
```

### Parameter table

```{eval-rst}
.. fastmcp-tool-input:: fastmcp_demo_tools.create_session
```

### Tool summary

```{eval-rst}
.. fastmcp-tool-summary::
```

---

## pytest fixtures

```{py:module} spf_demo_fixtures
:no-index:
```

### Fixture reference

```{eval-rst}
.. autofixtures:: spf_demo_fixtures
   :no-index:
```

---

## Sphinx config values

```{eval-rst}
.. autoconfigvalues:: sphinx_config_demo
   :no-index:
```

---

## docutils directives and roles

### Directives

```{eval-rst}
.. autodirective:: docutils_demo.DemoBadgeDirective
   :no-index:
```

### Roles

```{eval-rst}
.. autorole:: docutils_demo.demo_badge_role
   :no-index:
```
