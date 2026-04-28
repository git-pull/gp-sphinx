(gp-sphinx-astro-builder-how-to)=

# How to

:::{admonition} Pre-alpha
:class: warning

This package is the in-progress Sphinx builder for the planned Astro
documentation platform (see `notes/plans/astro.md` in the workspace
root). Public API is not yet stable; nothing here is wired into a
shipped site.
:::

## Install

The builder ships from the gp-sphinx workspace alongside the other
`sphinx-*` packages. From a consumer project:

```toml
# pyproject.toml
[project]
dependencies = [
    "gp-sphinx-astro-builder",
]
```

## Register the extension

Add the builder to `extensions` in `conf.py`:

```python
# conf.py
extensions = [
    "gp_sphinx_astro_builder",
    "sphinx.ext.autodoc",
    # ...
]
```

## Build the JSON output

Invoke `sphinx-build` with the `astro` builder name. The output goes
into your Astro site's content collection root:

```console
$ uv run sphinx-build -b astro docs/ astro/apps/your-site/src/
```

The builder walks each doctree, validates every node against the
Pydantic models declared in `models.py`, and writes one JSON file per
source document plus the cross-doc artifacts (`symbols.json`,
`xref-index.json`, `objects.inv`, `schemas/doctree.schema.json`,
`src/content.config.ts`).

## Skip vite when building astro

If your project also uses `sphinx-vite-builder`, the astro builder is
already on its skip list by default — no theme assets get rebuilt
when emitting JSON. Verify with:

```python
# conf.py
sphinx_vite_builder_skip_builders = ["astro"]  # default
```
