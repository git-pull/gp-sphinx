(sphinx-autodoc-api-style-tutorial)=

# Tutorial

## Add badges to existing autodoc

Start with the autodoc directives your API page already uses. Existing
{rst:dir}`sphinx:autofunction`, {rst:dir}`sphinx:autoclass`, and
{rst:dir}`sphinx:automodule` entries automatically receive badges when the
extension is loaded.

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
