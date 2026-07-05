(sphinx-autodoc-argparse-how-to)=

# How to

## Registered directives and roles

### Base `argparse` directive

```{eval-rst}
.. autodirective:: sphinx_autodoc_argparse.directive.ArgparseDirective
   :no-index:
```

### Exemplar override

```{eval-rst}
.. autodirective:: sphinx_autodoc_argparse.exemplar.CleanArgParseDirective
```

### CLI role callables

```{eval-rst}
.. autoroles:: sphinx_autodoc_argparse.roles
```

## Downstream usage snippets

Use native MyST directives in Markdown:

````myst
```{argparse}
:module: myproject.cli
:func: create_parser
:prog: myproject
```
````

Or reStructuredText:

```rst
.. argparse::
   :module: myproject.cli
   :func: create_parser
   :prog: myproject
```

```{package-reference} sphinx-autodoc-argparse
```
