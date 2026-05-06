(sphinx-autodoc-docutils-how-to)=

# How to

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_docutils"]
```

`sphinx_autodoc_docutils` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via `app.setup_extension()`.
You do not need to add them separately to your `extensions` list.
