(sphinx-autodoc-argparse-tutorial)=

# Tutorial

## Document your first parser

Start by loading the base parser extension and the exemplar layer. The exemplar
layer gives you the cleaner directive and roles used across the gp-sphinx docs:

```python
extensions = [
    "sphinx_autodoc_argparse",
    "sphinx_autodoc_argparse.exemplar",
]

argparse_examples_section_title = "Examples"
argparse_reorder_usage_before_examples = True
```
