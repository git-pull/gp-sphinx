# sphinx-autodoc-sphinx

```{gp-sphinx-package-meta} sphinx-autodoc-sphinx
```

:::{admonition} Alpha
:class: warning

Rendered output is stable. The Python API, CSS class names, and Sphinx
config value names may change without a major version bump. Pin your
dependency to a specific version range in production.
:::

Experimental Sphinx extension for documenting config values registered by
extension `setup()` hooks. It takes the repetitive part of `conf.py`
reference-writing, records {py:meth}`sphinx:~sphinx.application.Sphinx.add_config_value` calls, and renders them as
live `confval` entries and summary indexes.

Config entries now share the same badge, layout, and type-rendering stack as
the rest of the autodoc family: badges come from `sphinx-ux-badges`,
entry structure comes from `sphinx-ux-autodoc-layout`, and displayed config types
come from `sphinx-autodoc-typehints-gp`.

```console
$ pip install sphinx-autodoc-sphinx
```

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_sphinx"]
```

`sphinx_autodoc_sphinx` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via `app.setup_extension()`.
You do not need to add them separately to your `extensions` list.

## Working usage examples

Render one config value:

````myst
```{eval-rst}
.. autoconfigvalue:: sphinx_fonts.sphinx_font_preload
```
````

Render every config value from an extension module:

````myst
```{eval-rst}
.. autoconfigvalue-index:: sphinx_config_demo
```
````

## Live demos

This page also uses `sphinx-autodoc-docutils` to document the config-doc
directives themselves, so the page demonstrates both config-value output and
directive documentation.

### Index a demo extension's config surface

```{eval-rst}
.. autoconfigvalue-index:: sphinx_config_demo
```

### Render a single demo config value

```{eval-rst}
.. autoconfigvalue:: sphinx_config_single_demo.demo_debug
   :no-index:
```

### Bulk config values demo

Renders all config values from a module at once:

```{eval-rst}
.. autoconfigvalues:: sphinx_config_demo
```

## Directive reference

Generated from `app.add_directive()` registrations in
[`sphinx_autodoc_sphinx/__init__.py`](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-sphinx/src/sphinx_autodoc_sphinx/__init__.py)
via `sphinx-autodoc-docutils` — a meta-loop where the package that
documents config values uses its sibling package to document its own
directives. The summary table indexes every directive; the descriptor
blocks below carry the per-item signature, badge, and options.

```{eval-rst}
.. autodirective-index:: sphinx_autodoc_sphinx

.. autodirectives:: sphinx_autodoc_sphinx
```

## Package reference

```{package-reference} sphinx-autodoc-sphinx
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-sphinx) · [PyPI](https://pypi.org/project/sphinx-autodoc-sphinx/)
