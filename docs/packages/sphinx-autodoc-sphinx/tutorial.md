(sphinx-autodoc-sphinx-tutorial)=

# Tutorial

## Document a Sphinx extension surface

Render one config value:

````myst
```{eval-rst}
.. autoconfigvalue:: sphinx_fonts.sphinx_font_preload
```
````

Render every config value from an extension module:

````myst
```{eval-rst}
.. autoconfigvalues:: sphinx_config_demo
```
````

Exclude specific config values (useful when two extensions register
the same value and Sphinx warns on the duplicate ``confval``):

````myst
```{eval-rst}
.. autoconfigvalues:: sphinx_gp_llms
   :exclude: site_url
```
````

Builders and domains follow the same single/bulk pattern:

````myst
```{eval-rst}
.. autobuilder:: my_project.builders.ZipBuilder
```
````

````myst
```{eval-rst}
.. autodomains:: my_project
```
````

Bulk forms accept either an extension package (its `setup()` is
replayed so {py:meth}`~sphinx.application.Sphinx.add_builder` and
{py:meth}`~sphinx.application.Sphinx.add_domain` registrations surface) or a
plain module (scanned for `Builder` / `Domain` subclasses).
