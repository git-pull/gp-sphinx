# sphinx-argparse-neo

{bdg-success-line}`Beta` {bdg-primary}`extension`

Modern Sphinx extension for documenting `argparse` CLIs. The base package
registers the `argparse` directive plus renderer config values; the
`sphinx_argparse_neo.exemplar` layer adds example extraction, lexers, and CLI
inline roles.

```console
$ pip install sphinx-argparse-neo
```

## Downstream `conf.py`

```python
extensions = [
    "sphinx_argparse_neo",
    "sphinx_argparse_neo.exemplar",
]

argparse_examples_section_title = "Examples"
argparse_reorder_usage_before_examples = True
```

## Live directive demos

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
.. autoconfigvalue-index:: sphinx_argparse_neo
.. autoconfigvalues:: sphinx_argparse_neo
```

### Exemplar layer

```{eval-rst}
.. autoconfigvalue-index:: sphinx_argparse_neo.exemplar
.. autoconfigvalues:: sphinx_argparse_neo.exemplar
```

## Registered directives and roles

### Base `argparse` directive

```{eval-rst}
.. autodirective:: sphinx_argparse_neo.directive.ArgparseDirective
   :no-index:
```

### Exemplar override

```{eval-rst}
.. autodirective:: sphinx_argparse_neo.exemplar.CleanArgParseDirective
```

### CLI role callables

```{eval-rst}
.. autorole-index:: sphinx_argparse_neo.roles
.. autoroles:: sphinx_argparse_neo.roles
```

## Downstream usage snippets

Use native MyST directives in Markdown:

````md
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

```{package-reference} sphinx-argparse-neo
```

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/main/packages/sphinx-argparse-neo)
