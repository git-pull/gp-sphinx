(sphinx-autodoc-sphinx-how-to)=

# How to

## Downstream `conf.py`

```python
extensions = ["sphinx_autodoc_sphinx"]
```

`sphinx_autodoc_sphinx` automatically registers `sphinx_ux_badges`,
`sphinx_ux_autodoc_layout`, and `sphinx_autodoc_typehints_gp` via `app.setup_extension()`.
You do not need to add them separately to your `extensions` list.
