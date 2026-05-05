(sphinx-ux-autodoc-layout-examples)=

# Examples

## Live demos

```{py:module} api_demo_layout
```

### Class with members (regions + fold)

```{eval-rst}
.. autoclass:: api_demo_layout.LayoutDemo
   :members:
```

The class above renders with:

- **narrative** region (class docstring)
- **fields** region with fold (13 parameters > threshold of 10)
- **members** region (connect, execute, close methods)

### Small function (no fold)

```{eval-rst}
.. autofunction:: api_demo_layout.compact_function
```
