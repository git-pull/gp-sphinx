(sphinx-autodoc-sphinx-how-to)=

# How to

Use this extension when a Sphinx extension needs generated reference pages
for builders, domains, and configuration values that readers can link from
prose.

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_sphinx"]
```

`sphinx_autodoc_sphinx` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via
{py:meth}`~sphinx.application.Sphinx.setup_extension`. You do not need to add
them separately to your `extensions` list.

## Cross-reference documented components

Builder and domain entries register targets in the `sphinxext`
domain, so prose anywhere in the project can link to them:

```md
Run {sphinxext:builder}`ZipBuilder` to bundle the site.
```

The entry being linked must be rendered **without** `:no-index:` —
no-index entries create no cross-reference target. Use the
fully-qualified dotted path when two components share a bare class
name.
