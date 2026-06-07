(sphinx-autodoc-docutils-examples)=

# Examples

## Live demos

This page intentionally uses directive and role autodoc to document the
documentation helpers themselves. If that feels a little recursive, that is the
point: roles and directives should be documentable the same way fixtures are.

### Document one demo directive

```{eval-rst}
.. autodirective:: docutils_demo.DemoBadgeDirective
   :no-index:
```

### Document one demo role

```{eval-rst}
.. autorole:: docutils_demo.demo_badge_role
   :no-index:
```

### Bulk directives demo

Renders all directive classes in a module at once:

```{eval-rst}
.. autodirectives:: docutils_demo
   :no-index:
```

### Bulk roles demo

Renders all role callables in a module at once:

```{eval-rst}
.. autoroles:: docutils_demo
   :no-index:
```

### Document one demo transform

The single form imports the class directly and surfaces its
`default_priority` and registration phase:

```{eval-rst}
.. autotransform:: docutils_demo_components.DemoReorderTransform
```

### Bulk transforms demo

Renders every transform a module registers via `setup()` — here the
demo module's `app.add_transform()` call:

```{eval-rst}
.. autotransforms:: docutils_demo_components
   :no-index:
```

### Document one demo reader

Readers have no Sphinx registration call, so the single form imports
the class and surfaces its formats, config section, and transform set:

```{eval-rst}
.. autoreader:: docutils_demo_components.DemoArticleReader
```

### Bulk readers demo

Renders every reader class a module defines:

```{eval-rst}
.. autoreaders:: docutils_demo_components
   :no-index:
```

### Document one demo parser

Parsers surface their alias tuple and, when the module's `setup()`
calls `app.add_source_parser()`, the Sphinx registration:

```{eval-rst}
.. autoparser:: docutils_demo_components.DemoLineParser
```

### Bulk parsers demo

```{eval-rst}
.. autoparsers:: docutils_demo_components
   :no-index:
```

### Document one demo writer

Writers surface their output formats and translator class — resolved
defensively, since writers commonly assign `translator_class` inside
`__init__`:

```{eval-rst}
.. autowriter:: docutils_demo_components.DemoPlainWriter
```

### Bulk writers demo

```{eval-rst}
.. autowriters:: docutils_demo_components
   :no-index:
```

### Document one demo node

Custom node classes surface their base classes, docutils element
categories, and the builders their visit/depart handlers were
registered for via `app.add_node()`:

```{eval-rst}
.. autonode:: docutils_demo_components.demo_marker
```

### Bulk nodes demo

```{eval-rst}
.. autonodes:: docutils_demo_components
   :no-index:
```

### Cross-referencing components

Component entries register targets in the `docutils` domain, so prose
can link to them: {docutils:transform}`DemoReorderTransform` resolves
to the entry above, and {docutils:transform}`docutils_demo_components.DemoReorderTransform`
spells out the full path. Every component type has a matching role —
{docutils:reader}`DemoArticleReader` links the reader entry the same
way.

The extension itself registers directives, not docutils roles or Sphinx config
values. The generated package reference below lists its registered surface from
the live `setup()` calls.

```{package-reference} sphinx-autodoc-docutils
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-docutils) · [PyPI](https://pypi.org/project/sphinx-autodoc-docutils/)
