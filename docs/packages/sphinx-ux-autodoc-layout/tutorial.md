(sphinx-ux-autodoc-layout-tutorial)=

# Tutorial

## Render a compact API card

Render one compact function:

````myst
```{eval-rst}
.. autofunction:: my_project.api.compact_function
```
````

Render a class with grouped content regions and member entries:

````myst
```{eval-rst}
.. autoclass:: my_project.api.LayoutDemo
   :members:
```
````
