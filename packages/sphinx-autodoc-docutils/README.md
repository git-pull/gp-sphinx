# sphinx-autodoc-docutils

Sphinx extension for turning docutils components — directives, roles,
transforms, readers, parsers, writers, custom nodes, and translators —
into copyable reference entries inside your docs site.

The extension keeps its semantic `rst:*` parse path, but the rendered body
regions, badges, and shared type formatting now come from
`sphinx_ux_autodoc_layout`, `sphinx_ux_badges`, and `sphinx_autodoc_typehints_gp`.

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

Every docutils extension point gets the same single + bulk pair:

```rst
.. autotransform:: my_project.transforms.SanitizeTransform

.. autoreader:: my_project.readers.ArticleReader

.. autoparser:: my_project.parsers.LineParser

.. autowriter:: my_project.writers.PlainWriter

.. autonode:: my_project.nodes.icon

.. autotranslator:: my_project.writers.PlainTranslator
```

For module-wide reference pages:

```rst
.. autodirectives:: my_project.docs_ext

.. autoroles:: my_project.docs_roles

.. autotransforms:: my_project
```

Component entries register targets in a `docutils` Sphinx domain, so
prose can cross-reference them with roles like
`` :docutils:transform:`SanitizeTransform` ``.

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-autodoc-docutils/)
for live demos, directive option rendering, and downstream usage patterns.
