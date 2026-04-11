# sphinx-autodoc-api-style

Sphinx extension that adds type and modifier badges and card-style containers to
standard Python domain autodoc entries (functions, classes, methods, properties,
attributes, data, exceptions).

Internally it is now a thin metadata producer on top of the shared stack:
`sphinx_autodoc_badges` owns badge rendering, `sphinx_autodoc_layout` owns the
`api-*` entry structure, and `sphinx_typehints_gp` is auto-loaded for type
rendering.

## Install

```console
$ pip install sphinx-autodoc-api-style
```

Installing this package also installs `sphinx-autodoc-badges`,
`sphinx-autodoc-layout`, and `sphinx-typehints-gp` as declared dependencies.

## Usage

```python
extensions = ["sphinx_autodoc_api_style"]
```

No special directives are required — existing `.. autofunction::`,
`.. autoclass::`, and related directives receive badges automatically.

`sphinx_autodoc_api_style` automatically registers `sphinx_autodoc_badges`,
`sphinx_autodoc_layout`, and `sphinx_typehints_gp` via `app.setup_extension()`.
You do not need to add them separately to your `extensions` list.

## Documentation

See the [full documentation](https://gp-sphinx.git-pull.com/packages/sphinx-autodoc-api-style/) for
demos and the badge reference.
