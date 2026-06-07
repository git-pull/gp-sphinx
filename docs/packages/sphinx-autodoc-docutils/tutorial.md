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

The same single/bulk pattern covers every docutils extension point —
transforms, readers, parsers, writers, custom nodes, and translators:

````myst
```{eval-rst}
.. autotransform:: my_project.transforms.SanitizeTransform
```
````

````myst
```{eval-rst}
.. autonodes:: my_project
```
````

Bulk forms accept either an extension package (its `setup()` is
replayed so `app.add_transform()` / `app.add_node()` registrations
surface with their real metadata) or a plain module (scanned for
subclasses of the matching docutils base class).
