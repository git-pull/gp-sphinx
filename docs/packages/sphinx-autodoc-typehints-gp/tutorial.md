(sphinx-autodoc-typehints-gp-tutorial)=

# Tutorial

## Add static type rendering

Add `sphinx_autodoc_typehints_gp` to your `extensions` list in `conf.py`:

```python
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_autodoc_typehints_gp",
]

# Required: makes autodoc insert type annotations into parameter descriptions.
# Without this, the type cross-referencing pipeline fires but has nothing to attach to.
autodoc_typehints = "description"
```
