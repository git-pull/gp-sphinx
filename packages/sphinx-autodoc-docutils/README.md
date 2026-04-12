# sphinx-autodoc-docutils

Sphinx extension for turning docutils directives and roles into copyable
reference entries inside your docs site.

The extension keeps its semantic `rst:*` parse path, but the rendered body
regions, badges, and shared type formatting now come from
`sphinx_autodoc_layout`, `sphinx_ux_badges`, and `sphinx_autodoc_typehints_gp`.

## Install

```console
$ pip install sphinx-autodoc-docutils
```

## Usage

```python
extensions = ["sphinx_autodoc_docutils"]
```

Then document directive classes and role callables with `eval-rst`:

````md
```{eval-rst}
.. autodirective:: my_project.docs_ext.MyDirective
```

```{eval-rst}
.. autorole:: my_project.docs_roles.cli_option_role
```
````

For module-wide reference pages:

```rst
.. autodirective-index:: my_project.docs_ext
.. autodirectives:: my_project.docs_ext

.. autorole-index:: my_project.docs_roles
.. autoroles:: my_project.docs_roles
```

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-autodoc-docutils/)
for live demos, directive option rendering, and downstream usage patterns.
