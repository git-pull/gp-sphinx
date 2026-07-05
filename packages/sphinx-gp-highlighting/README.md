# sphinx-gp-highlighting

Reusable Sphinx highlighting helpers for git-pull documentation. The package
ships Pygments lexers for documentation-oriented blocks and Sphinx inline
literal helpers for commands, paths, and directories.

## Install

```console
$ pip install sphinx-gp-highlighting
```

## Usage

Enable the extension in `conf.py`:

```python
extensions = ["sphinx_gp_highlighting"]
```

Use the `tree` lexer for directory layouts:

````markdown
```tree
python_module
├── package
│   └── __init__.py
└── pyproject.toml
```
````
