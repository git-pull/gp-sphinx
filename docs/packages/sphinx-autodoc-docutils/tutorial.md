(sphinx-autodoc-docutils-tutorial)=

# Tutorial

## Working usage examples

Use a single-object directive when you want one rendered reference entry:

````myst
```{eval-rst}
.. autodirective:: my_project.docs_ext.MyDirective
```
````

````myst
```{eval-rst}
.. autorole:: my_project.docs_roles.cli_option_role
```
````

Use the bulk directives to render every directive or role a module
registers:

````myst
```{eval-rst}
.. autodirectives:: my_project.docs_ext
```
````

````myst
```{eval-rst}
.. autoroles:: my_project.docs_roles
```
````
