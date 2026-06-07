# sphinx-autodoc-sphinx

Sphinx extension for documenting the objects extensions register with
Sphinx — config values from `app.add_config_value()`, builders from
`app.add_builder()`, and domains from `app.add_domain()` — as copyable
reference entries.

Rendered entries use the shared stack: `sphinx_ux_autodoc_layout` owns the
visible `api-*` structure, `sphinx_ux_badges` owns badge output, and
`sphinx_autodoc_typehints_gp` is auto-loaded so displayed config types follow the same
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
.. autoconfigvalues:: sphinx_fonts
```

Builders and domains follow the same single + bulk pattern:

```rst
.. autobuilder:: my_project.builders.ZipBuilder

.. autodomains:: my_project
```

Builder and domain entries register targets in a `sphinxext` Sphinx
domain, so prose can cross-reference them with roles like
`` :sphinxext:builder:`ZipBuilder` ``.

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-autodoc-sphinx/)
for live demos, generated `confval` entries, and downstream usage patterns.
