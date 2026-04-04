# sphinx-autodoc-docutils

{bdg-warning-line}`Alpha` {bdg-primary}`extension`

Experimental Sphinx extension for documenting docutils directives and role
callables as reference material. The extension does not invent a new domain;
instead it introspects Python modules and renders copyable `rst:directive` and
`rst:role` reference blocks from the live objects.

```console
$ pip install sphinx-autodoc-docutils
```

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_docutils"]
```

## Working usage examples

Use a single-object directive when you want one rendered reference entry:

````md
```{eval-rst}
.. autodirective:: my_project.docs_ext.MyDirective
```

```{eval-rst}
.. autorole:: my_project.docs_roles.cli_option_role
```
````

Use the bulk directives to render a full module reference plus an index:

````md
```{eval-rst}
.. autodirective-index:: my_project.docs_ext
```

```{eval-rst}
.. autodirectives:: my_project.docs_ext
```

```{eval-rst}
.. autorole-index:: my_project.docs_roles
```

```{eval-rst}
.. autoroles:: my_project.docs_roles
```
````

## Live demos

This page intentionally uses directive and role autodoc to document the
documentation helpers themselves. If that feels a little recursive, that is the
point: roles and directives should be documentable the same way fixtures are.

### Index demo directives

```{eval-rst}
.. autodirective-index:: docutils_demo
```

### Document one demo directive

```{eval-rst}
.. autodirective:: docutils_demo.DemoBadgeDirective
   :no-index:
```

### Index demo roles

```{eval-rst}
.. autorole-index:: docutils_demo
```

### Document one demo role

```{eval-rst}
.. autorole:: docutils_demo.demo_badge_role
   :no-index:
```

The extension itself registers directives, not docutils roles or Sphinx config
values. The generated package reference below lists its registered surface from
the live `setup()` calls.

```{package-reference} sphinx-autodoc-docutils
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-autodoc-docutils)
