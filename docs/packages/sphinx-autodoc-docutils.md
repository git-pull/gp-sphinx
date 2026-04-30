# sphinx-autodoc-docutils

```{gp-sphinx-package-meta} sphinx-autodoc-docutils
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API, CSS class names, and Sphinx
config value names may change without a major version bump. Pin your
dependency to a specific version range in production.
:::

Experimental Sphinx extension for documenting docutils directives and role
callables as reference material. The extension does not invent a new domain;
instead it introspects Python modules and renders copyable `rst:directive` and
`rst:role` reference blocks from the live objects.

Those rendered entries now share the same badge, layout, and type-display
stack as the rest of the autodoc packages even though the package still keeps
its semantic `rst:*` generation path.

```console
$ pip install sphinx-autodoc-docutils
```

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_docutils"]
```

`sphinx_autodoc_docutils` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via `app.setup_extension()`.
You do not need to add them separately to your `extensions` list.

## Working usage examples

Use a single-object directive when you want one rendered reference entry:

````myst
```{eval-rst}
.. autodirective:: my_project.docs_ext.MyDirective
```
````

````myst
```{eval-rst}
.. autorole:: my_project.docs_roles.cli_option_role
```
````

Use the bulk directives to render every directive or role a module
registers:

````myst
```{eval-rst}
.. autodirectives:: my_project.docs_ext
```
````

````myst
```{eval-rst}
.. autoroles:: my_project.docs_roles
```
````

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

The extension itself registers directives, not docutils roles or Sphinx config
values. The generated package reference below lists its registered surface from
the live `setup()` calls.

```{package-reference} sphinx-autodoc-docutils
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-docutils) · [PyPI](https://pypi.org/project/sphinx-autodoc-docutils/)
