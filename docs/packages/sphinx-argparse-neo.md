# sphinx-argparse-neo

{bdg-success-line}`Beta` {bdg-primary}`extension`

Sphinx extension for documenting argparse-based CLI tools. Renders argument
parsers as structured documentation with usage sections, argument groups,
subcommands, and optional epilog-to-section transformation.

```console
$ pip install sphinx-argparse-neo
```

Or as a gp-sphinx optional extra:

```console
$ pip install gp-sphinx[argparse]
```

## Usage

Add to your Sphinx extensions:

```python
extensions = ["sphinx_argparse_neo"]
```

Then use the `argparse` directive:

```rst
.. argparse::
   :module: myapp.cli
   :func: create_parser
   :prog: myapp
```

## Bundled Pygments lexers

The extension registers custom lexers for syntax-highlighted CLI output:

- `argparse` — general argparse output
- `argparse-usage` — usage line formatting
- `argparse-help` — help text formatting

The `argparse_exemplar` sub-extension adds `cli-usage` and CLI inline roles
for richer documentation.

## Renderer

Output is customizable via the renderer system — sections vs rubrics,
subcommand flattening, and configurable heading levels.

[Source on GitHub](https://github.com/git-pull/gp-sphinx/tree/master/packages/sphinx-argparse-neo)
