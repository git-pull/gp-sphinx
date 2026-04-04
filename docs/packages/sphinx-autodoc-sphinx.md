# sphinx-autodoc-sphinx

{bdg-warning-line}`Alpha` {bdg-primary}`extension`

Experimental Sphinx extension for documenting config values registered by
extension `setup()` hooks. It takes the repetitive part of `conf.py`
reference-writing, records `app.add_config_value()` calls, and renders them as
live `confval` entries and summary indexes.

```console
$ pip install sphinx-autodoc-sphinx
```

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_sphinx"]
```

## Working usage examples

Render one config value:

````md
```{eval-rst}
.. autoconfigvalue:: sphinx_fonts.sphinx_font_preload
```
````

Render every config value from an extension module:

````md
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

### Document the extension's own directive helper

```{eval-rst}
.. autodirective:: sphinx_autodoc_sphinx._directives.AutoconfigvalueDirective
   :no-index:
```

The extension itself registers documentation directives rather than new roles
or config values. The generated package reference below lists its registered
surface from the live `setup()` calls.

```{package-reference} sphinx-autodoc-sphinx
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-sphinx)
