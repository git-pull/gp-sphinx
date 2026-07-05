(sphinx-gp-highlighting-how-to)=

# How to

## Highlight a directory tree

Use the `tree` lexer for static directory layouts. It highlights connector glyphs, directory names, filenames, and trailing comments without treating the snippet as a shell transcript:

````markdown
```tree
python_module
├── tmuxp_plugin_my_plugin_module
│   ├── __init__.py
│   └── plugin.py
└── pyproject.toml  # Python project configuration file
```
````

The aliases `directory-tree` and `dir-tree` are equivalent.

## Mark up inline commands and paths

Use explicit roles when the prose knows what the literal is:

```markdown
Run {cmd}`tmuxp freeze my-session`, then edit {path}`~/.config/tmuxp/config.yaml`.
Store plugin modules under {dir}`./plugins/`.
```

The `{cmd}` role uses Sphinx's inline Pygments path with Bash highlighting. The `{path}` and `{dir}` roles keep ordinary inline-code styling and add package-owned classes for path-specific CSS.

## Enable safe automatic inline highlighting

Automatic highlighting of ordinary backtick literals is opt-in:

```python
gp_highlighting_inline_literals = "safe"
gp_highlighting_inline_commands = ["tmuxp", "agentgrep", "unihan-etl"]
```

Safe mode only catches shell prompts, configured command names with arguments, and clear filesystem paths or directories. Literals such as `module_name` and `PackageClass` stay unchanged.

## Use MyST inline language attributes

MyST's `attrs_inline` extension can still request a lexer directly:

```markdown
Inline Python code `value = 1`{l=python}
```

`sphinx-gp-highlighting` leaves literals that already carry a language alone, so explicit MyST language attributes and the package's safe auto-detection can coexist.

