# sphinx-autodoc-sphinx

Sphinx extension for documenting config values registered by
`app.add_config_value()` as copyable `conf.py` reference entries.

Rendered entries use the shared stack: `sphinx_autodoc_layout` owns the
visible `api-*` structure, `sphinx_autodoc_badges` owns badge output, and
`sphinx_typehints_gp` is auto-loaded so displayed config types follow the same
annotation rules as the rest of the autodoc family.

## Install

```console
$ pip install sphinx-autodoc-sphinx
```

## Usage

```python
extensions = ["sphinx_autodoc_sphinx"]
```

Then document one config value:

````md
```{eval-rst}
.. autoconfigvalue:: sphinx_fonts.sphinx_font_preload
```
````

Or generate a full reference section for an extension module:

```rst
.. autoconfigvalue-index:: sphinx_fonts
.. autoconfigvalues:: sphinx_fonts

.. autoconfigvalue-page:: sphinx_argparse_neo.exemplar
```

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-autodoc-sphinx/)
for live demos, generated `confval` entries, and downstream usage patterns.
