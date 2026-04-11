# sphinx-autodoc-argparse

```{sab-package-meta} sphinx-autodoc-argparse
```

Modern Sphinx extension for documenting `argparse` CLIs. The base package
registers the `argparse` directive plus renderer config values; the
`sphinx_autodoc_argparse.exemplar` layer adds example extraction, lexers, and CLI
inline roles.

```console
$ pip install sphinx-autodoc-argparse
```

## Working usage examples

```python
extensions = [
    "sphinx_autodoc_argparse",
    "sphinx_autodoc_argparse.exemplar",
]

argparse_examples_section_title = "Examples"
argparse_reorder_usage_before_examples = True
```

## Live demos

### Base parser rendering

```{argparse}
:module: demo_cli
:func: create_parser
:prog: myapp
```

### Subcommand rendering

Drill into a single subcommand with `:path:`:

```{argparse}
:module: demo_cli
:func: create_parser
:path: mysubcommand
:prog: myapp
```

### Inline roles

The exemplar layer also registers live inline roles for CLI prose:
{cli-command}`myapp`, {cli-option}`--verbose`, {cli-choice}`json`,
{cli-metavar}`DIR`, and {cli-default}`text`.

## Configuration values

### Base extension

```{eval-rst}
.. autoconfigvalue-index:: sphinx_autodoc_argparse
.. autoconfigvalues:: sphinx_autodoc_argparse
```

### Exemplar layer

```{eval-rst}
.. autoconfigvalue-index:: sphinx_autodoc_argparse.exemplar
.. autoconfigvalues:: sphinx_autodoc_argparse.exemplar
```

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
.. autorole-index:: sphinx_autodoc_argparse.roles
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

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-autodoc-argparse) · [PyPI](https://pypi.org/project/sphinx-autodoc-argparse/)
