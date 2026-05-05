(sphinx-autodoc-api-style-tutorial)=

# Tutorial

## Working usage examples

No special directives are needed — existing `.. autofunction::`,
`.. autoclass::`, `.. automodule::` directives automatically receive badges.

Render one function:

````myst
```{eval-rst}
.. autofunction:: my_project.api.demo_function
```
````

Render one class and its members:

````myst
```{eval-rst}
.. autoclass:: my_project.api.DemoClass
   :members:
```
````
