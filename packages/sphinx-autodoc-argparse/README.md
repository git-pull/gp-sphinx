# sphinx-autodoc-argparse

Modern Sphinx extension for documenting argparse-based CLI tools.

A modernized replacement for `sphinx-argparse` that:
- Works with Sphinx 8.x and 9.x (no `autodoc.mock` dependency)
- Fixes long-standing issues (TOC pollution, heading levels)
- Provides configurable output (rubrics vs sections, flattened subcommands)
- Includes Pygments lexers for argparse help output and CLI usage blocks
- Supports extensibility via renderer classes

## Install

```console
$ pip install sphinx-autodoc-argparse
```

## Usage

In your `docs/conf.py`:

```python
extensions = ["sphinx_autodoc_argparse"]
```

Then use the `.. argparse::` directive:

```rst
.. argparse::
   :module: myapp.cli
   :func: create_parser
   :prog: myapp
```
