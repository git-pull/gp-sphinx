# sphinx-autodoc-argparse

```{gp-sphinx-package-meta} sphinx-autodoc-argparse
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

## Cross-reference roles

Every `.. argparse::` block populates a dedicated `argparse` domain
alongside the existing `std:cmdoption` entries.  Use these roles to
link to programs, options, subcommands, and positional arguments
declared anywhere in the project:

| Role | Resolves to | Example |
|------|-------------|---------|
| `:argparse:program:` | A top-level program | `` :argparse:program:`myapp` `` |
| `:argparse:option:` | An optional flag, scoped by program | `` :argparse:option:`myapp --verbose` `` or `` :argparse:option:`myapp sync --force` `` |
| `:argparse:subcommand:` | A subcommand under a parent program | `` :argparse:subcommand:`myapp sync` `` |
| `:argparse:positional:` | A positional argument, scoped by program | `` :argparse:positional:`myapp FILE` `` |

Whitespace-joined targets (`myapp sync --force`) are split on the final
space to match the stored `(program, name)` tuple.  Bare forms
(`--verbose`) also resolve when only one registration matches, though
the fully-qualified form is preferred for multi-program sites.

### Auto-generated indices

Two domain indices are built into every project that loads the
extension:

- `argparse-programsindex` — alphabetised list of every registered
  program; link via `` :ref:`argparse-programsindex` ``.
- `argparse-optionsindex` — options grouped by program, alphabetised
  within each group; link via `` :ref:`argparse-optionsindex` ``.

### Intersphinx compatibility

The classic `:option:` / `std:cmdoption` emission is preserved — both
roles resolve and both appear in `objects.inv`.  Downstream consumers
linking via intersphinx continue to work; new authoring inside
projects using this extension can prefer the `:argparse:*` namespace
for program-scoped clarity.

## Configuration values

### Base extension

```{eval-rst}
.. autoconfigvalues:: sphinx_autodoc_argparse
```

### Exemplar layer

```{eval-rst}
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
